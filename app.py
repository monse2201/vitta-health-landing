import markdown
# -*- coding: utf-8 -*-
import os
import threading
import logging
import json
import gc
import redis
import re
import tempfile
from datetime import datetime, timezone, timedelta
import io 
import secrets
import string
import click
import base64 


# --- MAIN IMPORTS ---
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, current_app, get_flashed_messages, session, send_from_directory, send_file
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from sqlalchemy.orm import joinedload 
from flask_migrate import Migrate
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_required, current_user, login_user, logout_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
from functools import wraps
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.flac import FLAC
from pydub import AudioSegment


def convertir_webm_a_wav(ruta_original):
    if not ruta_original.endswith(".webm"):
        return ruta_original  # No conversion needed

    ruta_convertida = ruta_original.replace(".webm", ".wav")
    try:
        audio = AudioSegment.from_file(ruta_original, format="webm")
        audio.export(ruta_convertida, format="wav")
        return ruta_convertida
    except Exception as e:
        logging.error(f"Error converting audio: {e}")
        return None

def obtener_duracion_audio_segundos(ruta_archivo):
    try:
        audio = AudioSegment.from_file(ruta_archivo)
        duracion_ms = len(audio)
        return duracion_ms // 1000  # convertir a segundos
    except Exception as e:
        logging.warning(f"Could not get audio duration: {e}")
        return None


def convertir_webm_a_wav(ruta_original):
    if not ruta_original.endswith(".webm"):
        return ruta_original  # No conversion needed

    ruta_convertida = ruta_original.replace(".webm", ".wav")
    try:
        audio = AudioSegment.from_file(ruta_original, format="webm")
        audio.export(ruta_convertida, format="wav")
        return ruta_convertida
    except Exception as e:
        logging.error(f"Error converting audio: {e}")
        return None

from mutagen.mp4 import MP4
import math

class ListPagination:
    """Manual pagination class for any Python list."""
    def __init__(self, items_list, page, per_page):
        self.total = len(items_list)
        self.page = page
        self.per_page = per_page
        
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        self.items = items_list[start_index:end_index]

    @property
    def pages(self):
        if self.per_page == 0:
            return 0
        return math.ceil(self.total / self.per_page)

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def prev_num(self):
        return self.page - 1 if self.has_prev else None

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def next_num(self):
        return self.page + 1 if self.has_next else None

    def iter_pages(self, left_edge=2, left_current=2, right_current=2, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

# Importaciones específicas de la aplicación (asegúrate de que estas bibliotecas estén instaladas)
debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
try:
    import PyPDF2
except ImportError:
    logging.error("🚨 No se pudo importar la biblioteca PyPDF2. La extracción de texto de PDFs no estará disponible.")
    PyPDF2 = None

try:
    from docx import Document as DocxDocument
except ImportError:
    logging.error("🚨 No se pudo importar la biblioteca python-docx. La extracción de texto de DOCX no estará disponible.")
    DocxDocument = None

try:
    from PIL import Image
except ImportError:
    logging.error("🚨 No se pudo importar la biblioteca Pillow. La extracción de texto de imágenes (OCR) no estará disponible.")
    Image = None

try:
    import pytesseract
except ImportError:
    logging.error("🚨 No se pudo importar la biblioteca pytesseract. La extracción de texto de imágenes (OCR) no estará disponible.")
    pytesseract = None

try:
    from openai import OpenAI, APIError, RateLimitError, APIConnectionError, AuthenticationError, BadRequestError
except ImportError:
    logging.error("🚨 No se pudo importar la biblioteca OpenAI. Las funcionalidades de IA no estarán disponibles.")
    OpenAI = None
    APIError = RateLimitError = APIConnectionError = AuthenticationError = BadRequestError = Exception # type: ignore

try:
    import tiktoken
except ImportError:
    logging.error("🚨 No se pudo importar la biblioteca tiktoken. El conteo de tokens para OpenAI no estará disponible.")
    tiktoken = None

try:
    from huggingface_hub import login
    from transformers import pipeline
    HUGGINGFACE_PIPELINE_AVAILABLE = True
except ImportError:
    logging.error("🚨 No se pudo importar la biblioteca 'transformers'. Las funcionalidades de traducción con HF no estarán disponibles.")
    HUGGINGFACE_PIPELINE_AVAILABLE = False
    pipeline = None # type: ignore
    login = None # type: ignore

try:
    from weasyprint import HTML # Descomentar si se usa WeasyPrint para generar PDFs
except ImportError:
    logging.warning("🚨 WeasyPrint no está instalado. La generación de PDFs desde HTML no estará disponible o usará un método alternativo.")
    HTML = None

# --- NUEVA IMPORTACIÓN PARA CIFRADO ---
try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    logging.error("🚨 No se pudo importar la biblioteca 'cryptography'. El cifrado de archivos a nivel de aplicación no estará disponible.")
    Fernet = None
    InvalidToken = Exception # type: ignore


# --- CONFIGURACIÓN DE LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# --- DATOS FIJOS PARA LA DEMO DE PROFESIONALES ---
# --- DATOS FIJOS PARA LA DEMO DE PROFESIONALES ---
DEMO_STATS_PROFESIONALES = {
    # Nombres completos actualizados
    "María Liseth Arias Tames": {"minutos": 2815, "docs_creados": 47, "pacientes": 62, "visitas": 62, "resumidos": 20},
    "Diana Guzmán":             {"minutos": 814,  "docs_creados": 29, "pacientes": 29, "visitas": 29, "resumidos": 10},
    "Jesús Camargo González":   {"minutos": 455,  "docs_creados": 14, "pacientes": 33, "visitas": 14, "resumidos": 0}
}

ALLOWED_OPENAI_AUDIO_EXTENSIONS = [
    '.flac', '.m4a', '.mp3', '.mp4', '.mpeg', 
    '.mpga', '.oga', '.ogg', '.wav', '.webm'
]

# --- INICIALIZACIÓN DE LA APLICACIÓN FLASK ---
app = Flask(__name__)

# === ENVIRONMENT-BASED CONFIGURATION ===
import os

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///dev.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')
app.config['SESSION_PERMANENT'] = False
app.config['MAIL_SUPPRESS_SEND'] = os.getenv('FLASK_ENV', 'development') == 'development'


# --- CONFIGURACIÓN DE VARIABLES DE ENTORNO (o valores por defecto para desarrollo) ---
# Environment Type
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')

# API Keys and Security
app.secret_key = os.environ.get('SECRET_KEY', '1cc211a1a2357f80fb028885caa21d0e3983a27dfb2ea7ac')

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') 
# Hugging Face Token (para modelos de traducción)
hf_token = os.environ.get('HUGGINGFACE_TOKEN', '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')

# --- NUEVA VARIABLE DE ENTORNO PARA CIFRADO DE ARCHIVOS ---
# Generar con: from cryptography.fernet import Fernet; Fernet.generate_key().decode()
# Esta clave DEBE ser de 32 bytes codificados en base64 seguros para URL.
FILE_ENCRYPTION_KEY_STR = os.environ.get('FILE_ENCRYPTION_KEY')
fernet_cipher = None
if FILE_ENCRYPTION_KEY_STR and Fernet:
    try:
        fernet_cipher = Fernet(FILE_ENCRYPTION_KEY_STR.encode())
        logging.info("✅ Llave de cifrado de archivos cargada. El cifrado de archivos a nivel de aplicación está HABILITADO.")
    except Exception as e_fernet_init:
        logging.error(f"🚨 Error al inicializar Fernet con FILE_ENCRYPTION_KEY: {e_fernet_init}. El cifrado de archivos estará DESHABILITADO.")
        fernet_cipher = None
elif Fernet:
    logging.warning("⚠️ FILE_ENCRYPTION_KEY no configurada. El cifrado de archivos a nivel de aplicación está DESHABILITADO.")
else:
    logging.warning("⚠️ Biblioteca 'cryptography' no disponible. El cifrado de archivos a nivel de aplicación está DESHABILITADO.")


# Database Configuration
DATABASE_URL_LOCAL = os.environ.get('DATABASE_URL_LOCAL', 'postgresql+psycopg2://whatsapp_user:securepassword@postgres-db:5432/whatsapp_project')
# Para producción, se recomienda enfáticamente que la base de datos (PostgreSQL en este caso)
# esté configurada para cifrado en reposo a nivel de proveedor (ej. DigitalOcean Managed DB).
# La cadena de conexión ya incluye `?sslmode=require` para cifrado en tránsito (TLS).
DATABASE_URL_PROD = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://doadmin:AVNS_zRk7-87CB8FurBYkWFN@vitta-db-cluster-do-user-22731081-0.k.db.ondigitalocean.com:25060/vitta_db?sslmode=require')

# Configuración de correo electrónico
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
# TLS/SSL para correo ya está manejado por estas variables para cifrado en tránsito.
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() in ('true', '1', 't')
MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'true').lower() in ('true', '1', 't')
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'info@vitta.health')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'duzo nztm nfst flnr')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'info@vitta.health')

# Configuración de Redis para SocketIO y Flask-Session
REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
REDIS_USE_SSL = os.environ.get('REDIS_USE_SSL', 'false').lower() == 'true' # Para conexiones TLS a Redis
redis_url_for_socketio = os.environ.get("REDIS_URL_SOCKETIO")


# --- CONFIGURACIÓN DE LA APLICACIÓN (app.config) ---
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if FLASK_ENV == 'development':
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL_LOCAL
    logging.info(f"Configured PostgreSQL for development: {DATABASE_URL_LOCAL}")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL_PROD
    logging.info(f"Configured PostgreSQL for production: {DATABASE_URL_PROD}")
    # En producción, se asume que un proxy inverso (Nginx, Caddy) maneja TLS 1.3 para HTTPS.
    # La aplicación Flask en sí no necesita manejar certificados SSL directamente en este caso.

client_openai = None
if OPENAI_API_KEY and OpenAI:
    try:
        client_openai = OpenAI(api_key=OPENAI_API_KEY)
        logging.info("OpenAI client initialized successfully.")
    except Exception as e_openai_init:
        logging.error(f"Failed to initialize OpenAI client: {e_openai_init}. OpenAI functionalities will be disabled.")
else:
    logging.warning("OpenAI API Key not found or OpenAI library not imported. OpenAI functionalities will be disabled.")

if hf_token and HUGGINGFACE_PIPELINE_AVAILABLE and login:
    try:
        login(token=hf_token)
        logging.info("Hugging Face Hub login successful (or token accepted).")
    except Exception as e_hf_login:
        logging.error(f"Error during Hugging Face Hub login: {e_hf_login}")
elif HUGGINGFACE_PIPELINE_AVAILABLE:
    logging.info("Hugging Face token not provided. Some models might require login for translation.")

app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['REGISTROS_FOLDER'] = 'registros_medicos'
app.config['AUDIO_FOLDER'] = 'audio_consultas'
app.config['PLANES_PDF_FOLDER'] = 'planes_nutricionales_pdf'
app.config['NOTAS_AI_PDF_FOLDER'] = 'notas_ia_pdf'

os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], app.config['REGISTROS_FOLDER']), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], app.config['AUDIO_FOLDER']), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], app.config['PLANES_PDF_FOLDER']), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], app.config['NOTAS_AI_PDF_FOLDER']), exist_ok=True)

app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER
mail = Mail(app)

if REDIS_HOST:
    try:
        protocol = "rediss://" if REDIS_USE_SSL else "redis://"
        redis_connection_url_parts = [protocol]
        # La contraseña debe usarse incluso con SSL/TLS para la autenticación de Redis.
        if REDIS_PASSWORD:
            redis_connection_url_parts.append(f":{REDIS_PASSWORD}@")
        redis_connection_url_parts.append(f"{REDIS_HOST}:{REDIS_PORT}/0")
        redis_connection_url = "".join(redis_connection_url_parts)

        ssl_kwargs_redis = {}
        if REDIS_USE_SSL:
            # Para redis-py, si el servidor Redis requiere verificación de certificado del cliente
            # o un CA específico, se configurarían aquí.
            # Ejemplo: ssl_kwargs_redis['ssl_cert_reqs'] = 'required'
            # ssl_kwargs_redis['ssl_ca_certs'] = '/path/to/your/ca.crt'
            # Los servicios gestionados de Redis a menudo manejan esto de forma transparente
            # si se usa su endpoint habilitado para SSL.
            logging.info(f"Intentando conexión SSL/TLS a Redis: {redis_connection_url}")
        else:
            logging.info(f"Intentando conexión estándar (no SSL/TLS) a Redis: {redis_connection_url}")

        app.config['SESSION_REDIS'] = redis.from_url(redis_connection_url, **ssl_kwargs_redis)
        app.config['SESSION_TYPE'] = 'redis'
        redis_url_for_socketio = redis_connection_url # Asegurar que SocketIO también use la URL (con SSL si está configurado)
        logging.info(f"Configured Flask-Session with Redis at {redis_connection_url} (SSL/TLS: {REDIS_USE_SSL})")
    except Exception as e_redis:
        logging.error(f"Error configuring Redis for Flask-Session: {e_redis}. Falling back to filesystem session.", exc_info=True)
        app.config['SESSION_TYPE'] = 'filesystem'
        app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, 'flask_session')
        os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
        logging.info(f"LOCAL: Configured Flask-Session with filesystem at {app.config['SESSION_FILE_DIR']}")
else:
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, 'flask_session')
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    logging.info(f"LOCAL: Configured Flask-Session with filesystem at {app.config['SESSION_FILE_DIR']}")
    logging.info("LOCAL: REDIS_HOST not set. SocketIO will run without a message queue in local dev if not configured.")

Session(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()


# --- Modificaciones para el Requerimiento de Verificación ---

# 1. Función para manejar el acceso no autorizado o no verificado
@login_manager.unauthorized_handler
def unauthorized_callback():
    # Si el usuario está autenticado pero no verificado
    if current_user.is_authenticated and not current_user.is_verified:
        # Enviamos un message específico y lo redirigimos a la página de login
        flash('Su perfil aún no ha sido verificado. Por favor, espere a que un administrador apruebe su cuenta.', 'warning')
        # Es importante cerrar la sesión para que no quede en un bucle de redirección
        logout_user()
        return redirect(url_for('login_route'))

    # Comportamiento estándar para usuarios no logueados
    flash('Por favor, inicia sesión para acceder a esta página.', 'info')
    return redirect(url_for('login_route', next=request.path))

# --- Fin de Modificaciones ---

login_manager.init_app(app)

# --- INICIO: CÓDIGO DEL DECORADOR DE ADMINISTRADOR ---
# Este es nuestro "guardia de seguridad" para las rutas de admin
def admin_required(allowed_roles=None): # This function now takes an argument
    if allowed_roles is None:
        allowed_roles = ['admin'] # Default to 'admin' if no specific roles are passed

    def decorator(f): # This is the actual decorator that will wrap the view function
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Por favor, inicia sesión para acceder a esta página.', 'info')
                return redirect(url_for('login_route'))

            # Check if the current user's role is in the allowed_roles list
            if current_user.role not in allowed_roles:
                flash(f'Acceso no autorizado. Se requiere uno de los siguientes roles: {", ".join(allowed_roles)}.', 'danger')
                
                # Redirect based on user role or to a generic unauthorized page
                if current_user.is_authenticated and current_user.role in ['admin_super', 'admin_nutricion']:
                    # If an admin but not allowed for this specific admin dashboard, send to their own specific admin dashboard
                    if current_user.role == 'admin_super':
                        return redirect(url_for('super_admin_dashboard'))
                    elif current_user.role == 'admin_nutricion':
                        return redirect(url_for('nutricion_admin_dashboard'))
                # For non-admin roles trying to access an admin page, or other edge cases
                return redirect(url_for('dashboard')) # Fallback for non-admin unauthorized access to any admin page

            return f(*args, **kwargs)
        return decorated_function
    return decorator
# --- FIN: CÓDIGO DEL DECORADOR DE ADMINISTRADOR ---


login_manager.login_view = 'login_route'
login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."
login_manager.login_message_category = "info"

socketio_kwargs = {
    "cors_allowed_origins": "*",
    "async_mode": 'eventlet'
}
if redis_url_for_socketio:
    socketio_kwargs["message_queue"] = redis_url_for_socketio
    logging.info(f"SocketIO initialized WITH message queue Redis ({redis_url_for_socketio}). Async_mode auto-detected.")
else:
    logging.info("SocketIO initialized WITHOUT message queue Redis. Async_mode auto-detected.")
socketio = SocketIO(app, **socketio_kwargs)


# --- Modelos de Base de Datos ---
class User(db.Model, UserMixin):
    __tablename__='user'
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(100), nullable=False)
    email=db.Column(db.String(100), unique=True, nullable=False)
    password_hash=db.Column(db.String(255), nullable=False)
    role=db.Column(db.String(50), nullable=False, default="medico")
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at=db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
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

    show_clinic_name_pdf = db.Column(db.Boolean, default=True, nullable=False)
    show_clinic_logo_pdf = db.Column(db.Boolean, default=True, nullable=False)
    show_clinic_address_pdf = db.Column(db.Boolean, default=True, nullable=False)
    show_clinic_phone_pdf = db.Column(db.Boolean, default=True, nullable=False)
    show_clinic_website_pdf = db.Column(db.Boolean, default=True, nullable=False)
    show_doctor_license_pdf = db.Column(db.Boolean, default=True, nullable=False)
    show_doctor_phone_pdf = db.Column(db.Boolean, default=True, nullable=False)
    show_doctor_bio_pdf = db.Column(db.Boolean, default=True, nullable=False)

    pacientes_creados = db.relationship('Paciente', foreign_keys='Paciente.creado_por_id', backref='creador_usuario', lazy='dynamic')
    visitas_asignadas = db.relationship('Visita', foreign_keys='Visita.medico_id', backref='medico_asignado_usuario', lazy='dynamic')
    notas_creadas = db.relationship('Nota', foreign_keys='Nota.usuario_id', backref='creador_nota_usuario', lazy='dynamic')
    tareas_asignadas = db.relationship('Tarea', foreign_keys='Tarea.usuario_id', backref='asignado_a_usuario', lazy='dynamic')
    respuestas_rapidas_creadas = db.relationship('RespuestaRapida', foreign_keys='RespuestaRapida.usuario_id', backref='creador_respuesta_usuario', lazy='dynamic')
    messages_programados_creados = db.relationship('MensajeProgramado', foreign_keys='MensajeProgramado.usuario_id', backref='creador_message_usuario', lazy='dynamic')
    recetas_emitidas = db.relationship('RecetaMedica', foreign_keys='RecetaMedica.medico_id', backref='medico_emisor_receta', lazy='dynamic')
    referencias_emitidas = db.relationship('ReferenciaMedica', foreign_keys='ReferenciaMedica.medico_referente_id', backref='medico_emisor_referencia', lazy='dynamic')
    planes_nutricionales_emitidos = db.relationship('PlanNutricional', foreign_keys='PlanNutricional.medico_id', backref='medico_emisor_plan', lazy='dynamic')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class MensajeProgramado(db.Model):
    __tablename__='message_programado'
    id=db.Column(db.Integer, primary_key=True)
    contacto=db.Column(db.String(100), nullable=False)
    message=db.Column(db.Text, nullable=False) # Considerar cifrado si es información sensible
    fecha_programada=db.Column(db.DateTime, nullable=False)
    usuario_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class RespuestaRapida(db.Model):
    __tablename__='respuesta_rapida'
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(100), nullable=False)
    message=db.Column(db.Text, nullable=False) # Considerar cifrado si es información sensible
    usuario_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Tarea(db.Model):
    __tablename__='tarea'
    id=db.Column(db.Integer, primary_key=True)
    title=db.Column(db.String(200), nullable=False)
    type=db.Column(db.String(100), nullable=False)
    priority=db.Column(db.String(20), nullable=False, default='normal')
    description=db.Column(db.Text, nullable=True) # Considerar cifrado si es información sensible
    dateTime=db.Column(db.String(50), nullable=False)
    assignedTo=db.Column(db.String(100), nullable=False)
    guests=db.Column(db.Text, nullable=True)
    links=db.Column(db.Text, nullable=True)
    status=db.Column(db.String(50), nullable=False, default="Sin comenzar")
    usuario_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Paciente(db.Model):
    __tablename__='paciente'
    id=db.Column(db.Integer, primary_key=True)
    # Campos como nombre, identificacion_documento, telefono, email
    # podrían requerir cifrado a nivel de columna si las políticas de seguridad son muy estrictas
    # y el cifrado a nivel de proveedor de BD no es suficiente.
    # Esto añadiría complejidad significativa a las búsquedas y consultas.
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
class EstadisticasDemo(db.Model):
    __tablename__ = 'estadisticas_demo'
    id = db.Column(db.Integer, primary_key=True)
    minutos_grabados = db.Column(db.Integer)
    visitas_generadas = db.Column(db.Integer)
    pacientes_creados = db.Column(db.Integer)
    documentos_creados = db.Column(db.Integer)
    documentos_resumidos = db.Column(db.Integer)


class Nota(db.Model):
    __tablename__='nota'
    id=db.Column(db.Integer, primary_key=True)
    chat_id=db.Column(db.String(100), nullable=True)
    paciente_id=db.Column(db.Integer, db.ForeignKey('paciente.id', ondelete='CASCADE'), nullable=False)
    contenido=db.Column(db.Text, nullable=False) # Considerar cifrado
    fecha=db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    usuario_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Visita(db.Model):
    __tablename__='visita'
    id=db.Column(db.Integer, primary_key=True)  # This line was the problem
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id', ondelete='CASCADE'), nullable=False, index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plantilla=db.Column(db.String(100), nullable=True)
    transcripcion=db.Column(db.Text, nullable=True)
    resumen_ai=db.Column(db.Text, nullable=True)
    notas_ai = db.Column(db.Text, nullable=True)
    ruta_notas_ai_pdf = db.Column(db.String(512), nullable=True) # This field will no longer be used for AI notes PDF
    fecha=db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    idioma_detectado=db.Column(db.String(20), nullable=True)
    tipo_visita = db.Column(db.String(50), nullable=False, default="audio_consulta")
    duracion_grabacion_segundos = db.Column(db.Integer, nullable=True)
    archivos_adjuntos = db.Column(db.Text, nullable=True)
    registros_actividad=db.relationship('RegistroActividad', backref='visita', lazy=True, cascade="all, delete-orphan")
    recetas_visita = db.relationship('RecetaMedica', backref='visita_receta', lazy='dynamic', cascade="all, delete-orphan")
    referencias_visita = db.relationship('ReferenciaMedica', backref='visita_referencia', lazy='dynamic', cascade="all, delete-orphan")
    planes_nutricionales_visita = db.relationship('PlanNutricional', backref='visita_plan', lazy='dynamic', cascade="all, delete-orphan")

class RegistroActividad(db.Model):
    __tablename__='registro_actividad'
    id=db.Column(db.Integer, primary_key=True)
    visita_id=db.Column(db.Integer, db.ForeignKey('visita.id', ondelete='SET NULL'), nullable=True, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    usuario_nombre_display = db.Column(db.String(100), nullable=False)
    accion=db.Column(db.String(50), nullable=False)
    descripcion=db.Column(db.Text, nullable=False) # Considerar cifrado si es muy detallado/sensible
    fecha=db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class RecetaMedica(db.Model):
    __tablename__ = 'receta_medica'
    id = db.Column(db.Integer, primary_key=True)
    visita_id = db.Column(db.Integer, db.ForeignKey('visita.id', ondelete='SET NULL'), nullable=True, index=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id', ondelete='CASCADE'), nullable=False, index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    fecha_emision = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    # medicamentos_json y diagnostico_relacionado son candidatos para cifrado.
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
    # Este es el nuevo campo para el motivo que pide el bot
    motivo_referencia = db.Column(db.Text, nullable=True)
    # resumen_clinico_relevante y estudios_adjuntos_info son candidatos para cifrado.
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
    # contenido_json es candidato para cifrado.
    contenido_json = db.Column(db.Text, nullable=False)
    notas_adicionales = db.Column(db.Text, nullable=True)
    # ruta_pdf_almacenada apunta a un archivo que será cifrado con Fernet.
    ruta_pdf_almacenada = db.Column(db.String(512), nullable=True)
    estado = db.Column(db.String(50), nullable=False, default="activo")

    def __repr__(self):
        return f'<PlanNutricional {self.id} - Paciente {self.paciente_id}>'

class ProspectoInteres(db.Model):
    __tablename__ = 'prospectos_interes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(50), nullable=False)
    especialidad = db.Column(db.String(150), nullable=True) # Campo nuevo
    carne_medico = db.Column(db.String(100), nullable=True)
    identificacion = db.Column(db.String(50), nullable=True)
    lugar_trabajo = db.Column(db.String(255), nullable=True)
    consentimiento = db.Column(db.Boolean, nullable=False, default=False) # Campo nuevo
    fecha_registro = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<ProspectoInteres {self.id} - {self.nombre} {self.apellidos}>'


# --- CONSOLIDATED FILE HANDLING FUNCTIONS ---
def guardar_archivo_subido(archivo_request_file, subcarpeta_config_key):
    global fernet_cipher
    if not archivo_request_file or not archivo_request_file.filename:
        logging.error("guardar_archivo_subido: No se proporcionó archivo o nombre de archivo.")
        return None
    subcarpeta_destino_nombre = app.config.get(subcarpeta_config_key, "archivos_generales")
    filename_seguro = secure_filename(archivo_request_file.filename)
    nombre_base, extension = os.path.splitext(filename_seguro)
    # Añadir ".enc" a la extensión si el archivo será cifrado para identificarlo.
    # Esto es opcional pero puede ser útil.
    extension_final = extension + (".enc" if fernet_cipher else "")
    unique_filename = f"{nombre_base}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}{extension_final}"

    directorio_destino_local_completo = os.path.join(app.config['UPLOAD_FOLDER'], subcarpeta_destino_nombre)
    os.makedirs(directorio_destino_local_completo, exist_ok=True)
    ruta_guardado_local_completa = os.path.join(directorio_destino_local_completo, unique_filename)

    try:
        file_bytes = archivo_request_file.read() # Leer en memoria
        archivo_request_file.seek(0) # Resetear puntero si se necesita en otro lugar

        if fernet_cipher: # Solo cifrar si la clave y Fernet están disponibles
            encrypted_data = fernet_cipher.encrypt(file_bytes)
            with open(ruta_guardado_local_completa, 'wb') as f:
                f.write(encrypted_data)
            logging.info(f"Archivo CIFRADO (AES-256) y guardado localmente: {ruta_guardado_local_completa}")
        else: # Guardar sin cifrar si la clave no está configurada o Fernet no está disponible
            with open(ruta_guardado_local_completa, 'wb') as f:
                f.write(file_bytes) # Guardar los bytes originales
            logging.warning(f"Archivo guardado SIN CIFRAR (clave/Fernet no disponible): {ruta_guardado_local_completa}")

        return os.path.join(subcarpeta_destino_nombre, unique_filename).replace('\\', '/')
    except Exception as e_local_save:
        logging.error(f"Error guardando archivo '{unique_filename}' en '{ruta_guardado_local_completa}': {e_local_save}", exc_info=True)
        return None

def leer_y_desencriptar_archivo(ruta_archivo_relativa_en_uploads):
    """
    Lee un archivo desde UPLOAD_FOLDER. Si está cifrado (basado en la extensión .enc y disponibilidad de fernet_cipher),
    lo desencripta. Devuelve los bytes del archivo (desencriptados o originales).
    """
    global fernet_cipher
    if not ruta_archivo_relativa_en_uploads:
        logging.error("leer_y_desencriptar_archivo: Ruta de archivo relativa no proporcionada.")
        return None

    ruta_local_completa = os.path.join(app.config['UPLOAD_FOLDER'], ruta_archivo_relativa_en_uploads)
    if not os.path.exists(ruta_local_completa):
        logging.error(f"leer_y_desencriptar_archivo: Archivo no encontrado en {ruta_local_completa}")
        return None

    try:
        with open(ruta_local_completa, 'rb') as f:
            file_bytes = f.read()

        # Determinar si el archivo podría estar cifrado
        # Podríamos basarnos en la extensión .enc o en un campo en la BD que indique cifrado.
        # Por simplicidad, si fernet_cipher está activo, intentamos desencriptar.
        # Una mejor aproximación sería almacenar un flag de cifrado junto al archivo en la BD.
        # O, si siempre se añade .enc al cifrar, verificar esa extensión.
        is_potentially_encrypted = ruta_archivo_relativa_en_uploads.lower().endswith(".enc")

        if fernet_cipher and is_potentially_encrypted:
            try:
                decrypted_data = fernet_cipher.decrypt(file_bytes)
                logging.info(f"Archivo '{ruta_archivo_relativa_en_uploads}' desencriptado exitosamente.")
                return decrypted_data
            except InvalidToken:
                logging.warning(f"Fallo al desencriptar '{ruta_archivo_relativa_en_uploads}'. Podría no estar cifrado o la clave es incorrecta. Devolviendo contenido original.")
                return file_bytes # Devolver bytes originales si falla la desencriptación (podría no estar cifrado)
            except Exception as e_decrypt:
                logging.error(f"Error inesperado al desencriptar '{ruta_archivo_relativa_en_uploads}': {e_decrypt}", exc_info=True)
                return None # O manejar el error de otra forma
        else:
            # Si fernet_cipher no está disponible o el archivo no parece cifrado, devolver bytes originales
            logging.info(f"Archivo '{ruta_archivo_relativa_en_uploads}' leído sin intento de desencriptación (Fernet no activo o archivo no marcado como .enc).")
            return file_bytes

    except Exception as e_read:
        logging.error(f"Error leyendo archivo '{ruta_local_completa}': {e_read}", exc_info=True)
        return None

def procesar_archivo_subido(ruta_archivo_relativa, original_filename_for_extension):
    """
    Procesa un archivo (posiblemente cifrado) para extraer su texto.
    `ruta_archivo_relativa` es la ruta dentro de UPLOAD_FOLDER, podría tener .enc si está cifrado.
    `original_filename_for_extension` se usa para determinar el tipo de archivo original antes del cifrado.
    """
    decrypted_file_bytes = leer_y_desencriptar_archivo(ruta_archivo_relativa)

    if decrypted_file_bytes is None:
        logging.error(f"No se pudo leer o desencriptar el archivo en: {ruta_archivo_relativa}")
        return f"[Error: Archivo no encontrado o no se pudo leer/desencriptar en servidor: {os.path.basename(original_filename_for_extension)}]"

    # Usar el nombre de archivo original para determinar la extensión para el procesamiento de texto
    extension = os.path.splitext(original_filename_for_extension)[-1].lower()
    texto_extraido = ""

    # Crear un archivo temporal con los bytes desencriptados para las bibliotecas que esperan rutas de archivo
    # Esto es necesario porque PyPDF2, python-docx, pytesseract esperan rutas de archivo, no bytes directamente.
    # Asegurarse de que el archivo temporal tenga la extensión original para que las bibliotecas lo manejen correctamente.
    temp_file_descriptor, temp_file_path = -1, ""
    try:
        # Crear archivo temporal con la extensión original
        temp_file_descriptor, temp_file_path = tempfile.mkstemp(suffix=extension)
        with os.fdopen(temp_file_descriptor, 'wb') as tmp_file: # Abrir en modo binario para escribir bytes
            tmp_file.write(decrypted_file_bytes)
        temp_file_descriptor = -1 # Marcar como cerrado para evitar doble cierre

        # Ahora procesar el archivo temporal
        if extension == ".pdf" and PyPDF2:
            texto_extraido = extraer_texto_de_pdf(temp_file_path)
        elif extension in [".docx", ".doc"] and DocxDocument:
            texto_extraido = extraer_texto_de_docx(temp_file_path)
        elif extension == ".txt":
            texto_extraido = extraer_texto_de_txt(temp_file_path)
        elif extension in [".jpg", ".jpeg", ".png"] and Image and pytesseract:
            texto_extraido = extraer_texto_de_imagen_ocr(temp_file_path)
        else:
            logging.warning(f"Tipo de archivo no soportado para extracción de texto directa: {extension} para '{original_filename_for_extension}'. Se intentará como texto plano desde el archivo temporal.")
            try:
                # Si no es un tipo conocido, intentar leerlo como texto desde el archivo temporal
                with open(temp_file_path, 'r', encoding='utf-8', errors='ignore') as f_unknown:
                    texto_extraido = f_unknown.read()
                if texto_extraido.strip():
                    texto_extraido = f"[Contenido de '{original_filename_for_extension}' (tipo '{extension}') leído como texto plano]\n{texto_extraido}"
                else:
                    texto_extraido = f"[Tipo de archivo no soportado y sin contenido textual legible: {original_filename_for_extension}]"
            except Exception as e_read_unknown:
                logging.error(f"Error leyendo archivo de tipo desconocido '{extension}' como texto desde temp: {e_read_unknown}", exc_info=True)
                texto_extraido = f"[Error al intentar leer archivo de tipo desconocido: {original_filename_for_extension}]"

    except Exception as e:
        logging.error(f"Error crítico procesando archivo '{original_filename_for_extension}' (desde temp: {temp_file_path}): {e}", exc_info=True)
        texto_extraido = f"[Error crítico procesando archivo: {os.path.basename(original_filename_for_extension)}]"
    finally:
        if temp_file_descriptor != -1: # Si el archivo no se cerró correctamente en el try
             try: os.close(temp_file_descriptor)
             except OSError: pass # Ignorar error si ya estaba cerrado
        if temp_file_path and os.path.exists(temp_file_path):
            try: os.remove(temp_file_path)
            except OSError as e_remove_temp:
                 logging.warning(f"No se pudo eliminar el archivo temporal {temp_file_path}: {e_remove_temp}")

    return texto_extraido.strip() if texto_extraido else ""


def _eliminar_archivos_asociados_a_visita(visita_obj):
    if not visita_obj.archivos_adjuntos:
        logging.info(f"Visita ID {visita_obj.id} no tiene archivos adjuntos registrados para eliminar.")
        return
    paths_a_eliminar = []
    try:
        adjuntos_data_raw = visita_obj.archivos_adjuntos
        if isinstance(adjuntos_data_raw, str):
            try:
                parsed_json = json.loads(adjuntos_data_raw)
                if isinstance(parsed_json, dict) and "procesados" in parsed_json and isinstance(parsed_json["procesados"], list):
                    paths_a_eliminar.extend(parsed_json["procesados"])
                elif isinstance(parsed_json, list):
                    paths_a_eliminar.extend(parsed_json)
                else: # Si es una sola ruta de archivo (ej. audio)
                    if adjuntos_data_raw.strip():
                        paths_a_eliminar.append(adjuntos_data_raw)
            except json.JSONDecodeError: # Si no es JSON, asumir que es una sola ruta de archivo
                if adjuntos_data_raw.strip():
                    paths_a_eliminar.append(adjuntos_data_raw)
        else:
            logging.warning(f"Formato de archivos_adjuntos no reconocido o vacío para Visita ID {visita_obj.id}: {visita_obj.archivos_adjuntos}")
            return
    except Exception as e_parse:
        logging.error(f"Error inesperado parseando archivos_adjuntos para Visita ID {visita_obj.id}: {e_parse}", exc_info=True)
        return

    archivos_eliminados_count = 0
    for path_item in paths_a_eliminar:
        if not isinstance(path_item, str) or not path_item.strip():
            logging.warning(f"Item inválido encontrado en lista de archivos para Visita ID {visita_obj.id}: {path_item}")
            continue
        ruta_local_a_eliminar = os.path.join(app.config['UPLOAD_FOLDER'], path_item)
        if os.path.exists(ruta_local_a_eliminar):
            try:
                os.remove(ruta_local_a_eliminar)
                logging.info(f"Archivo local {'CIFRADO' if path_item.endswith('.enc') else 'NO CIFRADO'} eliminado: {ruta_local_a_eliminar}")
                archivos_eliminados_count +=1
            except Exception as e_local_del:
                logging.error(f"Error eliminando archivo local '{ruta_local_a_eliminar}': {e_local_del}", exc_info=True)
        else:
            logging.warning(f"Archivo local no encontrado para eliminación: {ruta_local_a_eliminar} (original path: {path_item})")
    if archivos_eliminados_count > 0:
        logging.info(f"Total {archivos_eliminados_count} archivo(s) físico(s) eliminado(s) para Visita ID {visita_obj.id}.")
def get_base64_image_from_path(relative_path_in_uploads):
    """
    Lee un archivo de imagen desde UPLOAD_FOLDER, lo desencripta si es necesario,
    y devuelve su cadena codificada en base64 adecuada para incrustar en HTML.
    """
    if not relative_path_in_uploads:
        return None

    # Asegúrate de que la ruta esté dentro de las subcarpetas permitidas para perfiles de usuario
    # Esto es crucial para la seguridad y evitar ataques de recorrido de directorio.
    allowed_profile_subfolders = [
        # app.config.get('PROFILE_FILES_FOLDER'), # Si tienes una carpeta general para perfiles
        os.path.join('usuarios_perfiles', str(current_user.id)) # Carpeta específica del usuario
    ]

    # Verificar si la ruta relativa comienza con alguna de las subcarpetas permitidas
    is_allowed_path = False
    for subfolder in allowed_profile_subfolders:
        # os.path.normpath normaliza las rutas para manejar / y \ y ..
        if os.path.normpath(relative_path_in_uploads).startswith(os.path.normpath(subfolder)):
            is_allowed_path = True
            break

    if not is_allowed_path:
        logging.error(f"Intento de acceder a una imagen fuera de las carpetas de perfil permitidas: {relative_path_in_uploads}")
        return None # Prevenir ataques de recorrido de directorio

    image_bytes = leer_y_desencriptar_archivo(relative_path_in_uploads)

    if image_bytes:
        # Determinar el tipo de contenido basado en la extensión del archivo
        _, ext = os.path.splitext(relative_path_in_uploads.replace('.enc', '').lower())
        mime_type = "image/png" # Por defecto
        if ext in ['.jpg', '.jpeg']:
            mime_type = "image/jpeg"
        elif ext == '.gif':
            mime_type = "image/gif"

        try:
            b64_string = base64.b64encode(image_bytes).decode('utf-8')
            return f"data:{mime_type};base64,{b64_string}"
        except Exception as e:
            logging.error(f"Error al codificar la imagen a base64 para {relative_path_in_uploads}: {e}", exc_info=True)
            return None
    return None
# --- Funciones Utilitarias ---
# (Sin cambios directos aquí para la privacidad)
def calcular_tiempo_transcurrido(fecha_param):
    ahora = datetime.now(timezone.utc)
    if not fecha_param: return "Fecha desconocida"
    fecha_obj = fecha_param
    if not isinstance(fecha_param, datetime):
        try:
            fecha_obj = datetime.fromisoformat(str(fecha_param)).replace(tzinfo=timezone.utc)
        except ValueError:
            logging.error(f"Formato de fecha inválido para calcular_tiempo_transcurrido: {fecha_param}")
            return "Fecha inválida"
    if fecha_obj.tzinfo is None:
        fecha_obj = fecha_obj.replace(tzinfo=timezone.utc)
    fecha_obj = fecha_obj.astimezone(timezone.utc)
    try:
        diferencia = ahora - fecha_obj
    except TypeError:
        logging.error(f"Error de tipo en fechas al calcular diferencia: '{ahora}' y '{fecha_obj}'")
        return "Error de fecha"
    if diferencia.total_seconds() < 0: return "En el futuro"
    days = diferencia.days
    secs = diferencia.seconds
    if days > 365: return f"hace más de un año"
    if days > 30: return f"hace {days // 30} mes{'es' if days // 30 > 1 else ''}"
    if days > 0: return f"hace {days} día{'s' if days > 1 else ''}"
    hrs = secs // 3600
    if hrs > 0: return f"hace {hrs} hora{'s' if hrs > 1 else ''}"
    mins = (secs % 3600) // 60
    if mins > 0: return f"hace {mins} minuto{'s' if mins > 1 else ''}"
    return "hace unos segundos"

def obtener_icono_para_accion(accion):
    iconos = {
        'visita_creada':'fas fa-calendar-plus text-blue-500',
        'grabacion_subida':'fas fa-upload text-green-500',
        'transcripcion_generada':'fas fa-file-alt text-purple-500',
        'resumen_generado':'fas fa-clipboard-list text-yellow-500',
        'notas_ia_generadas': 'fas fa-lightbulb text-orange-500',
        'visita_compartida': 'fas fa-share-alt text-teal-500',
        'documentos_subidos': 'fas fa-folder-open text-indigo-500',
        'resumen_registros_generado': 'fas fa-file-invoice text-pink-500',
        'visita_eliminada': 'fas fa-calendar-times text-red-600',
        'perfil_paciente_actualizado': 'fas fa-user-edit text-cyan-500',
        'paciente_eliminado': 'fas fa-user-slash text-red-700',
        'receta_creada': 'fas fa-prescription-bottle-alt text-lime-500',
        'referencia_creada': 'fas fa-directions text-amber-500',
        'receta_compartida': 'fas fa-envelope-open-text text-sky-500',
        'paciente_creado': 'fas fa-user-plus text-emerald-500',
        'plan_nutricional_creado': 'fas fa-apple-alt text-green-600',
        'plan_nutricional_compartido': 'fas fa-utensils text-blue-400',
    }
    return iconos.get(accion, 'fas fa-cog text-gray-500')

def obtener_datos_overview(visita_id_param=None):
    # Add the authentication check at the start
    if not current_user.is_authenticated:
        logging.warning("Intento de obtener overview sin usuario autenticado.")
        return {
            'staff': "No Asignado", 'paciente':'No disponible', 'paciente_id': None,
            'resumen':"Error: Por favor, inicie sesión.", 'activity_logs':[],
            'idioma_detectado':None, 'notas_ai': None, 'plantilla': 'N/E',
            'tipo_visita': 'N/D', 'resumen_ai': None
        }

    visita_id_a_buscar = visita_id_param if visita_id_param is not None else session.get('visita_actual_id')
    logging.info(f"Obteniendo datos overview para Visita ID: {visita_id_a_buscar} por Usuario ID: {current_user.id}")

    overview = {
        'staff': "No asignado", 'paciente':'No disponible', 'paciente_id': None,
        'paciente_identificacion_documento': None, 'paciente_telefono': None, 'paciente_email': None,
        'paciente_estado_tratamiento': None, 'resumen':"No disponible", 'activity_logs':[],
        'idioma_detectado':None, 'notas_ai': None, 'plantilla': 'N/E', 'tipo_visita': 'N/D', 'resumen_ai': None
    }

    if visita_id_a_buscar:
        try:
            visita_query = db.session.query(Visita).filter_by(id=int(visita_id_a_buscar))
            # The rest of the function remains the same
            # ...
            # A good practice would be to use current_user.id directly after the initial check
            visita_query = visita_query.filter_by(medico_id=current_user.id)
            visita = visita_query.first()
            # ...
            # The code inside the if block can stay as it is because we already checked for authentication.
        except Exception as e:
            logging.error(f"Error obteniendo datos overview para Visita ID {visita_id_a_buscar}: {e}", exc_info=True)
            overview.update({'resumen':"Error cargando datos de la visita.", 'paciente':"Error", 'staff':"Error"})
    else:
        overview['resumen']="No se ha especificado ninguna visita activa."
        logging.info("No se proporcionó ID de visita para obtener datos overview.")

    # This part of the code is now safe because the function will return early if no user is authenticated.
    if visita and visita.paciente:
        #... existing code
    return overview

# --- Funciones de IA y Texto (Sin cambios directos aquí para la privacidad) ---
def normalize_language_code(code):
    if not code: return None
    code_lower = str(code).lower().strip()
    mapping = {
        "english": "en", "inglés": "en", "ingles": "en", "eng": "en",
        "spanish": "es", "español": "es", "spa": "es",
        "french": "fr", "français": "fr", "francés": "fr", "fra": "fr",
        "german": "de", "alemán": "de", "deutsch": "de", "deu": "de", "ger": "de",
        "italian": "it", "italiano": "it", "ita": "it",
        "portuguese": "pt", "portugués": "pt", "portugues": "pt", "por": "pt"
    }
    if code_lower in mapping: return mapping[code_lower]
    if 2 <= len(code_lower) <= 3 and code_lower.isalpha(): return code_lower
    logging.warning(f"No se pudo normalizar el código de idioma '{code_lower}' a un formato conocido (ej. 'en', 'es'). Se devolverá sin cambios si tiene 2-3 letters, or None.")
    return None

translation_pipelines_cache = {}
def _traducir_texto_interno(texto_original, idioma_origen_code, idioma_destino_code, max_chunk_length=500):
    global HUGGINGFACE_PIPELINE_AVAILABLE
    if not HUGGINGFACE_PIPELINE_AVAILABLE or not pipeline:
        logging.error("Traducción con Hugging Face no disponible (biblioteca 'transformers' no importada).")
        return f"[Error de traducción: Servicio Hugging Face no disponible]\n{texto_original}"
    if not texto_original or not isinstance(texto_original, str) or not texto_original.strip():
        return texto_original
    norm_idioma_origen_code = normalize_language_code(idioma_origen_code)
    norm_idioma_destino_code = normalize_language_code(idioma_destino_code)
    if norm_idioma_origen_code == norm_idioma_destino_code and norm_idioma_origen_code is not None:
        logging.info(f"Traducción HF no necesaria: idioma origen ({norm_idioma_origen_code}) y destino ({norm_idioma_destino_code}) son iguales.")
        return texto_original
    if not norm_idioma_origen_code:
        logging.warning(f"Traducción HF cancelada: idioma de origen no válido o desconocido después de normalizar '{idioma_origen_code}'.")
        return f"[Error: Idioma de origen ('{idioma_origen_code}') no válido para traducir]\n{texto_original}"
    if not norm_idioma_destino_code:
        logging.warning(f"Traducción HF cancelada: idioma de destino no válido o desconocido después de normalizar '{idioma_destino_code}'.")
        return f"[Error: Idioma de destino ('{idioma_destino_code}') no válido para traducir]\n{texto_original}"
    model_name = f"Helsinki-NLP/opus-mt-{norm_idioma_origen_code}-{norm_idioma_destino_code}"
    pipeline_key = model_name
    logging.info(f"Intentando traducir con Hugging Face: Modelo '{model_name}' para '{norm_idioma_origen_code}' -> '{norm_idioma_destino_code}'")
    try:
        if pipeline_key in translation_pipelines_cache:
            translator = translation_pipelines_cache[pipeline_key]
            logging.info(f"Usando pipeline de traducción cacheado para {model_name}")
        else:
            logging.info(f"Cargando nuevo pipeline de traducción para {model_name}...")
            
            # --- INICIO DE LA SECCIÓN CORREGIDA ---
            # Forzamos la CPU para el pipeline de Hugging Face si no necesitamos GPU.
            # Esto evita que transformers intente instalar o usar torch con CUDA.
            device_arg = -1 # -1 para forzar el uso de CPU
            logging.info(f"Forzando uso de CPU para el pipeline de traducción de Hugging Face para {model_name}.")
            # --- FIN DE LA SECCIÓN CORREGIDA ---

            translator = pipeline("translation", model=model_name, tokenizer=model_name, device=device_arg) # type: ignore
            translation_pipelines_cache[pipeline_key] = translator
            logging.info(f"Pipeline para {model_name} cargado y cacheado (device: {device_arg}).")
        
        chunks = []
        if len(texto_original) > max_chunk_length:
            sentences = re.split(r'(?<=[.!?])\s+', texto_original)
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 < max_chunk_length:
                    current_chunk += sentence + " "
                else:
                    if current_chunk.strip(): chunks.append(current_chunk.strip())
                    current_chunk = sentence + " "
            if current_chunk.strip(): chunks.append(current_chunk.strip())
        else:
            chunks = [texto_original]
        logging.info(f"Texto dividido en {len(chunks)} chunks para traducción.")
        texto_traducido_completo = ""
        for i, chunk_text in enumerate(chunks):
            if not chunk_text.strip(): continue
            resultados_traduccion_chunk = translator(chunk_text, max_length=max_chunk_length + 100) # type: ignore
            if resultados_traduccion_chunk and isinstance(resultados_traduccion_chunk, list) and \
               len(resultados_traduccion_chunk) > 0 and 'translation_text' in resultados_traduccion_chunk[0]:
                texto_traducido_completo += resultados_traduccion_chunk[0]['translation_text'] + " "
            else:
                logging.error(f"Respuesta inesperada del pipeline de traducción HF para chunk {i+1} del modelo {model_name}: {resultados_traduccion_chunk}")
                texto_traducido_completo += f"[Error traduciendo parte del texto] "
            gc.collect() # Recolectar basura después de cada chunk para liberar memoria
        if texto_traducido_completo.strip():
            logging.info(f"Traducción con Hugging Face ({model_name}) exitosa.")
            return texto_traducido_completo.strip()
        else:
            logging.error(f"Resultado de traducción vacío para {model_name} después de procesar chunks.")
            return f"[Error: Resultado de traducción vacío]\n{texto_original}"
    except RuntimeError as e_runtime:
        logging.error(f"Error de ejecución (RuntimeError) durante la traducción con Hugging Face ({model_name}): {e_runtime}", exc_info=True)
        if pipeline_key in translation_pipelines_cache:
            del translation_pipelines_cache[pipeline_key]
        gc.collect()
        logging.info(f"Pipeline {pipeline_key} eliminado del caché debido a RuntimeError. Se intentará recargar en la próxima solicitud si es necesario.")
        return f"[Error de ejecución del modelo de traducción: {str(e_runtime)[:100]}...]\n{texto_original}"
    except Exception as e:
        logging.error(f"Error durante la traducción con Hugging Face ({model_name}): {e}", exc_info=True)
        error_str = str(e).lower()
        if any(err_key in error_str for err_key in ["can't be instantiated", "does not exist", "is not a valid model identifier", "404", "not found"]):
            return f"[Error: Modelo de traducción HF no encontrado o inválido para '{norm_idioma_origen_code}' a '{norm_idioma_destino_code}']\n{texto_original}"
        return f"[Error durante la traducción con Hugging Face: {str(e)[:100]}...]\n{texto_original}"


def extraer_texto_de_pdf(ruta_archivo_local):
    texto = ""
    if not PyPDF2: return "[Error: PyPDF2 no está disponible para extraer texto de PDFs]"
    try:
        with open(ruta_archivo_local, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                texto_pagina = page.extract_text()
                if texto_pagina:
                    texto += texto_pagina + "\n"
        logging.info(f"Texto extraído de PDF: {os.path.basename(ruta_archivo_local)} (longitud: {len(texto)})")
    except Exception as e:
        logging.error(f"Error extrayendo texto de PDF {os.path.basename(ruta_archivo_local)}: {e}", exc_info=True)
        texto = f"[Error al extraer texto de PDF: {os.path.basename(ruta_archivo_local)}]"
    return texto

def extraer_texto_de_docx(ruta_archivo_local):
    texto = ""
    if not DocxDocument: return "[Error: python-docx no está disponible para extraer texto de DOCX]"
    try:
        doc = DocxDocument(ruta_archivo_local)
        for para in doc.paragraphs:
            texto += para.text + "\n"
        logging.info(f"Texto extraído de DOCX: {os.path.basename(ruta_archivo_local)} (longitud: {len(texto)})")
    except Exception as e:
        logging.error(f"Error extrayendo texto de DOCX {os.path.basename(ruta_archivo_local)}: {e}", exc_info=True)
        texto = f"[Error al extraer texto de DOCX: {os.path.basename(ruta_archivo_local)}]"
    return texto

def extraer_texto_de_txt(ruta_archivo_local):
    texto = ""
    try:
        with open(ruta_archivo_local, 'r', encoding='utf-8', errors='ignore') as f:
            texto = f.read()
        logging.info(f"Texto extraído de TXT: {os.path.basename(ruta_archivo_local)} (longitud: {len(texto)})")
    except Exception as e:
        logging.error(f"Error extrayendo texto de TXT {os.path.basename(ruta_archivo_local)}: {e}", exc_info=True)
        texto = f"[Error al extraer texto de TXT: {os.path.basename(ruta_archivo_local)}]"
    return texto

def extraer_texto_de_imagen_ocr(ruta_archivo_local):
    texto = ""
    if not Image or not pytesseract: return "[Error: Pillow o Pytesseract no están disponibles para OCR]"
    try:
        pytesseract.get_tesseract_version()
        texto = pytesseract.image_to_string(Image.open(ruta_archivo_local), lang='spa+eng')
        logging.info(f"Texto extraído de imagen (OCR): {os.path.basename(ruta_archivo_local)} (longitud: {len(texto)})")
    except pytesseract.TesseractNotFoundError:
        logging.critical("Tesseract OCR no está instalado o no se encuentra en el PATH. OCR no funcionará.")
        texto = "[OCR no disponible: Tesseract no configurado en el servidor]"
    except Exception as e:
        logging.error(f"Error extrayendo texto de imagen (OCR) {os.path.basename(ruta_archivo_local)}: {e}", exc_info=True)
        texto = f"[Error al extraer texto de imagen con OCR: {os.path.basename(ruta_archivo_local)}]"
    return texto

def contar_tokens_openai(texto, modelo="gpt-3.5-turbo"):
    if not tiktoken:
        logging.warning("tiktoken no está disponible. No se puede contar tokens con precisión.")
        return len(texto.split())
    if not texto or not isinstance(texto, str): return 0
    try:
        encoding = tiktoken.encoding_for_model(modelo)
    except KeyError:
        logging.warning(f"Modelo {modelo} no encontrado para tiktoken. Usando cl100k_base como fallback.")
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(texto))

def _llamar_openai_chat(prompt_sistema, prompt_usuario, modelo_chat="gpt-3.5-turbo-0125", max_tokens_salida=500, temperature=0.2, response_format=None):
    global client_openai
    if not client_openai:
        logging.error("Intento de llamar a OpenAI Chat API sin cliente inicializado.")
        raise ValueError("Cliente OpenAI no inicializado. Verifica la API Key y la configuración.")
    logging.info(f"Llamando a OpenAI Chat API. Modelo: {modelo_chat}. Max tokens de salida: {max_tokens_salida}. Temperatura: {temperature}. Response Format: {response_format}")
    try:
        api_params = {
            "model": modelo_chat,
            "messages": [
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            "max_tokens": max_tokens_salida,
            "temperature": temperature,
        }
        if response_format:
            api_params["response_format"] = response_format
        completion = client_openai.chat.completions.create(**api_params) # type: ignore
        resultado = completion.choices[0].message.content.strip() if completion.choices and completion.choices[0].message else ""
        if completion.usage:
            logging.info(f"OpenAI Chat API Completado. Tokens usados: Prompt={completion.usage.prompt_tokens}, Completado={completion.usage.completion_tokens}, Total={completion.usage.total_tokens}")
        else:
            logging.warning("OpenAI Chat API: No se encontró información de uso de tokens en la respuesta.")
        return resultado
    except APIError as e:
        logging.error(f"Error de API OpenAI ({e.status_code if hasattr(e, 'status_code') else 'N/A'}): {e.message if hasattr(e, 'message') else str(e)}", exc_info=True)
        raise
    except APIConnectionError as e_conn:
        logging.error(f"Error de conexión con OpenAI: {e_conn}", exc_info=True)
        raise
    except RateLimitError as e_rate:
        logging.error(f"Error de límite de tasa de OpenAI: {e_rate}", exc_info=True)
        raise
    except AuthenticationError as e_auth:
        logging.error(f"Error de autenticación con OpenAI (verifica API Key): {e_auth}", exc_info=True)
        raise
    except BadRequestError as e_bad_req:
        logging.error(f"Error de solicitud incorrecta a OpenAI (BadRequestError): {e_bad_req}", exc_info=True)
        raise
    except Exception as e_general:
        logging.error(f"Error inesperado llamando a OpenAI: {e_general}", exc_info=True)
        raise

def resumir_texto_con_openai(texto_completo, modelo_chat="gpt-3.5-turbo-0125", max_tokens_salida=500, max_tokens_contexto_modelo=16000):
    if not texto_completo or not texto_completo.strip():
        return "No hay contenido textual suficiente para generar un resumen con IA."
    prompt_sistema = (
        "Eres un asistente médico virtual altamente especializado en analizar y resumir información clínica compleja "
        "proveniente de múltiples fuentes (PDFs, DOCX, TXT, imágenes OCR). Tu objetivo es producir un resumen conciso, "
        "estructurado y clínicamente relevante, ideal para que un profesional de la salud lo revise rápidamente. "
        "El resumen debe estar en formato Markdown. "
        "Si el texto contiene errores de OCR o es incoherente, intenta extraer la información más plausible y señala brevemente las áreas problemáticas si es necesario, pero prioriza generar un resumen útil."
        "Si el contenido es muy escaso o no parece clínico, indícalo."
        "La respuesta debe ser ÚNICAMENTE el resumen en Markdown, sin frases introductorias como 'Aquí está el resumen:'."
    )
    prompt_usuario_template = (
        "A partir del siguiente texto concatenado, extraído de varios documentos médicos de un paciente, genera un resumen clínico estructurado. "
        "El resumen debe incluir (si la información está presente en el texto):\n"
        "- **Datos del Paciente (si se mencionan explícitamente):** Nombre, edad, etc.\n"
        "- **Motivo Principal de Consulta/Problemas Activos:**\n"
        "- **Antecedentes Relevantes (Médicos, Quirúrgicos, Familiares, Sociales):**\n"
        "- **Hallazgos Clave de Exámenes/Estudios (si se describen):**\n"
        "- **Diagnósticos (Actuales o Previos mencionados):**\n"
        "- **Tratamientos (Actuales o Previos mencionados):**\n"
        "- **Recomendaciones o Planes (si se detallan):**\n"
        "Si alguna sección no tiene información, puedes omitirla o indicar 'No se encontró información'.\n"
        "Formatea la salida usando Markdown para una fácil lectura (encabezados, listas, negritas).\n"
        "--- INICIO DEL TEXTO DE LOS DOCUMENTOS ---\n"
        "{TEXTO_DOCUMENTOS}\n"
        "--- FIN DEL TEXTO DE LOS DOCUMENTOS ---\n\n"
        "Resumen Clínico Estructurado (en Markdown):"
    )
    tokens_prompt_base = contar_tokens_openai(prompt_sistema + prompt_usuario_template.replace("{TEXTO_DOCUMENTOS}", ""), modelo=modelo_chat)
    buffer_tokens = 250
    limite_tokens_documentos = max_tokens_contexto_modelo - tokens_prompt_base - max_tokens_salida - buffer_tokens
    texto_a_resumir = texto_completo
    tokens_documentos_actuales = contar_tokens_openai(texto_a_resumir, modelo=modelo_chat)
    if tokens_documentos_actuales > limite_tokens_documentos:
        logging.warning(f"El texto de los documentos ({tokens_documentos_actuales} tokens) excede el límite de {limite_tokens_documentos} tokens para el modelo {modelo_chat} con los prompts actuales. Se truncará el texto.")
        if tiktoken:
            try:
                encoding = tiktoken.encoding_for_model(modelo_chat)
            except KeyError:
                encoding = tiktoken.get_encoding("cl100k_base")
            tokens_codificados = encoding.encode(texto_a_resumir)
            tokens_truncados = tokens_codificados[:limite_tokens_documentos]
            texto_a_resumir = encoding.decode(tokens_truncados, errors='replace')
            logging.info(f"Texto truncado a aproximadamente {contar_tokens_openai(texto_a_resumir, modelo_chat)} tokens.")
            texto_a_resumir += "\n\n[AVISO: El texto original era demasiado largo y ha sido truncado para su procesamiento por IA.]"
        else:
            texto_a_resumir = texto_a_resumir[:limite_tokens_documentos * 4]
            texto_a_resumir += "\n\n[AVISO: El texto original era demasiado largo y ha sido truncado para su procesamiento por IA. (Sin tiktoken, truncado aproximado)]"
    prompt_final_usuario = prompt_usuario_template.format(TEXTO_DOCUMENTOS=texto_a_resumir)
    try:
        return _llamar_openai_chat(prompt_sistema, prompt_final_usuario, modelo_chat, max_tokens_salida, temperature=0.2)
    except ValueError as ve:
        logging.error(f"Error de configuración al llamar a OpenAI para resumir: {ve}")
        return f"[Error de configuración del servicio de IA: {str(ve)}]"
    except APIError as e:
        logging.error(f"Error de API OpenAI al intentar resumir: {e}", exc_info=True)
        error_message = f"[Error API OpenAI: {e.message if hasattr(e, 'message') else str(e)} (Código: {e.code if hasattr(e, 'code') else e.status_code if hasattr(e, 'status_code') else 'N/A'})]"
        if hasattr(e, 'code') and e.code == 'context_length_exceeded':
            error_message = "[Error: Los documentos son demasiado largos para ser procesados por el modelo de IA, incluso después de intentar truncarlos.]"
        return error_message
    except Exception as e_gen:
        logging.error(f"Error inesperado al resumir con OpenAI: {e_gen}", exc_info=True)
        return "[Ocurrió un error inesperado al intentar generar el resumen con IA.]"

def generar_resumen_inteligente_documentos(texto_completo_documentos):
    global client_openai
    if not texto_completo_documentos or not texto_completo_documentos.strip():
        return "No se extrajo contenido textual de los documentos para resumir."
    if client_openai:
        return resumir_texto_con_openai(
            texto_completo_documentos,
            modelo_chat="gpt-3.5-turbo-0125",
            max_tokens_salida=1000,
            max_tokens_contexto_modelo=16385
        )
    else:
        logging.warning("Cliente OpenAI no disponible. Devolviendo un extracto del texto en lugar de un resumen IA.")
        extracto = texto_completo_documentos[:2500] + ("..." if len(texto_completo_documentos) > 2500 else "")
        return (f"[Resumen con IA no disponible (servicio no configurado).]\n\n"
                f"-- INICIO DEL EXTRACTO DE LOS DOCUMENTOS --\n{extracto}\n-- FIN DEL EXTRACTO --")

language_codes_to_names = {
    'es': 'Español', 'en': 'Inglés', 'fr': 'Francés',
    'de': 'Alemán', 'it': 'Italiano', 'pt': 'Portugués',
}

def generar_resumen_ai_desde_transcripcion(transcripcion, plantilla_prompt="SOAP", idioma_objetivo_para_prompt="es"):
    if not transcripcion or not transcripcion.strip(): return "[No hay transcripción para generar resumen.]"
    global client_openai
    if not client_openai: return "[Error: Servicio IA (OpenAI) no configurado para resumen.]"
    nombre_idioma_prompt = language_codes_to_names.get(idioma_objetivo_para_prompt, f"el idioma del texto ({idioma_objetivo_para_prompt})")
    prompt_sistema = (
        f"Eres un asistente médico experto en extraer información clave de transcripciones y estructurarla CONCISAMENTE para un RESUMEN. "
        f"Responde en {nombre_idioma_prompt}. La respuesta debe ser ÚNICAMENTE el resumen en Markdown, sin frases introductorias."
    )
    plantilla_norm = plantilla_prompt.strip().lower() if plantilla_prompt else "general"
    prompt_usuario = ""
    common_instruction = (
        f"Analiza la siguiente transcripción de una consulta médica. Extrae la información relevante y RESÚMELA. "
        f"Si alguna sección no tiene información clara, indícalo. Responde en {nombre_idioma_prompt} usando formato Markdown conciso.\n\n"
        f"Transcripción:\n{transcripcion}\n\n"
    )
    if plantilla_norm == "soap":
        prompt_usuario = (
            common_instruction +
            f"Formato del resumen: notas SOAP (Subjetivo, Objetivo, Análisis, Plan).\n"
            f"Resumen en formato SOAP (en {nombre_idioma_prompt}):"
        )
    elif plantilla_norm == "soap simple":
        prompt_usuario = (
            common_instruction +
            f"Formato del resumen: SOAP simple (Subjetivo, Objetivo, Análisis, Plan), enfocándote en los puntos más cruciales.\n"
            f"Resumen SOAP Simple (en {nombre_idioma_prompt}):"
        )
    elif plantilla_norm == "consulta general":
        prompt_usuario = (
            common_instruction +
            f"Formato del resumen: Consulta General. Incluye Motivo de Consulta, Historia, Examen Físico, diagnósticos/impresiones, y plan de tratamiento/seguimiento conciso.\n"
            f"Resumen de Consulta General (en {nombre_idioma_prompt}):"
        )
    else: # Default or fallback
        prompt_usuario = (
            common_instruction +
            f"Formato del resumen: Puntos más importantes (problema principal, hallazgos significativos, plan de acción).\n"
            f"Resumen (en {nombre_idioma_prompt}):"
        )
    logging.info(f"Generando RESUMEN AI para transcripción. Plantilla: {plantilla_prompt}. Idioma: {idioma_objetivo_para_prompt}")
    try:
        return _llamar_openai_chat(prompt_sistema, prompt_usuario, modelo_chat="gpt-3.5-turbo-0125", max_tokens_salida=700, temperature=0.3)
    except ValueError as ve: return f"[Error de configuración del servicio de IA: {str(ve)}]"
    except APIError as e: return f"[Error API OpenAI (Resumen Transcripción): {e.message if hasattr(e, 'message') else str(e)}]"
    except Exception as e_gen:
        return f"[Error inesperado al generar resumen de transcripción: {str(e_gen)}]"

def generar_notas_ai_desde_transcripcion(transcripcion, plantilla_tipo="SOAP", idioma_objetivo_para_prompt="es", especialidad_usuario=None):
    if not transcripcion or not transcripcion.strip() or transcripcion.startswith("[Error"):
        return "[No hay transcripción válida para generar notas o contiene errores.]"
    global client_openai
    if not client_openai:
        return "[Error: Servicio IA (OpenAI) no configurado para notas.]"
    
    nombre_idioma_prompt = language_codes_to_names.get(idioma_objetivo_para_prompt, f"el idioma del texto ({idioma_objetivo_para_prompt})")    
    if especialidad_usuario and especialidad_usuario.strip().lower() == 'nutrición':
        prompt_sistema = (
            f"Eres un asistente de nutricionistas altamente competente, especializado en generar notas clínicas de nutrición detalladas y estructuradas. "
            f"Tu tarea es EXTRACTAR información PERTINENTE ÚNICAMENTE de la transcripción proporcionada. "
            f"NO inventes ni extrapoles información que no esté en la transcripción. "
            f"Si alguna sección no tiene información, indícalo explícitamente (ej. 'No se menciona en la transcripción'). "
            f"Tu respuesta debe estar en {nombre_idioma_prompt} y formateada estrictamente en Markdown. "
            f"La respuesta debe ser ÚNICAMENTE las notas en Markdown, sin frases introductorias."
        )

        prompt_usuario = (
            f"A partir de la siguiente transcripción de una consulta nutricional, genera notas clínicas DETALLADAS. "
            f"Basa tus notas estrictamente en la transcripción. La estructura de las notas debe ser la siguiente:\n"
            f"- **Motivo de Consulta Nutricional:**\n"
            f"- **Antecedentes Relevantes:** (Médicos, dietéticos, historial de peso, alergias, intolerancias, preferencias, aversiones)\n"
            f"- **Evaluación del Estilo de Vida:** (Actividad física, sueño, estrés, consumo de agua/alcohol)\n"
            f"- **Recordatorio de 24 horas o Patrón Alimentario (si se describe):**\n"
            f"- **Evaluación Antropométrica (si se menciona):** (Peso, talla, IMC, circunferencias)\n"
            f"- **Objetivos del Paciente:** (Metas de peso, salud, rendimiento, etc.)\n"
        f"- **Impresión Diagnóstica Nutricional:** (Basado en la información recabada)\n"
            f"- **Plan de Intervención y Educación:** (Recomendaciones específicas, pautas dietéticas, suplementación discutida, metas acordadas)\n"
            f"- **Seguimiento y Próxima Cita:**\n\n"
            f"Transcripción:\n{transcripcion}\n\n"
            f"Notas de Consulta Nutricional Detalladas (en {nombre_idioma_prompt}):"
        )
        
        logging.info(f"Generando NOTAS AI para transcripción con plantilla de NUTRICIÓN. Idioma: {idioma_objetivo_para_prompt}")

    else:
        prompt_sistema = (
            f"Eres un asistente médico altamente competente, especializado en generar NOTAS CLÍNICAS DETALLADAS y estructuradas. "
            f"Tu tarea principal es EXTRACTAR información PERTINENTE ÚNICAMENTE de la transcripción proporcionada. "
            f"NO inventes, extrapoles o añadas información que no esté explícitamente contenida en la transcripción. "
            f"Si alguna sección no tiene información clara o no se menciona en la transcripción, indícalo explícitamente (ej. 'No se menciona en la transcripción', 'Información no disponible') o omite la sección si no es aplicable. "
            f"Tu respuesta debe estar en {nombre_idioma_prompt} y formateada estrictamente en Markdown. "
            f"La respuesta debe ser ÚNICAMENTE las notas en Markdown, sin frases introductorias ni texto adicional fuera de las notas estructuradas."
        )

        plantilla_norm = plantilla_tipo.strip().lower() if plantilla_tipo else "general"
        prompt_usuario = ""
        common_instruction_notas = (
            f"A partir de la siguiente transcripción de una consulta médica, genera notas clínicas DETALLADAS. "
            f"Sé exhaustivo en cada sección, extrayendo TODA la información pertinente DIRECTAMENTE de la transcripción. "
            f"Si un dato no está en la transcripción, NO LO INVENTES, indica que no está disponible o es omite esa parte. "
            f"Responde en {nombre_idioma_prompt} usando formato Markdown. "
            f"Asegúrate de que cada punto de tus notas esté respaldado por la transcripción.\n\n"
            f"Transcripción:\n{transcripcion}\n\n"
        )
        if plantilla_norm == "soap":
            prompt_usuario = (
                common_instruction_notas +
                f"Formato de las notas: SOAP (Subjetivo, Objetivo, Análisis, Plan).\n"
                f"Notas SOAP Detalladas (en {nombre_idioma_prompt}):"
            )
        elif plantilla_norm == "soap simple":
            prompt_usuario = (
                common_instruction_notas +
                f"Formato de las notas: SOAP simple. Presenta de forma CONCISA pero COMPLETA la información Subjetiva, Objetiva, el Análisis y el Plan.\n"
                f"Notas SOAP Simple (en {nombre_idioma_prompt}):"
            )
        elif plantilla_norm == "consulta general":
            prompt_usuario = (
                common_instruction_notas +
                f"Formato de las notas: Consulta General. Incluye obligatoriamente: Motivo de Consulta, Historia de la Enfermedad Actual, Antecedentes (Personales Patológicos, Heredofamiliares, No Patológicos), "
                f"Revisión por Aparatos y Sistemas (si se infiere), Hallazgos DETALLADOS del Examen Físico (si se describen), Resultados de Estudios (si se mencionan), "
                f"Impresión Diagnóstica (o diferenciales), y Plan de Tratamiento y Seguimiento DETALLADO (medicamentos con dosis, indicaciones, estudios a solicitar, próxima cita).\n"
                f"Notas de Consulta General Detalladas (en {nombre_idioma_prompt}):"
            )
        else: 
            prompt_usuario = (
                common_instruction_notas +
                f"Formato de las notas: Estructura lógica estándar para una historia clínica, cubriendo todos los aspectos relevantes mencionados.\n"
                f"Notas Clínicas Detalladas (en {nombre_idioma_prompt}):"
            )
        logging.info(f"Generando NOTAS AI para transcripción. Plantilla: {plantilla_tipo}. Idioma: {idioma_objetivo_para_prompt}")
        
    try:
        markdown_text = _llamar_openai_chat(prompt_sistema, prompt_usuario, modelo_chat="gpt-3.5-turbo-0125", max_tokens_salida=1500, temperature=0.35)
        html_rendered = markdown.markdown(markdown_text)
        return {'markdown': markdown_text, 'html': html_rendered}
    except ValueError as ve: return f"[Error de configuración del servicio de IA: {str(ve)}]"
    except APIError as e: return f"[Error API OpenAI (Notas Transcripción): {e.message if hasattr(e, 'message') else str(e)}]"
    except Exception as e_gen: 
        return f"[Error inesperado al generar notas de transcripción: {str(e_gen)}]"

def extraer_medicamentos_con_ia(transcripcion, idioma_detectado='es'):
    global client_openai
    if not client_openai or not transcripcion or not transcripcion.strip():
        logging.warning("Extracción de medicamentos cancelada: Cliente OpenAI no disponible o transcripción vacía.")
        return None
    nombre_idioma_transcripcion = language_codes_to_names.get(idioma_detectado, idioma_detectado)
    
    # --- PROMPT MEJORADO PARA DIFERENCIAR 'CANTIDAD' Y 'DOSIS' ---
    prompt_sistema = (
        "Eres un asistente médico experto en farmacología y análisis de transcripciones. Tu tarea es analizar una transcripción y extraer información de medicamentos con alta precisión."
        "\nPara cada medicamento, obtén:"
        "\n- 'nombre': Nombre completo, concentración y forma farmacéutica (Ej: 'Amoxicilina 500mg Comprimidos')."
        "\n- 'cantidad': La cantidad TOTAL del producto a despachar en la farmacia. Se refiere al empaque o al número total de unidades (Ej: '1 caja de 20 comprimidos', '2 frascos', 'Suministro para 1 mes')."
        "\n- 'dosis': La cantidad de medicamento que el paciente toma en CADA TOMA INDIVIDUAL (Ej: '1 comprimido', '5 ml', '2 gotas')."
        "\n- 'frecuencia': Cada cuánto tiempo se debe tomar la dosis (Ej: 'Cada 8 horas', '3 veces al día')."
        "\n- 'duracion': Por cuánto tiempo se debe seguir el tratamiento (Ej: 'Por 7 días', 'Durante 1 mes')."
        "\n- 'indicaciones': Instrucciones adicionales para ese medicamento (Ej: 'Tomar con abundante agua', 'Después de las comidas')."
        "\n\n**INSTRUCCIÓN CRÍTICA**: No confundas 'cantidad' (el total a despachar, ej: '1 caja') con 'dosis' (la toma individual, ej: '1 tableta'). Son dos conceptos distintos y es vital no mezclarlos."
        "\n\nAdicionalmente, si se menciona, extrae un 'diagnostico_sugerido' que justifique la prescripción."
        "\n\nDevuelve la información estrictamente en el siguiente formato JSON. Si no se especifica algún detalle para un medicamento, usa una cadena vacía '' o null. Si no se mencionan medicamentos, devuelve un array 'medicamentos' vacío."
        "\nEjemplo de formato de salida:"
        "\n{\"medicamentos\": [{\"nombre\": \"Ibuprofeno 600mg Comprimidos\", \"cantidad\": \"1 caja (30 comps)\", \"dosis\": \"1 comprimido\", \"frecuencia\": \"Cada 8 horas si hay dolor\", \"duracion\": \"Por 5 días\", \"indicaciones\": \"Tomar con alimentos\"}], \"diagnostico_sugerido\": \"Cefalea tensional\"}"
        "\nResponde ÚNICAMENTE con el objeto JSON."
    )
    
    prompt_usuario = f"Transcripción clínica:\n---\n{transcripcion}\n---\nExtrae la información de prescripción en el formato JSON especificado."
    logging.info(f"Solicitando extracción de medicamentos de la transcripción (Idioma: {idioma_detectado}). Usando modelo gpt-4o o similar con prompt mejorado.")
    try:
        model_to_use = "gpt-4o"
        datos_extraidos = _llamar_openai_chat(prompt_sistema, prompt_usuario,
                                              modelo_chat=model_to_use, max_tokens_salida=1500,
                                              temperature=0.05, response_format={"type": "json_object"})
        json_to_parse = datos_extraidos
        if json_to_parse.startswith("```json"):
            json_to_parse = json_to_parse[7:]
        if json_to_parse.endswith("```"):
            json_to_parse = json_to_parse[:-3]
        json_to_parse = json_to_parse.strip()
        parsed_data = json.loads(json_to_parse)
        if isinstance(parsed_data, dict) and \
           "medicamentos" in parsed_data and \
           isinstance(parsed_data["medicamentos"], list):
            logging.info(f"Medicamentos extraídos exitosamente: {len(parsed_data['medicamentos'])} items. Diagnóstico sugerido: {parsed_data.get('diagnostico_sugerido')}")
            return parsed_data
        else:
            logging.warning(f"Respuesta IA para medicamentos no tiene la estructura JSON esperada: {json_to_parse}")
            return {"medicamentos": [], "diagnostico_sugerido": "[Error: Estructura JSON inesperada de IA]"}
    except json.JSONDecodeError as e_json:
        logging.error(f"Error decodificando JSON de OpenAI para medicamentos: {e_json}. Respuesta intentada: '{json_to_parse if 'json_to_parse' in locals() else 'N/A'}'")
        return {"medicamentos": [], "diagnostico_sugerido": "[Error: IA no devolvió JSON válido]"}
    except APIError as e_api:
        logging.error(f"Error de API OpenAI extrayendo medicamentos: {e_api}", exc_info=True)
        return {"medicamentos": [], "diagnostico_sugerido": f"[Error API OpenAI: {e_api.message if hasattr(e_api, 'message') else str(e_api)}]"}
    except Exception as e:
        logging.error(f"Error inesperado al extraer medicamentos con IA: {e}", exc_info=True)
        return {"medicamentos": [], "diagnostico_sugerido": f"[Error inesperado en extracción: {str(e)}]"}

def generar_contenido_plan_nutricional_con_ia(transcripcion, idioma_detectado='es'):
    global client_openai
    if not client_openai or not transcripcion or not transcripcion.strip():
        logging.warning("Generación de plan nutricional cancelada: Cliente OpenAI no disponible o transcripción vacía.")
        return {"error": "Cliente OpenAI no disponible o transcripción vacía para generar plan."}
    nombre_idioma_transcripcion = language_codes_to_names.get(idioma_detectado, idioma_detectado)
    prompt_sistema = (
        f"Eres un nutricionista experto altamente especializado en crear planes de alimentación personalizados basados en transcripciones de consultas. "
        f"Analiza la siguiente transcripción de una consulta con un paciente. Tu tarea es extraer información relevante como objetivos del paciente, "
        f"preferencias alimentarias, aversiones, alergias, condiciones médicas, nivel de actividad física, y cualquier otro dato pertinente. "
        f"Con base en esto, genera un plan nutricional detallado. "
        f"El plan debe incluir: "
        f"1. 'objetivo_principal': El objetivo principal del plan (ej: pérdida de peso, aumento de masa muscular, control de diabetes). "
        f"2. 'recomendaciones_generales': Lista de consejos generales (ej: beber 2L de agua, evitar ultraprocesados). "
        f"3. 'plan_diario_tipo': Un ejemplo de un día de comidas, estructurado por tiempo de comida (Desayuno, Media Mañana, Almuerzo, Merienda, Cena). "
        f"   Cada comida debe tener una lista de 'opciones_alimento', donde cada opción es un string describiendo el alimento y la porción sugerida (ej: '1 taza de avena cocida con 1/2 taza de fresas y 10 almendras', 'Pechuga de pollo a la plancha (150g) con ensalada mixta grande y 1/2 taza de quinoa cocida'). "
        f"4. 'notas_adicionales_plan': Cualquier nota importante específica para el plan. "
        f"Devuelve la información estrictamente en formato JSON. El JSON debe ser un objeto con las claves 'objetivo_principal', 'recomendaciones_generales' (array de strings), "
        f"'plan_diario_tipo' (objeto con claves de tiempo de comida, cada una un array de strings de opciones), y 'notas_adicionales_plan' (string). "
        f"Si no se especifica algún detalle, usa una cadena vacía '' o un array vacío []. "
        f"La transcripción está en {nombre_idioma_transcripcion}. La respuesta JSON NO debe incluir ninguna explicación adicional, solo el JSON puro. "
        f"Ejemplo de formato de salida esperado: "
        f"{{"
        f"  \"objetivo_principal\": \"Pérdida de peso gradual (0.5-1kg por semana)\", "
        f"  \"recomendaciones_generales\": ["
        f"    \"Beber al menos 2 litros de agua al día.\", "
        f"    \"Realizar 30 minutos de actividad física moderada 5 veces por semana.\", "
        f"    \"Evitar bebidas azucaradas y alimentos ultraprocesados.\" "
        f"  ], "
        f"  \"plan_diario_tipo\": {{ "
        f"    \"Desayuno\": [\"Opción 1: Batido de proteína (1 scoop) con espinacas, 1/2 plátano y 1 cda de chía.\", \"Opción 2: 2 huevos revueltos con tomate y cebolla, 1 tortilla de maíz integral.\"], "
        f"    \"Media Mañana\": [\"1 manzana mediana con 10-12 almendras.\"], "
        f"    \"Almuerzo\": [\"Opción 1: Salmón al horno (150g) con espárragos y 1/2 taza de camote asado.\", \"Opción 2: Lentejas guisadas (1.5 tazas) con arroz integral (1/2 taza) y ensalada verde.\"], "
        f"    \"Merienda\": [\"1 yogurt griego natural sin azúcar con un puñado de arándanos.\"], "
        f"    \"Cena\": [\"Opción 1: Pechuga de pavo a la plancha (120g) con ensalada de hojas verdes, pepino y pimiento.\", \"Opción 2: Sopa de verduras casera con 2 tostadas integrales.\"] "
        f"  }}, "
        f"  \"notas_adicionales_plan\": \"Ajustar porciones según hambre y saciedad. Consultar si hay dudas.\" "
        f"}}"
        "\nResponde ÚNICAMENTE con el objeto JSON."
    )
    prompt_usuario = f"Transcripción de la consulta nutricional:\n---\n{transcripcion}\n---\nGenera el plan nutricional en el formato JSON especificado."
    logging.info(f"Solicitando generación de plan nutricional de la transcripción (Idioma: {idioma_detectado}). Usando modelo gpt-4o o similar.")
    try:
        model_to_use = "gpt-4o"
        datos_extraidos = _llamar_openai_chat(
            prompt_sistema, prompt_usuario,
            modelo_chat=model_to_use, max_tokens_salida=2000,
            temperature=0.2, response_format={"type": "json_object"}
        )
        json_to_parse = datos_extraidos
        if json_to_parse.startswith("```json"): json_to_parse = json_to_parse[7:]
        if json_to_parse.endswith("```"): json_to_parse = json_to_parse[:-3]
        json_to_parse = json_to_parse.strip()
        parsed_data = json.loads(json_to_parse)
        if isinstance(parsed_data, dict) and \
           all(k in parsed_data for k in ['objetivo_principal', 'recomendaciones_generales', 'plan_diario_tipo', 'notas_adicionales_plan']) and \
           isinstance(parsed_data['recomendaciones_generales'], list) and \
           isinstance(parsed_data['plan_diario_tipo'], dict):
            logging.info(f"Contenido del plan nutricional generado exitosamente.")
            return parsed_data
        else:
            logging.warning(f"Respuesta IA para plan nutricional no tiene la estructura JSON esperada: {json_to_parse}")
            return {"error": "Estructura JSON inesperada de IA para el plan nutricional."}
    except json.JSONDecodeError as e_json:
        logging.error(f"Error decodificando JSON de OpenAI para plan nutricional: {e_json}. Respuesta: '{json_to_parse if 'json_to_parse' in locals() else 'N/A'}'")
        return {"error": "IA no devolvió JSON válido para el plan nutricional."}
    except APIError as e_api:
        logging.error(f"Error de API OpenAI generando plan nutricional: {e_api}", exc_info=True)
        return {"error": f"Error API OpenAI: {e_api.message if hasattr(e_api, 'message') else str(e_api)}"}
    except Exception as e:
        logging.error(f"Error inesperado al generar plan nutricional con IA: {e}", exc_info=True)
        return {"error": f"Error inesperado en generación de plan: {str(e)}"}


def generar_y_guardar_pdf_plan_nutricional(plan_nut_obj, current_user_obj, paciente_obj):
    """
    Genera un PDF usando la plantilla 'ver_plan_nutricional.html' para asegurar
    que el diseño sea idéntico al de la página web.
    """
    global fernet_cipher
    if not plan_nut_obj or not plan_nut_obj.contenido_json:
        logging.error("No se puede generar PDF: objeto PlanNutricional o contenido_json faltante.")
        return None

    try:
        contenido_plan = json.loads(plan_nut_obj.contenido_json)
    except json.JSONDecodeError:
        logging.error(f"Error decodificando contenido_json del PlanNutricional ID {plan_nut_obj.id} para PDF.")
        return None

    try:
        # --- CAMBIO CLAVE: Renderizar la misma plantilla que se usa para ver el plan ---
        html_content = render_template(
            'ver_plan_nutricional.html',
            plan=plan_nut_obj,
            contenido=contenido_plan
        )

        pdf_bytes = b""
        if HTML is None:
            pdf_bytes = f"""PDF Simulado (WeasyPrint no disponible). Contenido HTML:
            {html_content}""".encode('utf-8')

            logging.warning(f"WeasyPrint no disponible. PDF simulado generado en memoria para Plan ID {plan_nut_obj.id}.")
        else:
            # Generar PDF real con WeasyPrint
            pdf_bytes = HTML(string=html_content).write_pdf()
            logging.info(f"PDF del plan nutricional (ID: {plan_nut_obj.id}) generado con WeasyPrint desde la plantilla 'ver_plan_nutricional.html'.")

    except Exception as e_render:
        logging.error(f"Error crítico al renderizar o generar el PDF para el plan {plan_nut_obj.id}: {e_render}", exc_info=True)
        return None

    # El resto de la lógica para guardar el archivo (cifrado o no) permanece igual
    base_filename_no_ext = f"plan_nutricional_{plan_nut_obj.paciente_id}_{plan_nut_obj.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    pdf_filename_ext = ".pdf" + (".enc" if fernet_cipher else "")
    pdf_filename_final = secure_filename(base_filename_no_ext + pdf_filename_ext)

    subfolder_pdf = app.config['PLANES_PDF_FOLDER']
    ruta_relativa_pdf_db = os.path.join(subfolder_pdf, pdf_filename_final).replace('\\', '/')
    directorio_destino_pdf_abs = os.path.join(app.config['UPLOAD_FOLDER'], subfolder_pdf)
    os.makedirs(directorio_destino_pdf_abs, exist_ok=True)
    ruta_absoluta_pdf_guardado = os.path.join(directorio_destino_pdf_abs, pdf_filename_final)

    try:
        data_to_write = fernet_cipher.encrypt(pdf_bytes) if fernet_cipher else pdf_bytes
        with open(ruta_absoluta_pdf_guardado, 'wb') as f:
            f.write(data_to_write)

        log_msg = f"PDF {'CIFRADO' if fernet_cipher else '(sin cifrar)'} del plan nutricional guardado en: {ruta_absoluta_pdf_guardado}"
        logging.info(log_msg)

        plan_nut_obj.ruta_pdf_almacenada = ruta_relativa_pdf_db
        return ruta_relativa_pdf_db

    except Exception as e_pdf:
        logging.error(f"Error guardando PDF para PlanNutricional ID {plan_nut_obj.id}: {e_pdf}", exc_info=True)
        return None

def generar_y_guardar_pdf_desde_html(html_template_name, context, subfolder_config_key, base_filename_prefix):
    """
    Genera un PDF a partir de una plantilla HTML, lo guarda y devuelve la ruta relativa.
    context: diccionario de variables para el renderizado de la plantilla.
    subfolder_config_key: clave de app.config que contiene el nombre de la subcarpeta (ej. 'NOTAS_AI_PDF_FOLDER').
    base_filename_prefix: prefijo para el nombre del archivo PDF (ej. 'notas_visita').
    """
    global fernet_cipher
    
    if not HTML:
        logging.warning(f"WeasyPrint no está instalado. No se puede generar el PDF para {base_filename_prefix}.")
        return None

    try:
        context['now'] = datetime.now
        html_content = render_template(html_template_name, **context)
        pdf_bytes = HTML(string=html_content).write_pdf()
        logging.info(f"PDF generado para '{base_filename_prefix}' con WeasyPrint desde '{html_template_name}'.")

    except Exception as e_render:
        logging.error(f"Error crítico al renderizar o generar el PDF para {base_filename_prefix}: {e_render}", exc_info=True)
        return None

    timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
    filename_no_ext = f"{base_filename_prefix}_{timestamp_str}"
    pdf_filename_ext = ".pdf" + (".enc" if fernet_cipher else "")
    pdf_filename_final = secure_filename(filename_no_ext + pdf_filename_ext)

    subfolder_pdf = app.config.get(subfolder_config_key)
    if not subfolder_pdf:
        logging.error(f"Configuración de subcarpeta '{subfolder_config_key}' no encontrada.")
        return None

    ruta_relativa_pdf_db = os.path.join(subfolder_pdf, pdf_filename_final).replace('\\', '/')
    directorio_destino_pdf_abs = os.path.join(app.config['UPLOAD_FOLDER'], subfolder_pdf)
    os.makedirs(directorio_destino_pdf_abs, exist_ok=True)
    ruta_absoluta_pdf_guardado = os.path.join(directorio_destino_pdf_abs, pdf_filename_final)

    try:
        data_to_write = fernet_cipher.encrypt(pdf_bytes) if fernet_cipher else pdf_bytes
        with open(ruta_absoluta_pdf_guardado, 'wb') as f:
            f.write(data_to_write)

        log_msg = f"PDF {'CIFRADO' if fernet_cipher else '(sin cifrar)'} guardado en: {ruta_absoluta_pdf_guardado}"
        logging.info(log_msg)

        return ruta_relativa_pdf_db

    except Exception as e_pdf:
        logging.error(f"Error guardando PDF para '{base_filename_prefix}': {e_pdf}", exc_info=True)
        return None

@app.route('/dashboard')
def dashboard():
    # Initialize variables to a default value for unauthenticated users
    total_pacientes = 0
    visitas_hoy_count = 0
    tareas_pendientes_count = 0

    # Check if a user is authenticated
    if current_user.is_authenticated:
        # If authenticated, get the user's ID
        user_id = current_user.id
        
        # Now, perform the database queries using the user's ID
        total_pacientes = db.session.query(Paciente.id).filter_by(creado_por_id=user_id).count()
        
        today_utc = datetime.now(timezone.utc).date()
        today_start_utc = datetime.combine(today_utc, datetime.min.time(), tzinfo=timezone.utc)
        today_end_utc = datetime.combine(today_utc, datetime.max.time(), tzinfo=timezone.utc)
        
        visitas_hoy_count = db.session.query(Visita.id).filter(
            Visita.medico_id == user_id,
            Visita.fecha >= today_start_utc,
            Visita.fecha <= today_end_utc
        ).count()
        
        tareas_pendientes_count = db.session.query(Tarea.id).filter(
            Tarea.usuario_id == user_id,
            Tarea.status != "Completada"
        ).count()

    return render_template('dashboard.html',
                           total_pacientes=total_pacientes,
                           visitas_hoy=visitas_hoy_count,
                           tareas_pendientes=tareas_pendientes_count)

@app.route('/nutricion_admin_dashboard')
@admin_required(allowed_roles=['admin_nutricion']) # Use the decorator with the specific role
def nutricion_admin_dashboard():
    # Lógica específica para el Administrador de Nutrición
    # Por ejemplo, podría ver un resumen de todos los planes nutricionales,
    # o usuarios con especialidad de nutrición, etc.
    nutri_medicos = User.query.filter_by(especialidad='Nutrición', is_verified=True).count()
    total_planes_nutricionales = PlanNutricional.query.count()

    return render_template('nutricion_admin_dashboard.html',
                           nutri_medicos=nutri_medicos,
                           total_planes_nutricionales=total_planes_nutricionales,
                           css_file="css/nutricion_admin_dashboard.css") # Necesitarás crear este archivo HTML y CSS

@app.route('/formulario-interes', methods=['GET', 'POST'])
def formulario_interes_route():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        apellidos = request.form.get('apellidos', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefono = request.form.get('telefono', '').strip()
        especialidad = request.form.get('especialidad', 'No especificada').strip()
        carne_medico = request.form.get('carne_medico', '').strip()
        identificacion = request.form.get('identificacion', '').strip()
        lugar_trabajo = request.form.get('lugar_trabajo', '').strip()
        
        if not all([nombre, apellidos, email, telefono]):
            return jsonify({'error': 'Nombre, apellidos, correo y teléfono son obligatorios.'}), 400

        nuevo_prospecto = ProspectoInteres(
            nombre=nombre,
            apellidos=apellidos,
            email=email,
            telefono=telefono,
            especialidad=especialidad,
            carne_medico=carne_medico or None,
            identificacion=identificacion or None,
            lugar_trabajo=lugar_trabajo or None,
            consentimiento=True 
        )
        
        try:
            db.session.add(nuevo_prospecto)
            db.session.commit()
            logging.info(f"Nuevo prospecto de interés registrado: {email}")

            # Correo de notificación para el equipo de Vitta (código existente)
            try:
                html_body = f"""
                <h3>Nuevo Prospecto Interesado - Vitta Health</h3>
                <p>Se ha registrado un nuevo profesional de la salud a través del formulario de interés.</p>
                <ul>
                    <li><strong>Nombre:</strong> {nombre} {apellidos}</li>
                    <li><strong>Email:</strong> {email}</li>
                    <li><strong>Teléfono:</strong> {telefono}</li>
                    <li><strong>Especialidad:</strong> {especialidad}</li>
                    <li><strong>Carné Médico:</strong> {carne_medico or 'No proporcionado'}</li>
                    <li><strong>Identificación:</strong> {identificacion or 'No proporcionado'}</li>
                    <li><strong>Lugar de Trabajo:</strong> {lugar_trabajo or 'No proporcionado'}</li>
                </ul>
                """
                
                msg = Message(
                    subject="Nuevo Prospecto de Interés Registrado",
                    sender=('Vitta Health Scribe', app.config['MAIL_DEFAULT_SENDER']),
                    recipients=['info@vitta.health'], 
                    html=html_body
                )
                
                mail.send(msg)
                logging.info(f"Correo de notificación enviado a info@vitta.health para el prospecto {email}.")

            except Exception as e_mail:
                logging.error(f"FALLO al enviar el correo de notificación para {email}: {e_mail}", exc_info=True)
            
            # --- INICIO DEL NUEVO CÓDIGO: Enviar correo de confirmación al prospecto ---
            try:
                # Renderizar la plantilla HTML del correo de confirmación
                html_confirmacion_prospecto = render_template(
                    'confirmacion_interes.html', 
                    nombre=nuevo_prospecto.nombre
                )
                
                # Crear el objeto del message para el prospecto
                msg_prospecto = Message(
                    subject="Confirmación de tu solicitud en Vitta Health",
                    sender=('Vitta Health Scribe', app.config['MAIL_DEFAULT_SENDER']),
                    recipients=[nuevo_prospecto.email], # El destinatario es el correo del prospecto
                    html=html_confirmacion_prospecto
                )
                
                # Enviar el correo de confirmación
                mail.send(msg_prospecto)
                logging.info(f"Correo de confirmación enviado exitosamente a {nuevo_prospecto.email}.")

            except Exception as e_mail_prospecto:
                # Si falla el envío al prospecto, solo se registra el error pero no se detiene el proceso
                logging.error(f"FALLO al enviar el correo de confirmación al prospecto {nuevo_prospecto.email}: {e_mail_prospecto}", exc_info=True)
            # --- FIN DEL NUEVO CÓDIGO ---
            
            return jsonify({'message': 'Solicitud recibida exitosamente.'}), 200

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error al registrar prospecto de interés {email}: {e}", exc_info=True)
            return jsonify({'error': 'Ocurrió un error al guardar tu información.'}), 500
    
    # La parte del método GET no necesita cambios.
    return render_template('formulario_interes.html', form_data={})
    
@app.route('/register', methods=['GET', 'POST'])
def register_route():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form_data = request.form.to_dict() if request.method == 'POST' else {}
    if request.method == 'POST':
        nombre = form_data.get('nombre', '').strip()
        email = form_data.get('email', '').strip().lower()
        password = form_data.get('password')
        role = form_data.get('role', 'medico').strip()
        licencia = form_data.get('licencia_profesional', '').strip()
        especialidad_select = form_data.get('especialidad_select', '')
        especialidad_otro = form_data.get('especialidad_otro', '').strip()
        especialidad_final = especialidad_otro if especialidad_select == 'otro' else especialidad_select
        tel_prefijo = form_data.get('telefono_prefijo', '')
        tel_numero = form_data.get('telefono_numero', '').strip()
        telefono_final = f"{tel_prefijo}{tel_numero}" if tel_numero else None
        if especialidad_select == 'otro' and not especialidad_otro:
            flash('Si selecciona "Otra" especialidad, debe especificarla.', 'danger')
            return render_template('register.html', css_file="css/auth_form.css", **form_data)
        required_fields = {'Nombre': nombre, 'Email': email, 'Contraseña': password,
                           'Licencia Profesional': licencia, 'Especialidad': especialidad_final}
        missing_fields = [name for name, value in required_fields.items() if not value]
        if missing_fields:
            flash(f'Los campos {", ".join(missing_fields)} son obligatorios.', 'danger')
            return render_template('register.html', css_file="css/auth_form.css", **form_data)
        if User.query.filter_by(email=email).first():
            flash('Este correo electrónico ya está registrado.', 'warning')
            return render_template('register.html', css_file="css/auth_form.css", **form_data)
        if licencia and User.query.filter_by(licencia_profesional=licencia).first():
            flash('Esta licencia profesional ya está registrada.', 'warning')
            return render_template('register.html', css_file="css/auth_form.css", **form_data)
        nuevo_usuario = User(
            nombre=nombre, email=email, role=role,
            licencia_profesional=licencia, especialidad=especialidad_final,
            telefono_profesional=telefono_final
        )
        nuevo_usuario.set_password(password)
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash('¡Registro exitoso! Ahora puedes iniciar sesión.', 'success')
            logging.info(f"Nuevo usuario registrado: {email} con rol {role}")
            return redirect(url_for('login_route'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error al registrar usuario {email}: {e}", exc_info=True)
            flash('Error durante el registro. Por favor, intente de nuevo.', 'danger')
            return render_template('register.html', css_file="css/auth_form.css", **form_data)
    return render_template('register.html', css_file="css/auth_form.css", **form_data)

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    # The whole block for the login_route function is indented
    if current_user.is_authenticated:
        if not current_user.is_verified:
            flash('Su perfil aún no ha sido verificado. Por favor, espere a que un administrador apruebe su cuenta.', 'warning')
            logout_user()
            return redirect(url_for('login_route'))

        # Lógica para usuarios ya autenticados (antes de intentar login de nuevo)
        if current_user.role == 'admin_super':
            return redirect(url_for('super_admin_dashboard'))
        elif current_user.role == 'admin_nutricion':
            return redirect(url_for('nutricion_admin_dashboard'))
        else: # Medicos o cualquier otro rol
            return redirect(url_for('dashboard'))

    email_from_form = request.form.get('email', '') if request.method == 'POST' else request.args.get('email', '')

    if request.method == 'POST':
        # The code inside this `if` block must be indented
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if not email or not password:
            flash('Email y contraseña son requeridos.', 'danger')
            return render_template('login.html', email=email, css_file="css/auth_form.css")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            # The code inside this `if` block must also be indented
            if not user.is_verified:
                flash('Su perfil aún no ha sido verificado.', 'warning')
                return redirect(url_for('login_route'))

            login_user(user, remember=remember)

            # Lógica para usuarios recién autenticados
            if user.role == 'admin_super':
                flash('Inicio de sesión como Super Administrador exitoso!', 'success')
                return redirect(url_for('super_admin_dashboard'))
            elif user.role == 'admin':
                flash('Inicio de sesión como Administrador exitoso!', 'success')
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'admin_nutricion':
                flash('Inicio de sesión como Administrador de Nutrición exitoso!', 'success')
                return redirect(url_for('nutricion_admin_dashboard'))
            else: # Medicos o cualquier otro rol
                flash('Inicio de sesión exitoso!', 'success')
                return redirect(url_for('dashboard'))

        flash('Credenciales incorrectas. Por favor, intenta de nuevo.', 'danger')
        return redirect(url_for('login_route'))

    return render_template('login.html', email=email_from_form, css_file="css/auth_form.css")
@app.route('/logout')
def logout_route():
    user_email_for_log = current_user.email if hasattr(current_user, 'email') else 'Desconocido'
    logout_user()
    flash('Has cerrado sesión exitosamente.', 'info')
    logging.info(f"Usuario {user_email_for_log} ha cerrado sesión.")
    session.pop('visita_actual_id', None)
    return redirect(url_for('login_route'))

SPECIALTY_ACTIONS = {
    "Nutrición": {"text": "📝 Generar Plan Nutricional", "route_name": "nuevo_plan_nutricional_para_visita_page", "doc_type": "plan_nutricional"},
}

@app.route('/historial_visitas')
def historial_visitas():
    visita_reciente_id = request.args.get('visita_reciente', type=int)
    visitas_data_list = []
    try:
        visitas_db = (
            db.session.query(Visita)
            .filter(Visita.medico_id == current_user.id)
            .options(db.joinedload(Visita.paciente))
            .order_by(Visita.fecha.desc())
            .all()
        )
        for v_db in visitas_db:
            paciente_actual = v_db.paciente
            if paciente_actual:
                visitas_data_list.append({
                    'id': v_db.id,
                    'fecha_formateada': v_db.fecha.strftime('%d/%m/%Y %H:%M') if v_db.fecha else 'Fecha No Disponible',
                    'fecha_relativa': calcular_tiempo_transcurrido(v_db.fecha) if v_db.fecha else 'N/A',
                    'plantilla': v_db.plantilla or "N/E",
                    'transcripcion': v_db.transcripcion or "",
                    'resumen_ai': v_db.resumen_ai or "",
                    'notas_ai': v_db.notas_ai or "",
                    'idioma_detectado': v_db.idioma_detectado or "N/D",
                    'tipo_visita': v_db.tipo_visita.replace('_', ' ').capitalize() if v_db.tipo_visita else "No Especificado",
                    # 'ruta_notas_ai_pdf': v_db.ruta_notas_ai_pdf if hasattr(v_db, 'ruta_notas_ai_pdf') else None, # Removed for client-side PDF
                    'paciente': {
                        'id': paciente_actual.id,
                        'nombre': paciente_actual.nombre,
                        'identificacion_documento': paciente_actual.identificacion_documento,
                        'telefono': paciente_actual.telefono,
                        'email': paciente_actual.email,
                        'estado_tratamiento': paciente_actual.estado_tratamiento,
                        'url_avatar': getattr(paciente_actual, 'url_avatar', None)
                    },
                    'paciente_nombre': paciente_actual.nombre 
                })
            else:
                # Handle cases where patient might be None (shouldn't happen with proper foreign keys)
                visitas_data_list.append({
                    'id': v_db.id,
                    'fecha_formateada': v_db.fecha.strftime('%d/%m/%Y %H:%M') if v_db.fecha else 'Fecha No Disponible',
                    'fecha_relativa': calcular_tiempo_transcurrido(v_db.fecha) if v_db.fecha else 'N/A',
                    'plantilla': v_db.plantilla or "N/E",
                    'transcripcion': v_db.transcripcion or "",
                    'resumen_ai': v_db.resumen_ai or "",
                    'notas_ai': v_db.notas_ai or "",
                    'idioma_detectado': v_db.idioma_detectado or "N/D",
                    'tipo_visita': v_db.tipo_visita.replace('_', ' ').capitalize() if v_db.tipo_visita else "No Especificado",
                    # 'ruta_notas_ai_pdf': v_db.ruta_notas_ai_pdf if hasattr(v_db, 'ruta_notas_ai_pdf') else None, # Removed for client-side PDF
                    'paciente': {},
                    'paciente_nombre': "Paciente Desconocido" # Placeholder name
                })
    except Exception as e:
        logging.error(f"Error obteniendo historial de visitas para usuario {current_user.id}: {e}", exc_info=True)
        flash("Error al cargar el historial de visitas. Intente de nuevo más tarde.", "danger")

    visita_reciente_data = next((v for v in visitas_data_list if v['id'] == visita_reciente_id), None) if visita_reciente_id else None
    current_date_display = datetime.now().strftime('%d/%m/%Y')
    user_especialidad = current_user.especialidad if hasattr(current_user, 'especialidad') else None
    action_for_specialty = SPECIALTY_ACTIONS.get(user_especialidad) if user_especialidad else None

    return render_template('historial_visitas.html',
                           visitas=visitas_data_list,
                           current_date_display=current_date_display,
                           visita_reciente=visita_reciente_data,
                           action_for_specialty=action_for_specialty,
                           css_file="css/historial_visitas.css")

@app.route('/visita/<int:visita_id>/generar_documento_especializado/<string:doc_type>')
def generar_documento_especializado(visita_id, doc_type):
    visita = db.session.query(Visita).filter_by(id=visita_id, medico_id=current_user.id).first()
    if not visita:
        flash("Visita no encontrada o no tiene permiso para accederla.", "danger")
        return redirect(url_for('historial_visitas'))
    flash(f"Funcionalidad genérica para '{doc_type}' (Visita ID: {visita_id}) aún no implementada aquí. Verifique rutas específicas.", "info")
    return redirect(url_for('historial_visitas'))
@app.route('/visita/<int:visita_id>/notas_ia_pdf')
def descargar_pdf_notas_ia(visita_id):
    visita = db.session.get(Visita, visita_id)
    if not visita:
        flash("Visita no encontrada.", "danger")
        return redirect(url_for('historial_visitas'))

    if not visita.notas_ai:
        flash("No hay notas AI para esta visita.", "warning")
        return redirect(url_for('perfil_paciente', paciente_id=visita.paciente_id))

    if visita.medico_id != current_user.id:
        flash("No tiene permiso para ver las notas AI de esta visita.", "danger")
        return redirect(url_for('dashboard'))

    medico_for_pdf = visita.medico_asignado_usuario
    logo_base64 = get_base64_image_from_path(medico_for_pdf.url_logo_clinica) if medico_for_pdf.url_logo_clinica else None

    html_render = render_template(
        "ver_notas_ia_pdf.html",
        visita=visita,
        paciente=visita.paciente,
        medico=medico_for_pdf,
        idioma_generacion=visita.idioma_detectado or 'N/D',
        notas_contenido_html=markdown.markdown(visita.notas_ai),
        current_year=datetime.now().year,
        logo_clinica_base64=logo_base64,
        show_clinic_name=medico_for_pdf.show_clinic_name_pdf,
        show_clinic_address=medico_for_pdf.show_clinic_address_pdf,
        show_clinic_phone=medico_for_pdf.show_clinic_phone_pdf,
        show_clinic_website=medico_for_pdf.show_clinic_website_pdf,
        show_doctor_license=medico_for_pdf.show_doctor_license_pdf,
        show_doctor_phone=medico_for_pdf.show_doctor_phone_pdf,
        show_doctor_bio=medico_for_pdf.show_doctor_bio_pdf
    )

    pdf_bytes = b""
    if HTML:
        try:
            pdf_bytes = HTML(string=html_render).write_pdf()
            logging.info(f"PDF de notas AI para Visita ID {visita_id} generado con WeasyPrint.")
        except Exception as e:
            logging.error(f"Error generando PDF de notas AI con WeasyPrint para Visita ID {visita_id}: {e}", exc_info=True)
            flash("Error al generar el PDF de las notas AI.", "danger")
            # En un entorno de producción, considerar un redirect a una página de error o al perfil del paciente
            return redirect(url_for('perfil_paciente', paciente_id=visita.paciente_id)) 
    else:
        logging.warning("WeasyPrint no está instalado. No se puede generar un PDF real de las notas AI. Sirviendo un PDF de marcador de posición.")
        pdf_bytes = f"""
        <html><body>
            <h1>Error: No se pudo generar el PDF de Notas AI</h1>
            <p>WeasyPrint (o una herramienta similar para generar PDFs desde HTML) no está instalado en el servidor.</p>
            <p>Contenido de las notas:</p>
            <div>{markdown.markdown(visita.notas_ai)}</div>
        </body></html>
        """.encode('utf-8')

    return send_file(
        io.BytesIO(pdf_bytes),
        download_name=f"notas_visita_{visita.id}.pdf",
        mimetype="application/pdf"
    )
@app.route('/grabar_cita')
def grabar_cita():
    plantillas = [
        "Consulta General", "Seguimiento", "Examen Físico", "SOAP", "SOAP simple",
        "Resumen libre", "Nota Pediátrica de Rutina", "Control de Enfermedad Crónica",
        "Certificado Médico Simple"
    ]
    pacientes_activos = []
    
    # Check if the user is authenticated before performing the query
    if current_user.is_authenticated:
        try:
            pacientes_activos = Paciente.query.filter_by(creado_por_id=current_user.id).order_by(Paciente.nombre).all()
        except Exception as e:
            # The 'except' block also needs to handle the case where current_user.id might not exist.
            # But with the 'if current_user.is_authenticated' check, this is now safe.
            logging.error(f"Error obteniendo lista de pacientes para grabar cita (usuario {current_user.id}): {e}", exc_info=True)
            flash("Error al cargar la lista de pacientes.", "danger")
    else:
        # If not authenticated, the list of active patients remains empty.
        # This prevents the AttributeError.
        pass

    if 'visita_actual_id' in session:
        session.pop('visita_actual_id', None)
        logging.info("ID de visita actual eliminado de la sesión al entrar a /grabar_cita.")

    return render_template('grabar_cita.html',
                           css_file="css/grabar_cita.css",
                           plantillas=plantillas,
                           pacientes=pacientes_activos)

@app.route('/resumir_registros')
def resumir_registros_page():
    plantillas_resumen = ["Resumen de Registros", "Resumen General", "Puntos Clave"]
    pacientes_activos = []

    # Add the authentication check here
    if current_user.is_authenticated:
        try:
            pacientes_activos = Paciente.query.filter_by(creado_por_id=current_user.id).order_by(Paciente.nombre).all()
        except Exception as e:
            logging.error(f"Error obteniendo lista de pacientes para resumir_registros (usuario {current_user.id}): {e}", exc_info=True)
            flash("Error al cargar la lista de pacientes.", "danger")

    if 'visita_actual_id' in session:
        session.pop('visita_actual_id', None)
        logging.info("ID de visita actual eliminado de la sesión al entrar a /resumir_registros.")

    return render_template('resumir_registros.html',
                           plantillas=plantillas_resumen,
                           pacientes=pacientes_activos,
                           css_file="css/resumir_registros.css")

@app.route('/pacientes')
def pacientes_page():
    lista_pacientes = []

    # Add the authentication check here
    if current_user.is_authenticated:
        try:
            lista_pacientes = Paciente.query.filter_by(creado_por_id=current_user.id).order_by(Paciente.nombre).all()
        except Exception as e:
            logging.error(f"Error obteniendo la lista de pacientes para usuario {current_user.id}: {e}", exc_info=True)
            flash("Error al cargar la lista de pacientes.", "danger")

    return render_template('pacientes.html', pacientes=lista_pacientes, css_file="css/pacientes.css")

@app.route('/agregar_paciente', methods=['GET', 'POST'])
def agregar_paciente():
    form_data = request.form.to_dict() if request.method == 'POST' else {}
    if request.method == 'POST':
        nombre = form_data.get('nombre','').strip()
        ident_doc = form_data.get('identificacion_documento','').strip()
        telefono = form_data.get('telefono','').strip()
        email = form_data.get('email','').strip().lower()
        estado_trat = form_data.get('estado_tratamiento', 'No especificado').strip()
        if not nombre:
            flash('El nombre del paciente es obligatorio.', 'danger')
            return render_template('agregar_paciente.html', paciente_form_data=form_data, css_file="css/agregar_paciente.css")
        if Paciente.query.filter(Paciente.nombre.ilike(nombre), Paciente.creado_por_id == current_user.id).first():
            flash(f'Un paciente con el nombre "{nombre}" ya existe para usted.', 'warning')
            return render_template('agregar_paciente.html', paciente_form_data=form_data, css_file="css/agregar_paciente.css")
        if ident_doc and Paciente.query.filter(Paciente.identificacion_documento.ilike(ident_doc), Paciente.creado_por_id == current_user.id).first():
            flash(f'Un paciente con el documento de identificación "{ident_doc}" ya existe para usted.', 'warning')
            return render_template('agregar_paciente.html', paciente_form_data=form_data, css_file="css/agregar_paciente.css")
        nuevo_paciente = Paciente(
            nombre=nombre,
            identificacion_documento=ident_doc or None,
            telefono=telefono or None,
            email=email or None,
            estado_tratamiento=estado_trat or 'No especificado',
            creado_por_id=current_user.id
        )
        try:
            db.session.add(nuevo_paciente)
            db.session.commit()
            flash(f'Paciente "{nuevo_paciente.nombre}" agregado exitosamente.', 'success')
            reg_act = RegistroActividad(
                usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
                accion="paciente_creado",
                descripcion=f"Paciente '{nuevo_paciente.nombre}' (ID: {nuevo_paciente.id}, Doc: {nuevo_paciente.identificacion_documento or 'N/A'}) creado."
            )
            db.session.add(reg_act)
            db.session.commit()
            return redirect(url_for('pacientes_page'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error al agregar nuevo paciente para usuario {current_user.id}: {e}", exc_info=True)
            flash(f'Error al agregar paciente. Verifique los datos e intente de nuevo.', 'danger')
            return render_template('agregar_paciente.html', paciente_form_data=form_data, css_file="css/agregar_paciente.css")
    return render_template('agregar_paciente.html', css_file="css/agregar_paciente.css", paciente_form_data={})

@app.route('/perfil_paciente/<int:paciente_id>')
def perfil_paciente(paciente_id):
    paciente = db.session.query(Paciente).filter_by(id=paciente_id, creado_por_id=current_user.id).first()
    if not paciente:
        flash('Paciente no encontrado o no tiene permiso para verlo.', 'danger')
        return redirect(url_for('pacientes_page'))

    visitas_paciente_db = (Visita.query.filter_by(paciente_id=paciente.id, medico_id=current_user.id)
                           .order_by(Visita.fecha.desc()).all())
    visitas_data = []
    for v_db in visitas_paciente_db:
        archivos_adj_list_display = []
        if v_db.archivos_adjuntos:
            try:
                adj_data = json.loads(v_db.archivos_adjuntos)
                if isinstance(adj_data, dict) and "procesados" in adj_data:
                    # Mostrar solo el nombre base del archivo, no la ruta completa ni la extensión .enc
                    archivos_adj_list_display = [os.path.basename(p).replace('.enc','') for p in adj_data.get("procesados",[]) if isinstance(p, str)]
                elif isinstance(adj_data, list):
                     archivos_adj_list_display = [os.path.basename(p).replace('.enc','') for p in adj_data if isinstance(p, str)]
                elif isinstance(adj_data, str): # Para audio único
                    archivos_adj_list_display = [os.path.basename(adj_data).replace('.enc','')]
            except json.JSONDecodeError:
                if isinstance(v_db.archivos_adjuntos, str) and v_db.archivos_adjuntos.strip():
                    archivos_adj_list_display = [os.path.basename(v_db.archivos_adjuntos).replace('.enc','')]
                logging.warning(f"Formato de archivos_adjuntos no JSON para Visita ID {v_db.id}: {v_db.archivos_adjuntos}")
        trans_corta = 'No disponible'
        if v_db.transcripcion and not v_db.transcripcion.startswith("[Error") and v_db.transcripcion.strip().lower() not in ['transcripción no disponible o con errores.', 'transcripción no generada.']:
            trans_corta = (v_db.transcripcion[:200] + '...' if len(v_db.transcripcion) > 200 else v_db.transcripcion)
        elif v_db.resumen_ai and not v_db.resumen_ai.startswith("[Error"):
            trans_corta = (v_db.resumen_ai[:200] + '...' if len(v_db.resumen_ai) > 200 else v_db.resumen_ai)
        visitas_data.append({
            'id': v_db.id,
            'tipo_visita': v_db.tipo_visita.replace('_', ' ').capitalize() if v_db.tipo_visita else "No Especificado",
            'fecha_formateada': v_db.fecha.strftime('%d/%m/%Y %H:%M') if v_db.fecha else 'N/D',
            'fecha_relativa': calcular_tiempo_transcurrido(v_db.fecha) if v_db.fecha else 'N/A',
            'plantilla': v_db.plantilla or "N/E",
            'resumen_ai': v_db.resumen_ai or None,
            'transcripcion_corta': trans_corta,
            'notas_ai': v_db.notas_ai or None,
            'archivos_adjuntos_display': archivos_adj_list_display
        })

    notas_paciente_db = (Nota.query.filter_by(paciente_id=paciente.id, usuario_id=current_user.id)
                         .order_by(Nota.fecha.desc()).all())
    notas_data = [{'id': n.id, 'contenido': n.contenido,
                   'fecha_formateada': n.fecha.strftime('%d/%m/%Y %H:%M') if n.fecha else 'N/D',
                   'fecha_relativa': calcular_tiempo_transcurrido(n.fecha) if n.fecha else 'N/A'}
                  for n in notas_paciente_db]
    recetas_del_paciente = RecetaMedica.query.filter_by(paciente_id=paciente.id, medico_id=current_user.id).order_by(RecetaMedica.fecha_emision.desc()).all()
    referencias_del_paciente = ReferenciaMedica.query.filter_by(paciente_id=paciente.id, medico_referente_id=current_user.id).order_by(ReferenciaMedica.fecha_emision.desc()).all()
    planes_nutricionales_del_paciente = PlanNutricional.query.filter_by(paciente_id=paciente.id, medico_id=current_user.id).order_by(PlanNutricional.fecha_emision.desc()).all()

    return render_template('perfil_paciente.html',
                           paciente=paciente,
                           visitas=visitas_data,
                           notas=notas_data,
                           recetas=recetas_del_paciente,
                           referencias_paciente=referencias_del_paciente,
                           planes_nutricionales=planes_nutricionales_del_paciente,
                           css_file="css/perfil_paciente.css")

@app.route('/perfil_paciente/<int:paciente_id>/guardar', methods=['POST'])
def guardar_perfil_paciente(paciente_id):
    paciente = db.session.query(Paciente).filter_by(id=paciente_id, creado_por_id=current_user.id).first()
    if not paciente:
        flash('Paciente no encontrado o no tiene permiso para modificarlo.', 'danger')
        return redirect(url_for('pacientes_page'))

    nombre_pila = request.form.get('nombre_pila', '').strip()
    apellido = request.form.get('apellido', '').strip()
    nombre_completo = f"{nombre_pila} {apellido}".strip() if nombre_pila or apellido else paciente.nombre
    nuevo_ident_doc = request.form.get('identificacion_documento_paciente', '').strip()
    nuevo_telefono = request.form.get('telefono_paciente', '').strip()
    nuevo_email = request.form.get('email_paciente', '').strip().lower()
    nuevo_estado_trat = request.form.get('estado_tratamiento_paciente', '').strip()
    if not nombre_completo:
        flash('El nombre del paciente no puede estar vacío.', 'danger')
        return redirect(url_for('perfil_paciente', paciente_id=paciente_id))
    if nombre_completo != paciente.nombre and \
       Paciente.query.filter(Paciente.nombre.ilike(nombre_completo), Paciente.id != paciente_id, Paciente.creado_por_id == current_user.id).first():
        flash(f'Ya existe otro paciente con el nombre "{nombre_completo}" para usted.', 'warning')
        return redirect(url_for('perfil_paciente', paciente_id=paciente_id))
    if nuevo_ident_doc and nuevo_ident_doc != paciente.identificacion_documento and \
       Paciente.query.filter(Paciente.identificacion_documento.ilike(nuevo_ident_doc), Paciente.id != paciente_id, Paciente.creado_por_id == current_user.id).first():
        flash(f'Ya existe otro paciente con el documento de identificación "{nuevo_ident_doc}" para usted.', 'warning')
        return redirect(url_for('perfil_paciente', paciente_id=paciente_id))

    paciente.nombre = nombre_completo
    paciente.identificacion_documento = nuevo_ident_doc or None
    paciente.telefono = nuevo_telefono or None
    paciente.email = nuevo_email or None
    paciente.estado_tratamiento = nuevo_estado_trat or 'No especificado'
    try:
        db.session.commit()
        flash('Perfil del paciente actualizado exitosamente.', 'success')
        reg_act = RegistroActividad(
            usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
            accion="perfil_paciente_actualizado",
            descripcion=f"Perfil del paciente '{paciente.nombre}' (ID: {paciente.id}) actualizado."
        )
        db.session.add(reg_act)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error al actualizar perfil del paciente ID {paciente_id} (usuario {current_user.id}): {e}", exc_info=True)
        flash('Error al actualizar el perfil del paciente.', 'danger')
    return redirect(url_for('perfil_paciente', paciente_id=paciente_id))

@app.route('/paciente/<int:paciente_id>/eliminar', methods=['POST'])
def eliminar_paciente(paciente_id):
    paciente = db.session.query(Paciente).filter_by(id=paciente_id, creado_por_id=current_user.id).first()
    if not paciente:
        flash('Paciente no encontrado o no tiene permiso para eliminarlo.', 'danger')
        return redirect(url_for('pacientes_page'))
    try:
        paciente_nombre_original = paciente.nombre
        logging.info(f"Iniciando eliminación del Paciente ID: {paciente.id}, Nombre: {paciente_nombre_original} por Usuario ID: {current_user.id}")
        for visita_obj in paciente.visitas.all():
            logging.info(f"Procesando archivos para la visita ID: {visita_obj.id} del paciente a eliminar.")
            _eliminar_archivos_asociados_a_visita(visita_obj)
        for plan_obj in paciente.planes_nutricionales.all():
            if plan_obj.ruta_pdf_almacenada:
                ruta_pdf_completa = os.path.join(app.config['UPLOAD_FOLDER'], plan_obj.ruta_pdf_almacenada)
                if os.path.exists(ruta_pdf_completa):
                    try:
                        os.remove(ruta_pdf_completa)
                        logging.info(f"PDF de Plan Nutricional {'CIFRADO' if plan_obj.ruta_pdf_almacenada.endswith('.enc') else ''} eliminado: {ruta_pdf_completa}")
                    except Exception as e_del_pdf_plan:
                        logging.error(f"Error eliminando PDF de Plan Nutricional '{ruta_pdf_completa}': {e_del_pdf_plan}")
        db.session.delete(paciente)
        db.session.commit()
        reg_act = RegistroActividad(
            usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
            accion="paciente_eliminado",
            descripcion=f"Paciente '{paciente_nombre_original}' (ID: {paciente_id}) y todos sus datos asociados han sido eliminados."
        )
        db.session.add(reg_act)
        db.session.commit()
        flash(f'Paciente "{paciente_nombre_original}" y todos sus datos asociados han sido eliminados.', 'success')
        return redirect(url_for('pacientes_page'))
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error al eliminar el paciente ID {paciente_id} (usuario {current_user.id}): {e}", exc_info=True)
        flash('Error al eliminar el paciente.', 'danger')
        return redirect(url_for('perfil_paciente', paciente_id=paciente_id))

@app.route('/automatizaciones')
def automatizaciones():
    return render_template('automatizaciones.html', css_file="css/automatizaciones.css")

@app.route('/configuracion-perfil', methods=['GET', 'POST'])
def configuracion_perfil_profesional():
    usuario_a_actualizar = current_user  # Directamente usar current_user para la sesión

    if request.method == 'POST':
        usuario_a_actualizar = db.session.get(User, current_user.id)
        if not usuario_a_actualizar:
            flash('Usuario no encontrado para actualizar.', 'danger')
            return redirect(url_for('configuracion_perfil_profesional'))
        usuario_a_actualizar.nombre = request.form.get('prof_nombre_completo', usuario_a_actualizar.nombre).strip()
        prof_especialidad_select = request.form.get('prof_especialidad_select')
        prof_especialidad_otro = request.form.get('prof_especialidad_otro', '').strip()
        especialidad_final = usuario_a_actualizar.especialidad
        if prof_especialidad_select == 'otro':
            if prof_especialidad_otro:
                especialidad_final = prof_especialidad_otro
            else:
                flash('Si selecciona "Otra" especialidad, debe especificarla.', 'warning')
        elif prof_especialidad_select:
            especialidad_final = prof_especialidad_select
        usuario_a_actualizar.especialidad = especialidad_final
        nueva_licencia = request.form.get('prof_licencia', usuario_a_actualizar.licencia_profesional).strip()
        if nueva_licencia != usuario_a_actualizar.licencia_profesional and User.query.filter(User.licencia_profesional == nueva_licencia, User.id != usuario_a_actualizar.id).first():
            flash('La nueva licencia profesional ya está en uso. Por favor, elige otra.', 'danger')
            return redirect(url_for('configuracion_perfil_profesional'))
        usuario_a_actualizar.licencia_profesional = nueva_licencia

        nuevo_email = request.form.get('prof_email', usuario_a_actualizar.email).strip().lower()
        if nuevo_email != usuario_a_actualizar.email:
            if User.query.filter(User.email == nuevo_email, User.id != usuario_a_actualizar.id).first():
                flash('El nuevo correo electrónico ya está en uso. Por favor, elige otro.', 'danger')
                return redirect(url_for('configuracion_perfil_profesional'))
        usuario_a_actualizar.email = nuevo_email
        prefijo_tel = request.form.get('prof_telefono_prefijo', '')
        numero_tel_local = request.form.get('prof_telefono_numero', '').strip()
        telefono_profesional_final = usuario_a_actualizar.telefono_profesional
        if numero_tel_local:
            telefono_profesional_final = f"{prefijo_tel}{numero_tel_local}"
        elif request.form.get('prof_telefono_numero') is not None:
            telefono_profesional_final = None
        usuario_a_actualizar.telefono_profesional = telefono_profesional_final
        usuario_a_actualizar.biografia = request.form.get('prof_biografia', usuario_a_actualizar.biografia).strip()
        usuario_a_actualizar.clinica_nombre = request.form.get('clinica_nombre', usuario_a_actualizar.clinica_nombre).strip()
        usuario_a_actualizar.clinica_direccion = request.form.get('clinica_direccion', usuario_a_actualizar.clinica_direccion).strip()
        usuario_a_actualizar.clinica_telefono = request.form.get('clinica_telefono', usuario_a_actualizar.clinica_telefono).strip()
        usuario_a_actualizar.clinica_website = request.form.get('clinica_website', usuario_a_actualizar.clinica_website).strip()

        usuario_id_str = str(current_user.id)
        base_static_uploads = app.config['UPLOAD_FOLDER']
        usuario_profile_files_subfolder_key = 'PROFILE_FILES_FOLDER'
        app.config[usuario_profile_files_subfolder_key] = os.path.join('usuarios_perfiles', usuario_id_str)

        foto_perfil_archivo = request.files.get('prof_foto_perfil')
        if foto_perfil_archivo and foto_perfil_archivo.filename != '':
            ruta_db_foto = guardar_archivo_subido(foto_perfil_archivo, usuario_profile_files_subfolder_key)
            if ruta_db_foto:
                if usuario_a_actualizar.url_foto_perfil:
                    old_path_absoluto = os.path.join(base_static_uploads, usuario_a_actualizar.url_foto_perfil)
                    if os.path.exists(old_path_absoluto):
                        try:
                            os.remove(old_path_absoluto)
                        except Exception as e_del_old:
                            logging.error(f"Error eliminando foto de perfil anterior: {e_del_old}")
                usuario_a_actualizar.url_foto_perfil = ruta_db_foto
            else:
                flash("Error al guardar la nueva foto de perfil.", "danger")

        logo_clinica_archivo = request.files.get('clinica_logo')
        if logo_clinica_archivo and logo_clinica_archivo.filename != '':
            ruta_db_logo = guardar_archivo_subido(logo_clinica_archivo, usuario_profile_files_subfolder_key)
            if ruta_db_logo:
                if usuario_a_actualizar.url_logo_clinica:
                    old_path_absoluto_logo = os.path.join(base_static_uploads, usuario_a_actualizar.url_logo_clinica)
                    if os.path.exists(old_path_absoluto_logo):
                        try:
                            os.remove(old_path_absoluto_logo)
                        except Exception as e_del_old_logo:
                            logging.error(f"Error eliminando logo anterior: {e_del_old_logo}")
                usuario_a_actualizar.url_logo_clinica = ruta_db_logo
            else:
                flash("Error al guardar el nuevo logo de la clínica.", "danger")

        if not all([usuario_a_actualizar.nombre, usuario_a_actualizar.especialidad, usuario_a_actualizar.licencia_profesional, usuario_a_actualizar.email]):
            flash('Los campos Nombre, Especialidad, Licencia Profesional y Email son obligatorios.', 'danger')
            return redirect(url_for('configuracion_perfil_profesional'))

        try:
            db.session.commit()
            flash('Tu perfil profesional ha sido actualizado exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error guardando perfil profesional para usuario {current_user.id}: {e}", exc_info=True)
            flash('Error al guardar el perfil. Por favor, intente de nuevo.', 'danger')
        return redirect(url_for('configuracion_perfil_profesional'))

    logo_base64 = None
    if current_user.url_logo_clinica:
        logo_base64 = get_base64_image_from_path(current_user.url_logo_clinica)

    return render_template(
        'configuracion_perfil_profesional.html',
        user=current_user,
        logo_clinica_base64=logo_base64,
        css_file="css/configuracion_perfil.css"
    )

@app.route('/cambiar-contrasena', methods=['GET', 'POST'])
def cambiar_contrasena_route():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        if not old_password or not new_password or not confirm_new_password:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('cambiar_contrasena.html', css_file="css/configuracion_perfil.css") # You might want a dedicated CSS here

        if not current_user.check_password(old_password):
            flash('La contraseña actual es incorrecta.', 'danger')
            return render_template('cambiar_contrasena.html', css_file="css/configuracion_perfil.css")

        if new_password != confirm_new_password:
            flash('La nueva contraseña y su confirmación no coinciden.', 'danger')
            return render_template('cambiar_contrasena.html', css_file="css/configuracion_perfil.css")

        # Optional: Add password complexity requirements (e.g., minimum length)
        if len(new_password) < 8:
            flash('La nueva contraseña debe tener al menos 8 caracteres.', 'danger')
            return render_template('cambiar_contrasena.html', css_file="css/configuracion_perfil.css")

        try:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Tu contraseña ha sido cambiada exitosamente.', 'success')
            logging.info(f"Password changed for user: {current_user.email}")
            return redirect(url_for('configuracion_perfil_profesional')) # Redirect to profile or dashboard
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error changing password for user {current_user.id}: {e}", exc_info=True)
            flash('Ocurrió un error al cambiar la contraseña. Intenta de nuevo.', 'danger')
            return render_template('cambiar_contrasena.html', css_file="css/configuracion_perfil.css")

    # For GET request
    return render_template('cambiar_contrasena.html', css_file="css/configuracion_perfil.css")
    
@app.route('/visita/<int:visita_id>/receta/nueva', methods=['GET', 'POST'])
def nueva_receta_para_visita(visita_id):
    visita = db.session.query(Visita).filter_by(id=visita_id, medico_id=current_user.id).first()
    if not visita:
        flash('Visita no encontrada o no tiene permiso para accederla.', 'danger')
        return redirect(url_for('historial_visitas'))
    if not visita.paciente:
        flash('La visita seleccionada no tiene un paciente asociado.', 'danger')
        return redirect(url_for('historial_visitas'))

    # --- Lógica para la solicitud POST (cuando el usuario envía el formulario) ---
    if request.method == 'POST':
        form_data_repost = request.form.copy() # Usar para repoblar el formulario en caso de error
        medicamentos_json_str = request.form.get('medicamentos_json_str')

        if not medicamentos_json_str:
            flash('Debe agregar al menos un medicamento a la receta.', 'danger')
            return render_template('crear_receta.html', visita=visita, paciente=visita.paciente, css_file="css/crear_documento.css", form_data=form_data_repost)
        
        try:
            parsed_meds = json.loads(medicamentos_json_str)
            if not isinstance(parsed_meds, list) or not parsed_meds:
                flash('Debe agregar al menos un medicamento válido.', 'danger')
                raise json.JSONDecodeError("La lista de medicamentos no puede estar vacía.", medicamentos_json_str, 0)
            
            nueva_receta_db = RecetaMedica(
                visita_id=visita.id,
                paciente_id=visita.paciente_id,
                medico_id=current_user.id,
                medicamentos_json=medicamentos_json_str,
                diagnostico_relacionado=request.form.get('diagnostico_relacionado'),
                validez_dias=request.form.get('validez_dias', type=int, default=30),
                notas_adicionales_receta=request.form.get('notas_adicionales_receta'),
                estado="activa"
            )
            db.session.add(nueva_receta_db)
            db.session.commit()

            reg_act = RegistroActividad(
                visita_id=visita.id, usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
                accion="receta_creada",
                descripcion=f"Receta (ID: {nueva_receta_db.id}) creada para el paciente '{visita.paciente.nombre}'."
            )
            db.session.add(reg_act)
            db.session.commit()

            flash('Receta creada exitosamente.', 'success')
            return redirect(url_for('ver_receta', receta_id=nueva_receta_db.id))

        except json.JSONDecodeError as je:
            flash(f'Error en el formato de los medicamentos enviados: {je}.', 'danger')
            db.session.rollback()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error al crear receta para visita {visita_id}: {e}", exc_info=True)
            flash(f'Error al crear la receta: {str(e)}', 'danger')
        
        # Si ocurre un error, volver a renderizar el formulario con los datos que el usuario ya ingresó
        return render_template('crear_receta.html', visita=visita, paciente=visita.paciente, css_file="css/crear_documento.css", form_data=form_data_repost)

    # --- Lógica para la solicitud GET (carga inicial de la página) ---
    form_data_initial = {}
    if visita.transcripcion and visita.transcripcion.strip() and client_openai and not visita.transcripcion.startswith("[Error"):
        datos_ia = extraer_medicamentos_con_ia(visita.transcripcion, visita.idioma_detectado)
        if datos_ia and datos_ia.get("medicamentos"):
            form_data_initial['medicamentos_sugeridos_json'] = json.dumps(datos_ia["medicamentos"])
            flash(f"Se han sugerido {len(datos_ia['medicamentos'])} medicamento(s) basados en la transcripción. Por favor, revísalos y ajústalos.", 'info')
        if datos_ia and datos_ia.get("diagnostico_sugerido") and not datos_ia.get("diagnostico_sugerido","").startswith("[Error"):
            form_data_initial['diagnostico_relacionado'] = datos_ia["diagnostico_sugerido"]
            
    form_data_initial.setdefault('validez_dias', '30')

    return render_template('crear_receta.html', visita=visita, paciente=visita.paciente, css_file="css/crear_documento.css", form_data=form_data_initial)

@app.route('/receta/<int:receta_id>')
def ver_receta(receta_id):
    receta = (db.session.query(RecetaMedica)
              .options(
                  joinedload(RecetaMedica.paciente_receta),
                  joinedload(RecetaMedica.medico_emisor_receta)
              )
              .filter_by(id=receta_id, medico_id=current_user.id)
              .first())
    if not receta:
        flash('Receta no encontrada o no tiene permiso para verla.', 'danger')
        return redirect(url_for('historial_visitas'))
    
    medicamentos_lista = []
    try:
        if receta.medicamentos_json:
            medicamentos_lista = json.loads(receta.medicamentos_json)
    except json.JSONDecodeError:
        flash('Error al leer los medicamentos de la receta. El formato podría estar corrupto.', 'warning')
    
    medico_for_pdf = receta.medico_emisor_receta
    logo_base64 = get_base64_image_from_path(medico_for_pdf.url_logo_clinica) if medico_for_pdf.url_logo_clinica else None

    return render_template('ver_receta.html', 
        receta=receta, 
        medicamentos=medicamentos_lista, 
        css_file="css/ver_documento.css",
        medico=medico_for_pdf,
        logo_clinica_base64=logo_base64,
        show_clinic_name=medico_for_pdf.show_clinic_name_pdf,
        show_clinic_address=medico_for_pdf.show_clinic_address_pdf,
        show_clinic_phone=medico_for_pdf.show_clinic_phone_pdf,
        show_clinic_website=medico_for_pdf.show_clinic_website_pdf,
        show_doctor_license=medico_for_pdf.show_doctor_license_pdf,
        show_doctor_phone=medico_for_pdf.show_doctor_phone_pdf,
        show_doctor_bio=medico_for_pdf.show_doctor_bio_pdf
    )

@app.route('/visita/<int:visita_id>/referencia/nueva', methods=['GET', 'POST'])
def nueva_referencia_para_visita(visita_id):
    visita = db.session.query(Visita).filter_by(id=visita_id, medico_id=current_user.id).first()
    if not visita:
        flash('Visita no encontrada o no tiene permiso para accederla.', 'danger')
        return redirect(url_for('historial_visitas'))
    if not visita.paciente:
        flash('La visita seleccionada no tiene un paciente asociado.', 'danger')
        return redirect(url_for('historial_visitas'))

    form_data_to_pass = request.form.copy() if request.method == 'POST' else {}
    if request.method == 'GET':
        resumen_clinico_prefill = ""
        if visita.resumen_ai and not visita.resumen_ai.startswith("[Error"):
            resumen_clinico_prefill = visita.resumen_ai
        elif visita.notas_ai and not visita.notas_ai.startswith("[Error"):
            resumen_clinico_prefill = visita.notas_ai
        if resumen_clinico_prefill and not form_data_to_pass.get('resumen_clinico_relevante'):
            form_data_to_pass['resumen_clinico_relevante'] = resumen_clinico_prefill
    if request.method == 'POST':
        especialidad = request.form.get('especialidad_referida','').strip()
        if not especialidad:
            flash('La especialidad referida es obligatoria.', 'danger')
            return render_template('crear_referencia.html', visita=visita, paciente=visita.paciente, css_file="css/crear_documento.css", form_data=form_data_to_pass)
        try:
            nueva_referencia_db = ReferenciaMedica(
                visita_id=visita.id,
                paciente_id=visita.paciente_id,
                medico_referente_id=current_user.id,
                especialidad_referida=especialidad,
                medico_referido_nombre=request.form.get('medico_referido_nombre', '').strip() or None,
                institucion_referida=request.form.get('institucion_referida', '').strip() or None,
                resumen_clinico_relevante=request.form.get('resumen_clinico_relevante', '').strip() or None, # Considerar cifrar
                estudios_adjuntos_info=request.form.get('estudios_adjuntos_info', '').strip() or None, # Considerar cifrar
                estado=request.form.get('estado', 'pendiente')
            )
            db.session.add(nueva_referencia_db)
            db.session.commit()
            reg_act = RegistroActividad(
                visita_id=visita.id, usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
                accion="referencia_creada",
                descripcion=f"Referencia (ID: {nueva_referencia_db.id}) a {especialidad} creada para '{visita.paciente.nombre}'."
            )
            db.session.add(reg_act)
            db.session.commit()
            flash('Referencia médica creada exitosamente.', 'success')
            return redirect(url_for('ver_referencia', referencia_id=nueva_referencia_db.id))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error al crear referencia médica para visita {visita_id} (usuario {current_user.id}): {e}", exc_info=True)
            flash('Error al crear la referencia médica.', 'danger')
            return render_template('crear_referencia.html', visita=visita, paciente=visita.paciente, css_file="css/crear_documento.css", form_data=form_data_to_pass)
    return render_template('crear_referencia.html', visita=visita, paciente=visita.paciente, css_file="css/crear_documento.css", form_data=form_data_to_pass)

@app.route('/referencia/<int:referencia_id>')
def ver_referencia(referencia_id):
    referencia = db.session.query(ReferenciaMedica).filter_by(id=referencia_id, medico_referente_id=current_user.id).first()
    if not referencia:
        flash('Referencia médica no encontrada o no tiene permiso para verla.', 'danger')
        return redirect(url_for('historial_visitas'))

    medico_for_pdf = referencia.medico_emisor_referencia
    logo_base64 = get_base64_image_from_path(medico_for_pdf.url_logo_clinica) if medico_for_pdf.url_logo_clinica else None

    return render_template(
        'ver_referencia.html',
        referencia=referencia,
        medico=medico_for_pdf,
        logo_clinica_base64=logo_base64,
        css_file="css/ver_documento.css",
        show_clinic_name=medico_for_pdf.show_clinic_name_pdf,
        show_clinic_address=medico_for_pdf.show_clinic_address_pdf,
        show_clinic_phone=medico_for_pdf.show_clinic_phone_pdf,
        show_clinic_website=medico_for_pdf.show_clinic_website_pdf,
        show_doctor_license=medico_for_pdf.show_doctor_license_pdf,
        show_doctor_phone=medico_for_pdf.show_doctor_phone_pdf,
        show_doctor_bio=medico_for_pdf.show_doctor_bio_pdf
    )

@app.route('/configuracion-documentos', methods=['GET', 'POST'])
def configuracion_documentos():
    if request.method == 'POST':
        user_db_instance = db.session.get(User, current_user.id)
        if not user_db_instance:
            flash('Error: Usuario no encontrado para actualizar configuración.', 'danger')
            return redirect(url_for('configuracion_documentos'))

        user_db_instance.show_clinic_name_pdf = 'show_clinic_name_pdf' in request.form
        user_db_instance.show_clinic_address_pdf = 'show_clinic_address_pdf' in request.form
        user_db_instance.show_clinic_phone_pdf = 'show_clinic_phone_pdf' in request.form
        user_db_instance.show_clinic_website_pdf = 'show_clinic_website_pdf' in request.form
        user_db_instance.show_doctor_license_pdf = 'show_doctor_license_pdf' in request.form
        user_db_instance.show_doctor_phone_pdf = 'show_doctor_phone_pdf' in request.form
        user_db_instance.show_doctor_bio_pdf = 'show_doctor_bio_pdf' in request.form
        user_db_instance.show_clinic_logo_pdf = 'show_clinic_logo_pdf' in request.form

        try:
            db.session.commit()
            login_user(user_db_instance)
            flash('Configuración guardada con éxito', 'success')
            return redirect(url_for('configuracion_documentos'))
        except Exception as e:
            db.session.rollback()
            flash('Error al guardar configuración', 'danger')
            logging.error(f"Error al guardar la configuración de documentos para el usuario {current_user.id}: {e}", exc_info=True)

    updated_user = db.session.get(User, current_user.id)
    if not updated_user:
        flash('Error al cargar la información de tu perfil. Por favor, intenta iniciar sesión de nuevo.', 'danger')
        logout_user()
        return redirect(url_for('login_route'))

    logo_base64 = None
    if updated_user.url_logo_clinica:
        logo_base64 = get_base64_image_from_path(updated_user.url_logo_clinica)

    return render_template(
        'configuracion_documentos.html',
        user=updated_user,
        logo_clinica_base64=logo_base64
    )
@app.route('/visita/<int:visita_id>/nuevo_plan_nutricional_para_visita_page', methods=['GET', 'POST'])
def nuevo_plan_nutricional_para_visita_page(visita_id):
    visita = db.session.query(Visita).filter_by(id=visita_id, medico_id=current_user.id).first()
    if not visita:
        flash('Visita no encontrada o no tiene permiso para accederla.', 'danger')
        return redirect(url_for('historial_visitas'))
    if not visita.paciente:
        flash('La visita seleccionada no tiene un paciente asociado.', 'danger')
        return redirect(url_for('historial_visitas'))

    form_data_dict = {}
    if request.method == 'GET':
        contenido_sugerido_json_str = None
        if visita.transcripcion and visita.transcripcion.strip() and client_openai and not visita.transcripcion.startswith("[Error"):
            datos_ia_plan = generar_contenido_plan_nutricional_con_ia(visita.transcripcion, visita.idioma_detectado)
            if datos_ia_plan and not datos_ia_plan.get("error"):
                contenido_sugerido_json_str = json.dumps(datos_ia_plan, indent=2, ensure_ascii=False)
                form_data_dict['contenido_json_sugerido'] = contenido_sugerido_json_str
                flash("Se ha sugerido un borrador del plan nutricional basado en la transcripción. Por favor, revísalo y ajústalos.", 'info')
            elif datos_ia_plan and datos_ia_plan.get("error"):
                flash(f"Error al sugerir plan desde IA: {datos_ia_plan.get('error')}", "warning")
        form_data_dict.setdefault('notas_adicionales', request.form.get('notas_adicionales', ''))
        if request.form.get('contenido_json_final_str'):
             form_data_dict['contenido_json_final_str'] = request.form.get('contenido_json_final_str')
    if request.method == 'POST':
        form_data_dict = request.form.copy()
        contenido_json_final_str = request.form.get('contenido_json_final_str')
        notas_adicionales_form = request.form.get('notas_adicionales', '').strip()
        if not contenido_json_final_str:
            flash('El contenido del plan nutricional (JSON) es obligatorio.', 'danger')
            return render_template('crear_plan_nutricional.html', visita=visita, paciente=visita.paciente, css_file="css/crear_documento.css", form_data=form_data_dict)
        try:
            parsed_contenido = json.loads(contenido_json_final_str)
            if not isinstance(parsed_contenido, dict) or not all(k in parsed_contenido for k in ['objetivo_principal', 'recomendaciones_generales', 'plan_diario_tipo']):
                flash('El JSON del plan nutricional no tiene la estructura requerida. Debe incluir al menos: objetivo_principal, recomendaciones_generales, plan_diario_tipo.', 'danger')
                raise json.JSONDecodeError("Estructura JSON inválida", contenido_json_final_str, 0)
            nuevo_plan_db = PlanNutricional(
                visita_id=visita.id,
                paciente_id=visita.paciente_id,
                medico_id=current_user.id,
                contenido_json=contenido_json_final_str, # Considerar cifrar este JSON
                notas_adicionales=notas_adicionales_form or None, # Considerar cifrar
                estado="activo"
            )
            db.session.add(nuevo_plan_db)
            db.session.flush() # Para obtener el ID del plan para el nombre del PDF
            ruta_pdf = generar_y_guardar_pdf_plan_nutricional(nuevo_plan_db, current_user, visita.paciente)
            if ruta_pdf: # ruta_pdf ya incluirá .enc si está cifrado
                nuevo_plan_db.ruta_pdf_almacenada = ruta_pdf
                flash('Plan Nutricional creado y PDF generado exitosamente.', 'success')
            else:
                flash('Plan Nutricional creado, pero hubo un error al generar o guardar el PDF. Revise los logs.', 'warning')
            db.session.commit()
            reg_act = RegistroActividad(
                visita_id=visita.id, usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
                accion="plan_nutricional_creado",
                descripcion=f"Plan Nutricional (ID: {nuevo_plan_db.id}) creado para '{visita.paciente.nombre}'. PDF: {'Sí' if ruta_pdf else 'No'}"
            )
            db.session.add(reg_act)
            db.session.commit()
            return redirect(url_for('ver_plan_nutricional', plan_id=nuevo_plan_db.id))
        except json.JSONDecodeError as je:
            flash(f'Error en el formato JSON del plan nutricional: {je}. Por favor, verifique la estructura.', 'danger')
            db.session.rollback()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error al crear Plan Nutricional para visita {visita_id} (usuario {current_user.id}): {e}", exc_info=True)
            flash(f'Error al crear el Plan Nutricional: {str(e)}', 'danger')
        return render_template('crear_plan_nutricional.html', visita=visita, paciente=visita.paciente, css_file="css/crear_documento.css", form_data=form_data_dict)
    return render_template('crear_plan_nutricional.html', visita=visita, paciente=visita.paciente, css_file="css/crear_documento.css", form_data=form_data_dict)

@app.route('/plan_nutricional/<int:plan_id>')
def ver_plan_nutricional(plan_id):
    plan = db.session.query(PlanNutricional).filter_by(id=plan_id, medico_id=current_user.id).first()
    if not plan:
        flash('Plan Nutricional no encontrado o no tiene permiso para verlo.', 'danger')
        return redirect(url_for('historial_visitas'))

    contenido_dict = {}
    try:
        if plan.contenido_json:
            contenido_dict = json.loads(plan.contenido_json)
    except json.JSONDecodeError:
        flash('Error al leer el contenido del plan. El formato podría estar corrupto.', 'warning')

    medico_for_pdf = plan.medico_emisor_plan
    logo_base64 = get_base64_image_from_path(medico_for_pdf.url_logo_clinica) if medico_for_pdf.url_logo_clinica else None

    return render_template(
        'ver_plan_nutricional.html',
        plan=plan,
        contenido=contenido_dict,
        medico=medico_for_pdf,
        logo_clinica_base64=logo_base64,
        css_file="css/ver_documento.css",
        show_clinic_name=medico_for_pdf.show_clinic_name_pdf,
        show_clinic_address=medico_for_pdf.show_clinic_address_pdf,
        show_clinic_phone=medico_for_pdf.show_clinic_phone_pdf,
        show_clinic_website=medico_for_pdf.show_clinic_website_pdf,
        show_doctor_license=medico_for_pdf.show_doctor_license_pdf,
        show_doctor_phone=medico_for_pdf.show_doctor_phone_pdf,
        show_doctor_bio=medico_for_pdf.show_doctor_bio_pdf
    )

@app.route('/plan_nutricional/<int:plan_id>/pdf')
def descargar_plan_nutricional_pdf(plan_id):
    plan = db.session.query(PlanNutricional).filter_by(id=plan_id, medico_id=current_user.id).first()
    if not plan or not plan.ruta_pdf_almacenada:
        flash('PDF del Plan Nutricional no encontrado, no generado, o no tiene permiso para accederlo.', 'danger')
        return redirect(url_for('ver_plan_nutricional', plan_id=plan_id) if plan else url_for('historial_visitas'))

    try:
        # leer_y_desencriptar_archivo devolverá los bytes del PDF (desencriptados si es necesario)
        pdf_bytes = leer_y_desencriptar_archivo(plan.ruta_pdf_almacenada)
        if pdf_bytes is None:
            logging.error(f"No se pudieron obtener los bytes del PDF para el plan {plan_id} desde {plan.ruta_pdf_almacenada}")
            flash('Error al leer o desencriptar el archivo PDF del plan.', 'danger')
            return redirect(url_for('ver_plan_nutricional', plan_id=plan_id))

        # El nombre de descarga no debe tener .enc
        download_name_base = f"PlanNutricional_{plan.paciente_plan.nombre.replace(' ','_')}_{plan.id}.pdf"

        return send_file(
            io.BytesIO(pdf_bytes), # Enviar bytes desde memoria
            mimetype='application/pdf',
            as_attachment=True,
            download_name=download_name_base
        )
    except FileNotFoundError: # Esto no debería ocurrir si leer_y_desencriptar_archivo funciona bien
        logging.error(f"Archivo PDF no encontrado en el servidor al intentar servir: {os.path.join(app.config['UPLOAD_FOLDER'], plan.ruta_pdf_almacenada)}", exc_info=True)
        flash('Archivo PDF del plan no encontrado en el servidor.', 'danger')
    except Exception as e:
        logging.error(f"Error al intentar servir PDF del plan {plan_id} (usuario {current_user.id}): {e}", exc_info=True)
        flash('Error al descargar el PDF del plan.', 'danger')
    return redirect(url_for('ver_plan_nutricional', plan_id=plan_id))
@app.route('/api/buscar_pacientes', methods=['GET'])
def buscar_pacientes_api():
    query_str = request.args.get('q', '').strip()
    if not query_str or len(query_str) < 1:
        return jsonify([])
    try:
        pacientes_encontrados = Paciente.query.filter(
            Paciente.creado_por_id == current_user.id,
            or_(
                Paciente.nombre.ilike(f"%{query_str}%"),
                Paciente.identificacion_documento.ilike(f"%{query_str}%")
            )
        ).order_by(Paciente.nombre).limit(10).all()
        resultados_json = [{"id": p.id, "nombre": p.nombre, "identificacion_documento": p.identificacion_documento} for p in pacientes_encontrados]
        logging.info(f"Búsqueda de pacientes por '{query_str}' (usuario {current_user.id}): {len(resultados_json)} resultados.")
    except Exception as e:
        logging.error(f"Error en /api/buscar_pacientes con query '{query_str}' (usuario {current_user.id}): {e}", exc_info=True)
        return jsonify({"error": "Error interno al buscar pacientes."}), 500
    return jsonify(resultados_json)

@app.route('/api/iniciar_visita', methods=['POST'])
def iniciar_visita():
    logging.info(f"Solicitud POST a /api/iniciar_visita desde IP: {request.remote_addr} por Usuario ID: {current_user.id}")
    try:
        data = request.get_json()
        if not data:
            logging.warning("/api/iniciar_visita: No se recibió payload JSON.")
            return jsonify({"error": "No se recibió payload JSON."}), 400
    except Exception as e:
        logging.error(f"Error al parsear JSON en /api/iniciar_visita: {e}. Content-Type: {request.content_type}", exc_info=True)
        return jsonify({"error": "Solicitud JSON malformada o Content-Type incorrecto."}), 400

    paciente_nombre_form = data.get('paciente_nombre','').strip()
    plantilla_form = data.get('plantilla')
    tipo_visita_form = data.get('tipo_visita', 'audio_consulta')
    paciente_id_sel = data.get('paciente_id_seleccionado')
    paciente_ident_doc_form = data.get('paciente_identificacion_documento','').strip()
    paciente_obj, paciente_fue_creado = None, False

    if paciente_id_sel:
        try:
            paciente_obj = db.session.query(Paciente).filter_by(id=int(paciente_id_sel), creado_por_id=current_user.id).first()
            if not paciente_obj:
                 logging.warning(f"Intento de iniciar visita para paciente ID {paciente_id_sel} que no pertenece al usuario {current_user.id}.")
                 return jsonify({"error": "Paciente seleccionado no encontrado o no pertenece a este usuario."}), 404
        except ValueError:
            logging.warning(f"ID de paciente '{paciente_id_sel}' no es un entero válido.")
            return jsonify({"error": "ID de paciente inválido."}), 400

    if not paciente_obj:
        if paciente_ident_doc_form:
            paciente_obj = Paciente.query.filter_by(identificacion_documento=paciente_ident_doc_form, creado_por_id=current_user.id).first()
        if not paciente_obj and paciente_nombre_form:
            paciente_obj = Paciente.query.filter(Paciente.nombre.ilike(paciente_nombre_form), Paciente.creado_por_id == current_user.id).first()

        if not paciente_obj and paciente_nombre_form:
            if paciente_ident_doc_form and Paciente.query.filter_by(identificacion_documento=paciente_ident_doc_form, creado_por_id=current_user.id).first():
                return jsonify({"error": f"Ya existe un paciente con el documento de identificación '{paciente_ident_doc_form}' para usted."}), 409
            if Paciente.query.filter(Paciente.nombre.ilike(paciente_nombre_form), Paciente.creado_por_id == current_user.id).first():
                 return jsonify({"error": f"Ya existe un paciente con el nombre '{paciente_nombre_form}' para usted."}), 409

            paciente_obj = Paciente(
                nombre=paciente_nombre_form,
                identificacion_documento=paciente_ident_doc_form or None,
                creado_por_id=current_user.id
            )
            db.session.add(paciente_obj)
            paciente_fue_creado = True
            logging.info(f"Nuevo paciente '{paciente_nombre_form}' será creado por usuario {current_user.id}.")
        elif not paciente_obj and not paciente_nombre_form and (paciente_ident_doc_form or paciente_id_sel):
            return jsonify({"error": f"No se encontró paciente y no se proporcionó nombre para crear uno nuevo."}), 400
        elif not paciente_obj and not paciente_nombre_form and not paciente_ident_doc_form and not paciente_id_sel:
             return jsonify({"error": "No se proporcionó información suficiente para identificar o crear un paciente."}), 400

    if not paciente_obj:
        logging.critical(f"CRITICAL: No patient object could be resolved or created for user {current_user.id}. Cannot start visit.")
        return jsonify({"error": "Error crítico: no se pudo determinar el paciente para la visita."}), 500

    try:
        if paciente_fue_creado or db.session.is_modified(paciente_obj):
            db.session.flush()
        nueva_visita_db = Visita(
            paciente_id=paciente_obj.id,
            medico_id=current_user.id,
            plantilla=plantilla_form,
            tipo_visita=tipo_visita_form,
            fecha=datetime.now(timezone.utc)
        )
        db.session.add(nueva_visita_db)
        db.session.commit()
        desc_log = f"Visita de tipo '{tipo_visita_form.replace('_',' ').capitalize()}' iniciada para el paciente '{paciente_obj.nombre}'."
        if plantilla_form: desc_log += f" Usando la plantilla: '{plantilla_form}'."
        reg_act = RegistroActividad(
            visita_id=nueva_visita_db.id, usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
            accion="visita_creada", descripcion=desc_log
        )
        db.session.add(reg_act)
        db.session.commit()
        session['visita_actual_id'] = nueva_visita_db.id
        logging.info(f"Visita ID {nueva_visita_db.id} iniciada para Paciente ID {paciente_obj.id}, Nombre: {paciente_obj.nombre}. Plantilla: {plantilla_form}, Tipo: {tipo_visita_form}, Médico ID: {current_user.id}")
        return jsonify({
            "message": "Visita iniciada con éxito.", "visita_id": nueva_visita_db.id,
            "paciente_nombre": paciente_obj.nombre, "paciente_id": paciente_obj.id,
            "paciente_creado_ahora": paciente_fue_creado,
            "overview": obtener_datos_overview(nueva_visita_db.id)
        }), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error crítico al iniciar visita (paciente: {paciente_obj.nombre if paciente_obj else 'N/A'}, usuario {current_user.id}): {e}", exc_info=True)
        return jsonify({"error": f"No se pudo iniciar la visita: {str(e)}"}), 500

@app.route('/api/resumir_documentos_e_iniciar_visita', methods=['POST'])
def api_resumir_documentos_e_iniciar_visita():
    logging.info(f"Solicitud a /api/resumir_documentos_e_iniciar_visita desde IP: {request.remote_addr} por Usuario ID: {current_user.id}")
    if not client_openai:
        return jsonify({"error": "Servicio IA (OpenAI) no configurado en el servidor.", "status": "error_servicio_ia", "resumen_generado": "IA no disponible."}), 503

    pac_nom_form = request.form.get('paciente_nombre','').strip()
    plantilla_form = request.form.get('plantilla')
    archivos = request.files.getlist('documentos')
    pac_id_sel = request.form.get('paciente_id')
    pac_ident_doc_form = request.form.get('paciente_identificacion_documento','').strip()
    if not archivos:
        return jsonify({"error": "No se seleccionaron archivos para resumir.", "status": "warning", "resumen_generado": "No se subieron archivos."}), 400

    pac_obj, pac_nuevo = None, False
    if pac_id_sel:
        try:
            pac_obj = db.session.query(Paciente).filter_by(id=int(pac_id_sel), creado_por_id=current_user.id).first()
            if not pac_obj:
                logging.warning(f"Intento de resumir docs para paciente ID {pac_id_sel} que no pertenece al usuario {current_user.id}.")
                return jsonify({"error": "Paciente seleccionado no encontrado o no pertenece a este usuario."}), 404
        except ValueError: 
            logging.warning(f"ID de paciente '{pac_id_sel}' no válido.")
    if not pac_obj:
        if pac_ident_doc_form:
            pac_obj = Paciente.query.filter_by(identificacion_documento=pac_ident_doc_form, creado_por_id=current_user.id).first()
        if not pac_obj and pac_nom_form:
            pac_obj = Paciente.query.filter(Paciente.nombre.ilike(pac_nom_form), Paciente.creado_por_id == current_user.id).first()
        if not pac_obj and pac_nom_form:
            if pac_ident_doc_form and Paciente.query.filter_by(identificacion_documento=pac_ident_doc_form, creado_por_id=current_user.id).first():
                return jsonify({"error": f"Documento '{pac_ident_doc_form}' ya pertenece a otro paciente suyo."}), 409
            if Paciente.query.filter(Paciente.nombre.ilike(pac_nom_form), Paciente.creado_por_id == current_user.id).first():
                 return jsonify({"error": f"Ya existe un paciente con el nombre '{pac_nom_form}' para usted."}), 409
            pac_obj = Paciente(
                nombre=pac_nom_form,
                identificacion_documento=pac_ident_doc_form or None,
                creado_por_id=current_user.id
            )
            db.session.add(pac_obj); pac_nuevo = True
        elif not pac_obj and not pac_nom_form and (pac_ident_doc_form or pac_id_sel):
            return jsonify({"error": f"No se encontró paciente y no se proporcionó nombre para crear uno nuevo."}), 400
        elif not pac_obj and not pac_nom_form and not pac_ident_doc_form and not pac_id_sel:
             return jsonify({"error": "No se proporcionó información suficiente para identificar o crear un paciente."}), 400

    if not pac_obj:
        logging.critical(f"CRITICAL: No patient object could be resolved or created for document summarization (user {current_user.id}).")
        return jsonify({"error": "Error crítico: no se pudo determinar el paciente."}), 500
    try:
        if pac_nuevo or db.session.is_modified(pac_obj):
            db.session.flush()
    except Exception as e_flush:
        db.session.rollback(); logging.error(f"Error BD al hacer flush de paciente para resumen (usuario {current_user.id}): {e_flush}");
        return jsonify({"error": "Error de base de datos al preparar paciente."}), 500

    textos_concat = f"Documentos para el paciente {pac_obj.nombre} (ID: {pac_obj.identificacion_documento or 'N/A'}):\n\n"
    rutas_arch_guardados_db = [] # Rutas que se guardarán en la BD (con .enc si aplica)
    nombres_arch_originales_procesados = []
    nombres_arch_omitidos = []
    allowed_ext = {'.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx', '.txt', '.md'}

    for arch_file in archivos:
        if arch_file and arch_file.filename:
            original_fname_secure = secure_filename(arch_file.filename)
            _, ext_original = os.path.splitext(original_fname_secure.lower())

            if ext_original not in allowed_ext:
                nombres_arch_omitidos.append(original_fname_secure)
                textos_concat += f"[Archivo '{original_fname_secure}' omitido (tipo de archivo '{ext_original}' no soportado)]\n\n"
                continue

            # guardar_archivo_subido ya maneja el cifrado y la extensión .enc if está activo
            ruta_guardada_con_enc_si_aplica = guardar_archivo_subido(arch_file, 'REGISTROS_FOLDER')

            if ruta_guardada_con_enc_si_aplica:
                rutas_arch_guardados_db.append(ruta_guardada_con_enc_si_aplica)
                nombres_arch_originales_procesados.append(original_fname_secure)
                # procesar_archivo_subido se encarga de leer (y desencriptar si es necesario)
                # y luego extraer texto.
                texto_extraido_arch = procesar_archivo_subido(ruta_guardada_con_enc_si_aplica, original_fname_secure)
                textos_concat += f"--- INICIO DEL DOCUMENTO: {original_fname_secure} ---\n{texto_extraido_arch or '[Contenido no pudo ser extraído o está vacío]'}\n--- FIN DEL DOCUMENTO: {original_fname_secure} ---\n\n"
            else:
                nombres_arch_omitidos.append(original_fname_secure)
                textos_concat += f"[Error al guardar el archivo '{original_fname_secure}']\n\n"

    res_ia_docs, res_ia_docs_status = "No se generó resumen.", "no_generado"
    if not rutas_arch_guardados_db and not nombres_arch_omitidos: # rutas_arch_guardados_db ahora contiene las rutas con .enc
        res_ia_docs = "No se proporcionaron archivos válidos para procesar."
        res_ia_docs_status = "error_no_archivos_validos"
    elif client_openai and (textos_concat.strip() and len(textos_concat.strip()) > len(f"Documentos para el paciente {pac_obj.nombre} (ID: {pac_obj.identificacion_documento or 'N/A'}):\n\n".strip())):
        res_ia_docs = generar_resumen_inteligente_documentos(textos_concat)
        if any(err_indicator in res_ia_docs for err_indicator in ["[Error API OpenAI", "[Error inesperado", "[Error de configuración", "[Resumen con IA no disponible"]):
            res_ia_docs_status = "error_ia"
        else:
            res_ia_docs_status = "exito_ia" # Marcar como éxito si no hay error de IA
    elif not client_openai:
        res_ia_docs = "[Resumen con IA no disponible (servicio no configurado).]"
        res_ia_docs_status = "error_servicio_ia"

    try:
        arch_adj_json_db = json.dumps({
            "procesados": rutas_arch_guardados_db, # Guardar rutas con .enc si están cifradas
            "original_filenames": nombres_arch_originales_procesados, # Guardar nombres originales para referencia
            "omitidos": nombres_arch_omitidos
        })
        n_visita_res = Visita(
            paciente_id=pac_obj.id,
            medico_id=current_user.id,
            plantilla=plantilla_form or "Resumen Documentos General",
            tipo_visita="resumen_documentos",
            resumen_ai=res_ia_docs, # Considerar cifrar
            archivos_adjuntos=arch_adj_json_db, # Contiene rutas a archivos (posiblemente cifrados)
            fecha=datetime.now(timezone.utc)
        )
        db.session.add(n_visita_res)
        db.session.commit()
        session['visita_actual_id'] = n_visita_res.id
        desc_log = f"Resumen de {len(rutas_arch_guardados_db)} documento(s) generado para '{pac_obj.nombre}'. Estado IA: {res_ia_docs_status}."
        if nombres_arch_omitidos: desc_log += f" Omitidos: {len(nombres_arch_omitidos)}."
        reg_act = RegistroActividad(
            visita_id=n_visita_res.id, usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
            accion="resumen_registros_generado", descripcion=desc_log
        )
        db.session.add(reg_act); db.session.commit()
        final_msg = f"Proceso de resumen de documentos completado para '{pac_obj.nombre}'. Documentos procesados: {len(rutas_arch_guardados_db)}."
        if nombres_arch_omitidos: final_msg += f" Documentos omitidos: {len(nombres_arch_omitidos)}."
        return jsonify({
            "message": final_msg, "status": res_ia_docs_status, "visita_id": n_visita_res.id,
            "paciente_id": pac_obj.id, "paciente_nombre": pac_obj.nombre, "paciente_creado_ahora": pac_nuevo,
            "resumen_generado": res_ia_docs,
            "archivos_procesados_nombres": nombres_arch_originales_procesados, # Mostrar nombres originales en UI
            "archivos_omitidos": nombres_arch_omitidos,
            "overview": obtener_datos_overview(n_visita_res.id)
        }), 200
    except Exception as e_db:
        db.session.rollback(); logging.error(f"Error BD al guardar visita de resumen (usuario {current_user.id}): {e_db}", exc_info=True)
        return jsonify({"error": "Error de base de datos al guardar la visita de resumen."}), 500
@app.route('/chat-bot')
def chat_bot():
    return render_template('chat_bot.html')


@app.route('/api/subir_audio', methods=['POST'])
def subir_audio():
    if 'visita_actual_id' not in session:
        return jsonify({"error": "No hay visita activa. Por favor, inicie una nueva visita primero."}), 400

    visita_id = session['visita_actual_id']
    visita = db.session.query(Visita).filter_by(id=visita_id, medico_id=current_user.id).first()
    if not visita:
        session.pop('visita_actual_id', None)
        return jsonify({"error": f"La visita activa (ID: {visita_id}) no fue encontrada o no le pertenece."}), 404

    if 'audio' not in request.files:
        return jsonify({"error": "No se envió ningún archivo de audio."}), 400

    file = request.files['audio']

    if file.filename == '':
        return jsonify({"error": "El nombre del archivo de audio está vacío."}), 400

    if file:
        original_filename = secure_filename(file.filename)
        file_ext = os.path.splitext(original_filename)[1].lower()

        if file_ext not in ALLOWED_OPENAI_AUDIO_EXTENSIONS:
            logging.warning(f"Usuario {current_user.id} intentó subir un archivo con formato no soportado: {original_filename}")
            return jsonify({ "error": f"Formato de archivo no soportado ('{file_ext}')."}), 400

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        nuevo_nombre = f"visita_{visita.id}_grabacion_{timestamp}{file_ext}"

        # Guardar archivo físicamente
        # Usamos la función consolidada que también maneja el cifrado
        ruta_relativa_para_db = guardar_archivo_subido(file, 'AUDIO_FOLDER')

        if not ruta_relativa_para_db:
             logging.error(f"Fallo al guardar el archivo de audio '{nuevo_nombre}' para la visita ID {visita.id}")
             return jsonify({"error": "Error interno al guardar el archivo de audio."}), 500

        # Obtener duración del archivo ya guardado (y posiblemente cifrado)
        # Nota: Si el archivo está cifrado, necesitamos leerlo y desencriptarlo en memoria para obtener su duración.
        audio_bytes = leer_y_desencriptar_archivo(ruta_relativa_para_db)
        duracion_seg = None
        if audio_bytes:
            # Para obtener la duración, necesitamos escribir los bytes en un archivo temporal
            temp_file_path_for_duration = ""
            try:
                # Usar la extensión original para que pydub la reconozca
                temp_fd, temp_file_path_for_duration = tempfile.mkstemp(suffix=file_ext)
                with os.fdopen(temp_fd, 'wb') as tmp:
                    tmp.write(audio_bytes)

                # Ahora obtenemos la duración desde el archivo temporal desencriptado
                duracion_seg = obtener_duracion_audio_segundos(temp_file_path_for_duration)

            except Exception as e_dur:
                logging.error(f"Error obteniendo duración desde archivo temporal: {e_dur}")
            finally:
                if temp_file_path_for_duration and os.path.exists(temp_file_path_for_duration):
                    os.remove(temp_file_path_for_duration) # Limpiar archivo temporal

        if duracion_seg is None:
            logging.warning(f"No se pudo obtener la duración para el audio de la visita {visita.id}")
            # El message flash no es muy útil en una API, pero lo mantenemos por si acaso
            flash("❌ Error: No se pudo procesar la duración del audio.", "danger")

        # --- CORRECCIÓN CRÍTICA EN LA BASE DE DATOS ---
        # Guardar la ruta relativa en el campo correcto 'archivos_adjuntos'
        visita.archivos_adjuntos = ruta_relativa_para_db
        visita.duracion_grabacion_segundos = duracion_seg
        db.session.commit()

        # Registrar actividad
        desc_log_subida = f"Grabación de audio '{original_filename}' ({duracion_seg or 'N/A'}s) subida para la visita."
        reg_act = RegistroActividad(visita_id=visita.id, usuario_id=current_user.id, usuario_nombre_display=current_user.nombre, accion="grabacion_subida", descripcion=desc_log_subida)
        db.session.add(reg_act)
        db.session.commit()

        logging.info(f"Audio subido y procesado para Visita ID: {visita.id} por Usuario ID: {current_user.id}. Ruta en DB: {ruta_relativa_para_db}")

        # --- CORRECCIÓN CRÍTICA EN LA RESPUESTA JSON ---
        # Devolver la clave 'ruta_audio_procesable' que el JavaScript espera.
        return jsonify({
            "success": True, 
            "filename": nuevo_nombre, 
            "ruta_audio_procesable": ruta_relativa_para_db
        })
@app.route('/api/actualizar_notas_resumen_ai', methods=['POST'])
def api_actualizar_notas_resumen_ai():
    """
    Actualiza el contenido de notas_ai y resumen_ai para una visita específica.
    Recibe contenido en Markdown.
    """
    data = request.get_json()
    visita_id = data.get('visita_id')
    resumen_ai_content_raw = data.get('resumen_ai_content')
    notas_ai_content_raw = data.get('notas_ai_content')

    if not visita_id:
        return jsonify({"error": "ID de visita es requerido."}), 400

    visita = db.session.query(Visita).filter_by(id=visita_id, medico_id=current_user.id).first()

    if not visita:
        return jsonify({"error": "Visita no encontrada o no tiene permiso para actualizarla."}), 404

    try:
        # --- CAMBIO CLAVE AQUÍ: Desescapar los saltos de línea antes de guardar ---
        # Si el frontend envía '\n' como '\\n', necesitamos convertirlo a '\n'
        if resumen_ai_content_raw is not None:
            # Reemplazar '\\n' con '\n' para que se guarde como Markdown puro
            visita.resumen_ai = resumen_ai_content_raw.replace('\\n', '\n')
        else:
            visita.resumen_ai = visita.resumen_ai # Mantiene el valor existente

        if notas_ai_content_raw is not None:
            # Reemplazar '\\n' con '\n' para que se guarde como Markdown puro
            visita.notas_ai = notas_ai_content_raw.replace('\\n', '\n')
        else:
            visita.notas_ai = visita.notas_ai # Mantiene el valor existente
        # --- FIN DEL CAMBIO CLAVE ---
        
        db.session.commit()

        # Registrar actividad
        reg_act = RegistroActividad(
            visita_id=visita.id,
            usuario_id=current_user.id,
            usuario_nombre_display=current_user.nombre,
            accion="notas_ai_editadas",
            descripcion=f"Contenido de Notas y Resumen AI editado manualmente para la visita ID {visita.id}."
        )
        db.session.add(reg_act)
        db.session.commit()

        return jsonify({"message": "Contenido AI actualizado exitosamente."}), 200

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error al actualizar notas y resumen AI para visita {visita_id}: {e}", exc_info=True)
        return jsonify({"error": f"Error interno al actualizar el contenido AI: {str(e)}"}), 500

@app.route('/api/crear_referencia_desde_chat', methods=['POST'])
def api_crear_referencia_desde_chat():
    """
    Crea una referencia médica desde el chatbot sin una visita preexistente.
    Busca o crea al paciente según los datos proporcionados.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Faltan datos en la solicitud.'}), 400

    # Extraer datos del paciente y de la referencia
    patient_name = data.get('patientName', '').strip()
    patient_id_doc = data.get('patientId', '').strip()
    patient_email = data.get('patientEmail', '').strip()
    
    if not patient_name:
        return jsonify({'error': 'El nombre del paciente es obligatorio.'}), 400

    # Buscar al paciente por documento de identidad o por nombre
    paciente = None
    if patient_id_doc:
        paciente = Paciente.query.filter_by(
            identificacion_documento=patient_id_doc, 
            creado_por_id=current_user.id
        ).first()
    
    if not paciente:
        paciente = Paciente.query.filter(
            Paciente.nombre.ilike(patient_name),
            Paciente.creado_por_id == current_user.id
        ).first()

    # Si el paciente no existe, crearlo
    if not paciente:
        logging.info(f"Chatbot: Creando nuevo paciente '{patient_name}' para usuario {current_user.id}")
        paciente = Paciente(
            nombre=patient_name,
            identificacion_documento=patient_id_doc or None,
            email=patient_email or None,
            creado_por_id=current_user.id
        )
        db.session.add(paciente)
        db.session.flush() # Para obtener el ID del nuevo paciente

    try:
        # Crear la referencia médica
        nueva_referencia = ReferenciaMedica(
            paciente_id=paciente.id,
            medico_referente_id=current_user.id,
            especialidad_referida=data.get('specialty'),
            motivo_referencia=data.get('reason'),
            medico_referido_nombre=data.get('doctorName'),
            resumen_clinico_relevante=data.get('summary'),
            estudios_adjuntos_info=data.get('studies'),
            estado='pendiente',
            visita_id=None # Importante: No se asocia a ninguna visita
        )
        db.session.add(nueva_referencia)
        db.session.commit()

        # Registrar la actividad (sin asociarla a una visita)
        reg_act = RegistroActividad(
            visita_id=None, 
            usuario_id=current_user.id, 
            usuario_nombre_display=current_user.nombre,
            accion="referencia_creada",
            descripcion=f"Referencia (ID: {nueva_referencia.id}) a {nueva_referencia.especialidad_referida} creada para '{paciente.nombre}' desde el Chatbot."
        )
        db.session.add(reg_act)
        db.session.commit()

        return jsonify({
            'message': 'Documento de Referencia creado exitosamente.',
            'referencia': {
                'id': nueva_referencia.id,
                'url_ver': url_for('ver_referencia', referencia_id=nueva_referencia.id, _external=False)
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error en api_crear_referencia_desde_chat: {e}", exc_info=True)
        return jsonify({'error': 'Ocurrió un error interno al guardar la referencia.'}), 500

@app.route('/api/crear_receta_desde_chat', methods=['POST'])
def api_crear_receta_desde_chat():
    """
    Crea una receta médica desde el chatbot sin una visita preexistente.
    Busca o crea al paciente según los datos proporcionados.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Faltan datos en la solicitud.'}), 400

    # Extraer datos del paciente
    patient_name = data.get('patientName', '').strip()
    patient_id_doc = data.get('patientId', '').strip()
    patient_email = data.get('patientEmail', '').strip()
    
    if not patient_name:
        return jsonify({'error': 'El nombre del paciente es obligatorio.'}), 400

    # Buscar al paciente por documento de identidad o por nombre
    paciente = None
    if patient_id_doc:
        paciente = Paciente.query.filter_by(
            identificacion_documento=patient_id_doc, 
            creado_por_id=current_user.id
        ).first()
    
    if not paciente:
        paciente = Paciente.query.filter(
            Paciente.nombre.ilike(patient_name),
            Paciente.creado_por_id == current_user.id
        ).first()

    # Si el paciente no existe, crearlo
    if not paciente:
        logging.info(f"Chatbot: Creando nuevo paciente '{patient_name}' para receta (usuario {current_user.id})")
        paciente = Paciente(
            nombre=patient_name,
            identificacion_documento=patient_id_doc or None,
            email=patient_email or None,
            creado_por_id=current_user.id
        )
        db.session.add(paciente)
        db.session.flush() # Para obtener el ID del nuevo paciente

    try:
        # Extraer datos de la receta
        medicamentos = data.get('medicamentos')
        if not medicamentos or not isinstance(medicamentos, list):
            return jsonify({'error': 'La lista de medicamentos es obligatoria y debe ser un array.'}), 400

        # Crear la receta médica
        nueva_receta = RecetaMedica(
            paciente_id=paciente.id,
            medico_id=current_user.id,
            medicamentos_json=json.dumps(medicamentos),
            diagnostico_relacionado=data.get('diagnostico_relacionado'),
            validez_dias=data.get('validez_dias', type=int, default=30),
            notas_adicionales_receta=data.get('notas_adicionales_receta'),
            estado="activa",
            visita_id=None # Importante: No se asocia a ninguna visita
        )
        db.session.add(nueva_receta)
        db.session.commit()

        # Registrar la actividad (sin asociarla a una visita)
        reg_act = RegistroActividad(
            visita_id=None, 
            usuario_id=current_user.id, 
            usuario_nombre_display=current_user.nombre,
            accion="receta_creada",
            descripcion=f"Receta (ID: {nueva_receta.id}) creada para '{paciente.nombre}' desde el Chatbot."
        )
        db.session.add(reg_act)
        db.session.commit()

        return jsonify({
            'message': 'Receta Médica creada exitosamente.',
            'receta': {
                'id': nueva_receta.id,
                'url_ver': url_for('ver_receta', receta_id=nueva_receta.id, _external=False)
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error en api_crear_receta_desde_chat: {e}", exc_info=True)
        return jsonify({'error': 'Ocurrió un error interno al guardar la receta.'}), 500

@app.route('/api/transcribir_diarizar', methods=['POST'])
def transcribir_diarizar_audio():
    global client_openai
    if 'visita_actual_id' not in session:
        return jsonify({"error": "No hay visita activa para transcribir."}), 400
    visita_id = session['visita_actual_id']
    visita = db.session.query(Visita).filter_by(id=visita_id, medico_id=current_user.id).first()
    if not visita:
        session.pop('visita_actual_id', None)
        return jsonify({"error": f"Visita con ID {visita_id} no encontrada o no le pertenece."}), 404

    audio_path_relativo_en_db = visita.archivos_adjuntos # Esta ruta puede tener .enc
    if not audio_path_relativo_en_db:
        return jsonify({"error": "No se especificó la ruta del archivo de audio y no hay audio asociado a la visita."}), 400

    if not client_openai:
        logging.error("Cliente OpenAI no inicializado. No se puede realizar la transcripción.")
        visita.transcripcion = "[Error: Servicio de transcripción (OpenAI) no configurado en el servidor.]"
        db.session.commit()
        return jsonify({"error": "Servicio de transcripción (OpenAI) no configurado en el servidor."}), 503

    # Leer y desencriptar el audio si es necesario
    audio_bytes = leer_y_desencriptar_archivo(audio_path_relativo_en_db)
    if audio_bytes is None:
        logging.error(f"No se pudo leer o desencriptar el audio: {audio_path_relativo_en_db}")
        visita.transcripcion = "[Error: No se pudo leer o desencriptar el archivo de audio del servidor.]"
        db.session.commit()
        return jsonify({"error": "No se pudo leer o desencriptar el archivo de audio del servidor."}), 500

    # Whisper espera un objeto de archivo, así que usamos BytesIO
    audio_file_like_object = io.BytesIO(audio_bytes)
    # El nombre del archivo para Whisper no es crítico aquí, pero podemos usar el original sin .enc
    original_audio_filename_for_whisper = os.path.basename(audio_path_relativo_en_db).replace('.enc','')

    texto_transcrito = "[Transcripción no generada.]"
    idioma_detectado_whisper = "N/D"
    try:
        # Pasar el objeto BytesIO y un nombre de archivo a Whisper
        respuesta_transcripcion = client_openai.audio.transcriptions.create(
            model="whisper-1",
            file=(original_audio_filename_for_whisper, audio_file_like_object, 'application/octet-stream'), # Tupla para nombre y objeto archivo
            response_format="verbose_json"
        )
        texto_transcrito = respuesta_transcripcion.text
        idioma_detectado_whisper = respuesta_transcripcion.language
        logging.info(f"Audio transcrito para Visita ID {visita.id} (Usuario {current_user.id}). Idioma: {idioma_detectado_whisper}. Longitud: {len(texto_transcrito)}")
        visita.transcripcion = texto_transcrito # Considerar cifrar este campo
        visita.idioma_detectado = idioma_detectado_whisper
        db.session.commit()
        desc_log = f"Transcripción generada para la visita. Idioma detectado: {str(idioma_detectado_whisper).upper()}."
        reg_act = RegistroActividad(
            visita_id=visita.id, usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
            accion="transcripcion_generada", descripcion=desc_log
        )
        db.session.add(reg_act); db.session.commit()
        return jsonify({
            "message": "Audio transcrito exitosamente.", "transcripcion": texto_transcrito,
            "idioma_detectado": idioma_detectado_whisper,
            "overview": obtener_datos_overview(visita.id)
        }), 200
    except APIError as e_api:
        logging.error(f"Error de API OpenAI durante la transcripción (Visita {visita.id}, Usuario {current_user.id}): {e_api}", exc_info=True)
        error_msg = f"[Error del servicio de OpenAI al transcribir: {e_api.message if hasattr(e_api, 'message') else str(e_api)}]"
        visita.transcripcion = error_msg; db.session.commit()
        return jsonify({"error": error_msg}), getattr(e_api, 'status_code', 500)
    except BadRequestError as e_bad_req: # Esto puede ocurrir si el formato de audio no es soportado por Whisper
        logging.error(f"Error de BadRequest OpenAI durante la transcripción (Visita {visita.id}, Usuario {current_user.id}): {e_bad_req}", exc_info=True)
        error_msg = f"[Error en la solicitud de transcripción a OpenAI (ej. archivo no soportado/corrupto): {e_bad_req.message if hasattr(e_bad_req, 'message') else str(e_bad_req)}]"
        visita.transcripcion = error_msg; db.session.commit()
        return jsonify({"error": error_msg}), 400
    except Exception as e_gen:
        logging.error(f"Error inesperado durante la transcripción (Visita {visita.id}, Usuario {current_user.id}): {e_gen}", exc_info=True)
        visita.transcripcion = f"[Error inesperado durante la transcripción: {str(e_gen)[:100]}]"; db.session.commit()
        return jsonify({"error": "Ocurrió un error inesperado durante la transcripción."}), 500
    # No necesitamos eliminar el archivo temporal porque usamos BytesIO

@app.route('/api/generar_resumen_ai', methods=['POST'])
def api_generar_resumen_ai():
    data = request.get_json()
    visita_id = data.get('visita_id')
    if not visita_id: return jsonify({"error": "Falta el ID de la visita."}), 400
    visita = db.session.query(Visita).filter_by(id=visita_id, medico_id=current_user.id).first()
    if not visita: return jsonify({"error": "Visita no encontrada o no le pertenece."}), 404
    if not visita.transcripcion or visita.transcripcion.startswith("[Error") or not visita.transcripcion.strip():
        return jsonify({"error": "No hay transcripción válida disponible para generar el resumen."}), 400
    idioma_prompt = normalize_language_code(visita.idioma_detectado) or 'es'
    resumen_gen = generar_resumen_ai_desde_transcripcion(
        visita.transcripcion, visita.plantilla or "Consulta General", idioma_prompt
    )
    if not resumen_gen.startswith("[Error"):
        visita.resumen_ai = resumen_gen # Considerar cifrar
        db.session.commit()
        desc_log = f"Resumen AI generado/actualizado para la visita. Plantilla: '{visita.plantilla or "General"}'. Idioma: {idioma_prompt.upper()}."
        reg_act = RegistroActividad(
            visita_id=visita.id, usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
            accion="resumen_generado", descripcion=desc_log
        )
        db.session.add(reg_act); db.session.commit()
        return jsonify({"message": "Resumen AI generado exitosamente.", "resumen_ai": resumen_gen,
                        "overview": obtener_datos_overview(visita_id)}), 200
    else:
        logging.error(f"Fallo al generar resumen AI para Visita {visita_id} (Usuario {current_user.id}): {resumen_gen}")
        return jsonify({"error": f"No se pudo generar el resumen AI: {resumen_gen}"}), 500

@app.route('/api/generar_notas_ai', methods=['POST'])
def api_generar_notas_ai():
    data = request.get_json()
    visita_id = data.get('visita_id')
    if not visita_id: return jsonify({"error": "Falta el ID de la visita."}), 400
    
    visita = db.session.query(Visita).filter_by(id=visita_id, medico_id=current_user.id).first()
    if not visita: return jsonify({"error": "Visita no encontrada o no le pertenece."}), 404
    
    if not visita.transcripcion or visita.transcripcion.startswith("[Error") or not visita.transcripcion.strip():
        return jsonify({"error": "No hay transcripción válida disponible para generar las notas."}), 400

    idioma_prompt = normalize_language_code(visita.idioma_detectado) or 'es'
    
    # <-- INICIO DE LA MODIFICACIÓN -->
    # Obtener la especialidad del usuario actual
    user_specialty = current_user.especialidad
    
    # Pasar la especialidad a la función de generación de notas
    notas_gen_result = generar_notas_ai_desde_transcripcion(
        visita.transcripcion, 
        visita.plantilla or "SOAP", 
        idioma_prompt,
        especialidad_usuario=user_specialty  # <-- NUEVO PARÁMETRO
    )
    # <-- FIN DE LA MODIFICACIÓN -->

    if isinstance(notas_gen_result, str) and notas_gen_result.startswith("[Error"):
        logging.error(f"Fallo al generar notas AI para Visita {visita_id} (Usuario {current_user.id}): {notas_gen_result}")
        return jsonify({"error": f"No se pudieron generar las notas AI: {notas_gen_result}"}), 500

    notas_gen_markdown = notas_gen_result.get('markdown', '')
    notas_gen_html = notas_gen_result.get('html', '') 

    if not notas_gen_markdown:
        logging.error(f"Generación de notas AI exitosa, pero el contenido markdown está vacío para Visita {visita_id}.")
        return jsonify({"error": "Notas AI generadas, pero el contenido markdown está vacío."}), 500

    visita.notas_ai = notas_gen_markdown
    db.session.commit()

    desc_log = f"Notas AI generadas/actualizadas. Plantilla: '{visita.plantilla or "SOAP"}'. Idioma: {idioma_prompt.upper()}."
    if user_specialty and user_specialty.lower() == 'nutrición':
        desc_log += " (Plantilla de Nutrición)" # Log específico
        
    reg_act = RegistroActividad(
        visita_id=visita.id, usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
        accion="notas_ia_generadas", descripcion=desc_log
    )
    db.session.add(reg_act)
    db.session.commit()
    
    return jsonify({
        "message": "Notas AI generadas exitosamente.",
        "notas_ai_markdown": notas_gen_markdown,
        "notas_ai_html": notas_gen_html,
        "overview": obtener_datos_overview(visita_id)
    }), 200


@app.route('/api/generar_plan_alimenticio', methods=['POST'])
def api_generar_plan_alimenticio():
    data = request.get_json()
    visita_id = data.get('visita_id')

    if not visita_id:
        return jsonify({"error": "Falta el ID de la visita."}), 400

    visita = db.session.query(Visita).filter_by(id=visita_id, medico_id=current_user.id).first()
    if not visita:
        return jsonify({"error": "Visita no encontrada o no le pertenece."}), 404

    if not visita.transcripcion or visita.transcripcion.startswith("[Error") or not visita.transcripcion.strip():
        return jsonify({"error": "No hay transcripción válida disponible para generar el plan."}), 400

    logging.info(f"Iniciando generación de contenido de plan nutricional AI para visita ID: {visita_id}")

    contenido_plan_dict = generar_contenido_plan_nutricional_con_ia(
        visita.transcripcion,
        visita.idioma_detectado or 'es'
    )

    if "error" in contenido_plan_dict:
        logging.error(f"Fallo al generar contenido del plan AI para Visita {visita_id}: {contenido_plan_dict['error']}")
        return jsonify({"error": f"No se pudo generar el contenido del plan: {contenido_plan_dict['error']}"}), 500

    # Ahora, solo devolver el contenido JSON. El guardado en la BD y la generación del PDF
    # se realizarán en la página dedicada de creación del plan (en el método POST de esa ruta).
    return jsonify({
        "message": "Contenido del plan nutricional generado exitosamente por IA.",
        "plan_alimenticio_json": json.dumps(contenido_plan_dict, ensure_ascii=False) # Devuelve como string JSON
    }), 200

@app.route('/api/traducir_texto', methods=['POST'])
def api_traducir_texto():
    data = request.get_json()
    texto_original = data.get('texto_original')
    idioma_origen = data.get('idioma_origen_code')
    idioma_destino = data.get('idioma_destino_code')
    if not all([texto_original, idioma_origen, idioma_destino]):
        return jsonify({"error": "Faltan datos para la traducción (texto_original, idioma_origen_code, idioma_destino_code)."}), 400
    texto_traducido = _traducir_texto_interno(texto_original, idioma_origen, idioma_destino)
    if texto_traducido.startswith("[Error"):
        return jsonify({"error": texto_traducido.split('\n')[0], "texto_traducido": texto_original}), 500
    return jsonify({"texto_traducido": texto_traducido, "idioma_original_confirmado": idioma_origen})

@app.route('/api/visita_overview/<int:visita_id>')
def api_visita_overview(visita_id):
    overview_data = obtener_datos_overview(visita_id_param=visita_id)
    if "Error" in overview_data.get('paciente', '') or "Error" in overview_data.get('resumen', '') or "acceso denegado" in overview_data.get('resumen', '').lower():
        error_msg = overview_data.get('resumen', "Error al cargar datos de la visita o acceso denegado.")
        return jsonify({"error": error_msg}), 404
    return jsonify(overview_data)

@app.route('/api/eliminar_visita/<int:visita_id_param>', methods=['POST'])
def eliminar_visita_completa(visita_id_param):
    visita = db.session.query(Visita).filter_by(id=visita_id_param, medico_id=current_user.id).first()
    if not visita:
        return jsonify({"error": f"Visita ID {visita_id_param} no encontrada o no tiene permiso para eliminarla."}), 404
    try:
        pac_nombre = visita.paciente.nombre if visita.paciente else "Desconocido"
        logging.info(f"Iniciando eliminación de Visita ID {visita_id_param} para el paciente '{pac_nombre}' por Usuario ID: {current_user.id}")
        _eliminar_archivos_asociados_a_visita(visita) # Esto ya maneja archivos posiblemente cifrados
        for plan_obj in visita.planes_nutricionales_visita.all():
            if plan_obj.ruta_pdf_almacenada:
                ruta_pdf_completa = os.path.join(app.config['UPLOAD_FOLDER'], plan_obj.ruta_pdf_almacenada)
                if os.path.exists(ruta_pdf_completa):
                    try:
                        os.remove(ruta_pdf_completa)
                        logging.info(f"PDF de Plan Nutricional (asociado a visita, {'CIFRADO' if plan_obj.ruta_pdf_almacenada.endswith('.enc') else 'NO CIFRADO'}) eliminado: {ruta_pdf_completa}")
                    except Exception as e_del_pdf_plan:
                        logging.error(f"Error eliminando PDF de Plan Nutricional '{ruta_pdf_completa}' asociado a visita: {e_del_pdf_plan}")
        db.session.delete(visita)
        db.session.commit()
        reg_act = RegistroActividad(
            visita_id=None,
            usuario_id=current_user.id,
            usuario_nombre_display=current_user.nombre,
            accion="visita_eliminada",
            descripcion=f"Visita ID {visita_id_param} (Paciente: {pac_nombre}) eliminada."
        )
        db.session.add(reg_act)
        db.session.commit()

        logging.info(f"Visita ID {visita_id_param} y sus archivos asociados eliminados exitosamente por Usuario ID: {current_user.id}.")
        return jsonify({"message": f"Visita ID {visita_id_param} (Paciente: {pac_nombre}) eliminada exitosamente."}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error al eliminar la visita ID {visita_id_param} (Usuario {current_user.id}): {e}", exc_info=True)
        return jsonify({"error": "Error al eliminar la visita."}), 500

@app.route('/api/compartir_visita_email', methods=['POST'])
def compartir_visita_email():
    data = request.get_json()
    if not data: return jsonify({"error": "No se recibió payload JSON."}), 400
    visita_id = data.get('visita_id')
    email_dest = data.get('email_destinatario')
    asunto_opc = data.get('asunto')
    msg_adic_raw = data.get('message_adicional', '')
    idioma_email_sel = data.get('idioma_email', '')
    image_data_b64 = data.get('image_data') # <-- NUEVO: Captura la imagen base64

    if not visita_id or not email_dest:
        return jsonify({"error": "Falta ID de visita o email del destinatario."}), 400

    visita = db.session.query(Visita).filter_by(id=visita_id, medico_id=current_user.id).first()
    if not visita: return jsonify({"error": "Visita no encontrada o no tiene permiso para compartirla."}), 404

    if not all([app.config.get('MAIL_SERVER'), app.config.get('MAIL_USERNAME'), app.config.get('MAIL_PASSWORD')]):
        logging.error("Configuración de correo incompleta en el servidor.")
        return jsonify({"error": "Servicio de correo no configurado en el servidor."}), 503

    try:
        pac_nombre = visita.paciente.nombre if visita.paciente else "N/E"
        fecha_vis_obj = visita.fecha or datetime.now(timezone.utc)
        meses_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        fecha_vis_str = f"{fecha_vis_obj.day} de {meses_es[fecha_vis_obj.month - 1]} de {fecha_vis_obj.year}, {fecha_vis_obj.strftime('%H:%M %Z')}" \
            if 0 <= fecha_vis_obj.month -1 < 12 else fecha_vis_obj.strftime('%d/%m/%Y %H:%M %Z')
        asunto_final = asunto_opc or f"Detalles de la Visita Clínica: {pac_nombre} - {fecha_vis_obj.strftime('%d/%m/%Y')}"

        # Define el cuerpo HTML del correo. Si hay imagen, se enfoca en eso.
        # Si NO hay imagen, entonces incluye la transcripción, resumen y notas como texto/markdown.
        cuerpo_html = ""
        if image_data_b64:
            # Si se envía una imagen, el correo solo la contendrá junto a un message
            image_bytes = base64.b64decode(image_data_b64.split(',')[1]) # Decodificar la imagen
            nombre_archivo_imagen = f"Notas_Resumen_Visita_{visita_id}_{pac_nombre.replace(' ','_')}.png"

            msg_adic_html = f"<p><b>Mensaje adicional:</b><br>{msg_adic_raw.replace(chr(10), '<br>')}</p>" if msg_adic_raw else ''
            cuerpo_html = f"""
                <!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>{asunto_final}</title></head>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2>Notas y Resumen de la Visita</h2>
                    <p>Estimado/a,</p>
                    <p>Por favor, encuentre adjuntas las notas y el resumen de la visita para el paciente <strong>{pac_nombre}</strong>.</p>
                    {msg_adic_html}
                    <p>El documento está en formato de imagen (PNG).</p><br>
                    <p>Saludos cordiales,</p><p><em>Generado por Vitta Health Scribe</em></p>
                </body></html>
                """

            msg_obj = Message(subject=asunto_final, recipients=[email_dest], html=cuerpo_html, sender=app.config['MAIL_DEFAULT_SENDER'])
            msg_obj.attach(
                filename=nombre_archivo_imagen,
                content_type='image/png',
                data=image_bytes
            )
            mail.send(msg_obj)

            desc_log_email = f"Información de la Visita ID {visita_id} (Notas AI como imagen) compartida por email a {email_dest}."
            reg_act = RegistroActividad(
                visita_id=visita.id, usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
                accion="visita_compartida", descripcion=desc_log_email
            )
            db.session.add(reg_act); db.session.commit()
            logging.info(f"Email con imagen de notas AI de la visita {visita_id} enviado a {email_dest} (Usuario {current_user.id}).")
            return jsonify({"message": f"Notas AI de la visita enviadas exitosamente como imagen a {email_dest}."}), 200

        else:
            # Lógica existente para enviar el contenido de texto si no hay imagen adjunta
            trans_orig = visita.transcripcion if visita.transcripcion and not visita.transcripcion.startswith("[Error") else 'Transcripción no disponible o con errores.'
            res_orig = visita.resumen_ai if visita.resumen_ai and not visita.resumen_ai.startswith("[Error") else 'Resumen IA no disponible o con errores.'
            notas_orig = visita.notas_ai if visita.notas_ai and not visita.notas_ai.startswith("[Error") else 'Notas IA no disponibles o con errores.'
            idioma_orig_vis = normalize_language_code(visita.idioma_detectado) or 'es'
            idioma_final_email = idioma_orig_vis
            traducido = False
            trans_para_email, res_para_email, notas_para_email = trans_orig, res_orig, notas_orig

            if idioma_email_sel:
                norm_idioma_deseado = normalize_language_code(idioma_email_sel)
                if norm_idioma_deseado and norm_idioma_deseado != idioma_orig_vis:
                    logging.info(f"Traduciendo contenido de visita {visita_id} de {idioma_orig_vis} a {norm_idioma_deseado} para el email (Usuario {current_user.id}).")
                    temp_trans = _traducir_texto_interno(trans_orig, idioma_orig_vis, norm_idioma_deseado)
                    temp_res = _traducir_texto_interno(res_orig, idioma_orig_vis, norm_idioma_deseado)
                    temp_notas = _traducir_texto_interno(notas_orig, idioma_orig_vis, norm_idioma_deseado)
                    if not temp_trans.startswith("[Error"): trans_para_email = temp_trans; traducido = True
                    if not temp_res.startswith("[Error"): res_para_email = temp_res; traducido = True
                    if not temp_notas.startswith("[Error"): notas_para_email = temp_notas; traducido = True
                    if traducido: idioma_final_email = norm_idioma_deseado

            nombre_idioma_email = language_codes_to_names.get(idioma_final_email, str(idioma_final_email).upper())
            aviso_trad_html = f"<p><em>(Contenido traducido automáticamente a {nombre_idioma_email})</em></p>" if traducido and idioma_final_email != idioma_orig_vis else ""
            msg_adic_html = msg_adic_raw.replace('\n', '<br>') if msg_adic_raw else ''

            def basic_markdown_to_html(md_text):
                if not md_text or md_text.startswith("[Error"): return f"<pre>{md_text}</pre>"
                html = md_text
                html = re.sub(r'^\s*#\s*(.*?)\s*$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
                html = re.sub(r'^\s*##\s*(.*?)\s*$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
                html = re.sub(r'^\s*###\s*(.*?)\s*$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
                html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
                html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
                html_lines = []
                in_ul = False
                for line in html.splitlines():
                    if line.strip().startswith("- "):
                        if not in_ul:
                            html_lines.append("<ul>")
                        in_ul = True
                        html_lines.append(f"<li>{line.strip()[2:]}</li>")
                    else:
                        if in_ul:
                            html_lines.append("</ul>")
                            in_ul = False
                        if line.strip():
                            html_lines.append(line + "<br>")
                        else:
                            html_lines.append(line)
                if in_ul:
                    html_lines.append("</ul>")
                html = "\n".join(html_lines)
                return f"<div class='markdown-content'>{html}</div>"

            cuerpo_html = f"""
                <!DOCTYPE html><html lang="{idioma_final_email}"><head><meta charset="UTF-8"><title>{asunto_final}</title>
                <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; color: #333; }}
                .email-wrapper {{ max-width: 700px; margin: 20px auto; background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .email-header {{ background-color: #4A90E2; color: white; padding: 25px; text-align: center; border-top-left-radius: 8px; border-top-right-radius: 8px;}}
                .email-header h1 {{ margin: 0; font-size: 26px; font-weight: 500; }}
                .email-content {{ padding: 25px; }}
                .section {{ margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #eee; }}
                .section:last-child {{ border-bottom: none; }}
                .section h2 {{ font-size: 20px; color: #4A90E2; margin-top: 0; margin-bottom: 10px; font-weight: 500;}}
                .section p, .section div.markdown-content {{ font-size: 15px; line-height: 1.6; color: #555; }}
                .section pre {{ white-space: pre-wrap; background-color: #f9f9f9; padding: 12px; border-radius: 4px; border: 1px solid #eee; font-family: 'Courier New', Courier, monospace; font-size: 14px;}}
                .markdown-content h1, .markdown-content h2, .markdown-content h3 {{ color: #333; margin-top: 1em; margin-bottom: 0.5em; }}
                .markdown-content ul {{ padding-left: 25px; margin-top: 0.5em;}} .markdown-content li {{ margin-bottom: 5px; }}
                .additional-message {{ background-color: #e9f5ff; border-left: 5px solid #4A90E2; padding: 12px 15px; margin-bottom: 20px; border-radius: 4px;}}
                .language-notice {{ font-style: italic; color: #777; font-size: 0.9em; margin-bottom: 20px; text-align: center; }}
                .email-footer {{ text-align: center; padding: 20px; font-size: 13px; color: #999; background-color: #f7f7f7; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;}}
                </style>
                </head><body><div class="email-wrapper">
                <div class="email-header"><h1>Vitta Health Scribe</h1></div>
                <div class="email-content">
                {f'<div class="additional-message"><p>{msg_adic_html}</p></div>' if msg_adic_html else ''}
                <div class="section">
                <h2>Detalles de la Visita</h2>
                <p><strong>Paciente:</strong> {pac_nombre}</p>
                <p><strong>Fecha de la Visita:</strong> {fecha_vis_str}</p>
                <p><strong>Tipo de Visita:</strong> {visita.tipo_visita.replace('_',' ').capitalize() if visita.tipo_visita else 'N/E'}</p>
                <p><strong>Plantilla Usada:</strong> {visita.plantilla or 'N/E'}</p>
                </div>
                {f'<div class="language-notice"><p>El siguiente contenido está en {nombre_idioma_email}. {aviso_trad_html}</p></div>' if idioma_final_email else ''}
                <div class="section"><h2>Transcripción</h2><pre>{trans_para_email}</pre></div>
                <div class="section"><h2>Resumen IA</h2>{basic_markdown_to_html(res_para_email)}</div>
                <div class="section"><h2>Notas IA</h2>{basic_markdown_to_html(notas_para_email)}</div>
                </div>
                <div class="email-footer">Generado por Vitta Health Scribe &copy; {datetime.now().year}</div>
                </div></body></html>
                """
            msg_obj = Message(subject=asunto_final, recipients=[email_dest], html=cuerpo_html, sender=app.config['MAIL_DEFAULT_SENDER'])
            mail.send(msg_obj)

            desc_log_email = f"Información de la Visita ID {visita_id} compartida por email a {email_dest}."
            if traducido and idioma_final_email != idioma_orig_vis: desc_log_email += f" (Contenido traducido a {idioma_final_email.upper()})"
            reg_act = RegistroActividad(
                visita_id=visita.id, usuario_id=current_user.id, usuario_nombre_display=current_user.nombre,
                accion="visita_compartida", descripcion=desc_log_email
            )
            db.session.add(reg_act); db.session.commit()
            logging.info(f"Email con detalles de la visita {visita_id} enviado a {email_dest} (Usuario {current_user.id}).")
            return jsonify({"message": f"Información de la visita enviada exitosamente a {email_dest}."}), 200
    except Exception as e:
        logging.error(f"Error al intentar enviar email para visita {visita_id} (Usuario {current_user.id}): {e}", exc_info=True)
        return jsonify({"error": f"No se pudo enviar el email: {str(e)}"}), 500

@app.route('/api/receta/<int:receta_id>/compartir_email', methods=['POST'])
def compartir_receta_email(receta_id):
    data = request.get_json()
    if not data: return jsonify({"error": "No se recibió payload JSON."}), 400
    email_dest = data.get('email_destinatario')
    asunto_opc = data.get('asunto')
    msg_adic_raw = data.get('message_adicional', '')
    idioma_email_sel = data.get('idioma_email', 'es')
    if not email_dest: return jsonify({"error": "Falta email del destinatario."}), 400
    receta = db.session.query(RecetaMedica).filter_by(id=receta_id, medico_id=current_user.id).first()
    if not receta: return jsonify({"error": "Receta no encontrada o no tiene permiso para compartirla."}), 404
    if not receta.paciente_receta: return jsonify({"error": "Paciente asociado a la receta no encontrado."}), 404
    if not all([app.config.get('MAIL_SERVER'), app.config.get('MAIL_USERNAME'), app.config.get('MAIL_PASSWORD')]):
        logging.error("Configuración de correo incompleta para compartir receta.")
        return jsonify({"error": "Servicio de correo no configurado en el servidor."}), 503
    try:
        pac_nombre = receta.paciente_receta.nombre
        medico_nombre = receta.medico_emisor_receta.nombre if receta.medico_emisor_receta else "Profesional Encargado"
        fecha_em_obj = receta.fecha_emision or datetime.now(timezone.utc)
        meses_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        fecha_em_str = f"{fecha_em_obj.day} de {meses_es[fecha_em_obj.month - 1]} de {fecha_em_obj.year}" \
            if 0 <= fecha_em_obj.month -1 < 12 else fecha_em_obj.strftime('%d/%m/%Y')
        asunto_final = asunto_opc or f"Receta Médica para {pac_nombre} - Emitida el {fecha_em_obj.strftime('%d/%m/%Y')}"
        # Asumir que la receta original está en español para la lógica de traducción
        idioma_orig_receta = 'es'
        norm_idioma_deseado = normalize_language_code(idioma_email_sel) or 'es'
        traducido = False

        # Desencriptar campos si estuvieran cifrados en BD antes de traducir
        # diag_orig = desencriptar_si_necesario(receta.diagnostico_relacionado)
        diag_orig = receta.diagnostico_relacionado or "No especificado"
        diag_para_email = diag_orig
        if norm_idioma_deseado != idioma_orig_receta and diag_para_email != "No especificado" and not diag_para_email.startswith("[Error"):
            trad_diag = _traducir_texto_interno(diag_para_email, idioma_orig_receta, norm_idioma_deseado)
            if not trad_diag.startswith("[Error"):
                diag_para_email = trad_diag
                traducido = True

        # notas_orig = desencriptar_si_necesario(receta.notas_adicionales_receta)
        notas_orig = receta.notas_adicionales_receta or ""
        notas_para_email = notas_orig
        if norm_idioma_deseado != idioma_orig_receta and notas_para_email and not notas_para_email.startswith("[Error"):
            trad_notas = _traducir_texto_interno(notas_para_email, idioma_orig_receta, norm_idioma_deseado)
            if not trad_notas.startswith("[Error"):
                notas_para_email = trad_notas
                traducido = True

        # meds_json_orig = desencriptar_si_necesario(receta.medicamentos_json)
        meds_json_orig = receta.medicamentos_json or '[]'
        meds_lista_orig = json.loads(meds_json_orig)
        meds_lista_email = []
        if norm_idioma_deseado != idioma_orig_receta:
            for med_o in meds_lista_orig:
                med_t = med_o.copy()
                for campo in ['nombre', 'cantidad', 'dosis', 'frecuencia', 'duracion', 'indicaciones']:
                    if med_t.get(campo) and isinstance(med_t[campo], str) and not med_t[campo].startswith("[Error"):
                        trad_campo_med = _traducir_texto_interno(med_t[campo], idioma_orig_receta, norm_idioma_deseado)
                        if not trad_campo_med.startswith("[Error"):
                            med_t[campo] = trad_campo_med
                            if trad_campo_med != med_o.get(campo):
                                traducido = True
                meds_lista_email.append(med_t)
        else:
            meds_lista_email = meds_lista_orig

        nombre_idioma_email = language_codes_to_names.get(norm_idioma_deseado, str(norm_idioma_deseado).upper())
        aviso_trad_html = f"<p><em>(Contenido traducido automáticamente a {nombre_idioma_email})</em></p>" if traducido and norm_idioma_deseado != idioma_orig_receta else ""
        msg_adic_html = msg_adic_raw.replace('\n', '<br>') if msg_adic_raw else ''
        medicamentos_html_items = ""
        if not meds_lista_email:
            medicamentos_html_items = "<li>No se especificaron medicamentos.</li>"
        for idx, med in enumerate(meds_lista_email):
            item_html = f"<li style='margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee;'>"
            item_html += f"<h4 style='margin: 0 0 8px 0; font-size: 1.1em; color: #333; font-weight: bold;'>{idx+1}. {med.get('nombre','Nombre no especificado')}</h4>"
            if med.get('cantidad'): item_html += f"<p style='margin: 3px 0;'><strong>Cantidad:</strong> {med['cantidad']}</p>"
            if med.get('dosis'): item_html += f"<p style='margin: 3px 0;'><strong>Dosis:</strong> {med['dosis']}</p>"
            if med.get('frecuencia'): item_html += f"<p style='margin: 3px 0;'><strong>Frecuencia:</strong> {med['frecuencia']}</p>"
            if med.get('duracion'): item_html += f"<p style='margin: 3px 0;'><strong>Duración:</strong> {med['duracion']}</p>"
            if med.get('indicaciones'): item_html += f"<p style='margin: 3px 0; font-style:italic;'><strong>Indicaciones:</strong> {med['indicaciones']}</p>"
            item_html += "</li>"
            medicamentos_html_items += item_html
        cuerpo_html = f"""
<!DOCTYPE html><html lang="{norm_idioma_deseado}"><head><meta charset="UTF-8"><title>{asunto_final}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; color: #333; }}
.email-wrapper {{ max-width: 700px; margin: 20px auto; background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.email-header {{ background-color: #4A90E2; color: white; padding: 25px; text-align: center; border-top-left-radius: 8px; border-top-right-radius: 8px;}}
.email-header h1 {{ margin: 0; font-size: 26px; font-weight: 500; }}
.email-content {{ padding: 25px; }}
.section {{ margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #eee; }}
.section:last-child {{ border-bottom: none; }}
.section h2 {{ font-size: 20px; color: #4A90E2; margin-top: 0; margin-bottom: 10px; font-weight: 500;}}
.section h3 {{ font-size: 18px; color: #333; margin-top: 0; margin-bottom: 8px; font-weight: 500;}}
.section p, .section ul {{ font-size: 15px; line-height: 1.6; color: #555; }}
.section ul {{ list-style-type: none; padding-left: 0; }}
.additional-message {{ background-color: #e9f5ff; border-left: 5px solid #4A90E2; padding: 12px 15px; margin-bottom: 20px; border-radius: 4px;}}
.language-notice {{ font-style: italic; color: #777; font-size: 0.9em; margin-bottom: 20px; text-align: center; }}
.email-footer {{ text-align: center; padding: 20px; font-size: 13px; color: #999; background-color: #f7f7f7; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;}}
</style>
</head><body><div class="email-wrapper">
<div class="email-header"><h1>Receta Médica</h1></div>
<div class="email-content">
{f'<div class="additional-message"><p>{msg_adic_html}</p></div>' if msg_adic_html else ''}
<div class="section">
<h3>Información del Paciente y Prescripción</h3>
<p><strong>Paciente:</strong> {pac_nombre}</p>
<p><strong>Emitida por:</strong> Dr(a). {medico_nombre}</p>
<p><strong>Fecha de Emisión:</strong> {fecha_em_str}</p>
{f"<p><strong>Diagnóstico Relacionado:</strong> {diag_para_email}</p>" if diag_para_email != "No especificado" else ""}
{f"<p><strong>Válida por:</strong> {receta.validez_dias} días desde la emisión</p>" if receta.validez_dias else ""}
</div>
{f'<div class="language-notice"><p>El siguiente contenido está en {nombre_idioma_email}. {aviso_trad_html}</p></div>' if norm_idioma_deseado else ''}
<div class="section">
<h3>Medicamentos Prescritos</h3>
<ul>{medicamentos_html_items}</ul>
</div>
{f"<div class='section'><h3>Notas Adicionales</h3><p>{notas_para_email}</p></div>" if notas_para_email else ""}
</div>
<div class="email-footer">Esta es una receta generada digitalmente. Vitta Health Scribe &copy; {datetime.now().year}</div>
</div></body></html>"""
        msg_obj = Message(subject=asunto_final, recipients=[email_dest], html=cuerpo_html, sender=app.config['MAIL_DEFAULT_SENDER'])
        mail.send(msg_obj)
        desc_log_email = f"Receta Médica ID {receta_id} compartida por email a {email_dest}."
        if traducido and norm_idioma_deseado != idioma_orig_receta: desc_log_email += f" (Contenido traducido a {norm_idioma_deseado.upper()})"
        reg_act_data = {"usuario_id": current_user.id, "usuario_nombre_display": current_user.nombre, "accion": "receta_compartida", "descripcion": desc_log_email}
        if receta.visita_id: reg_act_data["visita_id"] = receta.visita_id
        reg_act = RegistroActividad(**reg_act_data) # type: ignore
        db.session.add(reg_act); db.session.commit()
        logging.info(f"Email con receta médica {receta_id} enviado a {email_dest} (Usuario {current_user.id}).")
        return jsonify({"message": f"Receta médica enviada exitosamente a {email_dest}."}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error al intentar enviar email para receta {receta_id} (Usuario {current_user.id}): {e}", exc_info=True)
        return jsonify({"error": f"No se pudo enviar el email de la receta: {str(e)}"}), 500

def enviar_messages_programados_worker():
    pass

@app.route('/api/plan_nutricional/<int:plan_id>/compartir_email', methods=['POST'])
def compartir_plan_nutricional_email(plan_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibió payload JSON."}), 400

    email_dest = data.get('email_destinatario')
    asunto_opc = data.get('asunto')
    msg_adic_raw = data.get('message_adicional', '')
    image_data_b64 = data.get('image_data') # <-- NUEVO: Recibimos la imagen en base64

    if not email_dest or not image_data_b64:
        return jsonify({"error": "Falta email del destinatario o los datos de la imagen."}), 400

    plan = db.session.query(PlanNutricional).options(
        joinedload(PlanNutricional.paciente_plan),
        joinedload(PlanNutricional.medico_emisor_plan)
    ).filter_by(id=plan_id, medico_id=current_user.id).first()

    if not plan:
        return jsonify({"error": "Plan nutricional no encontrado."}), 404
        
    if not all([app.config.get('MAIL_SERVER'), app.config.get('MAIL_USERNAME'), app.config.get('MAIL_PASSWORD')]):
        logging.error("Configuración de correo incompleta.")
        return jsonify({"error": "Servicio de correo no configurado en el servidor."}), 503

    try:
        paciente_obj = plan.paciente_plan
        medico_obj = plan.medico_emisor_plan
        fecha_em_obj = plan.fecha_emision or datetime.now(timezone.utc)
        fecha_em_str = fecha_em_obj.strftime('%d/%m/%Y')
        asunto_final = asunto_opc or f"Plan Nutricional Adjunto para {paciente_obj.nombre} - {fecha_em_str}"
        nombre_archivo_imagen = f"Plan_Nutricional_{paciente_obj.nombre.replace(' ', '_')}_{plan.id}.png"

        # Decodificar la imagen de base64 a bytes
        # La cabecera 'data:image/png;base64,' se elimina antes de decodificar
        image_bytes = base64.b64decode(image_data_b64.split(',')[1])

        # Crear el cuerpo del email
        msg_adic_html = f"<p><b>Mensaje adicional:</b><br>{msg_adic_raw.replace(chr(10), '<br>')}</p>" if msg_adic_raw else ''
        cuerpo_html = f"""
        <!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>{asunto_final}</title></head>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2>Plan Nutricional Adjunto</h2>
            <p>Estimado/a,</p>
            <p>Por favor, encuentre adjunto el plan nutricional para el paciente <strong>{paciente_obj.nombre}</strong>, preparado por el/la <strong>Dr(a). {medico_obj.nombre}</strong>.</p>
            {msg_adic_html}
            <p>El documento está en formato de imagen (PNG).</p><br>
            <p>Saludos cordiales,</p><p><em>Generado por Vitta Health Scribe</em></p>
        </body></html>
        """

        # Adjuntar la imagen y enviar
        msg = Message(asunto_final, recipients=[email_dest], html=cuerpo_html, sender=app.config['MAIL_DEFAULT_SENDER'])
        msg.attach(
            filename=nombre_archivo_imagen,
            content_type='image/png', # <-- Cambiado a image/png
            data=image_bytes
        )
        mail.send(msg)

        # Registrar actividad
        reg_act_data = {
            "usuario_id": current_user.id, "usuario_nombre_display": current_user.nombre,
            "accion": "plan_nutricional_compartido",
            "descripcion": f"Plan Nutricional (ID: {plan.id}) compartido como IMAGEN adjunta por email a {email_dest}."}
        if plan.visita_id:
            reg_act_data["visita_id"] = plan.visita_id
        
        reg_act = RegistroActividad(**reg_act_data)
        db.session.add(reg_act)
        db.session.commit()

        logging.info(f"Email con IMAGEN adjunta del plan nutricional {plan.id} enviado a {email_dest}.")
        return jsonify({"message": f"Plan nutricional enviado como imagen adjunta a {email_dest}."}), 200

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error al enviar email con imagen adjunta para plan {plan.id}: {str(e)}", exc_info=True)
        return jsonify({"error": f"No se pudo enviar el correo con la imagen: {str(e)}"}), 500
@app.route('/api/referencia/<int:referencia_id>/compartir_email', methods=['POST'])
def compartir_referencia_email(referencia_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibió payload JSON."}), 400

    email_dest = data.get('email_destinatario')
    asunto_opc = data.get('asunto')
    msg_adic_raw = data.get('message_adicional', '')

    if not email_dest:
        return jsonify({"error": "Falta email del destinatario."}), 400

    referencia = db.session.query(ReferenciaMedica).filter_by(id=referencia_id, medico_referente_id=current_user.id).first()
    if not referencia:
        return jsonify({"error": "Referencia no encontrada o no tiene permiso para compartirla."}), 404

    # Verificar que las dependencias y la configuración de correo existan
    if not HTML:
        logging.error("WeasyPrint no está instalado. No se puede generar el PDF para el correo.")
        return jsonify({"error": "La función para generar PDF no está disponible en el servidor."}), 500

    if not all([app.config.get('MAIL_SERVER'), app.config.get('MAIL_USERNAME'), app.config.get('MAIL_PASSWORD')]):
        logging.error("Configuración de correo incompleta en el servidor.")
        return jsonify({"error": "Servicio de correo no configurado en el servidor."}), 503

@app.route('/admin/panel-principal')
@admin_required(allowed_roles=['admin'])
def admin_dashboard():
    """
    Ruta para la página principal del panel de administración.
    Muestra métricas globales y una lista paginada de doctores y prospectos.
    """
    error = None
    try:
        # --- 1. Carga de Métricas para Widgets (Modo Demo) ---
        stats = db.session.query(EstadisticasDemo).filter_by(id=1).first()

        # --- CORRECCIÓN DE INDENTACIÓN AQUÍ ---
        # El siguiente bloque 'if/else' fue movido para estar correctamente
        # dentro del bloque 'try'.
        if stats:
            total_minutes_recorded = stats.minutos_grabados
            total_visitas_generadas = stats.visitas_generadas
            total_pacientes_creados = stats.pacientes_creados
            total_docs_created = stats.documentos_creados
            total_docs_resumidos = stats.documentos_resumidos
        else:
            # Valores por defecto si la tabla está vacía
            total_minutes_recorded, total_visitas_generadas, total_pacientes_creados, total_docs_created, total_docs_resumidos = 0, 0, 0, 0, 0
        # --- FIN DE LA CORRECCIÓN DE INDENTACIÓN ---

        # Los conteos de doctores y prospectos se pueden mantener igual
        verified_doctors_count = User.query.filter_by(role='medico', is_verified=True).count()
        unverified_doctors_count = User.query.filter_by(role='medico', is_verified=False).count()
        prospects_count = ProspectoInteres.query.count()

        # --- 2. Lógica de Búsqueda, Filtro y Unificación ---
        page = request.args.get('page', 1, type=int)
        search_query = request.args.get('search', '').strip()
        status_filter = request.args.get('status_filter', '')

        contactos_unificados = []

        # Añadir doctores a la lista
        doctors_query = User.query.filter_by(role='medico')
        for doctor in doctors_query.all():
            contactos_unificados.append({'type': 'doctor', 'data': doctor, 'date': doctor.created_at})

        # Añadir prospectos a la lista
        prospects_list = ProspectoInteres.query.all()
        for prospecto in prospects_list:
            contactos_unificados.append({'type': 'prospecto', 'data': prospecto, 'date': prospecto.fecha_registro})

        # Ordenar la lista combinada por fecha de creación (los más nuevos primero)
        contactos_unificados.sort(key=lambda x: x['date'], reverse=True)

        # Aplicar filtros de estado
        if status_filter == 'verified':
            contactos_unificados = [c for c in contactos_unificados if c['type'] == 'doctor' and c['data'].is_verified]
        elif status_filter == 'not_verified':
            contactos_unificados = [c for c in contactos_unificados if c['type'] == 'doctor' and not c['data'].is_verified]
        elif status_filter == 'prospecto':
            contactos_unificados = [c for c in contactos_unificados if c['type'] == 'prospecto']

        # Aplicar búsqueda por nombre
        if search_query:
            contactos_unificados = [
                c for c in contactos_unificados
                if search_query.lower() in f"{c['data'].nombre or ''} {getattr(c['data'], 'apellidos', '')}".lower()
            ]

        # --- 3. Paginación ---
        pagination = ListPagination(items_list=contactos_unificados, page=page, per_page=10)

    except Exception as e:
        error = f"Ocurrió un error al cargar los datos: {str(e)}"
        logging.error(f"Error en admin_dashboard: {e}", exc_info=True)
        # Inicializar variables para que la plantilla no falle
        verified_doctors_count, unverified_doctors_count, prospects_count = 0, 0, 0
        total_minutes_recorded, total_docs_created, total_pacientes_creados, total_visitas_generadas, total_docs_resumidos = 0, 0, 0, 0, 0
        pagination = None

    # --- 4. Renderizar Plantilla con Todos los Datos ---
    return render_template('admin_dashboard.html',
                           verified_doctors_count=verified_doctors_count,
                           unverified_doctors_count=unverified_doctors_count,
                           prospects_count=prospects_count,
                           total_minutes_recorded=total_minutes_recorded,
                           total_docs_created=total_docs_created,
                           total_pacientes_creados=total_pacientes_creados,
                           total_visitas_generadas=total_visitas_generadas,
                           total_docs_resumidos=total_docs_resumidos,
                           pagination=pagination,
                           error=error)

@app.route('/admin/test-emails')
@admin_required(allowed_roles=['admin'])
def admin_test_emails():
    """
    Página para que los administradores envíen correos de prueba.
    GET: Muestra la página con los botones de envío.
    POST: Envía el correo de prueba seleccionado.
    """
    if request.method == 'POST':
        # Obtener los datos comunes del formulario
        recipient_email = request.form.get('recipient_email')
        email_type = request.form.get('email_type')

        if not recipient_email:
            flash('El correo del destinatario es obligatorio.', 'danger')
            return redirect(url_for('admin_test_emails'))

        # Lógica para enviar el correo según el tipo seleccionado
        try:
            if email_type == 'welcome_doctor':
                # --- Correo de Bienvenida a Doctor ---
                # Usamos datos de ejemplo para rellenar la plantilla
                login_url = url_for('login_route', _external=True)
                current_year = datetime.now().year
                
                html_body = render_template(
                'bienvenida_doctor.html',                    nombre_doctor="Dr. De Prueba",
                    email_doctor=recipient_email,
                    temp_password="password_de_prueba_123",
                    login_url=login_url,
                    year=current_year
                )
                msg = Message(
                    subject="[PRUEBA] Bienvenido a Vitta Health Scribe",
                    recipients=[recipient_email],
                    html=html_body,
                    sender=('Vitta Health Scribe', app.config['MAIL_DEFAULT_SENDER'])
                )
                mail.send(msg)
                flash(f'Correo de bienvenida de doctor enviado a {recipient_email}.', 'success')

            elif email_type == 'interest_confirmation':
                # --- Correo de Confirmación de Interés ---
                html_body = render_template(
                    'confirmacion_interes.html', 
                    nombre="Prospecto de Prueba"
                )
                msg = Message(
                    subject="[PRUEBA] Confirmación de tu solicitud en Vitta Health",
                    recipients=[recipient_email],
                    html=html_body,
                    sender=('Vitta Health Scribe', app.config['MAIL_DEFAULT_SENDER'])
                )
                mail.send(msg)
                flash(f'Correo de confirmación de interés enviado a {recipient_email}.', 'success')
            
            else:
                flash('Tipo de correo desconocido.', 'danger')

        except Exception as e:
            logging.error(f"Error enviando correo de prueba a {recipient_email}: {e}", exc_info=True)
            flash(f'Error al enviar el correo: {e}', 'danger')

        return redirect(url_for('admin_test_emails'))

    # Para el método GET, simplemente renderiza la página
    return render_template('admin/admin_test_emails.html')
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin/prospect/<int:prospect_id>")
@admin_required(allowed_roles=['admin']) # Asegúrate de especificar el rol correcto
def admin_prospect_detail(prospect_id):
    try:
        # Se corrige la consulta para que busque en el modelo ProspectoInteres
        prospect = db.session.query(ProspectoInteres).filter_by(id=prospect_id).first()
        
        if not prospect:
            flash("Prospecto no encontrado.", "danger")
            return redirect(url_for('admin_dashboard'))
            
        # El nombre del archivo de la plantilla ya es correcto
        return render_template("admin_prospect_detail.html", prospect=prospect)
        
    except Exception as e:
        logging.exception("❌ Error al mostrar detalles del prospecto:")
        flash("Error al cargar los detalles del prospecto.", "danger")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/doctor/<int:doctor_id>', methods=['GET', 'POST'])
@admin_required(allowed_roles=['admin'])
def admin_doctor_detail(doctor_id):
    """ Muestra y actualiza la página de detalles para un doctor específico. """
    doctor = db.session.query(User).filter_by(id=doctor_id, role='medico').first_or_404()

    if request.method == 'POST':
        # Lógica para guardar cambios del formulario (sin cambios)
        doctor.nombre = request.form.get('nombre')
        doctor.identificacion = request.form.get('identificacion')
        doctor.email = request.form.get('email')
        
        prefijo = request.form.get('telefono_prefijo')
        numero = request.form.get('telefono_numero')
        doctor.telefono_profesional = f"{prefijo}{numero}" if prefijo and numero else None
        
        doctor.is_verified = 'is_verified' in request.form
        
        try:
            db.session.commit()
            flash('Perfil del doctor actualizado exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el perfil: {e}', 'danger')
            logging.error(f"Error actualizando doctor {doctor.id} desde admin: {e}")
            
        return redirect(url_for('admin_doctor_detail', doctor_id=doctor.id))

    # --- LÓGICA MODIFICADA PARA MOSTRAR DATOS DE DEMO O REALES ---
    if doctor.nombre in DEMO_STATS_PROFESIONALES:
        # Si el doctor está en el diccionario de la demo, usa los datos fijos
        stats = DEMO_STATS_PROFESIONALES[doctor.nombre]
        patients_count = stats["pacientes"]
        visits_count = stats["visitas"]
        docs_resumidos_count = stats["resumidos"]
        minutes_recorded = stats["minutos"]
        documents_created_count = stats["docs_creados"]
        
    else:
        # Si no es un doctor de la demo, calcula los datos reales
        patients_count = Paciente.query.filter_by(creado_por_id=doctor.id).count()
        visits_count = Visita.query.filter_by(medico_id=doctor.id).count()
        docs_resumidos_count = Visita.query.filter_by(medico_id=doctor.id, tipo_visita='resumen_documentos').count()
        
        total_seconds = db.session.query(db.func.sum(Visita.duracion_grabacion_segundos)).filter_by(medico_id=doctor.id).scalar() or 0
        minutes_recorded = round(total_seconds / 60)
        
        recetas_count = RecetaMedica.query.filter_by(medico_id=doctor.id).count()
        referencias_count = ReferenciaMedica.query.filter_by(medico_referente_id=doctor.id).count()
        planes_count = PlanNutricional.query.filter_by(medico_id=doctor.id).count()
        documents_created_count = recetas_count + referencias_count + planes_count

    doctor_metrics = {
        'patients_count': patients_count,
        'visits_count': visits_count,
        'minutes_recorded': minutes_recorded,
        'documents_created_count': documents_created_count,
        'docs_resumidos_count': docs_resumidos_count
    }    
    return render_template('admin_doctor_detail.html', 
                           doctor=doctor, 
                           doctor_metrics=doctor_metrics)
                           # Se ha eliminado 'recent_activity' de aquí
@app.route('/admin/doctor/<int:doctor_id>/verify', methods=['POST'])
@admin_required(allowed_roles=['admin'])
def admin_verify_doctor(doctor_id):
    """ Verifica la cuenta de un doctor. """
    doctor = db.session.query(User).filter_by(id=doctor_id, role='medico').first_or_404()
    doctor.is_verified = not doctor.is_verified # Cambia el estado (Verificar/Desverificar)
    db.session.commit()
    
    status = "verificado" if doctor.is_verified else "puesto en no verificado"
    flash(f'El doctor {doctor.nombre} ha sido {status}.', 'success')
    return redirect(url_for('admin_doctor_detail_route', doctor_id=doctor.id))

@app.route('/admin/doctor/<int:doctor_id>/delete', methods=['POST'])
@admin_required(allowed_roles=['admin'])
def admin_delete_doctor(doctor_id):
    """ Elimina la cuenta de un doctor. """
    doctor = db.session.query(User).filter_by(id=doctor_id, role='medico').first_or_404()
    doctor_name = doctor.nombre
    
    # Opcional: Eliminar datos asociados si es necesario (pacientes, visitas, etc.)
    # Esta es una acción destructiva, úsala con cuidado.
    # Paciente.query.filter_by(creado_por_id=doctor.id).delete()
    
    db.session.delete(doctor)
    db.session.commit()
    
    flash(f'El doctor {doctor_name} y sus datos han sido eliminados permanentemente.', 'success')
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/prospect/<int:prospect_id>/convert', methods=['POST'])
@admin_required(allowed_roles=['admin'])
def admin_convert_prospect(prospect_id):
    """
    Convierte un prospecto en una cuenta de doctor verificada.
    """
    prospect = db.session.query(ProspectoInteres).filter_by(id=prospect_id).first()
    if not prospect:
        flash("Prospecto no encontrado.", "danger")
        return redirect(url_for('admin_dashboard'))

    # 1. Verificar si ya existe un doctor con ese email
    existing_user = User.query.filter_by(email=prospect.email).first()
    if existing_user:
        flash(f"Ya existe un usuario con el correo electrónico {prospect.email}. No se puede convertir el prospecto.", "warning")
        return redirect(url_for('admin_prospect_detail', prospect_id=prospect.id))

    try:
        # 2. Generar una contraseña temporal segura
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(12))

        # 3. Crear el nuevo usuario (doctor) con los datos del prospecto
        new_doctor = User(
            nombre=f"{prospect.nombre} {prospect.apellidos}".strip(),
            email=prospect.email,
            role='medico',
            is_verified=True,  # Se crea como verificado
            especialidad=prospect.especialidad,
            licencia_profesional=prospect.carne_medico,
            identificacion=prospect.identificacion,
            telefono_profesional=prospect.telefono,
            lugar_trabajo=prospect.lugar_trabajo
        )
        new_doctor.set_password(temp_password)

        db.session.add(new_doctor)
        
        # 4. (Opcional) Eliminar el prospecto original después de la conversión
        db.session.delete(prospect)
        
        db.session.commit()

        # 5. (Opcional pero recomendado) Enviar un correo de bienvenida al nuevo doctor
        try:
            # Renderizar la plantilla del correo de bienvenida
            html_body = render_template(
                'bienvenida_doctor.html', # Necesitarás crear esta plantilla de correo
                nombre_doctor=new_doctor.nombre,
                email_doctor=new_doctor.email,
                temp_password=temp_password,
                login_url=url_for('login_route', _external=True),
                year=datetime.now().year
            )
            
            msg = Message(
                subject="¡Bienvenido a Vitta Health Scribe! Tu cuenta ha sido creada.",
                sender=('Vitta Health Scribe', app.config['MAIL_DEFAULT_SENDER']),
                recipients=[new_doctor.email],
                html=html_body
            )
            mail.send(msg)
            logging.info(f"Correo de bienvenida enviado al nuevo doctor: {new_doctor.email}")
            flash(f"¡Doctor '{new_doctor.nombre}' creado exitosamente! Se ha enviado un correo de bienvenida con una contraseña temporal.", "success")
        except Exception as e_mail:
            logging.error(f"FALLO al enviar el correo de bienvenida para {new_doctor.email}: {e_mail}", exc_info=True)
            flash("Doctor creado exitosamente, pero falló el envío del correo de bienvenida.", "warning")

        # 6. Redirigir a la página de detalles del nuevo doctor
        return redirect(url_for('admin_doctor_detail', doctor_id=new_doctor.id))

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error al convertir el prospecto ID {prospect_id} a doctor: {e}", exc_info=True)
        flash("Ocurrió un error inesperado durante la conversión del prospecto.", "danger")
        return redirect(url_for('admin_prospect_detail', prospect_id=prospect_id))
@app.route('/admin/prospect/<int:prospect_id>/delete', methods=['POST'])
@admin_required(allowed_roles=['admin'])
def admin_delete_prospect(prospect_id):
    """
    Elimina un prospecto de interés de la base de datos.
    """
    try:
        # Busca el prospecto en la base de datos
        prospect = db.session.query(ProspectoInteres).filter_by(id=prospect_id).first()

        if not prospect:
            flash("Prospecto no encontrado para eliminar.", "danger")
            return redirect(url_for('admin_dashboard'))

        prospect_name = prospect.nombre
        
        # Elimina el registro del prospecto
        db.session.delete(prospect)
        db.session.commit()

        flash(f"El prospecto '{prospect_name}' ha sido eliminado exitosamente.", "success")
        logging.info(f"Prospecto ID {prospect_id} ({prospect_name}) eliminado por el admin {current_user.email}.")

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error al eliminar el prospecto ID {prospect_id}: {e}", exc_info=True)
        flash("Ocurrió un error al eliminar el prospecto.", "danger")

    return redirect(url_for('admin_dashboard'))

@app.route("/vitta-health-pitch.html")
def pitch_deck_route():
    return render_template("vitta-health-pitch.html")

@app.route("/vitta-health-pitch-investors.html")
def investors_pitch_deck_route():
    return render_template("vitta-health-pitch-investors.html")
