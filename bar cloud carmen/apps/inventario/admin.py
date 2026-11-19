from django.contrib import admin

from .models import Movimiento


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'producto', 'tipo', 'cantidad', 'stock_despues', 'usuario']
    list_filter = ['tipo', 'fecha']
    search_fields = ['producto__nombre', 'nota']
    readonly_fields = [f.name for f in Movimiento._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
