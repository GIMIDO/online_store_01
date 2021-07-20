from django.views.generic.detail import SingleObjectMixin
from django.views.generic import View

from .models import Category, Cart, Client, Hoodie, Shoes, Pants

class CategoryDetailMixin(SingleObjectMixin):
    CATEGORY_SLUG_TO_CLOTHES_MODEL = {
        'shoes': Shoes,
        'hoodies': Hoodie,
        'pants': Pants
    }

    def get_context_data(self, **kwargs):
        if isinstance(self.get_object(), Category):
            model = self.CATEGORY_SLUG_TO_CLOTHES_MODEL[self.get_object().slug]
            context = super().get_context_data(**kwargs)
            context['categories'] = Category.objects.get_categories_for_nav()
            context['category_clothes'] = model.objects.all()
            return context
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.get_categories_for_nav()
        return context


class CartMixin(View):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            client = Client.objects.filter(user=request.user).first()
            if not client:
                client = Client.objects.create(user=request.user)
            cart = Cart.objects.filter(owner=client, in_order=False).first()
            if not cart:
                cart = Cart.objects.create(owner=client)
        else:
            cart = Cart.objects.filter(anon_user=True).first()
            if not cart:
                cart = Cart.objects.create(anon_user=True)
        self.cart = cart
        return super().dispatch(request, *args, **kwargs)