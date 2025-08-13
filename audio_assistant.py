#!/usr/bin/env python3
"""
🎤 SERVIDOR DE AUDIO PARA TU ASISTENTE INTELIGENTE
==================================================

Este servidor permite interactuar con tu asistente mediante:
- 🎤 Entrada de audio (micrófono)
- 🔊 Salida de audio (texto a voz)
- 💬 Procesamiento en tiempo real
- 🧠 Integración con tu API de 405 acciones

Requisitos:
- pip install speechrecognition pyttsx3 pyaudio
- Micrófono y altavoces/audífonos

Uso:
- python audio_assistant.py
- Habla cuando aparezca "🎤 Habla ahora..."
- Di "salir" o "terminar" para cerrar
"""

import speech_recognition as sr
import pyttsx3
import requests
import json
import time
import threading
from datetime import datetime
import sys
import os

class AudioAssistant:
    def __init__(self, api_base_url="http://localhost:8000"):
        """Inicializar el asistente de audio"""
        self.api_base_url = api_base_url
        self.session_id = None
        self.user_id = f"audio_user_{int(time.time())}"
        
        # Configurar reconocimiento de voz
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Configurar síntesis de voz
        self.tts_engine = pyttsx3.init()
        self.setup_voice()
        
        # Variables de control
        self.running = True
        self.listening = False
        
        print("🤖 Inicializando Asistente de Audio...")
        self.calibrate_microphone()
        self.test_api_connection()
        self.start_session()

    def setup_voice(self):
        """Configurar la voz del asistente"""
        voices = self.tts_engine.getProperty('voices')
        
        # Buscar voz en español si está disponible
        spanish_voice = None
        for voice in voices:
            if 'spanish' in voice.name.lower() or 'es' in voice.id.lower():
                spanish_voice = voice
                break
        
        if spanish_voice:
            self.tts_engine.setProperty('voice', spanish_voice.id)
            print(f"✅ Voz configurada: {spanish_voice.name}")
        else:
            print("⚠️ Voz en español no encontrada, usando voz por defecto")
        
        # Configurar velocidad y volumen
        self.tts_engine.setProperty('rate', 180)  # Velocidad
        self.tts_engine.setProperty('volume', 0.9)  # Volumen

    def calibrate_microphone(self):
        """Calibrar el micrófono para el ruido ambiente"""
        print("🔧 Calibrando micrófono...")
        with self.microphone as source:
            print("   Ajustando para ruido ambiente... (silencio por favor)")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        print("✅ Micrófono calibrado")

    def test_api_connection(self):
        """Probar conexión con la API"""
        try:
            response = requests.get(f"{self.api_base_url}/api/v1/health", timeout=5)
            if response.status_code == 200:
                print("✅ Conexión con API establecida")
                return True
            else:
                print(f"⚠️ API respondió con código: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Error conectando con API: {e}")
            print("💡 Asegúrate de que tu servidor esté ejecutándose en:", self.api_base_url)
            return False

    def start_session(self):
        """Iniciar sesión con el asistente inteligente"""
        try:
            response = requests.post(
                f"{self.api_base_url}/api/v1/intelligent-assistant/session/start",
                json={
                    "user_id": self.user_id,
                    "context": "Interfaz de audio"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get('session_id')
                print(f"✅ Sesión iniciada: {self.session_id}")
                return True
            else:
                print(f"⚠️ Error iniciando sesión: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error iniciando sesión: {e}")
            return False

    def speak(self, text):
        """Convertir texto a voz"""
        print(f"🤖 Asistente: {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def listen(self):
        """Escuchar y reconocer audio del micrófono"""
        try:
            with self.microphone as source:
                print("🎤 Habla ahora... (di 'salir' para terminar)")
                self.listening = True
                
                # Escuchar con timeout
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=10)
                self.listening = False
                
                print("🔄 Procesando audio...")
                
                # Reconocer audio
                text = self.recognizer.recognize_google(audio, language='es-ES')
                print(f"👤 Tú dijiste: {text}")
                return text
                
        except sr.WaitTimeoutError:
            print("⏰ Tiempo de espera agotado")
            return None
        except sr.UnknownValueError:
            print("❌ No se pudo entender el audio")
            return None
        except sr.RequestError as e:
            print(f"❌ Error del servicio de reconocimiento: {e}")
            return None
        finally:
            self.listening = False

    def send_message_to_api(self, message):
        """Enviar mensaje al asistente inteligente"""
        try:
            response = requests.post(
                f"{self.api_base_url}/api/v1/intelligent-assistant/chat",
                json={
                    "message": message,
                    "user_id": self.user_id,
                    "session_id": self.session_id
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"❌ Error de API: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error enviando mensaje: {e}")
            return None

    def process_response(self, response_data):
        """Procesar respuesta del asistente"""
        if not response_data:
            self.speak("Lo siento, hubo un error procesando tu solicitud.")
            return
        
        # Respuesta principal
        main_response = response_data.get('response', 'No obtuve respuesta del servidor.')
        self.speak(main_response)
        
        # Información adicional
        if response_data.get('action_executed'):
            action_msg = f"He ejecutado la acción: {response_data['action_executed']}"
            print(f"✅ {action_msg}")
        
        if response_data.get('suggestions'):
            suggestions = response_data['suggestions']
            if len(suggestions) > 0:
                suggestions_text = "También puedes preguntarme: " + ", ".join(suggestions[:2])
                print(f"💡 {suggestions_text}")

    def run(self):
        """Ejecutar el asistente de audio"""
        print("\n" + "="*60)
        print("🎤 ASISTENTE DE AUDIO INICIADO")
        print("="*60)
        print("💬 Comandos disponibles:")
        print("   • Habla naturalmente para hacer solicitudes")
        print("   • Di 'salir', 'terminar' o 'adiós' para cerrar")
        print("   • Presiona Ctrl+C para forzar salida")
        print("="*60)
        
        # Mensaje de bienvenida
        welcome_msg = "¡Hola! Soy tu asistente inteligente con acceso a 405 acciones. ¿En qué puedo ayudarte hoy?"
        self.speak(welcome_msg)
        
        while self.running:
            try:
                # Escuchar comando de voz
                user_input = self.listen()
                
                if user_input is None:
                    continue
                
                # Verificar comandos de salida
                exit_commands = ['salir', 'terminar', 'adiós', 'chao', 'hasta luego', 'exit']
                if any(cmd in user_input.lower() for cmd in exit_commands):
                    self.speak("¡Hasta luego! Que tengas un excelente día.")
                    break
                
                # Enviar mensaje al asistente
                print("🧠 Consultando con el asistente inteligente...")
                response = self.send_message_to_api(user_input)
                
                # Procesar y responder
                self.process_response(response)
                
                print("\n" + "-"*40)
                
            except KeyboardInterrupt:
                print("\n🛑 Interrupción recibida")
                break
            except Exception as e:
                print(f"❌ Error inesperado: {e}")
                self.speak("Ha ocurrido un error. Intentemos de nuevo.")
        
        print("👋 Asistente de audio cerrado")

def main():
    """Función principal"""
    print("🚀 INICIANDO ASISTENTE DE AUDIO")
    print("=" * 50)
    
    # Verificar dependencias
    try:
        import speech_recognition
        import pyttsx3
        print("✅ Dependencias de audio instaladas")
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        print("💡 Instala con: pip install speechrecognition pyttsx3 pyaudio")
        return
    
    # Verificar argumentos de línea de comandos
    api_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    
    print(f"🌐 URL de API: {api_url}")
    
    try:
        # Crear y ejecutar asistente
        assistant = AudioAssistant(api_base_url=api_url)
        assistant.run()
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        print("💡 Asegúrate de tener micrófono y altavoces conectados")

if __name__ == "__main__":
    main()
