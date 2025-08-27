from django.contrib import admin

# Register your models here.
from .models import Product, Payment

class ProductAdmin(admin.ModelAdmin):
    list_display = ['id','name','description','price']

class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id','user','product','amount','status']

admin.site.register(Product,ProductAdmin)
admin.site.register(Payment,PaymentAdmin)