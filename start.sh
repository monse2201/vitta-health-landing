#!/bin/sh

set -e

echo "--- Esperando a que postgres-db esté disponible en el puerto 5432 ---"
/usr/local/bin/wait-for-it.sh postgres-db:5432 --timeout=60 -- echo "postgres-db está listo para recibir conexiones!"

echo "--- Inicializando la base de datos (se maneja al importar la aplicación) ---"

echo "--- Iniciando el servidor Gunicorn ---"
exec gunicorn app:app --bind 0.0.0.0:5001 --worker-class eventlet --log-level info