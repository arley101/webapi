"""
📱 INTEGRACIÓN CON WHATSAPP BUSINESS
===================================

Este módulo permite conectar tu asistente inteligente con WhatsApp Business.
Los usuarios podrán chatear con tu asistente directamente desde WhatsApp.

Características:
- WhatsApp Business API integration
- Mensajes de texto y audio
- Respuestas automáticas inteligentes
- Acceso a las 405 acciones
- Soporte multimedia (imágenes, documentos)

Setup:
1. WhatsApp Business Account
2. Meta for Developers webhook
3. Conectar con tu API existente
"""

from flask import Flask, request, jsonify
import requests
import json
import os
import asyncio
import aiohttp
from datetime import datetime

class WhatsAppAssistant:
    """Integración de WhatsApp con tu asistente inteligente"""
    
    def __init__(self):
        self.api_base_url = os.getenv('YOUR_API_URL', 'https://tu-app.azurewebsites.net')
        self.whatsapp_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.whatsapp_phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN', 'tu_token_verificacion')
        self.session_storage = {}  # En producción usar base de datos

    def verify_webhook(self, verify_token, challenge):
        """Verificar webhook de WhatsApp"""
        if verify_token == self.verify_token:
            return challenge
        return None

    async def handle_message(self, message_data):
        """Manejar mensaje recibido de WhatsApp"""
        try:
            # Extraer información del mensaje
            from_number = message_data['from']
            message_text = message_data.get('text', {}).get('body', '')
            message_type = message_data.get('type', 'text')
            
            if not message_text and message_type == 'audio':
                # Manejar mensaje de audio
                return await self.handle_audio_message(message_data, from_number)
            
            if message_text:
                # Procesar mensaje de texto
                response = await self.process_with_assistant(message_text, from_number)
                await self.send_whatsapp_message(from_number, response)
                
        except Exception as e:
            print(f"Error handling WhatsApp message: {e}")
            await self.send_whatsapp_message(
                from_number, 
                "❌ Lo siento, hubo un error procesando tu mensaje."
            )

    async def handle_audio_message(self, message_data, from_number):
        """Manejar mensaje de audio de WhatsApp"""
        # Implementar transcripción de audio
        # Por ahora, respuesta automática
        await self.send_whatsapp_message(
            from_number,
            "🎤 He recibido tu mensaje de audio. Pronto podré procesarlo. Por ahora, envíame un mensaje de texto."
        )

    async def process_with_assistant(self, message: str, user_id: str):
        """Procesar mensaje con el asistente inteligente"""
        try:
            # Iniciar sesión si no existe
            if user_id not in self.session_storage:
                session_id = await self.start_assistant_session(user_id)
                self.session_storage[user_id] = session_id
            
            # Enviar al asistente
            async with aiohttp.ClientSession() as session:
                payload = {
                    "message": message,
                    "user_id": f"whatsapp_{user_id}",
                    "session_id": self.session_storage[user_id]
                }
                
                async with session.post(
                    f"{self.api_base_url}/api/v1/intelligent-assistant/chat",
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Formatear respuesta para WhatsApp
                        full_response = data['response']
                        
                        if data.get('action_executed'):
                            full_response += f"\n\n✅ Acción completada: {data['action_executed']}"
                        
                        if data.get('suggestions') and len(data['suggestions']) > 0:
                            suggestions = "\n".join(data['suggestions'][:2])
                            full_response += f"\n\n💡 También puedes:\n{suggestions}"
                        
                        return full_response
                    else:
                        return "❌ No pude procesar tu solicitud en este momento."
                        
        except Exception as e:
            print(f"Error processing with assistant: {e}")
            return "❌ Error interno del servidor."

    async def start_assistant_session(self, user_id: str):
        """Iniciar sesión con el asistente"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "user_id": f"whatsapp_{user_id}",
                    "context": "WhatsApp Business integration"
                }
                
                async with session.post(
                    f"{self.api_base_url}/api/v1/intelligent-assistant/session/start",
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('session_id')
                    return None
        except Exception as e:
            print(f"Error starting session: {e}")
            return None

    async def send_whatsapp_message(self, to_number: str, message: str):
        """Enviar mensaje a WhatsApp"""
        try:
            url = f"https://graph.facebook.com/v17.0/{self.whatsapp_phone_id}/messages"
            
            headers = {
                'Authorization': f'Bearer {self.whatsapp_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {"body": message}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        print(f"Message sent to {to_number}")
                    else:
                        print(f"Failed to send message: {response.status}")
                        
        except Exception as e:
            print(f"Error sending WhatsApp message: {e}")

    def send_template_message(self, to_number: str, template_name: str, language="es"):
        """Enviar mensaje con plantilla de WhatsApp"""
        url = f"https://graph.facebook.com/v17.0/{self.whatsapp_phone_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {self.whatsapp_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language}
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200


# Flask app para webhook
app = Flask(__name__)
whatsapp_assistant = WhatsAppAssistant()

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verificación de webhook
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        verified_challenge = whatsapp_assistant.verify_webhook(verify_token, challenge)
        if verified_challenge:
            return verified_challenge
        return 'Forbidden', 403
    
    elif request.method == 'POST':
        # Manejar mensaje entrante
        data = request.get_json()
        
        if data.get('object') == 'whatsapp_business_account':
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        messages = change.get('value', {}).get('messages', [])
                        for message in messages:
                            # Procesar mensaje de forma asíncrona
                            asyncio.create_task(whatsapp_assistant.handle_message(message))
        
        return 'OK', 200

@app.route('/send-template', methods=['POST'])
def send_template():
    """Endpoint para enviar plantillas de WhatsApp"""
    data = request.get_json()
    
    result = whatsapp_assistant.send_template_message(
        data['to_number'],
        data['template_name'],
        data.get('language', 'es')
    )
    
    return jsonify({'success': result})

# Plantillas de WhatsApp sugeridas
WHATSAPP_TEMPLATES = {
    "bienvenida": {
        "name": "bienvenida_asistente",
        "language": "es",
        "components": [
            {
                "type": "BODY",
                "text": "¡Hola! Soy tu asistente inteligente personal 🤖\n\nPuedo ayudarte con más de 405 tareas diferentes:\n📅 Gestionar tu calendario\n📧 Enviar emails\n📊 Crear reportes\n💼 Automatizar tareas\n\n¿En qué puedo ayudarte hoy?"
            }
        ]
    },
    "confirmacion": {
        "name": "confirmacion_accion",
        "language": "es", 
        "components": [
            {
                "type": "BODY",
                "text": "✅ He completado tu solicitud exitosamente.\n\n¿Hay algo más en lo que pueda ayudarte?"
            }
        ]
    }
}

if __name__ == "__main__":
    print("📱 CONFIGURACIÓN DE WHATSAPP BUSINESS")
    print("====================================")
    print("1. Crea una cuenta de WhatsApp Business")
    print("2. Configura Meta for Developers")
    print("3. Obtén Access Token y Phone Number ID")
    print("4. Configura webhook apuntando a este servidor")
    print("5. Verifica el webhook con el token configurado")
    print("\n🎯 Una vez configurado, los usuarios podrán:")
    print("   • Enviar: 'Programa reunión mañana 10am'")
    print("   • Enviar: 'Crea reporte de ventas'")
    print("   • Enviar: 'Organiza mis documentos'")
    print("   • Recibir respuestas automáticas inteligentes")
    
    # Solo para desarrollo - en producción usar gunicorn
    app.run(debug=True, port=5000)
