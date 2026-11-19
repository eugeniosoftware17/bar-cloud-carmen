from django.urls import path

from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('movimientos/', views.movimientos, name='movimientos'),
    path('entrada/', views.entrada, name='entrada'),
    path('<int:pk>/ajustar/', views.ajuste, name='ajuste'),
    path('pedir/', views.pedir, name='pedir'),
    path('pedir/imprimir/', views.pedir_imprimir, name='pedir_imprimir'),
]
