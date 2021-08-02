from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.urls import reverse
from django.utils import timezone


User = get_user_model()

def get_clothes_url(obj, viewname):
    ct_model = obj.__class__._meta.model_name
    return reverse(viewname, kwargs={'ct_model': ct_model, 'slug': obj.slug})


def get_models_for_count(*model_names):
    return [models.Count(model_name) for model_name in model_names]


# вывод 8 единиц одежды с возможностью выбора вывода определенных вещей первыми
class LatestProductsManager:
    @staticmethod
    def get_products_for_main_page(*args, **kwargs):
        respect_to = kwargs.get('respect_to')
        clothes = []
        ct_models = ContentType.objects.filter(model__in=args)
        for ct_model in ct_models:
            model_clothes = ct_model.model_class()._base_manager.all().order_by('-id')[:8]
            clothes.extend(model_clothes)
        if respect_to:
            ct_model = ContentType.objects.filter(model=respect_to)
            if ct_model.exists():
                if respect_to in args:
                    return sorted(
                        clothes, key=lambda x: x.__class__._meta.model_name.startswith(respect_to), reverse=True)
        return clothes


class LatestProducts:
    objects = LatestProductsManager


class CategoryManager(models.Manager):
    CATEGORY_NAME_COUNT_NAME = {
        'Худи': 'hoodie__count',
        'Брюки': 'pants__count',
        'Обувь': 'shoes__count'
    }

    def get_queryset(self):
        return super().get_queryset()

    def get_categories_for_nav(self):
        models = get_models_for_count('pants', 'shoes', 'hoodie')
        qs = list(self.get_queryset().annotate(*models))
        data = [
            dict(name=c.name, url=c.get_absolute_url(), count=getattr(c, self.CATEGORY_NAME_COUNT_NAME[c.name]))
            for c in qs
        ]
        return data


class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name='Имя категории')
    slug = models.SlugField(unique=True)
    objects = CategoryManager()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail', kwargs={'slug': self.slug})


class Brand(models.Model):
    name = models.CharField(max_length=255, verbose_name='Имя бренда')
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Clothes(models.Model):
    class Meta:
        abstract = True

    category = models.ForeignKey(Category, verbose_name='Категория', on_delete=models.CASCADE)
    title = models.CharField(max_length=255, verbose_name='Наименование')
    # slug = models.SlugField(unique=True)
    image = models.ImageField(verbose_name='Изображение', default=None)
    description = models.TextField(verbose_name='Описание', null=True)
    price = models.DecimalField(max_digits=7, decimal_places=2, verbose_name='Цена')

    def __str__(self):
        return self.title

    def get_model_name(self):
        return self.__class__.__name__.lower()

class Hoodie(Clothes):
    color = models.CharField(max_length=255, verbose_name='Цвет')
    length = models.CharField(max_length=255, verbose_name='Длина')
    length_sleeve = models.CharField(max_length=255, verbose_name='Длина рукава')
    pattern = models.CharField(max_length=255, verbose_name='Узор')
    brand = models.ForeignKey(Brand, verbose_name='Бренд', on_delete=models.CASCADE)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return "{} : {}".format(self.category.name, self.title)

    def get_absolute_url(self):
        return get_clothes_url(self, 'clothes_detail')


class Pants(Clothes):
    color = models.CharField(max_length=255, verbose_name='Цвет')
    length_inside = models.CharField(max_length=15, verbose_name='Длина по внутреннему шву')
    length_side = models.CharField(max_length=15, verbose_name='Длина по боковому шву')
    bottom_width = models.CharField(max_length=15, verbose_name='Ширина по низу')
    pattern = models.CharField(max_length=255, verbose_name='Узор')
    claps = models.CharField(max_length=50, verbose_name='Застежка')
    brand = models.ForeignKey(Brand, verbose_name='Бренд', on_delete=models.CASCADE)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return "{} : {}".format(self.category.name, self.title)

    def get_absolute_url(self):
        return get_clothes_url(self, 'clothes_detail')


class Shoes(Clothes):
    color = models.CharField(max_length=255, verbose_name='Цвет')
    size = models.CharField(max_length=255, verbose_name='Размер')
    outsole_material = models.CharField(max_length=200, verbose_name='Материал подошвы')
    insole_material = models.CharField(max_length=200, verbose_name='Материал стельки')
    inner_material = models.CharField(max_length=200, verbose_name='Внутренний материал')
    top_material = models.CharField(max_length=200, verbose_name='Верхний материал')
    brand = models.ForeignKey(Brand, verbose_name='Бренд', on_delete=models.CASCADE)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return "{} : {}".format(self.category.name, self.title)

    def get_absolute_url(self):
        return get_clothes_url(self, 'clothes_detail')


class CartProduct(models.Model):
    user = models.ForeignKey('Client', verbose_name='Покупатель', on_delete=models.CASCADE)
    cart = models.ForeignKey('Cart', verbose_name='Корзина', on_delete=models.CASCADE, related_name='related_products')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    qty = models.PositiveIntegerField(default=1)
    final_price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Общая цена')

    def __str__(self):
        return "Товар: {} (для корзины)".format(self.content_object.title)

    def save(self, *args, **kwargs):
        self.final_price = self.qty * self.content_object.price
        super().save(*args, **kwargs)


class Cart(models.Model):
    owner = models.ForeignKey('Client', null=True, verbose_name='Владелец', on_delete=models.CASCADE)
    clothes = models.ManyToManyField(CartProduct, blank=True, related_name='related_cart')
    total_products = models.PositiveIntegerField(default=0)
    final_price = models.DecimalField(max_digits=9, default=0, decimal_places=2, verbose_name='Общая цена')
    in_order = models.BooleanField(default=False)
    anon_user = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)


class Client(models.Model):
    user = models.ForeignKey(User, verbose_name='', on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, verbose_name='Номер телефона', null=True, blank=True)
    address = models.CharField(max_length=255, verbose_name='Адрес', null=True, blank=True)
    orders = models.ManyToManyField('Order', verbose_name='Заказы покупателя', related_name='related_client')

    def __str__(self):
        return "Покупатель {} {}".format(self.user.first_name, self.user.last_name)


class Order(models.Model):
    STATUS_NEW = 'new'
    STATUS_READY = 'is_ready'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'

    BUYING_TYPE_SELF = 'self'
    BUYING_TYPE_DELIVERY = 'delivery'

    STATUS_CHOICES = (
        (STATUS_NEW, 'Новый заказ'),
        (STATUS_READY, 'Заказ готов'),
        (STATUS_IN_PROGRESS, 'Заказ в обработке'),
        (STATUS_COMPLETED, 'Заказ выполнен')
    )

    BUYING_TYPE_CHOICES = (
        (BUYING_TYPE_SELF, 'Самовывоз'),
        (BUYING_TYPE_DELIVERY, 'Доставка')
    )

    client = models.ForeignKey(Client, verbose_name='Покупатель', on_delete=models.CASCADE, related_name='related_orders')
    first_name = models.CharField(max_length=255, verbose_name='Имя')
    last_name = models.CharField(max_length=255, verbose_name='Фамилия')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    address = models.CharField(max_length=1024, verbose_name='Адрес', null=True, blank=True)
    status = models.CharField(max_length=128, verbose_name='Статус заказа', choices=STATUS_CHOICES, default=STATUS_NEW)
    buying_type = models.CharField(max_length=128, verbose_name='Тип заказа', choices=BUYING_TYPE_CHOICES, default=BUYING_TYPE_SELF)
    comment = models.TextField(verbose_name='Комментарий к заказу', null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True, verbose_name='Дата создания заказа')
    order_date = models.DateField(verbose_name='Дата поучения заказа', default=timezone.now)
    cart = models.ForeignKey(Cart, verbose_name='Корзина', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.id)
