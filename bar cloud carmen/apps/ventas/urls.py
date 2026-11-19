from django.urls import path

from . import views

app_name = 'ventas'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('cobrar/', views.cobrar, name='cobrar'),
    path('cierre/', views.cierre, name='cierre'),
    path('cierre/imprimir/', views.cierre_imprimir, name='cierre_imprimir'),
    path('<int:pk>/', views.detalle, name='detalle'),
    path('<int:pk>/recibo/', views.recibo, name='recibo'),
    path('<int:pk>/anular/', views.anular, name='anular'),
]
