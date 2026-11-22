from django.urls import path

from . import views

app_name = 'configuracion'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('muestra-recibo/', views.muestra_recibo, name='muestra_recibo'),
    path('acceso-caja/', views.acceso_caja, name='acceso_caja'),
]
