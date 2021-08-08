from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import *


urlpatterns = [
    path('', BaseView.as_view(), name='base'),
    path('clothes/<str:ct_model>/<str:slug>/', ClothesDetailView.as_view(), name='clothes_detail'),
    path('category/<str:slug>/', CategoryDetailView.as_view(), name='category_detail'),
    path('cart/', CartView.as_view(), name='cart'),
    path('add-to-cart/<str:ct_model>/<str:slug>/', AddToCartView.as_view(), name='add_to_cart'),
    path('remove-from-cart/<str:ct_model>/<str:slug>/', DeleteFromCartView.as_view(), name='delete_from_cart'),
    path('change-qty/<str:ct_model>/<str:slug>/', ChangeQTYView.as_view(), name='change_qty'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('make-order/', MakeOrderView.as_view(), name='make_order'),

    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page="/"), name='logout'),
    path('registration/', RegistrationView.as_view(), name='registration'),
    path('profile/', ProfileView.as_view(), name='profile'),

    path('clothes-delete/<str:ct_model>/<str:slug>/', ClothesDelete.as_view(), name='clothes_delete'),

    path('shoes-add/', ShoesCreateView.as_view(), name='shoes_add'),
    path('pants-add/', PantsCreateView.as_view(), name='pants_add'),
    path('hoodie-add/', HoodieCreateView.as_view(), name='hoodie_add'),
    path('brand-add/', BrandCreateView.as_view(), name='brand_add'),

    path('<str:get_model_name>/<str:slug>/update/', ShoesUpdateView.as_view(), name='shoes_update'),
    path('<str:get_model_name>/<str:slug>/update/', PantsUpdateView.as_view(), name='pants_update'),
    path('<str:get_model_name>/<str:slug>/update/', HoodieUpdateView.as_view(), name='hoodie_update')
]
