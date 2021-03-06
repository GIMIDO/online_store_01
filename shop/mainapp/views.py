from django.db import transaction
from django.shortcuts import render
from django.views.generic import DetailView, View, UpdateView, CreateView
from django.http import HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.urls.base import reverse_lazy

from .models import Shoes, Pants, Hoodie, Category, LatestProducts, Client, CartProduct, Order, Brand, User
from .mixins import CategoryDetailMixin, CartMixin, AuthenticatedSuperuserMixin, AuthenticatedUserMixin
from .forms import OrderForm, LoginForm, RegistrationForm, ShoesForm, PantsForm, HoodieForm, BrandForm
from .utils import recalc_cart

# displays the start page
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

# displays the clothes page
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

# displays the category page
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

# adding an item to the cart
class AddToCartView(AuthenticatedUserMixin, CartMixin, View):

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
        messages.add_message(request, messages.INFO, "?????????? ????????????????")
        return HttpResponseRedirect('/cart/')

# removing an item from the cart
class DeleteFromCartView(AuthenticatedUserMixin, CartMixin, View):

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
        messages.add_message(request, messages.INFO, "?????????? ????????????")
        return HttpResponseRedirect('/cart/')

# changing the number of items in the cart
class ChangeQTYView(AuthenticatedUserMixin, CartMixin, View):

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
        messages.add_message(request, messages.INFO, "???????????????? ??????-???? ????????????")
        return HttpResponseRedirect('/cart/')

# displays the cart page
class CartView(AuthenticatedUserMixin, CartMixin, CategoryDetailMixin, View):

    def get(self, request):
        categories = (Category.objects.get_categories_for_nav())
        context = {
            'cart': self.cart,
            'categories': categories
        }
        return render(request, 'cart.html', context)

# displays the order creation page
class CheckoutView(AuthenticatedUserMixin, CartMixin, CategoryDetailMixin, View):

    def get(self, request):
        categories = (Category.objects.get_categories_for_nav())
        form = OrderForm(request.POST or None)
        context = {
            'cart': self.cart,
            'categories': categories,
            'form': form
        }
        return render(request, 'checkout.html', context)

# order creation
class MakeOrderView(AuthenticatedUserMixin, CartMixin, CategoryDetailMixin, View):

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
            messages.add_message(request, messages.INFO, '????????????????!')
            return HttpResponseRedirect('/')
        return HttpResponseRedirect('/checkout/')

# displays the login page
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

# displays the registration page
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

# displays the user profile page
class ProfileView(AuthenticatedUserMixin, CartMixin, CategoryDetailMixin, View):

    def get(self, request):
        client = Client.objects.get(user=request.user)
        orders = Order.objects.filter(client=client).order_by('-created_at')
        categories = Category.objects.get_categories_for_nav()
        return render(request, 'profile/profile.html', {'orders': orders, 'cart': self.cart, 'categories': categories})

# deleting an item from the database
class ClothesDelete(AuthenticatedSuperuserMixin, View):

    def get(self, request, **kwargs):
        ct_model, clothes_slug = kwargs.get('ct_model'), kwargs.get('slug')
        content_type = ContentType.objects.get(model=ct_model)
        product = content_type.model_class().objects.get(slug=clothes_slug)
        product.delete()
        messages.add_message(request, messages.INFO, "?????????? ???????????? ???? ????????")
        return HttpResponseRedirect('/category/{}s/'.format(ct_model))

# displays the product creation page to the database
class ClothesCreateView(AuthenticatedSuperuserMixin, CreateView):

    CT_MODEL_FORM_CLASS = {
        'Shoes': ShoesForm,
        'Hoodie': HoodieForm,
        'Pants': PantsForm
    }

    def dispatch(self, request, *args, **kwargs):
        self.model = kwargs.get('model')
        self.form_class = self.CT_MODEL_FORM_CLASS[kwargs['model']]
        return super().dispatch(request, *args, **kwargs)

    template_name = 'crud/crud_template.html'
    success_url = reverse_lazy('base')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['button_name'] = '????????????????'
        if self.model == 'Hoodie':
            context['title'] = '???????????????? ????????'
        elif self.model == 'Pants':
            context['title'] = '???????????????? ??????????'
        if self.model == 'Shoes':
            context['title'] = '???????????????? ??????????'
        return context

# displays the product update page to the database
class ClothesUpdateView(AuthenticatedSuperuserMixin, UpdateView):

    CT_MODEL_MODEL_CLASS = {
        'shoes': Shoes,
        'hoodie': Hoodie,
        'pants': Pants
    }
    CT_MODEL_FORM_CLASS = {
        'shoes': ShoesForm,
        'hoodie': HoodieForm,
        'pants': PantsForm
    }

    def dispatch(self, request, *args, **kwargs):
        self.model = self.CT_MODEL_MODEL_CLASS[kwargs['ct_model']]
        self.queryset = self.model._base_manager.all()
        self.form_class = self.CT_MODEL_FORM_CLASS[kwargs['ct_model']]
        return super().dispatch(request, *args, **kwargs)

    template_name = 'crud/crud_template.html'
    success_url = reverse_lazy('base')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['button_name'] = '????????????????'
        if self.model == 'Hoodie':
            context['title'] = '???????????????? ????????'
        elif self.model == 'Pants':
            context['title'] = '???????????????? ??????????'
        if self.model == 'Shoes':
            context['title'] = '???????????????? ??????????'
        return context

# displays the brand creation page in the database
class BrandCreateView(AuthenticatedSuperuserMixin, CreateView):

    model = Brand
    template_name = 'crud/crud_template.html'
    success_url = reverse_lazy('base')
    form_class = BrandForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '???????????????? ??????????'
        return context

# displays a page with registered users
class UsersView(AuthenticatedSuperuserMixin, CartMixin, CategoryDetailMixin, View):
    def get(self, request):
        users = User.objects.all()
        categories = Category.objects.get_categories_for_nav()
        context = {
            'users': users,
            'cart': self.cart,
            'categories': categories
        }
        return render(request, 'profile/users.html', context)
