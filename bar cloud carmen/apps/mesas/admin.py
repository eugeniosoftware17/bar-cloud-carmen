from django.contrib import admin

from .models import Mesa, Mesera


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'orden', 'activa', 'abierta_en']
    list_editable = ['orden', 'activa']
    readonly_fields = ['abierta_en', 'abierta_por', 'mesera']


@admin.register(Mesera)
class MeseraAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activa']
    list_editable = ['activa']
