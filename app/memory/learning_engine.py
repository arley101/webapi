# app/memory/learning_engine.py
"""
Motor de Aprendizaje del Asistente de IA
Implementa:
- Aprendizaje de feedback del usuario
- Mejora continua de sugerencias
- Adaptación de respuestas
- Predicción de necesidades
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import numpy as np
from collections import defaultdict, Counter
from dataclasses import dataclass
import re

from app.core.auth_manager import get_auth_client
from app.actions import sharepoint_actions, notion_actions, gemini_actions

logger = logging.getLogger(__name__)

@dataclass
class FeedbackEntry:
    """Entrada de feedback del usuario"""
    user_id: str
    interaction_id: str
    feedback_type: str  # 'positive', 'negative', 'suggestion', 'correction'
    rating: Optional[int]  # 1-5
    comment: Optional[str]
    timestamp: datetime
    context: Dict[str, Any]

@dataclass
class LearningPattern:
    """Patrón de aprendizaje identificado"""
    pattern_id: str
    pattern_type: str
    description: str
    confidence: float
    occurrences: int
    last_seen: datetime
    impact_score: float

class LearningEngine:
    """Motor de aprendizaje que mejora el asistente basado en feedback"""
    
    def __init__(self):
        self.feedback_history = []
        self.learning_patterns = {}
        self.improvement_suggestions = []
        self.adaptation_rules = {}
        
        # Configuración del motor de aprendizaje
        self.config = {
            "min_feedback_for_pattern": 3,
            "pattern_confidence_threshold": 0.6,
            "learning_decay_days": 30,
            "max_patterns_to_track": 100,
            "feedback_weight_multiplier": 1.5
        }
    
    async def process_user_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa feedback del usuario y actualiza el aprendizaje"""
        try:
            # Crear entrada de feedback
            feedback = FeedbackEntry(
                user_id=feedback_data.get("user_id", ""),
                interaction_id=feedback_data.get("interaction_id", ""),
                feedback_type=feedback_data.get("type", ""),
                rating=feedback_data.get("rating"),
                comment=feedback_data.get("comment"),
                timestamp=datetime.now(),
                context=feedback_data.get("context", {})
            )
            
            # Guardar feedback
            await self._save_feedback(feedback)
            self.feedback_history.append(feedback)
            
            # Analizar y aprender del feedback
            learning_result = await self._analyze_feedback_patterns(feedback)
            
            # Generar mejoras basadas en el feedback
            improvements = await self._generate_improvements(feedback)
            
            # Actualizar reglas de adaptación
            await self._update_adaptation_rules(feedback, learning_result)
            
            return {
                "success": True,
                "feedback_id": feedback.interaction_id,
                "learning_patterns_updated": len(learning_result.get("new_patterns", [])),
                "improvements_generated": len(improvements),
                "message": "Feedback procesado y aprendizaje actualizado"
            }
            
        except Exception as e:
            logger.error(f"Error procesando feedback: {e}")
            return {"success": False, "error": str(e)}
    
    async def _save_feedback(self, feedback: FeedbackEntry) -> None:
        """Guarda el feedback en SharePoint"""
        try:
            auth_client = get_auth_client()
            
            feedback_data = {
                "list_name": "Elite_AI_Feedback",
                "item_data": {
                    "user_id": feedback.user_id,
                    "interaction_id": feedback.interaction_id,
                    "feedback_type": feedback.feedback_type,
                    "rating": feedback.rating or 0,
                    "comment": feedback.comment or "",
                    "timestamp": feedback.timestamp.isoformat(),
                    "context": json.dumps(feedback.context)
                }
            }
            
            await sharepoint_actions.create_list_item(auth_client, feedback_data)
            
        except Exception as e:
            logger.error(f"Error guardando feedback: {e}")
    
    async def _analyze_feedback_patterns(self, feedback: FeedbackEntry) -> Dict[str, Any]:
        """Analiza patrones en el feedback recibido"""
        try:
            # Obtener feedback histórico similar
            similar_feedback = await self._get_similar_feedback(feedback)
            
            # Identificar patrones nuevos
            new_patterns = []
            
            # Patrón por tipo de feedback
            type_pattern = self._analyze_feedback_type_pattern(feedback, similar_feedback)
            if type_pattern:
                new_patterns.append(type_pattern)
            
            # Patrón por contexto
            context_pattern = self._analyze_context_pattern(feedback, similar_feedback)
            if context_pattern:
                new_patterns.append(context_pattern)
            
            # Patrón por comentarios (NLP básico)
            if feedback.comment:
                comment_pattern = await self._analyze_comment_pattern(feedback)
                if comment_pattern:
                    new_patterns.append(comment_pattern)
            
            # Actualizar patrones existentes
            updated_patterns = []
            for pattern in new_patterns:
                updated_pattern = self._update_or_create_pattern(pattern)
                updated_patterns.append(updated_pattern)
            
            return {
                "new_patterns": new_patterns,
                "updated_patterns": updated_patterns,
                "similar_feedback_count": len(similar_feedback)
            }
            
        except Exception as e:
            logger.error(f"Error analizando patrones de feedback: {e}")
            return {"new_patterns": [], "updated_patterns": []}
    
    async def _get_similar_feedback(self, feedback: FeedbackEntry) -> List[FeedbackEntry]:
        """Obtiene feedback similar del histórico"""
        similar = []
        
        for historical_feedback in self.feedback_history:
            similarity_score = self._calculate_feedback_similarity(feedback, historical_feedback)
            if similarity_score > 0.5:  # Umbral de similitud
                similar.append(historical_feedback)
        
        return similar
    
    def _calculate_feedback_similarity(self, feedback1: FeedbackEntry, feedback2: FeedbackEntry) -> float:
        """Calcula similitud entre dos feedbacks"""
        similarity = 0.0
        
        # Similitud por usuario
        if feedback1.user_id == feedback2.user_id:
            similarity += 0.3
        
        # Similitud por tipo
        if feedback1.feedback_type == feedback2.feedback_type:
            similarity += 0.2
        
        # Similitud por rating
        if feedback1.rating and feedback2.rating:
            rating_diff = abs(feedback1.rating - feedback2.rating)
            similarity += (1 - rating_diff / 4) * 0.2  # Normalizar diferencia de rating
        
        # Similitud por contexto
        context_similarity = self._calculate_context_similarity(
            feedback1.context, feedback2.context
        )
        similarity += context_similarity * 0.3
        
        return min(similarity, 1.0)
    
    def _calculate_context_similarity(self, context1: Dict, context2: Dict) -> float:
        """Calcula similitud entre contextos"""
        if not context1 or not context2:
            return 0.0
        
        common_keys = set(context1.keys()) & set(context2.keys())
        if not common_keys:
            return 0.0
        
        similarity = 0.0
        for key in common_keys:
            if context1[key] == context2[key]:
                similarity += 1.0
        
        return similarity / len(common_keys)
    
    def _analyze_feedback_type_pattern(self, feedback: FeedbackEntry, similar_feedback: List[FeedbackEntry]) -> Optional[LearningPattern]:
        """Analiza patrones por tipo de feedback"""
        if len(similar_feedback) < self.config["min_feedback_for_pattern"]:
            return None
        
        pattern_id = f"type_{feedback.feedback_type}_{feedback.user_id}"
        confidence = min(len(similar_feedback) / 10, 1.0)
        
        if confidence >= self.config["pattern_confidence_threshold"]:
            return LearningPattern(
                pattern_id=pattern_id,
                pattern_type="feedback_type",
                description=f"Usuario {feedback.user_id} tiende a dar feedback {feedback.feedback_type}",
                confidence=confidence,
                occurrences=len(similar_feedback) + 1,
                last_seen=feedback.timestamp,
                impact_score=self._calculate_impact_score(feedback, similar_feedback)
            )
        
        return None
    
    def _analyze_context_pattern(self, feedback: FeedbackEntry, similar_feedback: List[FeedbackEntry]) -> Optional[LearningPattern]:
        """Analiza patrones por contexto"""
        if not feedback.context or len(similar_feedback) < self.config["min_feedback_for_pattern"]:
            return None
        
        # Buscar elementos de contexto comunes
        context_elements = Counter()
        for similar in similar_feedback:
            for key, value in similar.context.items():
                context_elements[f"{key}:{value}"] += 1
        
        # Identificar elemento más común
        if context_elements:
            most_common = context_elements.most_common(1)[0]
            if most_common[1] >= self.config["min_feedback_for_pattern"]:
                pattern_id = f"context_{most_common[0]}_{feedback.user_id}"
                confidence = min(most_common[1] / len(similar_feedback), 1.0)
                
                return LearningPattern(
                    pattern_id=pattern_id,
                    pattern_type="context_pattern",
                    description=f"Contexto '{most_common[0]}' genera feedback {feedback.feedback_type}",
                    confidence=confidence,
                    occurrences=most_common[1],
                    last_seen=feedback.timestamp,
                    impact_score=self._calculate_impact_score(feedback, similar_feedback)
                )
        
        return None
    
    async def _analyze_comment_pattern(self, feedback: FeedbackEntry) -> Optional[LearningPattern]:
        """Analiza patrones en comentarios usando IA"""
        if not feedback.comment or len(feedback.comment) < 10:
            return None
        
        try:
            # Usar Gemini para analizar el comentario
            auth_client = get_auth_client()
            
            analysis_prompt = f"""
            Analiza este comentario de feedback del usuario y extrae:
            1. Sentimiento principal (positivo/negativo/neutral)
            2. Temas principales mencionados
            3. Sugerencias específicas
            4. Nivel de urgencia (bajo/medio/alto)
            
            Comentario: "{feedback.comment}"
            
            Responde en formato JSON con: sentiment, themes, suggestions, urgency
            """
            
            analysis_result = await gemini_actions.analyze_conversation(auth_client, {
                "conversation_data": analysis_prompt,
                "analysis_type": "feedback_analysis"
            })
            
            if analysis_result.get("success"):
                analysis_data = analysis_result.get("data", {})
                
                pattern_id = f"comment_analysis_{feedback.user_id}_{feedback.timestamp.strftime('%Y%m%d')}"
                
                return LearningPattern(
                    pattern_id=pattern_id,
                    pattern_type="comment_analysis",
                    description=f"Análisis de comentario: {analysis_data.get('sentiment', 'neutral')}",
                    confidence=0.8,  # Alta confianza en análisis IA
                    occurrences=1,
                    last_seen=feedback.timestamp,
                    impact_score=self._calculate_comment_impact(analysis_data)
                )
        
        except Exception as e:
            logger.error(f"Error analizando comentario: {e}")
        
        return None
    
    def _calculate_impact_score(self, feedback: FeedbackEntry, similar_feedback: List[FeedbackEntry]) -> float:
        """Calcula el impacto de un patrón"""
        base_score = 0.5
        
        # Impacto por rating
        if feedback.rating:
            rating_impact = (feedback.rating - 3) / 2  # Normalizar -1 a 1
            base_score += rating_impact * 0.3
        
        # Impacto por frecuencia
        frequency_impact = min(len(similar_feedback) / 10, 0.3)
        base_score += frequency_impact
        
        # Impacto por tipo de feedback
        type_impacts = {
            "negative": 0.8,
            "correction": 0.7,
            "suggestion": 0.6,
            "positive": 0.4
        }
        base_score += type_impacts.get(feedback.feedback_type, 0.5) * 0.2
        
        return min(max(base_score, 0.0), 1.0)
    
    def _calculate_comment_impact(self, analysis_data: Dict) -> float:
        """Calcula impacto basado en análisis de comentario"""
        base_score = 0.5
        
        sentiment = analysis_data.get("sentiment", "neutral")
        urgency = analysis_data.get("urgency", "medio")
        
        sentiment_impacts = {"positive": 0.3, "neutral": 0.5, "negative": 0.8}
        urgency_impacts = {"bajo": 0.3, "medio": 0.6, "alto": 0.9}
        
        base_score = sentiment_impacts.get(sentiment, 0.5) * 0.6
        base_score += urgency_impacts.get(urgency, 0.6) * 0.4
        
        return min(max(base_score, 0.0), 1.0)
    
    def _update_or_create_pattern(self, pattern: LearningPattern) -> LearningPattern:
        """Actualiza patrón existente o crea uno nuevo"""
        if pattern.pattern_id in self.learning_patterns:
            existing = self.learning_patterns[pattern.pattern_id]
            existing.occurrences += pattern.occurrences
            existing.last_seen = pattern.last_seen
            existing.confidence = min(
                (existing.confidence + pattern.confidence) / 2 + 0.1, 1.0
            )
            existing.impact_score = max(existing.impact_score, pattern.impact_score)
            return existing
        else:
            self.learning_patterns[pattern.pattern_id] = pattern
            return pattern
    
    async def _generate_improvements(self, feedback: FeedbackEntry) -> List[Dict[str, Any]]:
        """Genera mejoras basadas en feedback"""
        improvements = []
        
        # Mejoras por feedback negativo
        if feedback.feedback_type == "negative" and feedback.rating and feedback.rating <= 2:
            improvements.append({
                "type": "response_adjustment",
                "priority": "high",
                "description": "Ajustar respuestas para usuario con feedback negativo",
                "action": "make_responses_more_detailed"
            })
        
        # Mejoras por sugerencias
        if feedback.feedback_type == "suggestion" and feedback.comment:
            improvements.append({
                "type": "feature_suggestion",
                "priority": "medium",
                "description": f"Implementar sugerencia: {feedback.comment[:100]}",
                "action": "add_suggested_feature"
            })
        
        # Mejoras por correcciones
        if feedback.feedback_type == "correction":
            improvements.append({
                "type": "accuracy_improvement",
                "priority": "high",
                "description": "Mejorar precisión basada en corrección",
                "action": "update_knowledge_base"
            })
        
        return improvements
    
    async def _update_adaptation_rules(self, feedback: FeedbackEntry, learning_result: Dict) -> None:
        """Actualiza reglas de adaptación del asistente"""
        user_id = feedback.user_id
        
        if user_id not in self.adaptation_rules:
            self.adaptation_rules[user_id] = {
                "response_style": "standard",
                "detail_level": "medium",
                "preferred_format": "mixed",
                "feedback_patterns": []
            }
        
        user_rules = self.adaptation_rules[user_id]
        
        # Actualizar basado en rating
        if feedback.rating:
            if feedback.rating <= 2:
                user_rules["detail_level"] = "high"
                user_rules["response_style"] = "careful"
            elif feedback.rating >= 4:
                user_rules["response_style"] = "confident"
        
        # Actualizar basado en tipo de feedback
        if feedback.feedback_type == "negative":
            user_rules["detail_level"] = "high"
        elif feedback.feedback_type == "positive":
            # Mantener estilo actual
            pass
        
        # Agregar patrón de feedback
        user_rules["feedback_patterns"].append({
            "type": feedback.feedback_type,
            "timestamp": feedback.timestamp.isoformat(),
            "context": feedback.context
        })
        
        # Limitar historial de patrones
        if len(user_rules["feedback_patterns"]) > 20:
            user_rules["feedback_patterns"] = user_rules["feedback_patterns"][-20:]
    
    async def get_personalized_suggestions(self, user_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Genera sugerencias personalizadas basadas en aprendizaje"""
        suggestions = []
        
        # Obtener reglas de adaptación del usuario
        user_rules = self.adaptation_rules.get(user_id, {})
        
        # Obtener patrones relevantes
        relevant_patterns = [
            pattern for pattern in self.learning_patterns.values()
            if user_id in pattern.pattern_id and pattern.confidence > 0.6
        ]
        
        # Generar sugerencias basadas en patrones
        for pattern in relevant_patterns:
            if pattern.pattern_type == "feedback_type" and pattern.impact_score > 0.7:
                suggestions.append({
                    "type": "behavioral_adjustment",
                    "description": f"Ajustar comportamiento basado en patrón de {pattern.description}",
                    "confidence": pattern.confidence,
                    "priority": "medium"
                })
        
        # Sugerencias basadas en contexto actual
        if context.get("action_requested"):
            action = context["action_requested"]
            
            # Buscar patrones relacionados con esta acción
            action_patterns = [
                p for p in relevant_patterns 
                if action.lower() in p.description.lower()
            ]
            
            if action_patterns:
                best_pattern = max(action_patterns, key=lambda x: x.confidence)
                suggestions.append({
                    "type": "action_optimization",
                    "description": f"Optimizar {action} basado en experiencia previa",
                    "confidence": best_pattern.confidence,
                    "priority": "high"
                })
        
        return suggestions[:5]  # Limitar a 5 sugerencias

# Instancia global del motor de aprendizaje
learning_engine = LearningEngine()
