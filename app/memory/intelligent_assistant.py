# app/memory/intelligent_assistant.py
"""
Sistema de Asistente de IA Inteligente con Aprendizaje Evolutivo
Funcionalidades:
- Memoria contextual entre sesiones
- Análisis de patrones de usuario
- Aprendizaje de feedback
- Sugerencias personalizadas
- Conexión de información histórica
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import hashlib
from collections import defaultdict, Counter
import re

from app.core.auth_manager import get_auth_client
from app.actions import sharepoint_actions, notion_actions, gemini_actions
from .persistent_memory import PersistentMemoryManager

logger = logging.getLogger(__name__)

class IntelligentAssistant:
    """Asistente de IA que aprende y evoluciona con cada interacción"""
    
    def __init__(self):
        self.memory_manager = PersistentMemoryManager()
        self.user_profiles = {}  # Cache de perfiles de usuario
        self.pattern_cache = {}  # Cache de patrones identificados
        
        # Configuración del asistente
        self.config = {
            "learning_threshold": 5,  # Mínimo de interacciones para aprender
            "pattern_confidence": 0.7,  # Confianza mínima para patrones
            "max_history_days": 90,  # Días de historial a considerar
            "max_suggestions": 5,  # Máximo de sugerencias
            "feedback_weight": 2.0,  # Peso del feedback en aprendizaje
        }
    
    async def analyze_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analiza patrones históricos del usuario"""
        try:
            auth_client = get_auth_client()
            
            # Obtener historial del usuario
            cutoff_date = (datetime.now() - timedelta(days=self.config["max_history_days"])).isoformat()
            
            # Buscar en SharePoint todas las interacciones del usuario
            search_result = await sharepoint_actions.search_list_items(auth_client, {
                "list_name": "Elite_Memory_Store",
                "search_query": f"user_id:{user_id}",
                "filter": f"timestamp ge '{cutoff_date}'",
                "top": 1000
            })
            
            if not search_result.get("success"):
                return {"success": False, "error": "No se pudo obtener historial"}
            
            interactions = search_result.get("data", [])
            
            # Análisis de patrones
            patterns = self._analyze_interaction_patterns(interactions)
            preferences = self._extract_user_preferences(interactions)
            usage_trends = self._analyze_usage_trends(interactions)
            common_flows = self._identify_common_workflows(interactions)
            
            # Generar insights
            insights = self._generate_user_insights(patterns, preferences, usage_trends)
            
            # Actualizar perfil del usuario
            user_profile = {
                "user_id": user_id,
                "last_analysis": datetime.now().isoformat(),
                "total_interactions": len(interactions),
                "patterns": patterns,
                "preferences": preferences,
                "usage_trends": usage_trends,
                "common_workflows": common_flows,
                "insights": insights,
                "confidence_score": self._calculate_confidence_score(interactions)
            }
            
            # Guardar perfil actualizado
            await self._save_user_profile(user_profile)
            self.user_profiles[user_id] = user_profile
            
            return {
                "success": True,
                "user_profile": user_profile,
                "message": f"Análisis completado: {len(interactions)} interacciones analizadas"
            }
            
        except Exception as e:
            logger.error(f"Error analizando patrones de usuario: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyze_interaction_patterns(self, interactions: List[Dict]) -> Dict[str, Any]:
        """Analiza patrones en las interacciones"""
        patterns = {
            "most_used_actions": Counter(),
            "time_patterns": defaultdict(int),
            "category_preferences": Counter(),
            "success_rates": defaultdict(list),
            "query_patterns": [],
            "session_lengths": []
        }
        
        session_interactions = defaultdict(list)
        
        for interaction in interactions:
            # Acción más usada
            action = interaction.get("action_executed", "")
            if action:
                patterns["most_used_actions"][action] += 1
            
            # Patrones temporales
            timestamp = interaction.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hour = dt.hour
                    day_of_week = dt.weekday()
                    patterns["time_patterns"][f"hour_{hour}"] += 1
                    patterns["time_patterns"][f"day_{day_of_week}"] += 1
                except:
                    pass
            
            # Categorías preferidas
            category = interaction.get("category", "")
            if category:
                patterns["category_preferences"][category] += 1
            
            # Tasas de éxito
            success = interaction.get("success", True)
            if action:
                patterns["success_rates"][action].append(1 if success else 0)
            
            # Agrupar por sesión
            session_id = interaction.get("session_id", "")
            if session_id:
                session_interactions[session_id].append(interaction)
            
            # Patrones en queries
            query = interaction.get("query_original", "")
            if query and len(query) > 10:
                patterns["query_patterns"].append(query.lower())
        
        # Calcular longitudes de sesión
        for session_id, session_data in session_interactions.items():
            patterns["session_lengths"].append(len(session_data))
        
        # Procesar tasas de éxito
        for action, successes in patterns["success_rates"].items():
            if successes:
                patterns["success_rates"][action] = sum(successes) / len(successes)
        
        return patterns
    
    def _extract_user_preferences(self, interactions: List[Dict]) -> Dict[str, Any]:
        """Extrae preferencias del usuario basado en su historial"""
        preferences = {
            "preferred_platforms": Counter(),
            "content_types": Counter(),
            "complexity_level": "medium",
            "response_format": "detailed",
            "working_hours": [],
            "frequent_keywords": Counter()
        }
        
        for interaction in interactions:
            # Plataformas preferidas
            action = interaction.get("action_executed", "")
            if action:
                if "sharepoint" in action.lower():
                    preferences["preferred_platforms"]["sharepoint"] += 1
                elif "onedrive" in action.lower():
                    preferences["preferred_platforms"]["onedrive"] += 1
                elif "notion" in action.lower():
                    preferences["preferred_platforms"]["notion"] += 1
                elif "teams" in action.lower():
                    preferences["preferred_platforms"]["teams"] += 1
                elif "outlook" in action.lower() or "email" in action.lower():
                    preferences["preferred_platforms"]["outlook"] += 1
            
            # Tipos de contenido
            params = interaction.get("parameters_used", {})
            if isinstance(params, dict):
                if any(key in str(params).lower() for key in ["video", "mp4", "avi"]):
                    preferences["content_types"]["video"] += 1
                if any(key in str(params).lower() for key in ["image", "jpg", "png", "gif"]):
                    preferences["content_types"]["image"] += 1
                if any(key in str(params).lower() for key in ["document", "pdf", "docx"]):
                    preferences["content_types"]["document"] += 1
                if any(key in str(params).lower() for key in ["audio", "mp3", "wav"]):
                    preferences["content_types"]["audio"] += 1
            
            # Horarios de trabajo
            timestamp = interaction.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    preferences["working_hours"].append(dt.hour)
                except:
                    pass
            
            # Keywords frecuentes
            query = interaction.get("query_original", "")
            if query:
                words = re.findall(r'\b\w+\b', query.lower())
                for word in words:
                    if len(word) > 3:  # Solo palabras significativas
                        preferences["frequent_keywords"][word] += 1
        
        return preferences
    
    def _analyze_usage_trends(self, interactions: List[Dict]) -> Dict[str, Any]:
        """Analiza tendencias de uso a lo largo del tiempo"""
        trends = {
            "activity_by_day": defaultdict(int),
            "growth_trend": "stable",
            "peak_hours": [],
            "most_productive_days": [],
            "seasonal_patterns": {}
        }
        
        daily_counts = defaultdict(int)
        hourly_counts = defaultdict(int)
        
        for interaction in interactions:
            timestamp = interaction.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    date_key = dt.strftime('%Y-%m-%d')
                    daily_counts[date_key] += 1
                    hourly_counts[dt.hour] += 1
                except:
                    pass
        
        trends["activity_by_day"] = dict(daily_counts)
        
        # Horas pico
        if hourly_counts:
            sorted_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)
            trends["peak_hours"] = [hour for hour, count in sorted_hours[:3]]
        
        # Días más productivos
        if daily_counts:
            sorted_days = sorted(daily_counts.items(), key=lambda x: x[1], reverse=True)
            trends["most_productive_days"] = [day for day, count in sorted_days[:5]]
        
        return trends
    
    def _identify_common_workflows(self, interactions: List[Dict]) -> List[Dict[str, Any]]:
        """Identifica flujos de trabajo comunes"""
        workflows = []
        session_flows = defaultdict(list)
        
        # Agrupar por sesión
        for interaction in interactions:
            session_id = interaction.get("session_id", "")
            action = interaction.get("action_executed", "")
            if session_id and action:
                session_flows[session_id].append(action)
        
        # Buscar secuencias comunes
        flow_patterns = Counter()
        for session_id, actions in session_flows.items():
            if len(actions) >= 2:
                for i in range(len(actions) - 1):
                    flow = f"{actions[i]} -> {actions[i+1]}"
                    flow_patterns[flow] += 1
        
        # Convertir a workflows
        for flow, count in flow_patterns.most_common(10):
            if count >= 2:  # Al menos 2 ocurrencias
                workflows.append({
                    "sequence": flow,
                    "frequency": count,
                    "confidence": min(count / len(session_flows), 1.0)
                })
        
        return workflows
    
    def _generate_user_insights(self, patterns: Dict, preferences: Dict, trends: Dict) -> List[str]:
        """Genera insights personalizados del usuario"""
        insights = []
        
        # Insight sobre acciones favoritas
        if patterns["most_used_actions"]:
            top_action = patterns["most_used_actions"].most_common(1)[0]
            insights.append(f"Tu acción más utilizada es '{top_action[0]}' ({top_action[1]} veces)")
        
        # Insight sobre horarios
        if patterns["time_patterns"]:
            peak_hour = max(
                [k for k in patterns["time_patterns"].keys() if k.startswith("hour_")],
                key=lambda x: patterns["time_patterns"][x]
            )
            hour = peak_hour.split("_")[1]
            insights.append(f"Eres más activo a las {hour}:00")
        
        # Insight sobre plataformas
        if preferences["preferred_platforms"]:
            top_platform = preferences["preferred_platforms"].most_common(1)[0]
            insights.append(f"Tu plataforma preferida es {top_platform[0]} ({top_platform[1]} usos)")
        
        # Insight sobre productividad
        if trends["most_productive_days"]:
            insights.append(f"Tu día más productivo fue: {trends['most_productive_days'][0]}")
        
        # Insight sobre éxito
        success_rates = patterns.get("success_rates", {})
        if success_rates:
            avg_success = sum(success_rates.values()) / len(success_rates)
            insights.append(f"Tu tasa de éxito promedio es {avg_success:.1%}")
        
        return insights
    
    def _calculate_confidence_score(self, interactions: List[Dict]) -> float:
        """Calcula un score de confianza basado en la cantidad y calidad de datos"""
        if not interactions:
            return 0.0
        
        # Factores de confianza
        interaction_count = len(interactions)
        unique_sessions = len(set(i.get("session_id", "") for i in interactions if i.get("session_id")))
        recent_interactions = sum(1 for i in interactions 
                                if (datetime.now() - datetime.fromisoformat(
                                    i.get("timestamp", "2020-01-01").replace('Z', '+00:00')
                                )).days <= 7)
        
        # Calcular score
        count_score = min(interaction_count / 50, 1.0)  # Máximo en 50 interacciones
        session_score = min(unique_sessions / 10, 1.0)   # Máximo en 10 sesiones
        recency_score = min(recent_interactions / 10, 1.0)  # Máximo en 10 recientes
        
        return (count_score + session_score + recency_score) / 3
    
    async def _save_user_profile(self, user_profile: Dict[str, Any]) -> None:
        """Guarda el perfil del usuario en Notion"""
        try:
            auth_client = get_auth_client()
            
            # Preparar datos para Notion
            notion_data = {
                "database_name": "Elite AI Assistant Profiles",
                "properties": {
                    "User ID": user_profile["user_id"],
                    "Last Analysis": user_profile["last_analysis"],
                    "Total Interactions": user_profile["total_interactions"],
                    "Confidence Score": user_profile["confidence_score"],
                    "Top Action": user_profile["patterns"]["most_used_actions"].most_common(1)[0][0] if user_profile["patterns"]["most_used_actions"] else "N/A",
                    "Preferred Platform": user_profile["preferences"]["preferred_platforms"].most_common(1)[0][0] if user_profile["preferences"]["preferred_platforms"] else "N/A",
                    "Profile Data": json.dumps(user_profile, indent=2)
                }
            }
            
            await notion_actions.create_page(auth_client, notion_data)
            
        except Exception as e:
            logger.error(f"Error guardando perfil de usuario: {e}")

# Instancia global del asistente inteligente
intelligent_assistant = IntelligentAssistant()
