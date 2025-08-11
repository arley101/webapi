#!/bin/bash
# Script para hacer un respaldo completo del proyecto

# Configuración
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/Users/arleygalan/Downloads/EliteDynamicsAPI_backup_${TIMESTAMP}"
PROJECT_DIR="/Users/arleygalan/Downloads/output (desplegado)"

# Crear directorio de respaldo
mkdir -p "$BACKUP_DIR"
echo "📂 Creando respaldo completo en: $BACKUP_DIR"

# Copiar todo el proyecto (excepto entorno virtual y archivos temporales)
echo "🔄 Copiando archivos del proyecto..."
rsync -av --progress "$PROJECT_DIR/" "$BACKUP_DIR/" \
  --exclude "antenv" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude ".git" \
  --exclude "*.log" \
  --exclude "node_modules"

# Crear archivo de manifiesto con estructura de directorios
echo "📋 Generando manifiesto de archivos..."
find "$BACKUP_DIR" -type f | sort > "$BACKUP_DIR/file_manifest.txt"

# Generar archivo de requisitos actualizado
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
  cp "$PROJECT_DIR/requirements.txt" "$BACKUP_DIR/requirements.txt"
  echo "📦 Archivo requirements.txt copiado"
else
  echo "⚠️ No se encontró requirements.txt en el proyecto original"
fi

# Copiar archivo .env si existe (contiene configuraciones)
if [ -f "$PROJECT_DIR/.env" ]; then
  cp "$PROJECT_DIR/.env" "$BACKUP_DIR/.env"
  echo "🔑 Archivo .env copiado"
else
  echo "⚠️ No se encontró archivo .env en el proyecto original"
fi

# Comprimir el respaldo
echo "🗜️ Comprimiendo respaldo..."
cd "$(dirname "$BACKUP_DIR")"
zip -r "EliteDynamicsAPI_backup_${TIMESTAMP}.zip" "EliteDynamicsAPI_backup_${TIMESTAMP}"

echo "✅ Respaldo completo creado en:"
echo "📁 Directorio: $BACKUP_DIR"
echo "📦 Archivo ZIP: $(dirname "$BACKUP_DIR")/EliteDynamicsAPI_backup_${TIMESTAMP}.zip"
