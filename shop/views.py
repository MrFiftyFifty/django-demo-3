from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, ProtectedError
from django.core.paginator import Paginator
from .models import Product, Order, UserProfile, Category, Manufacturer, Supplier
from .forms import ProductForm
import os


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
        
        if user is not None:
            login(request, user)
            return redirect('product_list')
        else:
            messages.error(request, 'Неверный логин или пароль')
    
    return render(request, 'shop/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def product_list(request):
    products = Product.objects.select_related('category', 'manufacturer', 'supplier').all()
    
    role = get_user_role(request)
    
    search_query = request.GET.get('search', '')
    supplier_filter = request.GET.get('supplier', '')
    sort_by = request.GET.get('sort', '')
    
    if role in ['manager', 'admin'] and search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(manufacturer__name__icontains=search_query) |
            Q(supplier__name__icontains=search_query) |
            Q(article__icontains=search_query)
        )
    
    if role in ['manager', 'admin'] and supplier_filter:
        products = products.filter(supplier__id=supplier_filter)
    
    if role in ['manager', 'admin'] and sort_by == 'stock':
        products = products.order_by('stock_quantity')
    
    suppliers = Supplier.objects.all()
    
    context = {
        'products': products,
        'role': role,
        'suppliers': suppliers,
        'search_query': search_query,
        'supplier_filter': supplier_filter,
        'sort_by': sort_by,
    }
    
    return render(request, 'shop/product_list.html', context)


@login_required
def product_add(request):
    role = get_user_role(request)
    
    if role != 'admin':
        messages.error(request, 'У вас нет прав для выполнения этого действия')
        return redirect('product_list')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Товар успешно добавлен')
            return redirect('product_list')
    else:
        form = ProductForm()
    
    return render(request, 'shop/product_form.html', {'form': form, 'action': 'add'})


@login_required
def product_edit(request, product_id):
    role = get_user_role(request)
    
    if role != 'admin':
        messages.error(request, 'У вас нет прав для выполнения этого действия')
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
            messages.success(request, 'Товар успешно обновлен')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'shop/product_form.html', {
        'form': form,
        'action': 'edit',
        'product': product
    })


@login_required
def product_delete(request, product_id):
    role = get_user_role(request)
    
    if role != 'admin':
        messages.error(request, 'У вас нет прав для выполнения этого действия')
        return redirect('product_list')
    
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        try:
            if product.image:
                if os.path.isfile(product.image.path):
                    os.remove(product.image.path)
            
            product.delete()
            messages.success(request, 'Товар успешно удален')
        except ProtectedError:
            messages.error(request, 'Невозможно удалить товар, так как он используется в заказах')
        
        return redirect('product_list')
    
    return render(request, 'shop/product_delete.html', {'product': product})


@login_required
def order_list(request):
    role = get_user_role(request)
    
    if role not in ['manager', 'admin']:
        messages.error(request, 'У вас нет прав для просмотра заказов')
        return redirect('product_list')
    
    orders = Order.objects.select_related('user', 'pickup_point').prefetch_related('items__product').all()
    
    context = {
        'orders': orders,
        'role': role,
    }
    
    return render(request, 'shop/order_list.html', context)
