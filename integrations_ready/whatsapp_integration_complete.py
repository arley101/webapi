"""
📱 WHATSAPP BUSINESS INTEGRATION - ELITE DYNAMICS AI
==================================================

Integración completa de WhatsApp Business con tu asistente inteligente.
Permite a los usuarios acceder a las 466+ acciones y 5 workflows desde WhatsApp.
"""

from flask import Flask, request, jsonify, Blueprint
import requests
import json
import os
import asyncio
import aiohttp
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Blueprint para WhatsApp
whatsapp_bp = Blueprint('whatsapp', __name__)

class WhatsAppEliteDynamics:
    """Integración de WhatsApp con Elite Dynamics AI"""
    
    def __init__(self):
        self.api_base_url = os.getenv('YOUR_API_URL', 'https://elitedynamicsapi.azurewebsites.net')
        self.whatsapp_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.whatsapp_phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN', 'elite_dynamics_verify_123')
        self.session_storage = {}  # En producción usar Redis/CosmosDB
        
        # URLs de WhatsApp API
        self.whatsapp_api_url = f"https://graph.facebook.com/v17.0/{self.whatsapp_phone_id}/messages"
        
        logger.info("🚀 WhatsApp Elite Dynamics AI inicializado")

    def verify_webhook(self, verify_token, challenge):
        """Verificar webhook de WhatsApp"""
        if verify_token == self.verify_token:
            logger.info("✅ Webhook verificado exitosamente")
            return challenge
        logger.warning("❌ Token de verificación incorrecto")
        return None

    async def send_to_elite_api(self, user_message, from_number):
        """Enviar mensaje al API de Elite Dynamics"""
        try:
            async with aiohttp.ClientSession() as session:
                # Usar el endpoint de chat inteligente
                url = f"{self.api_base_url}/api/v1/chatgpt"
                
                payload = {
                    "query": user_message,
                    "context": f"WhatsApp user: {from_number}"
                }
                
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        logger.error(f"Error API: {response.status}")
                        return {"error": "Error comunicándose con el asistente"}
                        
        except Exception as e:
            logger.error(f"Error enviando a API: {e}")
            return {"error": "Error interno del sistema"}

    def format_response_for_whatsapp(self, api_response):
        """Formatear respuesta del API para WhatsApp"""
        try:
            if api_response.get("success"):
                data = api_response.get("data", {})
                message = api_response.get("message", "")
                
                # Si es un workflow
                if "workflow" in str(data).lower():
                    if data.get("status") == "success":
                        workflow_name = data.get("workflow", "")
                        steps = data.get("steps_completed", 0)
                        return f"✅ *Workflow ejecutado exitosamente*\n\n🔧 {workflow_name}\n📊 {steps} pasos completados\n\n{message}"
                    else:
                        return f"⚠️ *Error en workflow*\n\n{data.get('message', 'Error desconocido')}"
                
                # Si es listado de workflows
                elif "predefined_workflows" in str(data):
                    workflows = data.get("predefined_workflows", {})
                    response = "📋 *Workflows Disponibles:*\n\n"
                    for name, info in workflows.items():
                        response += f"🔧 *{info.get('name', name)}*\n"
                        response += f"📄 {info.get('description', 'Sin descripción')}\n"
                        response += f"📊 {info.get('steps_count', 0)} pasos\n\n"
                    
                    response += "💬 *Comandos útiles:*\n"
                    response += "• _Ejecuta backup completo_\n"
                    response += "• _Sincroniza marketing_\n"
                    response += "• _Crea contenido_\n"
                    response += "• _Ayuda_"
                    return response
                
                # Respuesta estándar
                else:
                    formatted = f"🤖 *Elite Dynamics AI*\n\n{message}"
                    if data:
                        # Agregar información adicional si está disponible
                        if isinstance(data, dict) and len(str(data)) < 500:
                            formatted += f"\n\n📊 *Detalles:*\n{json.dumps(data, indent=2, ensure_ascii=False)[:300]}"
                    return formatted
            
            else:
                error_msg = api_response.get("error", "Error desconocido")
                return f"❌ *Error*\n\n{error_msg}\n\n💡 Intenta con:\n• _Lista workflows_\n• _Ayuda_\n• _Ejecuta backup completo_"
                
        except Exception as e:
            logger.error(f"Error formateando respuesta: {e}")
            return "❌ Error procesando respuesta. Intenta de nuevo."

    def send_whatsapp_message(self, to_number, message):
        """Enviar mensaje a WhatsApp"""
        try:
            headers = {
                'Authorization': f'Bearer {self.whatsapp_token}',
                'Content-Type': 'application/json'
            }
            
            # Dividir mensajes largos
            if len(message) > 1500:
                messages = [message[i:i+1500] for i in range(0, len(message), 1500)]
            else:
                messages = [message]
            
            for msg in messages:
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to_number,
                    "type": "text",
                    "text": {"body": msg}
                }
                
                response = requests.post(self.whatsapp_api_url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    logger.info(f"✅ Mensaje enviado a {to_number}")
                else:
                    logger.error(f"❌ Error enviando mensaje: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Error enviando mensaje WhatsApp: {e}")

    async def handle_message(self, message_data):
        """Manejar mensaje recibido de WhatsApp"""
        try:
            from_number = message_data.get('from')
            
            # Manejar diferentes tipos de mensaje
            if message_data.get('type') == 'text':
                message_text = message_data.get('text', {}).get('body', '')
            elif message_data.get('type') == 'interactive':
                message_text = message_data.get('interactive', {}).get('button_reply', {}).get('title', '')
            else:
                message_text = "ayuda"  # Default para tipos no soportados
            
            logger.info(f"📱 Mensaje recibido de {from_number}: {message_text}")
            
            # Comando de bienvenida
            if message_text.lower() in ['hola', 'hi', 'hello', 'inicio', 'start']:
                welcome_msg = """🤖 *¡Hola! Soy Elite Dynamics AI*

🚀 *Tu asistente inteligente con:*
• 466+ acciones empresariales
• 5 workflows automatizados
• Integración con Office 365, Google, Meta y más

💬 *Comandos populares:*
• _Lista workflows_ - Ver automatizaciones
• _Ejecuta backup completo_ - Respaldar datos
• _Sincroniza marketing_ - Dashboard unificado
• _Ayuda_ - Ver todos los comandos

¿En qué puedo ayudarte hoy? 😊"""
                self.send_whatsapp_message(from_number, welcome_msg)
                return
            
            # Comando de ayuda
            elif message_text.lower() in ['ayuda', 'help', 'comandos']:
                help_msg = """📋 *Comandos Disponibles:*

🔧 *WORKFLOWS:*
• _Lista workflows_ - Ver todos los workflows
• _Ejecuta backup completo_ - Backup empresarial
• _Sincroniza marketing_ - Dashboard marketing
• _Crea contenido_ - Pipeline de contenido
• _Onboarding cliente [nombre]_ - Setup cliente

📊 *ACCIONES RÁPIDAS:*
• _Mis emails_ - Últimos correos
• _Calendario hoy_ - Eventos de hoy
• _Archivos OneDrive_ - Documentos recientes
• _Equipos Teams_ - Mis equipos

💼 *EJEMPLOS:*
• _"Programa reunión mañana 3pm"_
• _"Busca emails de esta semana"_
• _"Crea post para LinkedIn"_
• _"Analiza mi canal YouTube"_

¿Qué te gustaría hacer? 🚀"""
                self.send_whatsapp_message(from_number, help_msg)
                return
            
            # Enviar al API de Elite Dynamics
            api_response = await self.send_to_elite_api(message_text, from_number)
            
            # Formatear y enviar respuesta
            formatted_response = self.format_response_for_whatsapp(api_response)
            self.send_whatsapp_message(from_number, formatted_response)
            
        except Exception as e:
            logger.error(f"Error manejando mensaje: {e}")
            error_msg = "❌ Error procesando tu mensaje. Intenta de nuevo o escribe 'ayuda'."
            self.send_whatsapp_message(from_number, error_msg)

# Instancia global
whatsapp_assistant = WhatsAppEliteDynamics()

@whatsapp_bp.route('/webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    """Webhook para WhatsApp"""
    
    if request.method == 'GET':
        # Verificación del webhook
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        result = whatsapp_assistant.verify_webhook(verify_token, challenge)
        if result:
            return result
        return "Error de verificación", 403
    
    elif request.method == 'POST':
        # Procesar mensaje entrante
        try:
            data = request.get_json()
            
            if data and 'entry' in data:
                for entry in data['entry']:
                    for change in entry.get('changes', []):
                        if change.get('field') == 'messages':
                            messages = change.get('value', {}).get('messages', [])
                            
                            for message in messages:
                                # Procesar mensaje de forma asíncrona
                                asyncio.create_task(whatsapp_assistant.handle_message(message))
            
            return jsonify({"status": "success"}), 200
            
        except Exception as e:
            logger.error(f"Error en webhook: {e}")
            return jsonify({"error": "Error procesando webhook"}), 500

@whatsapp_bp.route('/send-test', methods=['POST'])
def send_test_message():
    """Endpoint para enviar mensajes de prueba"""
    try:
        data = request.get_json()
        to_number = data.get('to')
        message = data.get('message', '🧪 Mensaje de prueba desde Elite Dynamics AI')
        
        whatsapp_assistant.send_whatsapp_message(to_number, message)
        
        return jsonify({
            "success": True,
            "message": "Mensaje enviado exitosamente"
        })
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500

@whatsapp_bp.route('/status', methods=['GET'])
def whatsapp_status():
    """Estado de la integración WhatsApp"""
    return jsonify({
        "service": "WhatsApp Elite Dynamics AI",
        "status": "active",
        "api_url": whatsapp_assistant.api_base_url,
        "features": [
            "466+ acciones empresariales",
            "5 workflows automatizados", 
            "Chat inteligente",
            "Soporte multimedia"
        ],
        "commands": [
            "Lista workflows",
            "Ejecuta backup completo",
            "Sincroniza marketing",
            "Ayuda"
        ]
    })

# Para uso directo
if __name__ == "__main__":
    app = Flask(__name__)
    app.register_blueprint(whatsapp_bp, url_prefix='/whatsapp')
    
    print("🚀 WhatsApp Elite Dynamics AI iniciado")
    print("📱 Webhook: /whatsapp/webhook")
    print("🧪 Test: /whatsapp/send-test")
    print("📊 Status: /whatsapp/status")
    
    app.run(debug=True, port=5000)
