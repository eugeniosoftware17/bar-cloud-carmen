from django.urls import path

from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('ganancias/', views.ganancias, name='ganancias'),
    path('gastos/nuevo/', views.gasto_nuevo, name='gasto_nuevo'),
    path('gastos/<int:pk>/editar/', views.gasto_editar, name='gasto_editar'),
    path('gastos/<int:pk>/eliminar/', views.gasto_eliminar, name='gasto_eliminar'),
]
