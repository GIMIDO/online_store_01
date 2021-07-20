from django.forms import ModelChoiceField
from django.contrib import admin
from .models import *


# при выборе категории выпадает правильная категория
class ShoesAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            return ModelChoiceField(Category.objects.filter(slug='shoes'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class PantsAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            return ModelChoiceField(Category.objects.filter(slug='pants'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class HoodieAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            return ModelChoiceField(Category.objects.filter(slug='hoodies'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Category)
admin.site.register(CartProduct)
admin.site.register(Cart)
admin.site.register(Client)
admin.site.register(Brand)
admin.site.register(Shoes, ShoesAdmin)
admin.site.register(Hoodie, HoodieAdmin)
admin.site.register(Pants, PantsAdmin)
admin.site.register(Order)

