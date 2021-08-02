from django.db import transaction
from django.shortcuts import render
from django.views.generic import DetailView, View
from django.http import HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.contrib.auth import authenticate, login

from .models import Shoes, Pants, Hoodie, Category, LatestProducts, Client, Cart, CartProduct, Order, Clothes
from .mixins import CategoryDetailMixin, CartMixin
from .forms import OrderForm, LoginForm, RegistrationForm, AddShoesForm, AddPantsForm, AddHoodieForm
from .utils import recalc_cart


class BaseView(CartMixin, View):
    def get(self, request, *args, **kwargs):
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
    def get(self, request, *args, **kwargs):
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
    def get(self, request, *args, **kwargs):
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
    def post(self, request, *args, **kwargs):
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
    def get(self, request, *args, **kwargs):
        categories = (Category.objects.get_categories_for_nav())
        context = {
            'cart': self.cart,
            'categories': categories
        }
        return render(request, 'cart.html', context)


class CheckoutView(CartMixin, CategoryDetailMixin, View):
    def get(self, request, *args, **kwargs):
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
    def post(self, request, *args, **kwargs):
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

    def get(self, request, *args, **kwargs):
        form = LoginForm(request.POST or None)
        categories = Category.objects.get_categories_for_nav()
        context = {'form': form, 'categories': categories, 'cart': self.cart}
        return render(request, 'login.html', context)

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST or None)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return HttpResponseRedirect('/')
        context = {'form': form, 'cart': self.cart}
        return render(request, 'login.html', context)


class RegistrationView(CartMixin, CategoryDetailMixin, View):
    def get(self, request, *args, **kwargs):
        form = RegistrationForm(request.POST or None)
        categories = Category.objects.get_categories_for_nav()
        context = {'form': form, 'categories': categories, 'cart': self.cart}
        return render(request, 'registration.html', context)

    def post(self, request, *args, **kwargs):
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
        return render(request, 'registration.html', context)


class ProfileView(CartMixin, CategoryDetailMixin, View):

    def get(self, request, *args, **kwargs):
        client = Client.objects.get(user=request.user)
        orders = Order.objects.filter(client=client).order_by('-created_at')
        categories = Category.objects.get_categories_for_nav()
        return render(request, 'profile.html', {'orders': orders, 'cart': self.cart, 'categories': categories})


class ClothesDelete(CartMixin, View):
    def get(self, request, *args, **kwargs):
        ct_model, clothes_slug = kwargs.get('ct_model'), kwargs.get('slug')
        content_type = ContentType.objects.get(model=ct_model)
        product = content_type.model_class().objects.get(slug=clothes_slug)
        product.delete()
        messages.add_message(request, messages.INFO, "Товар удален из базы")
        return HttpResponseRedirect('/category/{}/'.format(ct_model))


class ShoesAddView(CartMixin, CategoryDetailMixin, View):
    def get(self, request, *args, **kwargs):
        form = AddShoesForm(request.POST or None)
        categories = Category.objects.get_categories_for_nav()
        context = {'form': form, 'categories': categories, 'cart': self.cart}
        return render(request, 'add_shoes.html', context)

    def post(self, request, *args, **kwargs):
        form = AddShoesForm(request.POST or None, request.FILES)
        if form.is_valid():
            form.save()
            Shoes.objects.create(
                category=form.cleaned_data['category'],
                title=form.cleaned_data['title'],
                description=form.cleaned_data['description'],
                price=form.cleaned_data['price'],
                image=form.cleaned_data['image'],
                color=form.cleaned_data['color'],
                size=form.cleaned_data['size'],
                outsole_material=form.cleaned_data['outsole_material'],
                insole_material=form.cleaned_data['insole_material'],
                inner_material=form.cleaned_data['inner_material'],
                top_material=form.cleaned_data['top_material'],
                brand=form.cleaned_data['brand'],
                slug=form.cleaned_data['slug']
            )
            return HttpResponseRedirect('/')
        context = {'form': form, 'cart': self.cart}
        return render(request, 'add_shoes.html', context)


class PantsAddView(CartMixin, CategoryDetailMixin, View):
    def get(self, request, *args, **kwargs):
        form = AddPantsForm(request.POST or None, request.FILES)
        categories = Category.objects.get_categories_for_nav()
        context = {'form': form, 'categories': categories, 'cart': self.cart}
        return render(request, 'add_pants.html', context)

    def post(self, request, *args, **kwargs):
        form = AddPantsForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            Pants.objects.create(
                category=form.cleaned_data['category'],
                title=form.cleaned_data['title'],
                description=form.cleaned_data['description'],
                price=form.cleaned_data['price'],
                image=form.cleaned_data['image'],
                color=form.cleaned_data['color'],
                length_inside=form.cleaned_data['length_inside'],
                length_side=form.cleaned_data['length_side'],
                bottom_width=form.cleaned_data['bottom_width'],
                pattern=form.cleaned_data['pattern'],
                claps=form.cleaned_data['claps'],
                brand=form.cleaned_data['brand'],
                slug=form.cleaned_data['slug']
            )
            return HttpResponseRedirect('/')
        context = {'form': form, 'cart': self.cart}
        return render(request, 'add_pants.html', context)


class HoodieAddView(CartMixin, CategoryDetailMixin, View):
    def get(self, request, *args, **kwargs):
        form = AddHoodieForm(request.POST or None, request.FILES)
        categories = Category.objects.get_categories_for_nav()
        context = {'form': form, 'categories': categories, 'cart': self.cart}
        return render(request, 'add_hoodie.html', context)

    def post(self, request, *args, **kwargs):
        form = AddHoodieForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            Hoodie.objects.create(
                category=form.cleaned_data['category'],
                title=form.cleaned_data['title'],
                description=form.cleaned_data['description'],
                price=form.cleaned_data['price'],
                image=form.cleaned_data['image'],
                color=form.cleaned_data['color'],
                length=form.cleaned_data['length'],
                length_sleeve=form.cleaned_data['length_sleeve'],
                pattern=form.cleaned_data['pattern'],
                brand=form.cleaned_data['brand'],
                slug=form.cleaned_data['slug']
            )
            return HttpResponseRedirect('/')
        context = {'form': form, 'cart': self.cart}
        return render(request, 'add_hoodie.html', context)