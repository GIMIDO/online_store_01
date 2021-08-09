from django.db import transaction
from django.shortcuts import render, redirect
from django.views.generic import DetailView, View, UpdateView, CreateView  #
from django.http import HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.urls.base import reverse_lazy  #

from .models import Shoes, Pants, Hoodie, Category, LatestProducts, Client, CartProduct, Order, Brand, User
from .mixins import CategoryDetailMixin, CartMixin, AuthenticatedMixin
from .forms import OrderForm, LoginForm, RegistrationForm, AddShoesForm, AddPantsForm, AddHoodieForm, AddBrandForm
from .utils import recalc_cart


class BaseView(CartMixin, View):
    def get(self, request):
        categories = (Category.objects.get_categories_for_nav())
        clothes = LatestProducts.objects.get_products_for_main_page('hoodie', 'pants', 'shoes')
        context = {
            'categories': categories,
            'all_clothes': clothes,
            'cart': self.cart
        }
        return render(request, 'base.html', context)


class ClothesDetailView(CartMixin, CategoryDetailMixin, DetailView):

    CT_MODEL_MODEL_CLASS = {
        'shoes': Shoes,
        'hoodie': Hoodie,
        'pants': Pants
    }

    def dispatch(self, request, *args, **kwargs):
        self.model = self.CT_MODEL_MODEL_CLASS[kwargs['ct_model']]
        self.queryset = self.model._base_manager.all()
        return super().dispatch(request, *args, **kwargs)

    context_object_name = 'clothes'
    template_name = 'clothes_detail.html'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ct_model'] = self.model._meta.model_name
        context['cart'] = self.cart
        return context


class CategoryDetailView(CartMixin, CategoryDetailMixin, DetailView):
    model = Category
    queryset = Category.objects.all()
    context_object_name = 'category'
    template_name = 'category_detail.html'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart'] = self.cart
        return context


class AddToCartView(CartMixin, View):
    def get(self, request, **kwargs):
        ct_model, clothes_slug = kwargs.get('ct_model'), kwargs.get('slug')
        content_type = ContentType.objects.get(model=ct_model)
        clothes = content_type.model_class().objects.get(slug=clothes_slug)
        cart_product, created = CartProduct.objects.get_or_create(
            user=self.cart.owner, cart=self.cart, content_type=content_type, object_id=clothes.id
        )
        if created:
            self.cart.clothes.add(cart_product)
        recalc_cart(self.cart)
        messages.add_message(request, messages.INFO, "Товар добавлен")
        return HttpResponseRedirect('/cart/')


class DeleteFromCartView(CartMixin, View):
    def get(self, request, **kwargs):
        ct_model, clothes_slug = kwargs.get('ct_model'), kwargs.get('slug')
        content_type = ContentType.objects.get(model=ct_model)
        clothes = content_type.model_class().objects.get(slug=clothes_slug)
        cart_product = CartProduct.objects.get(
            user=self.cart.owner, cart=self.cart, content_type=content_type, object_id=clothes.id
        )
        self.cart.clothes.remove(cart_product)
        cart_product.delete()
        recalc_cart(self.cart)
        messages.add_message(request, messages.INFO, "Товар удален")
        return HttpResponseRedirect('/cart/')


class ChangeQTYView(CartMixin, View):
    def post(self, request, **kwargs):
        ct_model, clothes_slug = kwargs.get('ct_model'), kwargs.get('slug')
        content_type = ContentType.objects.get(model=ct_model)
        clothes = content_type.model_class().objects.get(slug=clothes_slug)
        cart_product = CartProduct.objects.get(
            user=self.cart.owner, cart=self.cart, content_type=content_type, object_id=clothes.id
        )
        qty = int(request.POST.get('qty'))
        cart_product.qty = qty
        cart_product.save()
        recalc_cart(self.cart)
        messages.add_message(request, messages.INFO, "Изменено кол-во товара")
        return HttpResponseRedirect('/cart/')


class CartView(CartMixin, CategoryDetailMixin, View):
    def get(self, request):
        categories = (Category.objects.get_categories_for_nav())
        context = {
            'cart': self.cart,
            'categories': categories
        }
        return render(request, 'cart.html', context)


class CheckoutView(CartMixin, CategoryDetailMixin, View):
    def get(self, request):
        categories = (Category.objects.get_categories_for_nav())
        form = OrderForm(request.POST or None)
        context = {
            'cart': self.cart,
            'categories': categories,
            'form': form
        }
        return render(request, 'checkout.html', context)


class MakeOrderView(CartMixin, CategoryDetailMixin, View):
    @transaction.atomic
    def post(self, request):
        form = OrderForm(request.POST or None)
        client = Client.objects.get(user=request.user)
        if form.is_valid():
            new_order = form.save(commit=False)
            new_order.client = client
            new_order.first_name = form.cleaned_data['first_name']
            new_order.last_name = form.cleaned_data['last_name']
            new_order.phone = form.cleaned_data['phone']
            new_order.address = form.cleaned_data['address']
            new_order.buying_type = form.cleaned_data['buying_type']
            new_order.comment = form.cleaned_data['comment']
            new_order.save()
            self.cart.in_order = True
            self.cart.save()
            new_order.cart = self.cart
            new_order.save()
            client.orders.add(new_order)
            messages.add_message(request, messages.INFO, 'Заказано!')
            return HttpResponseRedirect('/')
        return HttpResponseRedirect('/checkout/')


class LoginView(CartMixin, CategoryDetailMixin, View):

    def get(self, request):
        form = LoginForm(request.POST or None)
        categories = Category.objects.get_categories_for_nav()
        context = {'form': form, 'categories': categories, 'cart': self.cart}
        return render(request, 'profile/login.html', context)

    def post(self, request):
        form = LoginForm(request.POST or None)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return HttpResponseRedirect('/')
        context = {'form': form, 'cart': self.cart}
        return render(request, 'profile/login.html', context)


class RegistrationView(CartMixin, CategoryDetailMixin, View):
    def get(self, request):
        form = RegistrationForm(request.POST or None)
        categories = Category.objects.get_categories_for_nav()
        context = {'form': form, 'categories': categories, 'cart': self.cart}
        return render(request, 'profile/registration.html', context)

    def post(self, request):
        form = RegistrationForm(request.POST or None)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.username = form.cleaned_data['username']
            new_user.email = form.cleaned_data['email']
            new_user.first_name = form.cleaned_data['first_name']
            new_user.last_name = form.cleaned_data['last_name']
            new_user.save()
            new_user.set_password(form.cleaned_data['password'])
            new_user.save()
            Client.objects.create(
                user=new_user,
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address']
            )
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            login(request, user)
            return HttpResponseRedirect('/')
        context = {'form': form, 'cart': self.cart}
        return render(request, 'profile/registration.html', context)


class ProfileView(CartMixin, CategoryDetailMixin, View):

    def get(self, request):
        client = Client.objects.get(user=request.user)
        orders = Order.objects.filter(client=client).order_by('-created_at')
        categories = Category.objects.get_categories_for_nav()
        return render(request, 'profile/profile.html', {'orders': orders, 'cart': self.cart, 'categories': categories})


class ClothesDelete(AuthenticatedMixin, CartMixin, View):
    def get(self, request, **kwargs):
        ct_model, clothes_slug = kwargs.get('ct_model'), kwargs.get('slug')
        content_type = ContentType.objects.get(model=ct_model)
        product = content_type.model_class().objects.get(slug=clothes_slug)
        product.delete()
        messages.add_message(request, messages.INFO, "Товар удален из базы")
        return HttpResponseRedirect('/category/{}/'.format(ct_model))


class ShoesCreateView(AuthenticatedMixin, CreateView):
    model = Shoes
    template_name = 'crud/add_template.html'
    success_url = reverse_lazy('base')
    form_class = AddShoesForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Добавить обувь'
        return context


class PantsCreateView(AuthenticatedMixin, CreateView):
    model = Pants
    template_name = 'crud/add_template.html'
    success_url = reverse_lazy('base')
    form_class = AddPantsForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Добавить брюки'
        return context


class HoodieCreateView(AuthenticatedMixin, CreateView):
    model = Hoodie
    template_name = 'crud/add_template.html'
    success_url = reverse_lazy('base')
    form_class = AddHoodieForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Добавить худи'
        return context


class ShoesUpdateView(AuthenticatedMixin, UpdateView):
    model = Shoes
    template_name = 'crud/add_template.html'
    success_url = reverse_lazy('base')
    form_class = AddShoesForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Обновить обувь'
        return context


class PantsUpdateView(AuthenticatedMixin, UpdateView):
    model = Pants
    template_name = 'crud/add_template.html'
    success_url = reverse_lazy('base')
    form_class = AddPantsForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Обновить брюки'
        return context


class HoodieUpdateView(AuthenticatedMixin, UpdateView):
    model = Hoodie
    template_name = 'crud/add_template.html'
    success_url = reverse_lazy('base')
    form_class = AddHoodieForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Обновить худи'
        return context


class BrandCreateView(AuthenticatedMixin, CreateView):
    model = Brand
    template_name = 'crud/add_template.html'
    success_url = reverse_lazy('base')
    form_class = AddBrandForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Добавить брэнд'
        return context


class UsersView(AuthenticatedMixin, View):
    def get(self, request):
        users = User.objects.all()
        context = {
            'users': users
        }
        return render(request, 'profile/users.html', context)