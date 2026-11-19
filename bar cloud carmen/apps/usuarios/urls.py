from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('nuevo/', views.nuevo, name='nuevo'),
    path('<int:pk>/editar/', views.editar, name='editar'),
    path('<int:pk>/clave/', views.clave, name='clave'),
]
