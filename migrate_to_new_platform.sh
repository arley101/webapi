#!/bin/bash
# Script para migrar el proyecto a una nueva plataforma

# Configuración
SOURCE_DIR="/Users/arleygalan/Downloads/output (desplegado)"
DEST_DIR="/ruta/a/nueva/plataforma"  # Actualiza esta ruta
GIT_REPO="https://github.com/arley101/webapi.git"

# Colores para mensajes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir pasos
print_step() {
  echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Función para verificar errores
check_error() {
  if [ $? -ne 0 ]; then
    echo -e "${RED}Error: $1${NC}"
    exit 1
  fi
}

# Iniciar migración
echo -e "${GREEN}=== INICIANDO MIGRACIÓN DEL PROYECTO ===${NC}"
echo "Origen: $SOURCE_DIR"
echo "Destino: $DEST_DIR"

# Paso 1: Crear directorio destino si no existe
print_step "1. Preparando directorio destino"
mkdir -p "$DEST_DIR"
check_error "No se pudo crear el directorio destino"

# Paso 2: Inicializar repositorio Git en destino (si corresponde)
print_step "2. Configurando repositorio Git"
cd "$DEST_DIR"

if [ -n "$GIT_REPO" ]; then
  echo "Clonando repositorio: $GIT_REPO"
  git clone "$GIT_REPO" .
  check_error "No se pudo clonar el repositorio"
else
  echo "Inicializando nuevo repositorio Git"
  git init
  check_error "No se pudo inicializar Git"
fi

# Paso 3: Copiar archivos del proyecto
print_step "3. Copiando archivos del proyecto"
rsync -av --progress "$SOURCE_DIR/" "$DEST_DIR/" \
  --exclude "antenv" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude ".git" \
  --exclude "*.log"
check_error "Error al copiar archivos"

# Paso 4: Configurar entorno virtual
print_step "4. Configurando entorno virtual"
cd "$DEST_DIR"
python -m venv venv
check_error "No se pudo crear el entorno virtual"

source venv/bin/activate
check_error "No se pudo activar el entorno virtual"

pip install --upgrade pip
pip install -r requirements.txt
check_error "Error instalando dependencias"

# Paso 5: Configurar variables de entorno
print_step "5. Configurando variables de entorno"
if [ -f "$SOURCE_DIR/.env" ]; then
  cp "$SOURCE_DIR/.env" "$DEST_DIR/.env"
  echo -e "${GREEN}Archivo .env copiado${NC}"
else
  echo -e "${YELLOW}No se encontró archivo .env en origen. Crea uno manualmente.${NC}"
  touch "$DEST_DIR/.env"
fi

# Paso 6: Probar instalación
print_step "6. Verificando instalación"
echo "Ejecutando prueba básica..."
cd "$DEST_DIR"
python -c "import sys; sys.path.insert(0, '.'); from app.core.config import settings; print(f'Configuración cargada para {settings.APP_NAME} v{settings.APP_VERSION}')"
check_error "Error en prueba básica"

# Paso 7: Resumen final
print_step "7. Migración completada"
echo -e "${GREEN}✅ Proyecto migrado exitosamente a:${NC} $DEST_DIR"
echo ""
echo -e "${YELLOW}Próximos pasos:${NC}"
echo "1. Verifica y actualiza las variables de entorno en .env"
echo "2. Configura los secretos/credenciales en la nueva plataforma"
echo "3. Ejecuta tests para verificar funcionalidad"
echo "4. Configura servicios externos (base de datos, storage, etc.)"
echo ""
echo -e "${BLUE}Para iniciar el servidor:${NC}"
echo "cd $DEST_DIR"
echo "source venv/bin/activate"
echo "python -m app.main"
