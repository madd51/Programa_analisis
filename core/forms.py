from django import forms

from .models import (
    Beneficiario,
    Municipio,
    Discapacidad,
    Organizacion,
    EstadoCivil,
    Educacion,
    Cuidador
)

TAMANO_MAXIMO_MB = 10


class SubirArchivoForm(forms.Form):
    archivo = forms.FileField(label="Archivo CSV o Excel (.xlsx)")
    solo_validar = forms.BooleanField(
        required=False,
        label="Solo validar: mostrar el resultado de la limpieza sin guardar en la base de datos",
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if not archivo.name.lower().endswith((".csv", ".xlsx")):
            raise forms.ValidationError("Formato no permitido. Sube un archivo .csv o .xlsx.")
        if archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024:
            raise forms.ValidationError(f"El archivo supera el máximo de {TAMANO_MAXIMO_MB} MB.")
        return archivo


# formulario de registro de beneficiario
class BeneficiarioForm(forms.ModelForm):

    sexo = forms.ChoiceField(
        choices=[
            ("Femenino", "Femenino"),
            ("Masculino", "Masculino"),
        ],
        widget=forms.Select(attrs={"class": "form-control"})
    )
            
    migrante = forms.ChoiceField(
        choices=[
            ("Sí", "Sí"),
            ("No", "No"),
        ],
        widget=forms.Select(attrs={"class": "form-control"})
    )
            
    ayuda_tecnica = forms.ChoiceField(
        choices=[
            ("Sí", "Sí"),
            ("No", "No"),
        ],
        widget=forms.Select(attrs={"class": "form-control"})
    )

    class Meta:
        model = Beneficiario

        fields = [
            "nombres",
            "apellidos",
            "municipio_nacimiento",
            "fecha_nacimiento",
            "sexo",
            "direccion",
            "telefono",
            "correo",
            "ocupacion",
            "descripcion_ocupacion",
            "ingreso_mensual",
            "migrante",
            "discapacidad",
            "causa_origen",
            "tipo_discapacidad",
            "descripcion_discapacidad",
            "ayuda_tecnica",
            "tipo_ayuda",
            "organizacion",
            "fecha_ingreso_org",
            "beneficios_org",
            "descripcion_benef",
            "estado_civil",
            "grado",
        ]

        widgets = {
            "nombres": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ingrese los nombres"
            }),

            "apellidos": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ingrese los apellidos"
            }),

            "municipio_nacimiento": forms.Select(attrs={
                "class": "form-control"
            }),

            "fecha_nacimiento": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),

            "sexo": forms.Select(attrs={
                "class": "form-control"
            }),

            "direccion": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Dirección de residencia"
            }),

            "telefono": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Número de teléfono"
            }),

            "correo": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "correo@ejemplo.com"
            }),

            "ocupacion": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "descripcion_ocupacion": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),

            "ingreso_mensual": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00"
            }),

            "migrante": forms.Select(attrs={
                "class": "form-control"
            }),

            "discapacidad": forms.Select(attrs={
                "class": "form-control"
            }),

            "causa_origen": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "tipo_discapacidad": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Especifique el tipo de discapacidad"
            }),

            "descripcion_discapacidad": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),

            "ayuda_tecnica": forms.Select(attrs={
                "class": "form-control"
            }),

            "tipo_ayuda": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Especifique la ayuda técnica"
            }),

            "organizacion": forms.Select(attrs={
                "class": "form-control"
            }),

            "fecha_ingreso_org": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),

            "beneficios_org": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),

            "descripcion_benef": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),

            "estado_civil": forms.Select(attrs={
                "class": "form-control"
            }),

            "grado": forms.Select(attrs={
                "class": "form-control"
            }),

        }

        labels = {
            "nombres": "Nombres",
            "apellidos": "Apellidos",
            "municipio_nacimiento": "Municipio de nacimiento",
            "fecha_nacimiento": "Fecha de nacimiento",
            "sexo": "Sexo",
            "direccion": "Dirección",
            "telefono": "Teléfono",
            "correo": "Correo electrónico",
            "ocupacion": "Ocupación",
            "descripcion_ocupacion": "Descripción de la ocupación",
            "ingreso_mensual": "Ingreso mensual",
            "migrante": "Condición migratoria",
            "discapacidad": "Origen de la discapacidad",
            "causa_origen": "Causa de origen",
            "tipo_discapacidad": "Tipo de discapacidad",
            "descripcion_discapacidad": "Descripción de la discapacidad",
            "ayuda_tecnica": "¿Utiliza ayuda técnica?",
            "tipo_ayuda": "Tipo de ayuda técnica",
            "organizacion": "Organización",
            "fecha_ingreso_org": "Fecha de ingreso a la organización",
            "beneficios_org": "Beneficios recibidos",
            "descripcion_benef": "Descripción del beneficio o estado de atención",
            "estado_civil": "Estado civil",
            "grado": "Nivel educativo y grado",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Mostrar únicamente discapacidades aplicables.
        self.fields["discapacidad"].queryset = (
            Discapacidad.objects.exclude(
                discapacidad__iexact="No aplica"
            )
        )

        # Ordenar las opciones de los campos relacionados.
        self.fields["municipio_nacimiento"].queryset = (
            Municipio.objects.select_related("departamento")
            .order_by("departamento__departamento", "municipio")
        )

        self.fields["organizacion"].queryset = (
            Organizacion.objects.all()
        )

        self.fields["estado_civil"].queryset = (
            EstadoCivil.objects.all()
        )

        self.fields["grado"].queryset = (
            Educacion.objects.select_related("nivel")
            .order_by("nivel__nivel", "grado")
        )

class CuidadorForm(forms.ModelForm):

    class Meta:
        model = Cuidador
        fields = [
            'nombre_cuidador',
            'parentesco_cuidador',
            'sexo_cuidador',
            'edad_cuidador',
            'direccion_cuidador',
            'telefono_cuidador',
        ]

        widgets = {
            'nombre_cuidador': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo'
            }),
            'parentesco_cuidador': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. Madre, padre, hermano'
            }),
            'sexo_cuidador': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sexo'
            }),
            'edad_cuidador': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Edad'
            }),
            'direccion_cuidador': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección'
            }),
            'telefono_cuidador': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de teléfono'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # El cuidador es opcional.
        for field in self.fields.values():
            field.required = False