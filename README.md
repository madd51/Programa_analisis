# Sistema de Gestión de Beneficiarios

Aplicación web desarrollada con **Django** y **PostgreSQL** para
registrar y consultar información de personas beneficiarias, incluyendo
sus datos personales, ubicación, información socioeconómica,
discapacidad, organización y cuidadores. El sistema incorpora un
dashboard para explorar indicadores y visualizar los datos registrados.

## 1. Tecnologías utilizadas

-   Python
-   Django
-   PostgreSQL
-   Pandas
-   Plotly
-   HTML y CSS

> Las versiones exactas de las dependencias deben consultarse en
> `requirements.txt`, si está incluido en el repositorio.

## 2. Requisitos previos

Antes de ejecutar el proyecto, instala o verifica lo siguiente:

1.  **Git**, para clonar el repositorio.
2.  **Python 3**, con una versión compatible con el proyecto.
3.  **PostgreSQL**, con el servicio de base de datos iniciado.
4.  **pip**, para instalar las dependencias de Python.
5.  Un editor de código, por ejemplo Visual Studio Code.

Comprueba las instalaciones desde una terminal:

``` bash
git --version
python --version
pip --version
psql --version
```

En algunos equipos Windows, el comando de Python puede ser `py` en lugar
de `python`.

## 3. Descargar el proyecto

Clona el repositorio desde GitHub. Sustituye la URL por la dirección
real del repositorio:

``` bash
git clone URL_DEL_REPOSITORIO
```

Entra en la carpeta descargada:

``` bash
cd NOMBRE_DEL_REPOSITORIO
```

También puedes descargar el repositorio como archivo ZIP desde GitHub y
extraerlo en tu equipo.

## 4. Crear y activar un entorno virtual

Se recomienda utilizar un entorno virtual para instalar las dependencias
sin afectar otros proyectos de Python.

### Windows (PowerShell)

``` powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Si utilizas el lanzador `py`:

``` powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación, puedes ejecutar esta instrucción
únicamente para la sesión actual:

``` powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Después, vuelve a ejecutar el comando de activación.

### Linux o macOS

``` bash
python3 -m venv venv
source venv/bin/activate
```

Cuando el entorno esté activo, normalmente aparecerá `(venv)` al inicio
de la línea de comandos.

## 5. Instalar las dependencias

Si el repositorio incluye un archivo `requirements.txt`, ejecuta:

``` bash
pip install -r requirements.txt
```

Si todavía no existe ese archivo, instala las dependencias declaradas
por el proyecto y utilizadas en el código. Como referencia, pueden
incluir:

``` bash
pip install django psycopg2-binary pandas plotly
```

Es preferible mantener un `requirements.txt` actualizado para que todas
las personas instalen las mismas versiones:

``` bash
pip freeze > requirements.txt
```

## 6. Configurar PostgreSQL

Inicia PostgreSQL y crea una base de datos para el sistema. Por ejemplo,
desde `psql`:

``` sql
CREATE DATABASE programa_analisis;
```

### Configurar la conexión en Django

Abre el archivo `settings.py` del proyecto y revisa la sección
`DATABASES`. La configuración debe apuntar a la base de datos local:

``` python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "programa_analisis",
        "USER": "USUARIO_POSTGRESQL",
        "PASSWORD": "CONTRASEÑA_POSTGRESQL",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
```

Sustituye `USUARIO_POSTGRESQL` y `CONTRASEÑA_POSTGRESQL` por las
credenciales locales de PostgreSQL.

**Seguridad:** no subas contraseñas, claves ni otros datos privados al
repositorio. Si el proyecto utiliza variables de entorno o un archivo
`.env`, configura los valores localmente y mantén ese archivo fuera del
control de versiones. Puedes incluir un `.env.example` sin credenciales
reales para documentar las variables necesarias.

## 7. Preparar la base de datos

Desde la carpeta que contiene `manage.py`, ejecuta las migraciones:

``` bash
python manage.py migrate
```

Si el proyecto tiene migraciones pendientes que todavía no están
creadas, genera los archivos correspondientes:

``` bash
python manage.py makemigrations
python manage.py migrate
```

No es necesario ejecutar `makemigrations` en cada instalación si las
migraciones ya están incluidas en el repositorio.

## 8. Ejecutar el sistema localmente

Inicia el servidor de desarrollo:

``` bash
python manage.py runserver
```

Abre el navegador y visita:

-   Aplicación: http://127.0.0.1:8000/

Si el proyecto utiliza una ruta inicial diferente, consulta las rutas
definidas en `urls.py`.

Para detener el servidor, presiona `Ctrl + C` en la terminal.

## 9. Funcionalidades principales

Según la implementación actual, el sistema contempla:

-   Registro de beneficiarios.
-   Captura de información personal y socioeconómica.
-   Registro de información relacionada con discapacidad.
-   Asociación del beneficiario con una organización.
-   Registro y asociación de cuidadores.
-   Consulta de información almacenada en PostgreSQL.
-   Dashboard con indicadores y gráficos para explorar los datos de
    beneficiarios.

La disponibilidad de cada módulo depende de la versión del código
descargada.

## 10. Estructura general del proyecto

La estructura puede variar según la organización del repositorio. Una
estructura Django habitual es:

``` text
NOMBRE_DEL_REPOSITORIO/
│
├── manage.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── templates/
│   └── base.html
│ 
└── core/
    ├── __pycache__/
    ├── migrations/
    ├── templates/
       └── core/
            ├── dashboard.html
            ├── formulario.html
            ├── index.html
            └── subir.html
    ├── static/
       ├── css/
            ├── styles.html
       └── img/
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── etl.py
    ├── forms.py
    ├── models.py
    ├── test.py
    ├── views.py
    └── urls.py
```


## 11. Solución de problemas frecuentes

### Error de conexión con PostgreSQL

Verifica que:

-   El servicio de PostgreSQL esté iniciado.
-   El nombre de la base de datos sea correcto.
-   El usuario y la contraseña sean válidos.
-   El host y el puerto coincidan con la configuración local.

### Error `No module named ...`

Activa el entorno virtual e instala las dependencias:

``` bash
pip install -r requirements.txt
```

### Error de migraciones

Comprueba que estás ejecutando los comandos desde la carpeta donde se
encuentra `manage.py` y que la conexión con PostgreSQL funciona.

``` bash
python manage.py showmigrations
python manage.py migrate
```

### El navegador muestra un error 404

Revisa las rutas configuradas en los archivos `urls.py` y confirma que
estás entrando a la dirección correcta.

### Los gráficos o el dashboard no cargan

Comprueba que las dependencias utilizadas por el dashboard estén
instaladas y que existan registros en la base de datos. También revisa
la terminal donde se ejecuta Django para identificar errores.

## 14. Buenas prácticas para colaborar

-   Crea una rama para cada cambio o funcionalidad.
-   No subas el entorno virtual (`venv/`) al repositorio.
-   No compartas contraseñas ni archivos `.env` con información privada.
-   Incluye las migraciones de Django cuando modifiques los modelos.
-   Actualiza `requirements.txt` cuando agregues o cambies dependencias.
-   Describe los cambios realizados en los mensajes de commit.

Ejemplo de trabajo con Git:

``` bash
git checkout -b nombre-de-la-funcionalidad
git add .
git commit -m "Describe el cambio realizado"
git push origin nombre-de-la-funcionalidad
```

## 15. Información para quien instala el proyecto por primera vez

Antes de considerar completa la instalación, verifica que:

-   [ ] El repositorio se descargó correctamente.
-   [ ] El entorno virtual está activo.
-   [ ] Las dependencias están instaladas.
-   [ ] PostgreSQL está iniciado.
-   [ ] La base de datos local está creada y configurada.
-   [ ] Las migraciones se ejecutaron correctamente.
-   [ ] El servidor Django inicia y la aplicación abre en el navegador.

------------------------------------------------------------------------

**Proyecto académico:** Sistema de Gestión de Beneficiarios\
**Backend:** Django\
**Base de datos:** PostgreSQL\
**Análisis y visualización:** Python, Pandas y Plotly
