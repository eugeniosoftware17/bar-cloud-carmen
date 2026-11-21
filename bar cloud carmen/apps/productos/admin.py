from django.contrib import admin

from .models import Categoria, ComboItem, Producto


class ComboItemInline(admin.TabularInline):
    model = ComboItem
    fk_name = 'combo'
    extra = 0
    autocomplete_fields = ['producto']


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'orden']
    list_editable = ['orden']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'precio', 'costo', 'stock', 'es_combo', 'controla_stock', 'activo']
    list_filter = ['categoria', 'activo', 'es_combo', 'controla_stock']
    search_fields = ['nombre']
    inlines = [ComboItemInline]
