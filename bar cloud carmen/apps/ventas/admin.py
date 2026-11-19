from django.contrib import admin

from .models import CierreCaja, LineaVenta, Venta


class LineaVentaInline(admin.TabularInline):
    model = LineaVenta
    extra = 0
    can_delete = False
    readonly_fields = ['producto', 'nombre', 'cantidad', 'precio', 'costo']


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'fecha', 'mesa', 'metodo', 'total', 'usuario', 'anulada']
    list_filter = ['metodo', 'anulada', 'fecha']
    inlines = [LineaVentaInline]
    readonly_fields = [f.name for f in Venta._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CierreCaja)
class CierreCajaAdmin(admin.ModelAdmin):
    list_display = ['dia', 'total_vendido', 'esperado', 'contado', 'diferencia', 'usuario']
    readonly_fields = [f.name for f in CierreCaja._meta.fields]

    def has_add_permission(self, request):
        return False
