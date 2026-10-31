from django.urls import path
from .views import inicio, subir_archivo, dashboard, formulario

urlpatterns = [
    path('', inicio, name='inicio'),
    path("subir/", subir_archivo, name="subir_archivo"),
    path("dashboard/", dashboard, name="dashboard"),
    path("formulario/", formulario, name="formulario"),
]