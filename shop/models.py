from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class Category(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name='Название категории')
    description = models.TextField(blank=True, verbose_name='Описание')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Manufacturer(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name='Название производителя')
    country = models.CharField(max_length=100, blank=True, verbose_name='Страна')

    class Meta:
        verbose_name = 'Производитель'
        verbose_name_plural = 'Производители'
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name='Название поставщика')
    contact_info = models.TextField(blank=True, verbose_name='Контактная информация')

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    article = models.CharField(max_length=50, unique=True, verbose_name='Артикул')
    name = models.CharField(max_length=300, verbose_name='Наименование товара')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', verbose_name='Категория')
    description = models.TextField(blank=True, verbose_name='Описание товара')
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT, related_name='products', verbose_name='Производитель')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='products', verbose_name='Поставщик')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Цена')
    unit = models.CharField(max_length=50, verbose_name='Единица измерения')
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name='Количество на складе')
    discount = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name='Действующая скидка (%)')
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='Фото')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name']

    def __str__(self):
        return f"{self.article} - {self.name}"

    @property
    def discounted_price(self):
        if self.discount > 0:
            return self.price * (100 - self.discount) / 100
        return self.price

    @property
    def is_out_of_stock(self):
        return self.stock_quantity == 0


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('guest', 'Гость'),
        ('client', 'Клиент'),
        ('manager', 'Менеджер'),
        ('admin', 'Администратор'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client', verbose_name='Роль')
    full_name = models.CharField(max_length=300, verbose_name='ФИО')

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"


class PickupPoint(models.Model):
    address = models.CharField(max_length=500, unique=True, verbose_name='Адрес пункта выдачи')

    class Meta:
        verbose_name = 'Пункт выдачи'
        verbose_name_plural = 'Пункты выдачи'

    def __str__(self):
        return self.address


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('in_progress', 'В обработке'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders', verbose_name='Клиент')
    order_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата заказа')
    delivery_date = models.DateField(null=True, blank=True, verbose_name='Дата доставки')
    pickup_point = models.ForeignKey(PickupPoint, on_delete=models.PROTECT, related_name='orders', verbose_name='Пункт выдачи')
    pickup_code = models.CharField(max_length=10, verbose_name='Код для получения')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Статус заказа')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма заказа')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-order_date']

    def __str__(self):
        return f"Заказ #{self.id} от {self.order_date.strftime('%d.%m.%Y')}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заказ')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items', verbose_name='Товар')
    quantity = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='Количество')
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена на момент покупки')

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.price_at_purchase
