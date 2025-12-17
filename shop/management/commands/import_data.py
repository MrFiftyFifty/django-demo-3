from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from shop.models import Category, Manufacturer, Supplier, Product, UserProfile, Order, OrderItem, PickupPoint
import openpyxl
from datetime import datetime
from decimal import Decimal


class Command(BaseCommand):
    help = 'Import data from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to Excel file')

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        wb = openpyxl.load_workbook(excel_file)

        self.stdout.write('Starting data import...')

        self.import_pickup_points(wb)
        self.import_products(wb)
        self.import_users(wb)
        self.import_orders(wb)

        self.stdout.write(self.style.SUCCESS('Data import completed successfully!'))

    def import_pickup_points(self, wb):
        sheet = wb['Pickup point']
        self.stdout.write('Importing pickup points...')
        
        for row in list(sheet.values)[1:]:
            if row[0]:
                PickupPoint.objects.get_or_create(address=row[0])
        
        self.stdout.write(f'Imported {PickupPoint.objects.count()} pickup points')

    def import_products(self, wb):
        sheet = wb['Product']
        self.stdout.write('Importing products...')
        
        for row in list(sheet.values)[1:]:
            if not row[0]:
                continue
            
            category, _ = Category.objects.get_or_create(name=row[6])
            manufacturer, _ = Manufacturer.objects.get_or_create(name=row[5])
            supplier, _ = Supplier.objects.get_or_create(name=row[4])
            
            Product.objects.get_or_create(
                article=row[0],
                defaults={
                    'name': row[1],
                    'unit': row[2],
                    'price': Decimal(str(row[3])),
                    'supplier': supplier,
                    'manufacturer': manufacturer,
                    'category': category,
                    'discount': row[7] or 0,
                    'stock_quantity': row[8] or 0,
                    'description': row[9] or '',
                }
            )
        
        self.stdout.write(f'Imported {Product.objects.count()} products')

    def import_users(self, wb):
        sheet = wb['User']
        self.stdout.write('Importing users...')
        
        role_mapping = {
            'Администратор': 'admin',
            'Менеджер': 'manager',
            'Клиент': 'client',
            'Гость': 'guest',
        }
        
        for row in list(sheet.values)[1:]:
            if not row[2]:
                continue
            
            username = row[2].replace('@kancmail.com', '')
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': row[2],
                    'first_name': row[1].split()[1] if len(row[1].split()) > 1 else '',
                    'last_name': row[1].split()[0] if row[1].split() else '',
                }
            )
            
            if created:
                user.set_password(row[3])
                user.save()
            
            role = role_mapping.get(row[0], 'client')
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role': role,
                    'full_name': row[1],
                }
            )
        
        self.stdout.write(f'Imported {User.objects.count()} users')

    def import_orders(self, wb):
        sheet = wb['Order']
        self.stdout.write('Importing orders...')
        
        status_mapping = {
            'Завершен': 'completed',
            'Новый': 'new',
            'В обработке': 'in_progress',
            'Отменен': 'cancelled',
        }
        
        for row in list(sheet.values)[1:]:
            if not row[0]:
                continue
            
            full_name = row[5]
            user = User.objects.filter(profile__full_name=full_name).first()
            
            if not user:
                username = full_name.lower().replace(' ', '_')[:30]
                user = User.objects.create_user(username=username)
                UserProfile.objects.create(user=user, full_name=full_name, role='client')
            
            pickup_points = PickupPoint.objects.all()
            pickup_point = pickup_points[row[4] - 1] if row[4] <= len(pickup_points) else pickup_points[0]
            
            order, created = Order.objects.get_or_create(
                user=user,
                order_date=row[2],
                defaults={
                    'delivery_date': row[3].date() if hasattr(row[3], 'date') else row[3],
                    'pickup_point': pickup_point,
                    'pickup_code': str(row[6]),
                    'status': status_mapping.get(row[7], 'new'),
                }
            )
            
            if created and row[1]:
                items = row[1].split(', ')
                total = Decimal('0')
                
                i = 0
                while i < len(items):
                    article = items[i]
                    quantity = int(items[i + 1]) if i + 1 < len(items) else 1
                    
                    try:
                        product = Product.objects.get(article=article)
                        price = product.discounted_price
                        
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            price_at_purchase=price
                        )
                        
                        total += price * quantity
                    except Product.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'Product {article} not found'))
                    
                    i += 2
                
                order.total_amount = total
                order.save()
        
        self.stdout.write(f'Imported {Order.objects.count()} orders')
