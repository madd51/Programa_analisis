import logging
from django.shortcuts import render, redirect
from . import etl
from .forms import SubirArchivoForm, BeneficiarioForm, CuidadorForm
from django.db.models import Q
from .models import Beneficiario, BeneficiarioCuidador
from datetime import date
import pandas as pd
import plotly.express as px
import plotly.io as pio
from django.contrib import messages
from django.db import transaction

logger = logging.getLogger(__name__)


def inicio(request):
    return render(request, 'core/index.html')

def subir_archivo(request):
    contexto = {"form": SubirArchivoForm()}
    if request.method == "POST":
        form = SubirArchivoForm(request.POST, request.FILES)
        contexto["form"] = form
        if form.is_valid():
            archivo = form.cleaned_data["archivo"]
            try:
                resultado = etl.limpiar(etl.leer_archivo(archivo.name, archivo.read()))
                contexto["resultado"] = resultado
                if form.cleaned_data["solo_validar"]:
                    contexto["modo_validacion"] = True
                elif resultado.n_validas:
                    contexto["carga"] = etl.cargar_en_bd(resultado.datos)
            except etl.ErrorETL as error:
                form.add_error("archivo", str(error))
            except Exception:
                logger.exception("Error al procesar el archivo")
                form.add_error(None, "Ocurrió un error al guardar en la base de datos. Revisa la consola del servidor.")
    return render(request, "core/subir.html", contexto)


def dashboard(request):
    # 1. Consultar SOLO beneficiarios con discapacidad registrada.
    # Excluir "No aplica" tanto del origen como del tipo.
    base_qs = Beneficiario.objects.select_related(
        "municipio_nacimiento__departamento",
        "discapacidad",
    ).exclude(
        discapacidad__discapacidad__iexact="No aplica"
    ).exclude(
        tipo_discapacidad__iexact="No aplica"
    )

    # Opciones de filtros: se obtienen de los datos guardados.
    # 2. Los filtros se construyen únicamente con personas
    # que sí tienen una discapacidad registrada.
    departamentos = list(
        base_qs.values_list(
            "municipio_nacimiento__departamento__departamento",
            flat=True,
        ).distinct().order_by(
            "municipio_nacimiento__departamento__departamento"
        )
    )

    sexos = list(
        base_qs.values_list(
            "sexo", flat=True
        ).distinct().order_by("sexo")
    )

    tipos_discapacidad = list(
        base_qs.values_list(
            "tipo_discapacidad", flat=True
        ).distinct().order_by("tipo_discapacidad")
    )

    # Leer filtros enviados desde la página.
    f_departamento = request.GET.get("departamento", "")
    f_sexo = request.GET.get("sexo", "")
    f_discapacidad = request.GET.get("discapacidad", "")

    # Partimos siempre de la consulta filtrada.
    qs = base_qs
    
    if f_departamento:
        qs = qs.filter(
            municipio_nacimiento__departamento__departamento=f_departamento
        )

    if f_sexo:
        qs = qs.filter(sexo=f_sexo)

    if f_discapacidad:
        qs = qs.filter(tipo_discapacidad=f_discapacidad)

    # Campos necesarios para los tres gráficos.
    registros = list(qs.values(
        "id_beneficiario",
        "fecha_nacimiento",
        "sexo",
        "tipo_discapacidad",
        "municipio_nacimiento__departamento__departamento",
        "ayuda_tecnica",
        "tipo_ayuda",
        "beneficios_org",
        "descripcion_benef",
    ))

    df = pd.DataFrame(registros)

    graficos = []
    kpis = {}
    hallazgos = []

    if not df.empty:
        df = df.rename(columns={
            "municipio_nacimiento__departamento__departamento":
                "departamento",
            "tipo_discapacidad": "discapacidad",
            "beneficios_org": "beneficio",
            "descripcion_benef": "descripcion",
        })

        # Calcular edad actual a partir de la fecha de nacimiento.
        df["fecha_nacimiento"] = pd.to_datetime(
            df["fecha_nacimiento"], errors="coerce"
        )

        hoy = date.today()

        def calcular_edad(fecha):
            if pd.isna(fecha):
                return None

            return (
                hoy.year - fecha.year
                - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
            )

        df["edad"] = df["fecha_nacimiento"].apply(calcular_edad)

        # Agrupar edades para facilitar la lectura.
        df["grupo_edad"] = pd.cut(
            df["edad"],
            bins=[0, 17, 29, 59, 120],
            labels=["0–17", "18–29", "30–59", "60+"],
            include_lowest=True,
        )

        # Normalizar estados para evitar diferencias de mayúsculas.
        df["ayuda_si"] = (
            df["ayuda_tecnica"].fillna("")
            .astype(str).str.strip().str.lower()
            .isin(["sí", "si"])
        )

        df["en_evaluacion"] = (
            df["descripcion"].fillna("")
            .astype(str).str.contains(
                r"en proceso de evaluación|en proceso de evaluacion",
                case=False, regex=True
            )
        )

        total = len(df)
        evaluacion = int(df["en_evaluacion"].sum())
        usan_ayuda = int(df["ayuda_si"].sum())

        kpis = {
            "total": total,
            "evaluacion": evaluacion,
            "porcentaje_evaluacion": round(
                evaluacion / total * 100, 1
            ) if total else 0,
            "usan_ayuda": usan_ayuda,
            "porcentaje_ayuda": round(
                usan_ayuda / total * 100, 1
            ) if total else 0,
        }

        def agregar_grafico(fig, titulo):
            fig.update_layout(
                title=titulo,
                template="plotly_white",
                font=dict(family="Arial", color="#26364A"),
                margin=dict(l=25, r=25, t=65, b=45),
                legend_title_text="",
            )

            graficos.append({
                "titulo": titulo,
                "html": pio.to_html(
                    fig,
                    full_html=False,
                    include_plotlyjs=False,
                    config={
                        "responsive": True,
                        "displaylogo": False,
                    },
                ),
            })

        # GRÁFICO 1:
        # Beneficios registrados por departamento.
        # Nota: beneficios_org representa una categoría de beneficio,
        # no un historial confirmado de servicios entregados.
        servicios = df.copy()

        servicios["beneficio"] = (
            servicios["beneficio"].fillna("Sin información")
            .replace("", "Sin información")
        )

        servicios = servicios[
            servicios["beneficio"].str.lower() != "ninguno"
        ]

        resumen_servicios = (
            servicios.groupby(
                ["departamento", "beneficio"], dropna=False
            )
            .size()
            .reset_index(name="personas")
        )

        # Ordenar los departamentos por total de registros.
        orden_deptos = (
            resumen_servicios.groupby("departamento")["personas"]
            .sum().sort_values(ascending=False).index.tolist()
        )

        if not resumen_servicios.empty:
            agregar_grafico(
                px.bar(
                    resumen_servicios,
                    x="departamento",
                    y="personas",
                    color="beneficio",
                    barmode="stack",
                    category_orders={"departamento": orden_deptos},
                    labels={
                        "departamento": "Departamento",
                        "personas": "Registros",
                        "beneficio": "Categoría de beneficio",
                    },
                ),
                "1. Beneficios registrados por departamento"
            )

        # GRÁFICO 2:
        # Distribución por edad y género.
        perfil = (
            df.dropna(subset=["grupo_edad", "sexo"])
            .groupby(["grupo_edad", "sexo"], observed=False)
            .size()
            .reset_index(name="personas")
        )

        if not perfil.empty:
            agregar_grafico(
                px.bar(
                    perfil,
                    x="grupo_edad",
                    y="personas",
                    color="sexo",
                    barmode="group",
                    category_orders={
                        "grupo_edad": ["0–17", "18–29", "30–59", "60+"]
                    },
                    labels={
                        "grupo_edad": "Grupo de edad",
                        "personas": "Beneficiarios",
                        "sexo": "Género",
                    },
                ),
                "2. Perfil de beneficiarios por edad y género"
            )

        # GRÁFICO 3:
        # Posibles necesidades de atención por departamento.
        # No usar ayudas técnicas no demuestra por sí solo una necesidad.
        brechas = (
            df.groupby("departamento", dropna=False)
            .agg(
                total=("id_beneficiario", "count"),
                en_evaluacion=("en_evaluacion", "sum"),
                sin_ayuda=("ayuda_si", lambda s: (~s).sum()),
            )
            .reset_index()
        )

        brechas["porcentaje_evaluacion"] = (
            brechas["en_evaluacion"]
            / brechas["total"].replace(0, pd.NA) * 100
        ).fillna(0).round(1)

        brechas = brechas.sort_values(
            "en_evaluacion", ascending=False
        )

        brechas_largas = brechas.melt(
            id_vars=["departamento", "total",
                     "porcentaje_evaluacion"],
            value_vars=["en_evaluacion", "sin_ayuda"],
            var_name="indicador",
            value_name="personas",
        )

        brechas_largas["indicador"] = brechas_largas[
            "indicador"
        ].map({
            "en_evaluacion": "En evaluación",
            "sin_ayuda": "No usan ayudas técnicas",
        })

        agregar_grafico(
            px.bar(
                brechas_largas,
                x="departamento",
                y="personas",
                color="indicador",
                barmode="group",
                category_orders={
                    "departamento": brechas["departamento"].tolist()
                },
                hover_data=["total", "porcentaje_evaluacion"],
                labels={
                    "departamento": "Departamento",
                    "personas": "Personas",
                    "indicador": "Indicador",
                },
            ),
            "3. Evaluación y uso de ayudas técnicas por departamento"
        )

        # GRÁFICO 4:
        # Distribución de beneficiarios por tipo de discapacidad.
        distribucion_discapacidad = (
            df.groupby("discapacidad", dropna=False)
            .agg(
                personas=("id_beneficiario", "count")
            )
            .reset_index()
        )

        # Ordenar de mayor a menor cantidad.
        distribucion_discapacidad = (
            distribucion_discapacidad
            .sort_values("personas", ascending=False)
        )

        # Calcular porcentaje de participación.
        distribucion_discapacidad["porcentaje"] = (
            distribucion_discapacidad["personas"] / len(df) * 100
        ).round(1)

        # Crear gráfico.
        fig_discapacidad = px.bar(
            distribucion_discapacidad,
            x="personas",
            y="discapacidad",
            orientation="h",
            text="personas",
            color="porcentaje",
            color_continuous_scale=["#DCE8F2", "#203A59"],
            hover_data={
                "personas": True,
                "porcentaje": True,
            },
            labels={
                "personas": "Cantidad de beneficiarios",
                "discapacidad": "Tipo de discapacidad",
                "porcentaje": "Porcentaje (%)",
            },
        )

        fig_discapacidad.update_traces(
            textposition="outside"
        )

        fig_discapacidad.update_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_colorbar_title="Porcentaje (%)",
        )

        agregar_grafico(
            fig_discapacidad,
            "4. Beneficiarios por tipo de discapacidad"
        )


        # Hallazgos calculados con los filtros actuales.
        hallazgos = [
            f"Se analizaron {total} beneficiarios.",
            (
                f"{evaluacion} personas ({kpis['porcentaje_evaluacion']} %) "
                "tienen una descripción que indica proceso de evaluación."
            ),
            (
                f"{usan_ayuda} personas ({kpis['porcentaje_ayuda']} %) "
                "figuran como usuarias de ayudas técnicas."
            ),
        ]

        if not brechas.empty:
            mayor = brechas.iloc[0]
            hallazgos.append(
                f"{mayor['departamento']} presenta "
                f"{int(mayor['en_evaluacion'])} personas en evaluación."
            )

    contexto = {
        "sin_datos": df.empty,
        "kpis": kpis,
        "graficos": graficos,
        "hallazgos": hallazgos,
        "departamentos": departamentos,
        "sexos": sexos,
        "tipos_discapacidad": tipos_discapacidad,
        "filtro_departamento": f_departamento,
        "filtro_sexo": f_sexo,
        "filtro_discapacidad": f_discapacidad,
    }

    return render(request, "core/dashboard.html", contexto)

# formulario de registro de beneficiario
def formulario(request):

    if request.method == "POST":
        form = BeneficiarioForm(request.POST)
        cuidador_form = CuidadorForm(
            request.POST,
            prefix="cuidador"
        )

        # Si se comenzó a completar el cuidador,
        # todos sus campos serán obligatorios.
        if cuidador_form.has_changed():
            for field in cuidador_form.fields.values():
                field.required = True

        beneficiario_valido = form.is_valid()
        cuidador_valido = cuidador_form.is_valid()

        if beneficiario_valido and cuidador_valido:

            with transaction.atomic():

                beneficiario = form.save()

                if cuidador_form.has_changed():

                    cuidador = cuidador_form.save()

                    BeneficiarioCuidador.objects.create(
                        beneficiario=beneficiario,
                        cuidador=cuidador
                    )

            messages.success(
                request,
                "El beneficiario fue registrado correctamente."
            )

            return redirect("formulario")

        else:
            messages.error(
                request,
                "Revisa los campos del formulario antes de continuar."
            )

    else:
        form = BeneficiarioForm()
        cuidador_form = CuidadorForm(prefix="cuidador")

    grupos = [
        {
            "titulo": "Datos personales",
            "numero": "01",
            "campos": [
                form["nombres"],
                form["apellidos"],
                form["fecha_nacimiento"],
                form["sexo"],
                form["municipio_nacimiento"],
                form["direccion"],
                form["estado_civil"],
                form["grado"],
            ]
        },
        {
            "titulo": "Información socioeconómica",
            "numero": "02",
            "campos": [
                form["telefono"],
                form["correo"],
                form["ocupacion"],
                form["descripcion_ocupacion"],
                form["ingreso_mensual"],
                form["migrante"],
            ]
        },
        {
            "titulo": "Información sobre discapacidad",
            "numero": "03",
            "campos": [
                form["discapacidad"],
                form["causa_origen"],
                form["tipo_discapacidad"],
                form["descripcion_discapacidad"],
                form["ayuda_tecnica"],
                form["tipo_ayuda"],
            ]
        },
        {
            "titulo": "Información organizacional",
            "numero": "04",
            "campos": [
                form["organizacion"],
                form["fecha_ingreso_org"],
                form["beneficios_org"],
                form["descripcion_benef"],
            ]
        },
    ]

    campos_cuidador = [
        cuidador_form["nombre_cuidador"],
        cuidador_form["parentesco_cuidador"],
        cuidador_form["sexo_cuidador"],
        cuidador_form["edad_cuidador"],
        cuidador_form["direccion_cuidador"],
        cuidador_form["telefono_cuidador"],
    ]

    return render(request, "core/formulario.html", {
        "form": form,
        "cuidador_form": cuidador_form,
        "grupos": grupos,
        "campos_cuidador": campos_cuidador,
    })
