#!/bin/bash

# 🚀 SCRIPT DE INSTALACIÓN Y PRUEBA DE INTERFACES
# ==============================================

echo "🎤 CONFIGURANDO ASISTENTE CON AUDIO E INTERFAZ WEB"
echo "=================================================="

# Función para verificar si un comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verificar Python
if ! command_exists python3; then
    echo "❌ Python3 no está instalado"
    exit 1
fi

echo "✅ Python3 encontrado: $(python3 --version)"

# Instalar dependencias de audio
echo "📦 Instalando dependencias de audio..."
pip3 install speechrecognition pyttsx3 pyaudio

# Para macOS, puede requerir instalación adicional
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Detectado macOS - Instalando dependencias adicionales..."
    
    # Verificar si brew está instalado
    if command_exists brew; then
        echo "🍺 Instalando portaudio con Homebrew..."
        brew install portaudio
    else
        echo "⚠️ Homebrew no encontrado. Puede que necesites instalar portaudio manualmente"
        echo "💡 Instala Homebrew desde: https://brew.sh"
    fi
fi

echo ""
echo "🌐 INSTRUCCIONES DE USO:"
echo "========================"

echo ""
echo "1️⃣ INTERFAZ WEB CON AUDIO:"
echo "   • Inicia tu servidor: python -m uvicorn app.main:app --reload"
echo "   • Abre tu navegador en: http://localhost:8000/chat"
echo "   • ✅ Chat por texto"
echo "   • 🎤 Entrada de voz (botón micrófono)"
echo "   • 🔊 Respuesta por voz automática"

echo ""
echo "2️⃣ ASISTENTE DE AUDIO PURO:"
echo "   • python audio_assistant.py"
echo "   • ✅ Solo comandos de voz"
echo "   • 🎤 Habla → 🧠 IA → 🔊 Respuesta"
echo "   • Di 'salir' para terminar"

echo ""
echo "3️⃣ VERIFICAR INSTALACIÓN:"
echo "   • python -c \"import speech_recognition; import pyttsx3; print('✅ Audio libs OK')\""

echo ""
echo "🎯 FUNCIONALIDADES:"
echo "==================="
echo "✅ Tu asistente con 405 acciones"
echo "✅ Reconocimiento de voz en español"
echo "✅ Síntesis de voz en español"
echo "✅ Memoria conversacional"
echo "✅ Aprendizaje continuo"
echo "✅ Interfaz web responsive"
echo "✅ Integración completa con tu API"

echo ""
echo "⚠️ SOLUCIÓN DE PROBLEMAS:"
echo "========================="
echo "• Micrófono no funciona → Verificar permisos del navegador"
echo "• PyAudio error → brew install portaudio (macOS)"
echo "• Voz no se escucha → Verificar volumen del sistema"
echo "• API no responde → Verificar que el servidor esté ejecutándose"

echo ""
echo "🎉 ¡INSTALACIÓN COMPLETADA!"
echo "============================"
echo "Ahora puedes usar tu asistente inteligente con:"
echo "💬 Texto → http://localhost:8000/chat"
echo "🎤 Audio → python audio_assistant.py"
