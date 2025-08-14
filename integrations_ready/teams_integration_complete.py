"""
👥 MICROSOFT TEAMS INTEGRATION - ELITE DYNAMICS AI
================================================

Integración completa de Microsoft Teams con tu asistente inteligente.
Permite a los equipos acceder a las 466+ acciones y 5 workflows desde Teams.
"""

from botbuilder.core import ActivityHandler, TurnContext, MessageFactory, CardFactory
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes, Attachment
from botbuilder.core.conversation_state import ConversationState
from botbuilder.core.user_state import UserState
import aiohttp
import json
import os
import logging
from datetime import datetime
from typing import List

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TeamsEliteDynamicsBot(ActivityHandler):
    """Bot de Teams integrado con Elite Dynamics AI"""
    
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        super().__init__()
        self.conversation_state = conversation_state
        self.user_state = user_state
        self.api_base_url = os.getenv('YOUR_API_URL', 'https://elitedynamicsapi.azurewebsites.net')
        self.session_storage = {}
        
        logger.info("🚀 Teams Elite Dynamics AI Bot inicializado")

    async def on_message_activity(self, turn_context: TurnContext):
        """Manejar mensajes de usuarios en Teams"""
        try:
            user_id = turn_context.activity.from_property.id
            user_name = turn_context.activity.from_property.name or "Usuario"
            user_message = turn_context.activity.text.strip()
            
            logger.info(f"👥 Mensaje de {user_name}: {user_message}")
            
            # Comando de bienvenida/ayuda
            if any(cmd in user_message.lower() for cmd in ['hola', 'hello', 'hi', 'ayuda', 'help']):
                await self.send_welcome_message(turn_context, user_name)
                return
            
            # Comando para listar workflows
            elif 'lista workflows' in user_message.lower() or 'workflows disponibles' in user_message.lower():
                await self.send_workflows_card(turn_context)
                return
            
            # Comandos específicos de workflows
            elif 'backup completo' in user_message.lower():
                await self.execute_workflow_with_card(turn_context, 'workflow_execute_backup_completo', 'Backup Completo')
                return
            
            elif 'sincroniza marketing' in user_message.lower() or 'sync marketing' in user_message.lower():
                await self.execute_workflow_with_card(turn_context, 'workflow_execute_sync_marketing', 'Sincronización Marketing')
                return
            
            elif 'crea contenido' in user_message.lower() or 'content creation' in user_message.lower():
                await self.execute_workflow_with_card(turn_context, 'workflow_execute_content_creation', 'Creación de Contenido')
                return
            
            # Enviar al API de Elite Dynamics
            else:
                await self.process_with_api(turn_context, user_message, user_name)
                
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
            error_message = "❌ Error procesando tu mensaje. Intenta escribir 'ayuda' para ver los comandos disponibles."
            await turn_context.send_activity(MessageFactory.text(error_message))

    async def send_welcome_message(self, turn_context: TurnContext, user_name: str):
        """Enviar mensaje de bienvenida con tarjeta interactiva"""
        
        # Crear tarjeta adaptativa
        welcome_card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": f"🤖 ¡Hola {user_name}!",
                            "size": "Large",
                            "weight": "Bolder",
                            "color": "Accent"
                        },
                        {
                            "type": "TextBlock", 
                            "text": "Soy Elite Dynamics AI, tu asistente empresarial inteligente",
                            "size": "Medium",
                            "wrap": True
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "🚀 Acciones:", "value": "466+ funciones empresariales"},
                                {"title": "🔧 Workflows:", "value": "5 automatizaciones completas"},
                                {"title": "🔗 Integración:", "value": "Office 365, Google, Meta, LinkedIn"}
                            ]
                        }
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "📋 Ver Workflows",
                    "data": {"action": "lista workflows"}
                },
                {
                    "type": "Action.Submit", 
                    "title": "🗄️ Backup Completo",
                    "data": {"action": "backup completo"}
                },
                {
                    "type": "Action.Submit",
                    "title": "📊 Sync Marketing", 
                    "data": {"action": "sincroniza marketing"}
                },
                {
                    "type": "Action.Submit",
                    "title": "💡 Ayuda",
                    "data": {"action": "ayuda comandos"}
                }
            ]
        }
        
        attachment = CardFactory.adaptive_card(welcome_card)
        await turn_context.send_activity(MessageFactory.attachment(attachment))

    async def send_workflows_card(self, turn_context: TurnContext):
        """Enviar tarjeta con workflows disponibles"""
        
        workflows_card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "🔧 Workflows Empresariales Disponibles",
                    "size": "Large",
                    "weight": "Bolder",
                    "color": "Accent"
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [{"type": "TextBlock", "text": "🗄️", "size": "Large"}]
                                },
                                {
                                    "type": "Column", 
                                    "width": "stretch",
                                    "items": [
                                        {"type": "TextBlock", "text": "**Backup Completo**", "weight": "Bolder"},
                                        {"type": "TextBlock", "text": "Respalda SharePoint, OneDrive, Notion, Emails y Teams", "wrap": True, "size": "Small"}
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto", 
                                    "items": [{"type": "TextBlock", "text": "📊", "size": "Large"}]
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [
                                        {"type": "TextBlock", "text": "**Sincronización Marketing**", "weight": "Bolder"},
                                        {"type": "TextBlock", "text": "Unifica Google Ads, Meta, LinkedIn y HubSpot en dashboard", "wrap": True, "size": "Small"}
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "ColumnSet", 
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [{"type": "TextBlock", "text": "✍️", "size": "Large"}]
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [
                                        {"type": "TextBlock", "text": "**Creación de Contenido**", "weight": "Bolder"},
                                        {"type": "TextBlock", "text": "Pipeline: WordPress → OneDrive → Teams → SharePoint", "wrap": True, "size": "Small"}
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [{"type": "TextBlock", "text": "📺", "size": "Large"}]
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch", 
                                    "items": [
                                        {"type": "TextBlock", "text": "**YouTube Pipeline**", "weight": "Bolder"},
                                        {"type": "TextBlock", "text": "Analytics + Performance + Dashboard automático", "wrap": True, "size": "Small"}
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [{"type": "TextBlock", "text": "🤝", "size": "Large"}]
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [
                                        {"type": "TextBlock", "text": "**Onboarding Clientes**", "weight": "Bolder"},
                                        {"type": "TextBlock", "text": "Setup automático: HubSpot + SharePoint + Teams + Calendario", "wrap": True, "size": "Small"}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "🗄️ Ejecutar Backup",
                    "data": {"action": "workflow_execute_backup_completo"}
                },
                {
                    "type": "Action.Submit",
                    "title": "📊 Ejecutar Marketing Sync", 
                    "data": {"action": "workflow_execute_sync_marketing"}
                },
                {
                    "type": "Action.Submit",
                    "title": "✍️ Ejecutar Content Creation",
                    "data": {"action": "workflow_execute_content_creation"}
                }
            ]
        }
        
        attachment = CardFactory.adaptive_card(workflows_card)
        await turn_context.send_activity(MessageFactory.attachment(attachment))

    async def execute_workflow_with_card(self, turn_context: TurnContext, workflow_action: str, workflow_name: str):
        """Ejecutar workflow y mostrar resultado en tarjeta"""
        
        # Enviar mensaje de inicio
        await turn_context.send_activity(MessageFactory.text(f"🚀 Ejecutando {workflow_name}..."))
        
        try:
            # Llamar al API
            api_response = await self.call_elite_api(workflow_action, {})
            
            # Crear tarjeta de resultado
            if api_response.get("success") and api_response.get("data", {}).get("status") == "success":
                data = api_response["data"]
                result_card = {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"✅ {workflow_name} Completado",
                            "size": "Large",
                            "weight": "Bolder", 
                            "color": "Good"
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "📊 Pasos ejecutados:", "value": str(data.get("steps_completed", 0))},
                                {"title": "✅ Exitosos:", "value": str(data.get("execution_summary", {}).get("successful_steps", 0))},
                                {"title": "⏱️ Ejecutado:", "value": datetime.now().strftime("%H:%M:%S")}
                            ]
                        },
                        {
                            "type": "TextBlock",
                            "text": data.get("message", "Workflow ejecutado exitosamente"),
                            "wrap": True
                        }
                    ]
                }
            else:
                # Tarjeta de error
                result_card = {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4", 
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"⚠️ Error en {workflow_name}",
                            "size": "Large",
                            "weight": "Bolder",
                            "color": "Warning"
                        },
                        {
                            "type": "TextBlock",
                            "text": api_response.get("error", "Error desconocido"),
                            "wrap": True
                        }
                    ]
                }
            
            attachment = CardFactory.adaptive_card(result_card)
            await turn_context.send_activity(MessageFactory.attachment(attachment))
            
        except Exception as e:
            logger.error(f"Error ejecutando workflow: {e}")
            await turn_context.send_activity(MessageFactory.text(f"❌ Error ejecutando {workflow_name}: {str(e)}"))

    async def call_elite_api(self, action: str, params: dict):
        """Llamar al API de Elite Dynamics"""
        try:
            async with aiohttp.ClientSession() as session:
                if action.startswith('workflow_'):
                    # Usar endpoint específico para workflows
                    url = f"{self.api_base_url}/api/v1/dynamics"
                    payload = {"action": action, "params": params}
                else:
                    # Usar endpoint de chat inteligente
                    url = f"{self.api_base_url}/api/v1/chatgpt"
                    payload = {"query": action, "context": "Teams Bot"}
                
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"Error API: {response.status}"}
                        
        except Exception as e:
            logger.error(f"Error llamando API: {e}")
            return {"error": f"Error de conexión: {str(e)}"}

    async def process_with_api(self, turn_context: TurnContext, user_message: str, user_name: str):
        """Procesar mensaje con el API de Elite Dynamics"""
        
        try:
            # Enviar indicador de tipeo
            await turn_context.send_activity(MessageFactory.text("🤖 Procesando..."))
            
            # Llamar al API
            api_response = await self.call_elite_api(user_message, {"teams_user": user_name})
            
            # Formatear respuesta
            if api_response.get("success"):
                message = api_response.get("message", "Procesado exitosamente")
                data = api_response.get("data", {})
                
                # Si hay datos estructurados, crear tarjeta
                if isinstance(data, dict) and len(data) > 0:
                    card = self.create_data_card(message, data)
                    attachment = CardFactory.adaptive_card(card)
                    await turn_context.send_activity(MessageFactory.attachment(attachment))
                else:
                    await turn_context.send_activity(MessageFactory.text(f"✅ {message}"))
            else:
                error_msg = api_response.get("error", "Error procesando solicitud")
                await turn_context.send_activity(MessageFactory.text(f"❌ {error_msg}"))
                
        except Exception as e:
            logger.error(f"Error procesando con API: {e}")
            await turn_context.send_activity(MessageFactory.text("❌ Error procesando solicitud. Intenta de nuevo."))

    def create_data_card(self, title: str, data: dict):
        """Crear tarjeta adaptativa con datos estructurados"""
        
        card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": title,
                    "size": "Medium",
                    "weight": "Bolder"
                }
            ]
        }
        
        # Agregar datos como FactSet si es pequeño
        if len(str(data)) < 500:
            facts = []
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)):
                    facts.append({"title": str(key), "value": str(value)})
            
            if facts:
                card["body"].append({
                    "type": "FactSet",
                    "facts": facts[:10]  # Máximo 10 facts
                })
        else:
            # Para datos grandes, mostrar resumen
            card["body"].append({
                "type": "TextBlock",
                "text": f"📊 Datos procesados: {len(data)} elementos",
                "wrap": True
            })
        
        return card

    async def on_members_added_activity(self, members_added: List[ChannelAccount], turn_context: TurnContext):
        """Manejar cuando se agrega el bot a un chat/canal"""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await self.send_welcome_message(turn_context, member.name or "Equipo")

# Para uso con Bot Framework
def create_teams_bot():
    """Factory para crear el bot de Teams"""
    from botbuilder.core.memory_storage import MemoryStorage
    from botbuilder.core.conversation_state import ConversationState
    from botbuilder.core.user_state import UserState
    
    # Crear storage y states
    memory_storage = MemoryStorage()
    conversation_state = ConversationState(memory_storage)
    user_state = UserState(memory_storage)
    
    # Crear bot
    bot = TeamsEliteDynamicsBot(conversation_state, user_state)
    
    return bot, conversation_state, user_state
