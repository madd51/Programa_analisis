from django.db import models

# ----------------------------- Catálogos -----------------------------
 
class Departamento(models.Model):
    id_departamento = models.AutoField(primary_key=True)
    departamento = models.CharField(max_length=100, unique=True)
 
    class Meta:
        db_table = "departamentos"
        ordering = ["departamento"]
 
    def __str__(self):
        return self.departamento
 
 
class Municipio(models.Model):
    id_municipio = models.AutoField(primary_key=True)
    municipio = models.CharField(max_length=100)
    departamento = models.ForeignKey(
        Departamento, on_delete=models.PROTECT, db_column="id_departamento", related_name="municipios"
    )
 
    class Meta:
        db_table = "municipios"
        ordering = ["municipio"]
        constraints = [
            models.UniqueConstraint(fields=["municipio", "departamento"], name="uq_municipio_departamento")
        ]
 
    def __str__(self):
        return f"{self.municipio} ({self.departamento})"
 
 
class Organizacion(models.Model):
    id_organizacion = models.AutoField(primary_key=True)
    nombre_organizacion = models.CharField(max_length=150, unique=True)
 
    class Meta:
        db_table = "organizaciones"
        ordering = ["nombre_organizacion"]
 
    def __str__(self):
        return self.nombre_organizacion
 
 
class EstadoCivil(models.Model):
    id_estado = models.AutoField(primary_key=True)
    estado = models.CharField(max_length=50, unique=True)
 
    class Meta:
        db_table = "estado_civil"
        ordering = ["estado"]
 
    def __str__(self):
        return self.estado
 
 
class Discapacidad(models.Model):
    """Origen de la discapacidad: Adquirida, Congénita o No aplica."""
    id_discapacidad = models.AutoField(primary_key=True)
    discapacidad = models.CharField(max_length=100, unique=True)
 
    class Meta:
        db_table = "discapacidades"
        ordering = ["discapacidad"]
 
    def __str__(self):
        return self.discapacidad
 
 
class NivelEducativo(models.Model):
    id_nivel = models.AutoField(primary_key=True)
    nivel = models.CharField(max_length=100, unique=True)
 
    class Meta:
        db_table = "nivel_educativo"
        ordering = ["id_nivel"]
 
    def __str__(self):
        return self.nivel
 
 
class Educacion(models.Model):
    id_grado = models.AutoField(primary_key=True)
    grado = models.CharField(max_length=100)
    nivel = models.ForeignKey(
        NivelEducativo, on_delete=models.PROTECT, db_column="id_nivel", related_name="grados"
    )
 
    class Meta:
        db_table = "educacion"
        ordering = ["nivel", "grado"]
        constraints = [models.UniqueConstraint(fields=["grado", "nivel"], name="uq_grado_nivel")]
 
    def __str__(self):
        return self.grado
 
 
# ----------------------------- Tablas principales -----------------------------
 
class Cuidador(models.Model):
    id_cuidador = models.AutoField(primary_key=True)
    nombre_cuidador = models.CharField(max_length=150)
    parentesco_cuidador = models.CharField(max_length=50)
    sexo_cuidador = models.CharField(max_length=20)
    edad_cuidador = models.IntegerField()
    direccion_cuidador = models.CharField(max_length=255)
    telefono_cuidador = models.CharField(max_length=50)
 
    class Meta:
        db_table = "cuidadores"
 
    def __str__(self):
        return self.nombre_cuidador
 
 
class Beneficiario(models.Model):
    id_beneficiario = models.AutoField(primary_key=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    # Se guarda solo el municipio; el departamento se obtiene a través de Municipio
    municipio_nacimiento = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, db_column="id_municipio_nacimiento", related_name="beneficiarios"
    )
    fecha_nacimiento = models.DateField()
    sexo = models.CharField(max_length=20)
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=50, null=True, blank=True)
    correo = models.CharField(max_length=150, null=True, blank=True)
    ocupacion = models.CharField(max_length=100, null=True, blank=True)
    descripcion_ocupacion = models.TextField(null=True, blank=True)
    ingreso_mensual = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    migrante = models.CharField(max_length=20)
    discapacidad = models.ForeignKey(
        Discapacidad, on_delete=models.PROTECT, db_column="id_discapacidad", related_name="beneficiarios"
    )
    causa_origen = models.CharField(max_length=100)
    tipo_discapacidad = models.CharField(max_length=100)
    descripcion_discapacidad = models.TextField(null=True, blank=True)
    ayuda_tecnica = models.CharField(max_length=20)
    tipo_ayuda = models.CharField(max_length=100, null=True, blank=True)
    organizacion = models.ForeignKey(
        Organizacion, on_delete=models.PROTECT, db_column="id_organizacion", related_name="beneficiarios"
    )
    fecha_ingreso_org = models.DateField(null=True, blank=True)
    beneficios_org = models.TextField(null=True, blank=True)
    descripcion_benef = models.TextField(null=True, blank=True)
    estado_civil = models.ForeignKey(
        EstadoCivil, on_delete=models.PROTECT, db_column="id_estado", related_name="beneficiarios"
    )
    grado = models.ForeignKey(
        Educacion, on_delete=models.PROTECT, db_column="id_grado", related_name="beneficiarios"
    )
 
    class Meta:
        db_table = "beneficiarios"
        ordering = ["id_beneficiario"]
 
    def __str__(self):
        return f"{self.nombres} {self.apellidos}"
 
 
class BeneficiarioCuidador(models.Model):
    id_cuida_benef = models.AutoField(primary_key=True)
    beneficiario = models.ForeignKey(
        Beneficiario, on_delete=models.CASCADE, db_column="id_beneficiario", related_name="cuidadores_rel"
    )
    cuidador = models.ForeignKey(
        Cuidador, on_delete=models.CASCADE, db_column="id_cuidador", related_name="beneficiarios_rel"
    )
 
    class Meta:
        db_table = "beneficiario_cuidador"
        constraints = [
            models.UniqueConstraint(fields=["beneficiario", "cuidador"], name="uq_beneficiario_cuidador")
        ]
 