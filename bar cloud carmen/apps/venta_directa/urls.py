from django.urls import path

from . import views

app_name = 'venta_directa'

urlpatterns = [
    path('', views.inicio, name='inicio'),
]
