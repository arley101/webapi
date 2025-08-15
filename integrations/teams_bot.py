"""
🤖 INTEGRACIÓN CON MICROSOFT TEAMS
=================================

Este módulo permite conectar tu asistente inteligente con Microsoft Teams.
Los usuarios podrán interactuar con tu asistente directamente desde Teams.

Características:
- Bot de Teams que conecta con tu API
- Comandos naturales: @TuBot "programa reunión mañana"
- Acceso a las 405 acciones desde Teams
- Notificaciones proactivas
- Integración con calendario de Teams

Setup:
1. Registrar bot en Azure Bot Service
2. Configurar Teams App Manifest
3. Conectar con tu API existente
"""

from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import ChannelAccount, Activity
import aiohttp
import json
import os
from typing import List

class TeamsAssistantBot(ActivityHandler):
    """Bot de Teams que conecta con tu asistente inteligente"""
    
    def __init__(self):
        super().__init__()
        self.api_base_url = os.getenv('YOUR_API_URL', 'https://tu-app.azurewebsites.net')
        self.session_storage = {}  # En producción usar Redis/CosmosDB

    async def on_message_activity(self, turn_context: TurnContext):
        """Manejar mensajes de usuarios en Teams"""
        user_id = turn_context.activity.from_property.id
        user_message = turn_context.activity.text
        
        # Iniciar sesión si no existe
        if user_id not in self.session_storage:
            session_id = await self.start_assistant_session(user_id)
            self.session_storage[user_id] = session_id
        
        # Enviar mensaje al asistente inteligente
        response = await self.send_to_assistant(
            user_message, 
            user_id, 
            self.session_storage[user_id]
        )
        
        # Responder en Teams
        if response:
            await turn_context.send_activity(MessageFactory.text(response['response']))
            
            # Enviar información adicional si existe
            if response.get('action_executed'):
                action_msg = f"✅ Acción ejecutada: {response['action_executed']}"
                await turn_context.send_activity(MessageFactory.text(action_msg))
            
            if response.get('suggestions'):
                suggestions = ", ".join(response['suggestions'][:3])
                suggest_msg = f"💡 También puedes: {suggestions}"
                await turn_context.send_activity(MessageFactory.text(suggest_msg))
        else:
            await turn_context.send_activity(
                MessageFactory.text("❌ Lo siento, hubo un error procesando tu solicitud.")
            )

    async def on_members_added_activity(
        self, members_added: List[ChannelAccount], turn_context: TurnContext
    ):
        """Mensaje de bienvenida cuando el bot es agregado"""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                welcome_text = (
                    "👋 ¡Hola! Soy tu asistente inteligente personal.\n\n"
                    "🤖 Tengo acceso a 405 acciones para ayudarte con:\n"
                    "📅 Gestión de calendario y reuniones\n"
                    "📧 Emails y comunicaciones\n"
                    "📊 Análisis de datos y reportes\n"
                    "💼 Automatización de tareas\n"
                    "🔍 Búsquedas y investigación\n\n"
                    "Simplemente escríbeme lo que necesitas en lenguaje natural."
                )
                await turn_context.send_activity(MessageFactory.text(welcome_text))

    async def start_assistant_session(self, user_id: str) -> str:
        """Iniciar sesión con el asistente inteligente"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "user_id": f"teams_{user_id}",
                    "context": "Microsoft Teams integration"
                }
                
                async with session.post(
                    f"{self.api_base_url}/api/v1/intelligent-assistant/session/start",
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('session_id')
                    else:
                        return None
        except Exception as e:
            print(f"Error starting session: {e}")
            return None

    async def send_to_assistant(self, message: str, user_id: str, session_id: str):
        """Enviar mensaje al asistente inteligente"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "message": message,
                    "user_id": f"teams_{user_id}",
                    "session_id": session_id
                }
                
                async with session.post(
                    f"{self.api_base_url}/api/v1/intelligent-assistant/chat",
                    json=payload
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
        except Exception as e:
            print(f"Error sending message to assistant: {e}")
            return None


# Teams App Manifest (teams_manifest.json)
TEAMS_MANIFEST = {
    "$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
    "manifestVersion": "1.16",
    "version": "1.0.0",
    "id": "tu-asistente-inteligente-id",
    "packageName": "com.tucompania.asistente",
    "developer": {
        "name": "Tu Compañía",
        "websiteUrl": "https://tu-app.azurewebsites.net",
        "privacyUrl": "https://tu-app.azurewebsites.net/privacy",
        "termsOfUseUrl": "https://tu-app.azurewebsites.net/terms"
    },
    "icons": {
        "color": "icon-color.png",
        "outline": "icon-outline.png"
    },
    "name": {
        "short": "Tu Asistente IA",
        "full": "Tu Asistente Inteligente Personal"
    },
    "description": {
        "short": "Asistente IA con 405 acciones para automatizar tu trabajo",
        "full": "Asistente inteligente personal que puede gestionar tu calendario, enviar emails, analizar datos y automatizar más de 405 tareas diferentes desde Microsoft Teams."
    },
    "accentColor": "#667eea",
    "bots": [
        {
            "botId": "tu-bot-id-de-azure",
            "scopes": ["personal", "team", "groupchat"],
            "commandLists": [
                {
                    "scopes": ["personal", "team", "groupchat"],
                    "commands": [
                        {
                            "title": "Ayuda",
                            "description": "Ver todas las capacidades del asistente"
                        },
                        {
                            "title": "Programar reunión",
                            "description": "Crear una nueva reunión en tu calendario"
                        },
                        {
                            "title": "Enviar email",
                            "description": "Redactar y enviar un email"
                        },
                        {
                            "title": "Análisis de datos",
                            "description": "Analizar datos y crear reportes"
                        }
                    ]
                }
            ]
        }
    ],
    "permissions": ["identity", "messageTeamMembers"],
    "validDomains": ["tu-app.azurewebsites.net"]
}

# Configuración para Azure Bot Service
BOT_CONFIGURATION = {
    "type": "MultiTenant",
    "displayName": "Tu Asistente Inteligente",
    "description": "Asistente IA con acceso a 405 acciones automáticas",
    "iconUrl": "https://tu-app.azurewebsites.net/static/bot-icon.png",
    "endpoint": "https://tu-bot-service.azurewebsites.net/api/messages",
    "msaAppId": "tu-app-id",
    "channels": {
        "msteams": {
            "callingWebhook": "https://tu-app.azurewebsites.net/api/teams/calling",
            "enableCalling": True,
            "enableVideo": True
        }
    }
}

if __name__ == "__main__":
    print("🤖 CONFIGURACIÓN DE BOT DE TEAMS")
    print("================================")
    print("1. Registra tu bot en Azure Bot Service")
    print("2. Usa el Teams App Manifest incluido")
    print("3. Configura el endpoint hacia tu API")
    print("4. Sube el bot a Teams App Store de tu organización")
    print("\n🎯 Una vez configurado, los usuarios podrán:")
    print("   • @TuBot programa reunión mañana a las 10am")
    print("   • @TuBot envía email a mi equipo sobre el proyecto")
    print("   • @TuBot crea reporte de ventas del mes")
    print("   • @TuBot busca documentos sobre clientes")
