import os

def get_database_uri():
    # Detecta si estás en producción (Cloud Run, App Engine, etc.)
    IS_PRODUCTION = os.environ.get("GAE_ENV", "") == "standard" or os.environ.get("K_SERVICE") is not None

    DB_USER = os.environ.get("DB_USER")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    DB_NAME = os.environ.get("DB_NAME")
    DB_HOST = os.environ.get("DB_HOST")
    DB_PORT = os.environ.get("DB_PORT", "5432")

    # Si tienes todos los datos, conecta a PostgreSQL (Cloud SQL)
    if all([DB_USER, DB_PASSWORD, DB_NAME, DB_HOST]):
        # Host suele ser "/cloudsql/INSTANCIA" en Cloud Run/GAE
        return f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?host={DB_HOST}&port={DB_PORT}"

    # En producción: NO permitas SQLite
    if IS_PRODUCTION:
        raise RuntimeError(
            "No se encontraron todas las variables de entorno requeridas para PostgreSQL (DB_USER, DB_PASSWORD, DB_NAME, DB_HOST, DB_PORT). "
            "Verifica tu configuración de Secret Manager y variables de entorno."
        )

    # En desarrollo: sí permite SQLite como fallback
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLITE_PATH = os.path.join(BASE_DIR, "instance", "local_database.db")
    return f"sqlite:///{SQLITE_PATH}"

SQLALCHEMY_DATABASE_URI = get_database_uri()
SQLALCHEMY_TRACK_MODIFICATIONS = False


