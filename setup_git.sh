#!/bin/bash
# Script para configurar repositorio Git y conectarlo con GitHub

echo "🚀 Iniciando configuración de Git para el proyecto..."

# Paso 1: Inicializar repositorio Git si no existe
if [ ! -d .git ]; then
  echo "📁 Inicializando repositorio Git..."
  git init
  echo "✅ Repositorio Git inicializado"
else
  echo "✅ Repositorio Git ya existe"
fi

# Paso 2: Configurar el repositorio remoto
echo "🔗 Configurando conexión con GitHub..."
git remote remove origin 2>/dev/null # Eliminar si existe
git remote add origin https://github.com/arley101/webapi.git
echo "✅ Repositorio remoto configurado: https://github.com/arley101/webapi.git"

# Paso 3: Crear nueva rama para cambios de YouTube
echo "🌿 Creando nueva rama para cambios de YouTube..."
git checkout -b feature-youtube
echo "✅ Rama 'feature-youtube' creada y seleccionada"

# Paso 4: Añadir archivos al seguimiento de Git
echo "📝 Añadiendo archivos al seguimiento de Git..."
git add app/actions/youtube_channel_actions.py app/actions/hubspot_actions.py app/core/auth_manager.py tools/check_actions.py
echo "✅ Archivos añadidos al seguimiento"

echo ""
echo "==============================================================="
echo "🎉 CONFIGURACIÓN COMPLETA"
echo "==============================================================="
echo ""
echo "Para continuar con tus cambios, usa estos comandos:"
echo ""
echo "  1. Hacer commit de tus cambios:"
echo "     git commit -m \"Mejoras en la integración con YouTube\""
echo ""
echo "  2. Subir la rama a GitHub:"
echo "     git push -u origin feature-youtube"
echo ""
echo "  3. Luego podrás crear un Pull Request en GitHub"
echo "     Visita: https://github.com/arley101/webapi/pull/new/feature-youtube"
echo ""
echo "==============================================================="
