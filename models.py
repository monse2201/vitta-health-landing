from app import db # Importa 'db' desde tu app.py, asumiendo que app.py es el punto de entrada y 'db' se inicializa allí.
from flask_login import UserMixin
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_ # Necesario si se usan filtros OR en relaciones o queries


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="medico")
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    especialidad = db.Column(db.String(150), nullable=True)
    licencia_profesional = db.Column(db.String(100), nullable=True, unique=True)
    identificacion = db.Column(db.String(50), nullable=True, unique=True) 
    telefono_profesional = db.Column(db.String(50), nullable=True)
    biografia = db.Column(db.Text, nullable=True)
    url_foto_perfil = db.Column(db.String(512), nullable=True) 
    clinica_nombre = db.Column(db.String(200), nullable=True)
    clinica_direccion = db.Column(db.Text, nullable=True)
    clinica_telefono = db.Column(db.String(50), nullable=True)
    clinica_website = db.Column(db.String(200), nullable=True)
    lugar_trabajo = db.Column(db.String(255), nullable=True)
    url_logo_clinica = db.Column(db.String(512), nullable=True) 

    # Relaciones desde User
    pacientes_creados = db.relationship('Paciente', foreign_keys='Paciente.creado_por_id', backref='creador_usuario', lazy='dynamic')
    visitas_asignadas = db.relationship('Visita', foreign_keys='Visita.medico_id', backref='medico_asignado_usuario', lazy='dynamic')
    notas_creadas = db.relationship('Nota', foreign_keys='Nota.usuario_id', backref='creador_nota_usuario', lazy='dynamic')
    tareas_asignadas = db.relationship('Tarea', foreign_keys='Tarea.usuario_id', backref='asignado_a_usuario', lazy='dynamic')
    respuestas_rapidas_creadas = db.relationship('RespuestaRapida', foreign_keys='RespuestaRapida.usuario_id', backref='creador_respuesta_usuario', lazy='dynamic')
    mensajes_programados_creados = db.relationship('MensajeProgramado', foreign_keys='MensajeProgramado.usuario_id', backref='creador_mensaje_usuario', lazy='dynamic')
    recetas_emitidas = db.relationship('RecetaMedica', foreign_keys='RecetaMedica.medico_id', backref='medico_emisor_receta', lazy='dynamic')
    referencias_emitidas = db.relationship('ReferenciaMedica', foreign_keys='ReferenciaMedica.medico_referente_id', backref='medico_emisor_referencia', lazy='dynamic')
    planes_nutricionales_emitidos = db.relationship('PlanNutricional', foreign_keys='PlanNutricional.medico_id', backref='medico_emisor_plan', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

class MensajeProgramado(db.Model):
    __tablename__='mensaje_programado'
    id=db.Column(db.Integer, primary_key=True)
    contacto=db.Column(db.String(100), nullable=False)
    mensaje=db.Column(db.Text, nullable=False)
    fecha_programada=db.Column(db.DateTime, nullable=False)
    usuario_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<MensajeProgramado {self.id}>'

class RespuestaRapida(db.Model):
    __tablename__='respuesta_rapida'
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(100), nullable=False)
    mensaje=db.Column(db.Text, nullable=False)
    usuario_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<RespuestaRapida {self.nombre}>'

class Tarea(db.Model):
    __tablename__='tarea'
    id=db.Column(db.Integer, primary_key=True)
    title=db.Column(db.String(200), nullable=False)
    type=db.Column(db.String(100), nullable=False)
    priority=db.Column(db.String(20), nullable=False, default='normal')
    description=db.Column(db.Text, nullable=True)
    dateTime=db.Column(db.String(50), nullable=False)
    assignedTo=db.Column(db.String(100), nullable=False)
    guests=db.Column(db.Text, nullable=True)
    links=db.Column(db.Text, nullable=True)
    status=db.Column(db.String(50), nullable=False, default="Sin comenzar")
    usuario_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Tarea {self.title}>'

class Paciente(db.Model):
    __tablename__='paciente'
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(100), nullable=False, index=True)
    identificacion_documento = db.Column(db.String(50), nullable=True, unique=False, index=True)
    telefono = db.Column(db.String(25), nullable=True)
    email = db.Column(db.String(120), nullable=True, index=True)
    estado_tratamiento = db.Column(db.String(100), nullable=True, default='No especificado')
    creado_por_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    visitas=db.relationship('Visita', backref='paciente', lazy='dynamic', cascade="all, delete-orphan")
    notas=db.relationship('Nota', backref='paciente_notas', lazy='dynamic', cascade="all, delete-orphan")
    recetas_paciente = db.relationship('RecetaMedica', backref='paciente_receta', lazy='dynamic', cascade="all, delete-orphan")
    referencias_paciente = db.relationship('ReferenciaMedica', backref='paciente_referencia', lazy='dynamic', cascade="all, delete-orphan")
    planes_nutricionales = db.relationship('PlanNutricional', backref='paciente_plan', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Paciente {self.nombre}>'

class Nota(db.Model):
    __tablename__='nota'
    id=db.Column(db.Integer, primary_key=True)
    chat_id=db.Column(db.String(100), nullable=True)
    paciente_id=db.Column(db.Integer, db.ForeignKey('paciente.id', ondelete='CASCADE'), nullable=False)
    contenido=db.Column(db.Text, nullable=False)
    fecha=db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    usuario_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Nota {self.id}>'

class Visita(db.Model):
    __tablename__='visita'
    id=db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id', ondelete='CASCADE'), nullable=False, index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plantilla=db.Column(db.String(100), nullable=True)
    transcripcion=db.Column(db.Text, nullable=True)
    resumen_ai=db.Column(db.Text, nullable=True)
    notas_ai = db.Column(db.Text, nullable=True)
    ruta_notas_ai_pdf = db.Column(db.String(512), nullable=True)
    fecha=db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    idioma_detectado=db.Column(db.String(20), nullable=True)
    tipo_visita = db.Column(db.String(50), nullable=False, default="audio_consulta")
    duracion_grabacion_segundos = db.Column(db.Integer, nullable=True)
    archivos_adjuntos = db.Column(db.Text, nullable=True)
    registros_actividad=db.relationship('RegistroActividad', backref='visita', lazy=True, cascade="all, delete-orphan")
    recetas_visita = db.relationship('RecetaMedica', backref='visita_receta', lazy='dynamic', cascade="all, delete-orphan")
    referencias_visita = db.relationship('ReferenciaMedica', backref='visita_referencia', lazy='dynamic', cascade="all, delete-orphan")
    planes_nutricionales_visita = db.relationship('PlanNutricional', backref='visita_plan', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Visita {self.id} Paciente {self.paciente_id}>'

class RegistroActividad(db.Model):
    __tablename__='registro_actividad'
    id=db.Column(db.Integer, primary_key=True)
    visita_id=db.Column(db.Integer, db.ForeignKey('visita.id', ondelete='SET NULL'), nullable=True, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    usuario_nombre_display = db.Column(db.String(100), nullable=False)
    accion=db.Column(db.String(50), nullable=False)
    descripcion=db.Column(db.Text, nullable=False)
    fecha=db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self):
        return f'<RegistroActividad {self.id}>'

class RecetaMedica(db.Model):
    __tablename__ = 'receta_medica'
    id = db.Column(db.Integer, primary_key=True)
    visita_id = db.Column(db.Integer, db.ForeignKey('visita.id', ondelete='SET NULL'), nullable=True, index=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id', ondelete='CASCADE'), nullable=False, index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    fecha_emision = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    medicamentos_json = db.Column(db.Text, nullable=False)
    diagnostico_relacionado = db.Column(db.Text, nullable=True)
    validez_dias = db.Column(db.Integer, nullable=True, default=30)
    notas_adicionales_receta = db.Column(db.Text, nullable=True)
    estado = db.Column(db.String(50), nullable=False, default="activa")

    def __repr__(self):
        return f'<RecetaMedica {self.id} - Paciente {self.paciente_id}>'

class ReferenciaMedica(db.Model):
    __tablename__ = 'referencia_medica'
    id = db.Column(db.Integer, primary_key=True)
    visita_id = db.Column(db.Integer, db.ForeignKey('visita.id', ondelete='SET NULL'), nullable=True, index=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id', ondelete='CASCADE'), nullable=False, index=True)
    medico_referente_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    fecha_emision = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    especialidad_referida = db.Column(db.String(150), nullable=False)
    medico_referido_nombre = db.Column(db.String(150), nullable=True)
    institucion_referida = db.Column(db.String(200), nullable=True)
    motivo_referencia = db.Column(db.Text, nullable=True)
    resumen_clinico_relevante = db.Column(db.Text, nullable=True)
    estudios_adjuntos_info = db.Column(db.Text, nullable=True)
    estado = db.Column(db.String(50), nullable=False, default="pendiente")

    def __repr__(self):
        return f'<ReferenciaMedica {self.id} - Paciente {self.paciente_id} a {self.especialidad_referida}>'

class PlanNutricional(db.Model):
    __tablename__ = 'plan_nutricional'
    id = db.Column(db.Integer, primary_key=True)
    visita_id = db.Column(db.Integer, db.ForeignKey('visita.id', ondelete='SET NULL'), nullable=True, index=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id', ondelete='CASCADE'), nullable=False, index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    fecha_emision = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    contenido_json = db.Column(db.Text, nullable=False)
    notas_adicionales = db.Column(db.Text, nullable=True)
    ruta_pdf_almacenada = db.Column(db.String(512), nullable=True)
    estado = db.Column(db.String(50), nullable=False, default="activo") # Asegúrate que este campo está en tu modelo

    def __repr__(self):
        return f'<PlanNutricional {self.id} - Paciente {self.paciente_id}>'

class ProspectoInteres(db.Model):
    __tablename__ = 'prospectos_interes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(50), nullable=False)
    especialidad = db.Column(db.String(150), nullable=True)
    carne_medico = db.Column(db.String(100), nullable=True)
    identificacion = db.Column(db.String(50), nullable=True)
    lugar_trabajo = db.Column(db.String(255), nullable=True)
    consentimiento = db.Column(db.Boolean, nullable=False, default=False)
    fecha_registro = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<ProspectoInteres {self.id} - {self.nombre} {self.apellidos}>'