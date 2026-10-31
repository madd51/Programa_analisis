"""ETL de beneficiarios: lectura (CSV/Excel), limpieza con corrección de tipos y carga a la base de datos.

Flujo:
    leer_archivo()  ->  limpiar()  ->  cargar_en_bd()
    (Extract)           (Transform)    (Load)

`leer_archivo` y `limpiar` solo usan pandas, así que se pueden probar sin Django.
`cargar_en_bd` es la única función que usa los modelos de Django.
"""
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd


class ErrorETL(Exception):
    """Error comprensible para el usuario (archivo inválido, faltan columnas, etc.)."""


# ---------------------------------------------------------------------------
# Definición de columnas
# ---------------------------------------------------------------------------
# nombre interno -> variantes aceptadas del encabezado (se comparan sin tildes, mayúsculas ni símbolos)
COLUMNAS = {
    "n": ["n"],
    "nombres": ["nombre", "nombres"],
    "apellidos": ["apellidos", "apellido"],
    "municipio": ["municipio"],
    "departamento": ["departamento"],
    "fecha_nacimiento": ["fecha_de_nacimiento", "fecha_nacimiento"],
    "edad": ["edad"],
    "sexo": ["sexo"],
    "estado_civil": ["estado_civil"],
    "direccion": ["direccion"],
    "telefono": ["telefono"],
    "correo": ["correo_electronico", "correo"],
    "nivel_educativo": ["nivel_educativo"],
    "ultimo_grado": ["ultimo_grado_aprobado", "ultimo_grado"],
    "ocupacion": ["ocupacion"],
    "descripcion_ocupacion": ["descripcion_de_ocupacion", "descripcion_ocupacion"],
    "ingreso_mensual": ["promedio_ingresos_mensuales_usd", "ingreso_mensual", "ingreso_mensual_usd"],
    "migrante": ["migrante"],
    "origen_discapacidad": ["discapacidad", "origen_discapacidad"],
    "causa_origen": ["causa_u_origen", "causa_origen"],
    "tipo_discapacidad": ["tipo_de_discapacidad", "tipo_discapacidad"],
    "descripcion_discapacidad": ["descripcion_de_discapacidad", "descripcion_discapacidad"],
    "usa_ayuda_tecnica": ["usa_ayudas_tecnicas", "usa_ayuda_tecnica", "ayuda_tecnica"],
    "tipo_ayuda": ["tipo_de_ayuda_tecnica", "tipo_ayuda"],
    "tiene_cuidador": ["tiene_cuidador"],
    "nombre_cuidador": ["nombre_del_cuidador", "nombre_cuidador"],
    "parentesco_cuidador": ["parentesco_cuidador"],
    "sexo_cuidador": ["sexo_cuidador"],
    "edad_cuidador": ["edad_cuidador"],
    "direccion_cuidador": ["direccion_cuidador"],
    "telefono_cuidador": ["telefono_cuidador"],
    "pertenece_org": ["pertenece_a_organizacion", "pertenece_org"],
    "organizacion": ["nombre_de_organizacion", "organizacion"],
    "fecha_ingreso_org": ["fecha_ingreso_organizacion", "fecha_ingreso_org"],
    "servicio": ["beneficios_red_de_sobrevivientes", "servicio", "beneficios_org"],
    "descripcion_beneficio": ["descripcion_del_beneficio", "descripcion_beneficio", "descripcion_benef"],
}

# Columnas sin las cuales no se puede guardar a la persona (son NOT NULL en la base de datos)
OBLIGATORIAS = [
    "nombres", "apellidos", "municipio", "departamento", "fecha_nacimiento", "sexo", "estado_civil",
    "direccion", "nivel_educativo", "ultimo_grado", "migrante", "origen_discapacidad",
    "causa_origen", "tipo_discapacidad", "usa_ayuda_tecnica",
]

ETIQUETAS = {
    "nombres": "Nombre", "apellidos": "Apellidos", "municipio": "Municipio", "departamento": "Departamento",
    "fecha_nacimiento": "Fecha de nacimiento", "sexo": "Sexo", "estado_civil": "Estado civil",
    "direccion": "Dirección", "nivel_educativo": "Nivel educativo", "ultimo_grado": "Último grado aprobado",
    "migrante": "Migrante", "origen_discapacidad": "Discapacidad (origen)", "causa_origen": "Causa u origen",
    "tipo_discapacidad": "Tipo de discapacidad", "usa_ayuda_tecnica": "Usa ayudas técnicas",
    "telefono": "Teléfono", "correo": "Correo", "ocupacion": "Ocupación", "tipo_ayuda": "Tipo de ayuda técnica",
    "organizacion": "Organización", "nombre_cuidador": "Nombre del cuidador",
    "parentesco_cuidador": "Parentesco del cuidador", "sexo_cuidador": "Sexo del cuidador",
    "direccion_cuidador": "Dirección del cuidador", "telefono_cuidador": "Teléfono del cuidador",
    "edad_cuidador": "Edad del cuidador", "descripcion_discapacidad": "Descripción de la discapacidad",
    "servicio": "Servicio o beneficio", "descripcion_beneficio": "Descripción del beneficio",
}

# Longitud máxima de cada columna de texto en la base de datos
LIMITES = {
    "nombres": 100, "apellidos": 100, "municipio": 100, "departamento": 100, "direccion": 255,
    "telefono": 50, "correo": 150, "nivel_educativo": 100, "ultimo_grado": 100, "ocupacion": 100,
    "migrante": 20, "origen_discapacidad": 100, "causa_origen": 100, "tipo_discapacidad": 100,
    "usa_ayuda_tecnica": 20, "tipo_ayuda": 100, "estado_civil": 50, "organizacion": 150, "sexo": 20,
    "nombre_cuidador": 150, "parentesco_cuidador": 50, "sexo_cuidador": 20,
    "direccion_cuidador": 255, "telefono_cuidador": 50,
}

# Textos que significan "sin dato" y que deben guardarse como vacío (NULL) en columnas opcionales
MARCADORES = {
    "tipo_ayuda": {"ninguna"},
    "descripcion_discapacidad": {"sin discapacidad registrada"},
    "servicio": {"ninguno"},
    "descripcion_beneficio": {"no aplica (sin discapacidad registrada)"},
    "nombre_cuidador": {"no aplica"},
    "parentesco_cuidador": {"no aplica"},
    "sexo_cuidador": {"no aplica"},
    "edad_cuidador": {"no aplica"},
    "direccion_cuidador": {"no aplica"},
    "telefono_cuidador": {"no aplica"},
}
MARCADORES_FECHA = {"no pertence", "no pertenece", "no aplica", "ninguno", "ninguna"}

FORMATOS_FECHA = ("%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y")
MAX_INGRESO_ADVERTENCIA = Decimal("10000")
SIN_ORGANIZACION = "No pertenece"
SEXOS = {"masculino": "Masculino", "m": "Masculino", "hombre": "Masculino",
         "femenino": "Femenino", "f": "Femenino", "mujer": "Femenino"}
SI = {"si", "s", "yes", "y", "1", "true", "verdadero"}
NO = {"no", "n", "0", "false", "falso"}


# ---------------------------------------------------------------------------
# Resultado del proceso
# ---------------------------------------------------------------------------
@dataclass
class ResultadoETL:
    total_leidas: int = 0
    datos: pd.DataFrame = field(default_factory=pd.DataFrame)      # filas limpias y válidas
    rechazadas: list = field(default_factory=list)                  # [{'fila', 'nombre', 'motivo'}]
    advertencias: list = field(default_factory=list)                # avisos que no impiden guardar
    correcciones: list = field(default_factory=list)                # transformaciones aplicadas
    tipos: list = field(default_factory=list)                       # conversión de tipos por campo
    columnas_detectadas: list = field(default_factory=list)
    columnas_ignoradas: list = field(default_factory=list)

    @property
    def n_validas(self):
        return len(self.datos)

    @property
    def n_rechazadas(self):
        return len(self.rechazadas)

    @property
    def vista_previa(self):
        if self.datos.empty:
            return []
        filas = []
        for r in self.datos.head(10).to_dict("records"):
            filas.append({
                "fila": r["fila"], "nombres": r["nombres"], "apellidos": r["apellidos"],
                "fecha_nacimiento": r["fecha_nacimiento"].isoformat() if r["fecha_nacimiento"] else "",
                "departamento": r["departamento"], "municipio": r["municipio"],
                "ingreso_mensual": "" if _vacio(r["ingreso_mensual"]) else f"{r['ingreso_mensual']:.2f}",
                "servicio": "" if _vacio(r["servicio"]) else r["servicio"],
            })
        return filas


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _vacio(v):
    return v is None or bool(pd.isna(v))


def _nulo(v):
    """None si el valor está vacío (None, NaN, NaT); si no, el mismo valor."""
    return None if _vacio(v) else v


def _norm(texto):
    """'Último_Grado (USD)' -> 'ultimo_grado_usd' (sin tildes, minúsculas, solo letras y números)."""
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


_ALIAS = {_norm(v): interno for interno, variantes in COLUMNAS.items() for v in variantes}


def _texto(v):
    """Recorta espacios y convierte vacíos en None."""
    if _vacio(v):
        return None
    s = re.sub(r"[ \t]+", " ", str(v).strip())
    return s or None


def _fecha(v):
    if _vacio(v):
        return None
    s = str(v).strip()
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(s, formato).date()
        except ValueError:
            continue
    return None


def _dinero(v):
    """'$1,234.50 ' -> Decimal('1234.50'). Devuelve None si no se puede convertir."""
    if _vacio(v) or "-" in str(v):
        return None
    s = re.sub(r"[^0-9.,]", "", str(v))
    if not s:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")   # 1.234,50 (punto de miles, coma decimal)
        else:
            s = s.replace(",", "")                     # 1,234.50 (coma de miles, punto decimal)
    elif "," in s:
        if re.fullmatch(r"\d{1,3}(,\d{3})+", s):
            s = s.replace(",", "")                     # 1,234 (coma de miles)
        else:
            s = s.replace(",", ".")                    # 1234,50 (coma decimal)
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")                         # 1.234 (punto de miles)
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _entero(v):
    if _vacio(v):
        return None
    try:
        f = float(str(v).strip())
    except ValueError:
        return None
    return int(f) if f.is_integer() and 0 <= f <= 150 else None


def _sexo(v):
    return None if _vacio(v) else SEXOS.get(_norm(v))


def _si_no(v):
    if _vacio(v):
        return None
    k = _norm(v)
    return "Sí" if k in SI else "No" if k in NO else None


def _clave(v):
    """Clave para comparar textos sin distinguir mayúsculas, tildes ni espacios."""
    return _norm(v)


def _indices(df, mascara):
    return list(df.index[mascara.astype(bool).to_numpy()])


# ---------------------------------------------------------------------------
# EXTRACT: lectura del archivo
# ---------------------------------------------------------------------------
def leer_archivo(nombre, contenido):
    """Lee un CSV o Excel (.xlsx) y devuelve un DataFrame con todo como texto."""
    nombre = nombre.lower()
    try:
        if nombre.endswith(".csv"):
            try:
                texto = contenido.decode("utf-8-sig")
            except UnicodeDecodeError:
                texto = contenido.decode("latin-1")
            primera_linea = texto.splitlines()[0] if texto.strip() else ""
            separador = max([",", ";", "\t", "|"], key=primera_linea.count)
            df = pd.read_csv(io.StringIO(texto), sep=separador, dtype=str,
                             keep_default_na=False, na_values=[""])
        elif nombre.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(contenido), dtype=str)
        else:
            raise ErrorETL("Formato no permitido. Sube un archivo .csv o .xlsx.")
    except ErrorETL:
        raise
    except Exception as e:
        raise ErrorETL(f"No se pudo leer el archivo: {e}") from e
    if df.empty:
        raise ErrorETL("El archivo no contiene filas de datos.")
    return df.reset_index(drop=True).astype(object)


# ---------------------------------------------------------------------------
# TRANSFORM: limpieza, corrección de tipos y validación
# ---------------------------------------------------------------------------
def _estandarizar_columnas(df, res):
    renombres = {}
    for col in df.columns:
        interno = _ALIAS.get(_norm(col))
        if interno and interno not in renombres.values():
            renombres[col] = interno
        else:
            res.columnas_ignoradas.append(str(col))
    df = df.rename(columns=renombres)[list(renombres.values())].copy()
    faltan = [ETIQUETAS[c] for c in OBLIGATORIAS if c not in df.columns]
    if faltan:
        raise ErrorETL("Faltan columnas obligatorias en el archivo: " + ", ".join(faltan))
    for c in COLUMNAS:
        if c not in df.columns:
            df[c] = None
    res.columnas_detectadas = list(renombres.values())
    return df


def limpiar(df_raw):
    """Aplica todas las transformaciones y separa las filas válidas de las rechazadas."""
    res = ResultadoETL(total_leidas=len(df_raw))
    df = _estandarizar_columnas(df_raw.reset_index(drop=True), res)
    df["fila"] = range(2, len(df) + 2)                    # línea del archivo (la 1 es el encabezado)
    motivos = {i: [] for i in df.index}

    # 1) Espacios sobrantes y celdas vacías
    recortadas = 0
    for c in [c for c in df.columns if c != "fila"]:
        recortadas += int(df[c].map(lambda v: isinstance(v, str) and _texto(v) != v).sum())
        df[c] = df[c].map(_texto)
    if recortadas:
        res.correcciones.append(f"Espacios sobrantes eliminados en {recortadas} celdas de texto.")

    # 2) Textos de 'sin dato' (Ninguno, NO APLICA...) -> vacío, solo en columnas opcionales
    for col, marcas in MARCADORES.items():
        mascara = df[col].map(lambda v: isinstance(v, str) and v.lower() in marcas).astype(bool)
        n = int(mascara.sum())
        if n:
            df.loc[mascara, col] = None
            res.correcciones.append(f"{ETIQUETAS.get(col, col)}: {n} marcadores de 'sin dato' convertidos a vacío.")

    # 3) Fechas -> tipo fecha
    hoy = date.today()
    originales = df["fecha_nacimiento"].copy()
    df["fecha_nacimiento"] = originales.map(_fecha)
    for i in df.index:
        f, orig = _nulo(df.at[i, "fecha_nacimiento"]), _nulo(originales.at[i])
        if orig is not None and f is None:
            motivos[i].append(f"Fecha de nacimiento no reconocida: '{orig}'")
        elif f is not None and not (date(1900, 1, 1) <= f <= hoy):
            motivos[i].append(f"Fecha de nacimiento fuera de rango: {f.isoformat()}")
    res.tipos.append({"campo": "fecha_nacimiento", "antes": "Texto (M/D/AAAA)", "despues": "Fecha",
                      "convertidos": int(df["fecha_nacimiento"].map(lambda v: not _vacio(v)).sum())})

    originales = df["fecha_ingreso_org"].copy()
    df["fecha_ingreso_org"] = originales.map(_fecha)
    texto_no_fecha = 0
    for i in df.index:
        f, orig = _nulo(df.at[i, "fecha_ingreso_org"]), _nulo(originales.at[i])
        if orig is not None and f is None:
            if orig.lower() in MARCADORES_FECHA:
                texto_no_fecha += 1
            else:
                res.advertencias.append(
                    f"Fila {df.at[i, 'fila']}: fecha de ingreso no reconocida ('{orig}'); se dejó vacía.")
        elif f is not None and f > hoy:
            res.advertencias.append(f"Fila {df.at[i, 'fila']}: la fecha de ingreso es futura ({f.isoformat()}).")
    if texto_no_fecha:
        res.correcciones.append(
            f"Fecha de ingreso a la organización: {texto_no_fecha} textos como 'No pertence' convertidos a vacío.")
    res.tipos.append({"campo": "fecha_ingreso_org", "antes": "Texto (M/D/AAAA o 'No pertence')", "despues": "Fecha (vacía si no aplica)",
                      "convertidos": int(df["fecha_ingreso_org"].map(lambda v: not _vacio(v)).sum())})

    # 4) Ingreso mensual -> decimal
    originales = df["ingreso_mensual"].copy()
    df["ingreso_mensual"] = originales.map(_dinero)
    for i in df.index:
        if not _vacio(originales.at[i]) and _vacio(df.at[i, "ingreso_mensual"]):
            res.advertencias.append(
                f"Fila {df.at[i, 'fila']}: ingreso mensual no reconocido ('{originales.at[i]}'); se dejó vacío.")
    res.tipos.append({"campo": "ingreso_mensual", "antes": "Texto con $, comas y espacios", "despues": "Decimal (2 decimales)",
                      "convertidos": int(df["ingreso_mensual"].map(lambda v: not _vacio(v)).sum())})
    altos = [i for i in df.index if not _vacio(df.at[i, "ingreso_mensual"])
             and df.at[i, "ingreso_mensual"] > MAX_INGRESO_ADVERTENCIA]
    if altos:
        filas = ", ".join(str(df.at[i, "fila"]) for i in altos[:10]) + ("..." if len(altos) > 10 else "")
        res.advertencias.append(
            f"{len(altos)} ingresos mensuales superan $10,000 (filas {filas}). Se cargaron sin cambios; "
            "conviene revisar si son errores o montos anuales.")

    # 5) Edad del cuidador -> entero
    originales = df["edad_cuidador"].copy()
    df["edad_cuidador"] = originales.map(_entero)
    res.tipos.append({"campo": "edad_cuidador", "antes": "Texto (número o 'NO APLICA')", "despues": "Entero",
                      "convertidos": int(df["edad_cuidador"].map(lambda v: not _vacio(v)).sum())})

    # 6) Categorías: sexo, Sí/No, estado civil, organización
    df["sexo"] = df["sexo"].map(lambda v: _sexo(v) if _sexo(v) else v)
    for i in _indices(df, df["sexo"].map(lambda v: not _vacio(v) and _sexo(v) is None)):
        motivos[i].append(f"Sexo no reconocido: '{df.at[i, 'sexo']}'")
    df["sexo_cuidador"] = df["sexo_cuidador"].map(lambda v: _sexo(v) if _sexo(v) else v)

    for col in ("migrante", "usa_ayuda_tecnica"):
        for i in df.index:
            orig = _nulo(df.at[i, col])
            if orig is None:
                continue
            nuevo = _si_no(orig)
            if nuevo is None:
                motivos[i].append(f"{ETIQUETAS[col]} no reconocido: '{orig}' (use Sí o No)")
            df.at[i, col] = nuevo or orig

    soltera = df["estado_civil"].map(lambda v: v == "Soltera")
    if int(soltera.sum()):
        df.loc[soltera.astype(bool), "estado_civil"] = "Soltero"
        res.correcciones.append(
            f"Estado civil: {int(soltera.sum())} registros 'Soltera' unificados como 'Soltero' (el catálogo no distingue género).")

    sin_org = df["organizacion"].isna()
    if int(sin_org.sum()):
        df.loc[sin_org, "organizacion"] = SIN_ORGANIZACION
        res.correcciones.append(
            f"Organización: {int(sin_org.sum())} filas sin organización se guardaron como '{SIN_ORGANIZACION}'.")

    # 7) Correo: se restaura el punto del dominio cuando viene como guion (gmail-com -> gmail.com)
    arreglados = invalidos = 0
    for i in df.index:
        c = _nulo(df.at[i, "correo"])
        if c is None:
            continue
        c = c.replace(" ", "")
        if "@" in c and "." not in c.split("@", 1)[1]:
            corregido = c.replace("-", ".")
            arreglados += corregido != c
            c = corregido
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", c):
            df.at[i, "correo"] = c
        else:
            df.at[i, "correo"] = None
            invalidos += 1
    if arreglados:
        res.correcciones.append(f"Correo: {arreglados} correos con el dominio sin punto (gmail-com) corregidos.")
    if invalidos:
        res.advertencias.append(f"{invalidos} correos con formato inválido se dejaron vacíos.")

    # 8) Campos obligatorios y longitudes
    for c in OBLIGATORIAS:
        for i in _indices(df, df[c].isna()):
            if not any(m.startswith(ETIQUETAS[c]) for m in motivos[i]):
                motivos[i].append(f"{ETIQUETAS[c]} vacío")
    for c, limite in LIMITES.items():
        largos = df[c].map(lambda v, lim=limite: isinstance(v, str) and len(v) > lim)
        for i in _indices(df, largos):
            motivos[i].append(f"{ETIQUETAS.get(c, c)} excede {limite} caracteres")

    # 9) Repetidos dentro del mismo archivo
    claves = df.apply(lambda r: (_clave(r["nombres"]), _clave(r["apellidos"]), r["fecha_nacimiento"]), axis=1)
    repetidas = int(claves.duplicated().sum())
    if repetidas:
        res.advertencias.append(
            f"{repetidas} filas repiten nombre, apellidos y fecha de nacimiento dentro del archivo; solo se cargará la primera.")

    # 10) Resultado
    validas = [i for i in df.index if not motivos[i]]
    res.datos = df.loc[validas].reset_index(drop=True)
    for i, lista in motivos.items():
        if lista:
            nombre = f"{_nulo(df.at[i, 'nombres']) or ''} {_nulo(df.at[i, 'apellidos']) or ''}".strip()
            res.rechazadas.append({"fila": int(df.at[i, "fila"]), "nombre": nombre, "motivo": "; ".join(lista)})
    return res


# ---------------------------------------------------------------------------
# LOAD: carga a la base de datos con el ORM de Django
# ---------------------------------------------------------------------------
def _asegurar_catalogo(modelo, campo, valores):
    """Crea los valores que no existan (sin distinguir mayúsculas ni tildes). Devuelve ({clave: objeto}, nuevos)."""
    existentes = {_clave(getattr(o, campo)): o for o in modelo.objects.all()}
    nuevos = 0
    for v in valores:
        k = _clave(v)
        if k not in existentes:
            existentes[k] = modelo.objects.create(**{campo: v})
            nuevos += 1
    return existentes, nuevos


def _datos_cuidador(r):
    """Devuelve los datos del cuidador, None si no hay, o False si están incompletos."""
    campos = ["nombre_cuidador", "parentesco_cuidador", "sexo_cuidador", "edad_cuidador",
              "direccion_cuidador", "telefono_cuidador"]
    valores = {c: (None if _vacio(r[c]) else r[c]) for c in campos}
    if all(v is None for v in valores.values()):
        return None
    if any(v is None for v in valores.values()):
        return False
    valores["edad_cuidador"] = int(valores["edad_cuidador"])
    return valores


def cargar_en_bd(df):
    """Guarda en PostgreSQL las filas limpias. Todo ocurre en una transacción: si algo falla, no se guarda nada."""
    from django.db import transaction

    from .models import (
        Beneficiario, BeneficiarioCuidador, Cuidador, Departamento, Discapacidad,
        Educacion, EstadoCivil, Municipio, NivelEducativo, Organizacion,
    )

    registros = df.to_dict("records")
    informe = {"filas_recibidas": len(registros), "insertados": 0, "duplicados_omitidos": 0,
               "cuidadores": 0, "cuidadores_incompletos": 0, "catalogos_nuevos": {}}

    with transaction.atomic():
        # --- Catálogos (se crean solo los valores que no existen) ---
        deptos, n = _asegurar_catalogo(Departamento, "departamento", [r["departamento"] for r in registros])
        informe["catalogos_nuevos"]["Departamentos"] = n
        origenes, n = _asegurar_catalogo(Discapacidad, "discapacidad", [r["origen_discapacidad"] for r in registros])
        informe["catalogos_nuevos"]["Discapacidades (origen)"] = n
        orgs, n = _asegurar_catalogo(Organizacion, "nombre_organizacion", [r["organizacion"] for r in registros])
        informe["catalogos_nuevos"]["Organizaciones"] = n
        estados, n = _asegurar_catalogo(EstadoCivil, "estado", [r["estado_civil"] for r in registros])
        informe["catalogos_nuevos"]["Estados civiles"] = n
        niveles, n = _asegurar_catalogo(NivelEducativo, "nivel", [r["nivel_educativo"] for r in registros])
        informe["catalogos_nuevos"]["Niveles educativos"] = n

        # --- Catálogos que dependen de otro (municipio -> departamento, grado -> nivel) ---
        municipios = {(_clave(m.municipio), m.departamento_id): m for m in Municipio.objects.all()}
        grados = {(_clave(g.grado), g.nivel_id): g for g in Educacion.objects.all()}
        nuevos_mun = nuevos_gra = 0
        for r in registros:
            depto = deptos[_clave(r["departamento"])]
            k = (_clave(r["municipio"]), depto.pk)
            if k not in municipios:
                municipios[k] = Municipio.objects.create(municipio=r["municipio"], departamento=depto)
                nuevos_mun += 1
            r["_municipio"] = municipios[k]

            nivel = niveles[_clave(r["nivel_educativo"])]
            k = (_clave(r["ultimo_grado"]), nivel.pk)
            if k not in grados:
                grados[k] = Educacion.objects.create(grado=r["ultimo_grado"], nivel=nivel)
                nuevos_gra += 1
            r["_grado"] = grados[k]
        informe["catalogos_nuevos"]["Municipios"] = nuevos_mun
        informe["catalogos_nuevos"]["Grados"] = nuevos_gra

        # --- Beneficiarios (se omiten los que ya existen: mismo nombre, apellidos y fecha de nacimiento) ---
        vistos = {(_clave(n), _clave(a), f) for n, a, f in
                  Beneficiario.objects.values_list("nombres", "apellidos", "fecha_nacimiento")}
        nuevos, datos_cuidadores = [], []
        for r in registros:
            clave = (_clave(r["nombres"]), _clave(r["apellidos"]), r["fecha_nacimiento"])
            if clave in vistos:
                informe["duplicados_omitidos"] += 1
                continue
            vistos.add(clave)
            nuevos.append(Beneficiario(
                nombres=r["nombres"], apellidos=r["apellidos"],
                municipio_nacimiento=r["_municipio"], fecha_nacimiento=r["fecha_nacimiento"],
                sexo=r["sexo"], direccion=r["direccion"],
                telefono=None if _vacio(r["telefono"]) else r["telefono"],
                correo=None if _vacio(r["correo"]) else r["correo"],
                ocupacion=None if _vacio(r["ocupacion"]) else r["ocupacion"],
                descripcion_ocupacion=None if _vacio(r["descripcion_ocupacion"]) else r["descripcion_ocupacion"],
                ingreso_mensual=None if _vacio(r["ingreso_mensual"]) else r["ingreso_mensual"],
                migrante=r["migrante"],
                discapacidad=origenes[_clave(r["origen_discapacidad"])],
                causa_origen=r["causa_origen"], tipo_discapacidad=r["tipo_discapacidad"],
                descripcion_discapacidad=None if _vacio(r["descripcion_discapacidad"]) else r["descripcion_discapacidad"],
                ayuda_tecnica=r["usa_ayuda_tecnica"],
                tipo_ayuda=None if _vacio(r["tipo_ayuda"]) else r["tipo_ayuda"],
                organizacion=orgs[_clave(r["organizacion"])],
                fecha_ingreso_org=None if _vacio(r["fecha_ingreso_org"]) else r["fecha_ingreso_org"],
                beneficios_org=None if _vacio(r["servicio"]) else r["servicio"],
                descripcion_benef=None if _vacio(r["descripcion_beneficio"]) else r["descripcion_beneficio"],
                estado_civil=estados[_clave(r["estado_civil"])], grado=r["_grado"],
            ))
            datos_cuidadores.append(_datos_cuidador(r))
        Beneficiario.objects.bulk_create(nuevos, batch_size=500)      # en PostgreSQL devuelve los id asignados
        informe["insertados"] = len(nuevos)

        # --- Cuidadores y su relación con el beneficiario ---
        cuidadores, duenos = [], []
        for beneficiario, datos in zip(nuevos, datos_cuidadores):
            if datos is False:
                informe["cuidadores_incompletos"] += 1
            elif datos:
                cuidadores.append(Cuidador(**datos))
                duenos.append(beneficiario)
        Cuidador.objects.bulk_create(cuidadores, batch_size=500)
        BeneficiarioCuidador.objects.bulk_create(
            [BeneficiarioCuidador(beneficiario=b, cuidador=c) for b, c in zip(duenos, cuidadores)],
            batch_size=500,
        )
        informe["cuidadores"] = len(cuidadores)

    return informe