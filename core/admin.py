from django.contrib import admin

from .models import (
    Beneficiario, BeneficiarioCuidador, Cuidador, Departamento, Discapacidad,
    Educacion, EstadoCivil, Municipio, NivelEducativo, Organizacion,
)
 
 
@admin.register(Beneficiario)
class BeneficiarioAdmin(admin.ModelAdmin):
    list_display = ("id_beneficiario", "nombres", "apellidos", "tipo_discapacidad", "beneficios_org")
    search_fields = ("nombres", "apellidos")
    list_filter = ("tipo_discapacidad", "sexo")
 
 
admin.site.register([
    Departamento, Municipio, Organizacion, EstadoCivil, Discapacidad,
    NivelEducativo, Educacion, Cuidador, BeneficiarioCuidador,
])
