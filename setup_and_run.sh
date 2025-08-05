#!/bin/bash

# Detener el script si algún comando falla
set -e

echo "📦 Iniciando configuración del entorno de construcción..."

# No es necesario crear un entorno virtual manualmente en DigitalOcean App Platform,
# ya que el entorno de construcción se gestiona automáticamente y pip está disponible.
# Estos pasos son más para desarrollo local.
# Sin embargo, si tu Dockerfile o tu App Spec requiere un venv, déjalos.
# Para la mayoría de los casos de App Platform, basta con instalar directamente.

# Si usas un Dockerfile, la configuración del venv y la instalación de pip
# deberían estar en el Dockerfile, no aquí.
# Si no usas Dockerfile y confías en la detección automática de DO:
# `pip install -r requirements.txt` es el comando clave.

echo "⬆️ Asegurando que pip esté actualizado para la construcción..."
# Ejecutar pip directamente para el entorno de construcción de DO
pip install --upgrade pip

# Instalar dependencias desde requirements.txt
if [ -f "requirements.txt" ]; then
    echo "⬇️ Instalando dependencias desde requirements.txt..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Error: Fallo al instalar dependencias desde requirements.txt."
        exit 1
    fi
else
    echo "⚠️ Advertencia: No se encontró el archivo 'requirements.txt'."
    echo "Asegúrate de tener un archivo 'requirements.txt' con todas las dependencias del proyecto."
    exit 1 # Es un error crítico si no hay requirements.txt en un despliegue.
fi

# Verificar la instalación de un paquete clave
KEY_PACKAGE="Flask-SocketIO"
echo "🔎 Verificando instalación de '$KEY_PACKAGE'..."
if pip show "$KEY_PACKAGE" > /dev/null 2>&1; then
    echo "✅ $KEY_PACKAGE está instalado."
else
    echo "❌ Error: $KEY_PACKAGE no parece estar instalado correctamente. Fallo en la construcción."
    exit 1
fi

echo "✅ Configuración del entorno de construcción completada."

# ESTE SCRIPT NO DEBE LANZAR LA APLICACIÓN.
# El comando de inicio (`gunicorn app:app`) debe estar en `start.sh`
# o directamente en la configuración de "Run Command" de DigitalOcean App Platform.
