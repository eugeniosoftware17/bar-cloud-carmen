from django.urls import path

from . import views

app_name = 'mesas'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('estado/', views.estado, name='estado'),
    path('nueva/', views.nueva, name='nueva'),
    path('<int:pk>/abrir/', views.abrir, name='abrir'),
    path('<int:pk>/consumo/', views.consumo, name='consumo'),
    path('<int:pk>/liberar/', views.liberar, name='liberar'),
    path('<int:pk>/cobrar/', views.cobrar, name='cobrar'),
    path('<int:pk>/precuenta/', views.precuenta, name='precuenta'),
]
