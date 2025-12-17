from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from shop.models import Category, Manufacturer, Supplier, Product, UserProfile, Order, OrderItem, PickupPoint
import openpyxl
from decimal import Decimal
from django.utils import timezone


class Command(BaseCommand):
    help = 'Import data from Excel'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str)

    def handle(self, *args, **options):
        wb = openpyxl.load_workbook(options['excel_file'])
        
        self.import_pickup_points(wb)
        self.import_products(wb)
        self.import_users(wb)
        self.import_orders(wb)
        
        self.stdout.write(self.style.SUCCESS('Import completed'))

    def import_pickup_points(self, wb):
        sheet = wb['Pickup point']
        for row in list(sheet.values)[1:]:
            if row[0]:
                PickupPoint.objects.get_or_create(address=row[0])

    def import_products(self, wb):
        sheet = wb['Product']
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

    def import_users(self, wb):
        sheet = wb['User']
        role_mapping = {
            'Администратор': 'admin',
            'Менеджер': 'manager',
            'Клиент': 'client',
        }
        for row in list(sheet.values)[1:]:
            if not row[2]:
                continue
            username = row[2].replace('@kancmail.com', '')
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': row[2]}
            )
            if created:
                user.set_password(row[3])
                user.save()
            UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': role_mapping.get(row[0], 'client'), 'full_name': row[1]}
            )

    def import_orders(self, wb):
        sheet = wb['Order']
        status_mapping = {'Завершен': 'delivered', 'Новый': 'processing', 'В обработке': 'processing'}
        
        for row in list(sheet.values)[1:]:
            if not row[0]:
                continue
            user = User.objects.filter(profile__full_name=row[5]).first()
            if not user:
                username = row[5].lower().replace(' ', '_')[:30]
                user = User.objects.create_user(username=username)
                UserProfile.objects.create(user=user, full_name=row[5], role='client')
            
            pickup_points = list(PickupPoint.objects.all())
            pickup_point = pickup_points[min(row[4]-1, len(pickup_points)-1)] if pickup_points else None
            
            order, created = Order.objects.get_or_create(
                order_number=str(row[0]),
                defaults={
                    'user': user,
                    'order_date': timezone.make_aware(row[2]) if hasattr(row[2], 'tzinfo') and row[2].tzinfo is None else row[2],
                    'delivery_date': row[3].date() if hasattr(row[3], 'date') else row[3],
                    'pickup_point': pickup_point,
                    'pickup_code': str(row[6]),
                    'status': status_mapping.get(row[7], 'processing'),
                }
            )
            
            if created and row[1]:
                items = str(row[1]).split(', ')
                total = Decimal('0')
                i = 0
                while i < len(items):
                    article = items[i]
                    quantity = int(items[i+1]) if i+1 < len(items) else 1
                    try:
                        product = Product.objects.get(article=article)
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            price_at_purchase=product.discounted_price
                        )
                        total += product.discounted_price * quantity
                    except Product.DoesNotExist:
                        pass
                    i += 2
                order.total_amount = total
                order.save()
