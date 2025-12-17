from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, ProtectedError
from django.utils import timezone
from .models import Product, Order, UserProfile, Supplier, OrderItem, PickupPoint, User
from .forms import ProductForm, OrderForm, OrderItemForm
import os
import random


def get_user_role(request):
    if request.user.is_authenticated:
        try:
            return request.user.profile.role
        except UserProfile.DoesNotExist:
            return 'guest'
    return 'guest'


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('product_list')
        messages.error(request, 'Неверный логин или пароль')
    return render(request, 'shop/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def product_list(request):
    products = Product.objects.select_related('category', 'manufacturer', 'supplier').all()
    role = get_user_role(request)
    
    search = request.GET.get('search', '')
    supplier_filter = request.GET.get('supplier', '')
    sort_by = request.GET.get('sort', '')
    
    if role in ['manager', 'admin'] and search:
        products = products.filter(
            Q(name__icontains=search) | Q(description__icontains=search) | 
            Q(manufacturer__name__icontains=search) | Q(supplier__name__icontains=search) | 
            Q(article__icontains=search)
        )
    
    if role in ['manager', 'admin'] and supplier_filter:
        products = products.filter(supplier__id=supplier_filter)
    
    if role in ['manager', 'admin'] and sort_by == 'stock':
        products = products.order_by('stock_quantity')
    
    return render(request, 'shop/product_list.html', {
        'products': products, 'role': role, 'suppliers': Supplier.objects.all(),
        'search_query': search, 'supplier_filter': supplier_filter, 'sort_by': sort_by
    })


@login_required
def product_add(request):
    if get_user_role(request) != 'admin':
        messages.error(request, 'Доступ запрещен')
        return redirect('product_list')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Товар добавлен')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'shop/product_form.html', {'form': form, 'action': 'add'})


@login_required
def product_edit(request, product_id):
    if get_user_role(request) != 'admin':
        messages.error(request, 'Доступ запрещен')
        return redirect('product_list')
    
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        old_image = product.image
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            if 'image' in request.FILES and old_image:
                if os.path.isfile(old_image.path):
                    os.remove(old_image.path)
            form.save()
            messages.success(request, 'Товар обновлен')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'shop/product_form.html', {'form': form, 'action': 'edit', 'product': product})


@login_required
def product_delete(request, product_id):
    if get_user_role(request) != 'admin':
        messages.error(request, 'Доступ запрещен')
        return redirect('product_list')
    
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        try:
            if product.image and os.path.isfile(product.image.path):
                os.remove(product.image.path)
            product.delete()
            messages.success(request, 'Товар удален')
        except ProtectedError:
            messages.error(request, 'Невозможно удалить товар в заказах')
        return redirect('product_list')
    return render(request, 'shop/product_delete.html', {'product': product})


@login_required
def order_list(request):
    role = get_user_role(request)
    if role not in ['manager', 'admin']:
        messages.error(request, 'Доступ запрещен')
        return redirect('product_list')
    
    orders = Order.objects.select_related('user', 'pickup_point').prefetch_related('items__product').all()
    
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) | 
            Q(user__profile__full_name__icontains=search)
        )
    
    return render(request, 'shop/order_list.html', {
        'orders': orders, 'role': role, 'status_filter': status_filter, 'search': search
    })


@login_required
def order_detail(request, order_id):
    role = get_user_role(request)
    if role not in ['manager', 'admin']:
        messages.error(request, 'Доступ запрещен')
        return redirect('product_list')
    
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)
    return render(request, 'shop/order_detail.html', {'order': order, 'role': role})


@login_required
def order_add(request):
    if get_user_role(request) != 'admin':
        messages.error(request, 'Доступ запрещен')
        return redirect('order_list')
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.order_number = f"ORD-{random.randint(10000, 99999)}"
            order.pickup_code = str(random.randint(100, 999))
            order.save()
            messages.success(request, 'Заказ создан')
            return redirect('order_edit', order_id=order.id)
    else:
        form = OrderForm()
    
    return render(request, 'shop/order_form.html', {'form': form, 'action': 'add'})


@login_required
def order_edit(request, order_id):
    if get_user_role(request) != 'admin':
        messages.error(request, 'Доступ запрещен')
        return redirect('order_list')
    
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        if 'update_order' in request.POST:
            form = OrderForm(request.POST, instance=order)
            if form.is_valid():
                old_status = order.status
                order = form.save()
                
                if old_status != order.status:
                    handle_status_change(order, old_status)
                
                order.calculate_total()
                order.save()
                messages.success(request, 'Заказ обновлен')
        
        elif 'add_item' in request.POST:
            item_form = OrderItemForm(request.POST)
            if item_form.is_valid():
                item = item_form.save(commit=False)
                item.order = order
                item.price_at_purchase = item.product.discounted_price
                
                product = item.product
                if item.quantity <= product.available_quantity:
                    product.reserved_quantity += item.quantity
                    product.save()
                    item.save()
                    order.calculate_total()
                    order.save()
                    messages.success(request, 'Товар добавлен')
                else:
                    messages.error(request, f'Недостаточно товара. Доступно: {product.available_quantity}')
        
        elif 'delete_item' in request.POST:
            item_id = request.POST.get('item_id')
            item = OrderItem.objects.get(id=item_id)
            product = item.product
            product.reserved_quantity -= item.quantity
            product.save()
            item.delete()
            order.calculate_total()
            order.save()
            messages.success(request, 'Товар удален')
        
        return redirect('order_edit', order_id=order.id)
    
    form = OrderForm(instance=order)
    item_form = OrderItemForm()
    items = order.items.all()
    
    return render(request, 'shop/order_form.html', {
        'form': form, 'item_form': item_form, 'order': order, 'items': items, 'action': 'edit'
    })


@login_required
def order_delete(request, order_id):
    if get_user_role(request) != 'admin':
        messages.error(request, 'Доступ запрещен')
        return redirect('order_list')
    
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        if order.status not in ['delivered', 'cancelled']:
            for item in order.items.all():
                product = item.product
                product.reserved_quantity -= item.quantity
                product.save()
        order.delete()
        messages.success(request, 'Заказ удален')
        return redirect('order_list')
    
    return render(request, 'shop/order_delete.html', {'order': order})


def handle_status_change(order, old_status):
    if order.status == 'delivered':
        for item in order.items.all():
            product = item.product
            product.stock_quantity -= item.quantity
            product.reserved_quantity -= item.quantity
            product.save()
    elif order.status == 'cancelled':
        for item in order.items.all():
            product = item.product
            product.reserved_quantity -= item.quantity
            product.save()
