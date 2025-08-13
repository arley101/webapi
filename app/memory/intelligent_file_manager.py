# app/memory/intelligent_file_manager.py
"""
Gestor de Archivos Automático Inteligente
Funcionalidades:
- Guardado automático de imágenes, videos y documentos
- Clasificación inteligente de archivos
- Integración con OneDrive, SharePoint y Notion
- Análisis de contenido y metadatos
- Organización automática
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import json
import os
import mimetypes
import hashlib
from pathlib import Path
from dataclasses import dataclass
import base64
from urllib.parse import urlparse
import re

from app.core.auth_manager import get_auth_client
from app.actions import sharepoint_actions, onedrive_actions, notion_actions, gemini_actions
from .persistent_memory import PersistentMemoryManager

logger = logging.getLogger(__name__)

@dataclass
class FileMetadata:
    """Metadatos de archivo"""
    file_id: str
    original_name: str
    file_type: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    user_id: str
    session_id: str
    source: str  # 'upload', 'generated', 'downloaded', 'extracted'
    content_hash: str
    classification: Dict[str, Any]
    storage_locations: List[str]
    ai_analysis: Optional[Dict[str, Any]]

@dataclass
class FileProcessingResult:
    """Resultado del procesamiento de archivo"""
    success: bool
    file_metadata: Optional[FileMetadata]
    storage_paths: List[str]
    analysis_result: Optional[Dict[str, Any]]
    error_message: Optional[str]

class IntelligentFileManager:
    """Gestor inteligente de archivos con clasificación y organización automática"""
    
    def __init__(self):
        self.persistent_memory = PersistentMemoryManager()
        self.file_cache = {}  # Cache de archivos procesados
        
        # Configuración
        self.config = {
            "auto_classify": True,
            "auto_organize": True,
            "ai_analysis": True,
            "duplicate_detection": True,
            "max_file_size_mb": 100,
            "supported_extensions": {
                "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"],
                "videos": [".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"],
                "documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt"],
                "presentations": [".ppt", ".pptx", ".odp"],
                "spreadsheets": [".xls", ".xlsx", ".csv", ".ods"],
                "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
                "code": [".py", ".js", ".html", ".css", ".json", ".xml", ".md"],
                "archives": [".zip", ".rar", ".7z", ".tar", ".gz"]
            },
            "classification_rules": {
                "work_documents": ["contrato", "propuesta", "informe", "reporte"],
                "personal": ["personal", "family", "vacation", "trip"],
                "projects": ["proyecto", "development", "code", "app"],
                "meetings": ["reunion", "meeting", "agenda", "minutes"],
                "presentations": ["presentacion", "demo", "pitch", "slides"],
                "finance": ["factura", "invoice", "budget", "financial"]
            }
        }
    
    async def process_file_automatically(self, file_data: Union[bytes, str], 
                                        file_name: str, user_id: str, 
                                        session_id: str, source: str = "upload",
                                        additional_context: Dict[str, Any] = None) -> FileProcessingResult:
        """Procesa un archivo automáticamente con clasificación e IA"""
        try:
            # Validar archivo
            validation_result = self._validate_file(file_data, file_name)
            if not validation_result["valid"]:
                return FileProcessingResult(
                    success=False,
                    file_metadata=None,
                    storage_paths=[],
                    analysis_result=None,
                    error_message=validation_result["error"]
                )
            
            # Generar metadatos
            file_metadata = await self._generate_file_metadata(
                file_data, file_name, user_id, session_id, source
            )
            
            # Detectar duplicados
            if self.config["duplicate_detection"]:
                duplicate_check = await self._check_for_duplicates(file_metadata)
                if duplicate_check["is_duplicate"]:
                    return FileProcessingResult(
                        success=True,
                        file_metadata=duplicate_check["existing_metadata"],
                        storage_paths=duplicate_check["existing_paths"],
                        analysis_result=None,
                        error_message="Archivo duplicado - usando versión existente"
                    )
            
            # Clasificar archivo
            classification = await self._classify_file(file_metadata, additional_context)
            file_metadata.classification = classification
            
            # Análisis con IA
            ai_analysis = None
            if self.config["ai_analysis"]:
                ai_analysis = await self._analyze_file_with_ai(file_data, file_metadata)
                file_metadata.ai_analysis = ai_analysis
            
            # Organizar automáticamente
            organization_plan = await self._create_organization_plan(file_metadata)
            
            # Guardar en múltiples ubicaciones
            storage_results = await self._store_file_intelligently(
                file_data, file_metadata, organization_plan
            )
            
            # Actualizar metadatos con ubicaciones de almacenamiento
            file_metadata.storage_locations = storage_results["success_paths"]
            
            # Guardar metadatos en memoria persistente
            await self._save_file_metadata(file_metadata)
            
            # Añadir al cache
            self.file_cache[file_metadata.file_id] = file_metadata
            
            return FileProcessingResult(
                success=True,
                file_metadata=file_metadata,
                storage_paths=storage_results["success_paths"],
                analysis_result=ai_analysis,
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"Error procesando archivo automáticamente: {e}")
            return FileProcessingResult(
                success=False,
                file_metadata=None,
                storage_paths=[],
                analysis_result=None,
                error_message=str(e)
            )
    
    def _validate_file(self, file_data: Union[bytes, str], file_name: str) -> Dict[str, Any]:
        """Valida el archivo antes de procesarlo"""
        try:
            # Validar tamaño
            if isinstance(file_data, str):
                file_size = len(file_data.encode('utf-8'))
            else:
                file_size = len(file_data)
            
            max_size = self.config["max_file_size_mb"] * 1024 * 1024
            if file_size > max_size:
                return {
                    "valid": False,
                    "error": f"Archivo demasiado grande: {file_size / 1024 / 1024:.1f}MB > {self.config['max_file_size_mb']}MB"
                }
            
            # Validar extensión
            file_ext = Path(file_name).suffix.lower()
            all_supported = []
            for ext_list in self.config["supported_extensions"].values():
                all_supported.extend(ext_list)
            
            if file_ext not in all_supported:
                return {
                    "valid": False,
                    "error": f"Tipo de archivo no soportado: {file_ext}"
                }
            
            # Validar nombre de archivo
            if not file_name or len(file_name) > 255:
                return {
                    "valid": False,
                    "error": "Nombre de archivo inválido"
                }
            
            return {"valid": True, "size": file_size, "extension": file_ext}
            
        except Exception as e:
            return {"valid": False, "error": f"Error validando archivo: {e}"}
    
    async def _generate_file_metadata(self, file_data: Union[bytes, str], 
                                     file_name: str, user_id: str, 
                                     session_id: str, source: str) -> FileMetadata:
        """Genera metadatos completos del archivo"""
        file_ext = Path(file_name).suffix.lower()
        mime_type, _ = mimetypes.guess_type(file_name)
        
        # Determinar tipo de archivo
        file_type = "unknown"
        for category, extensions in self.config["supported_extensions"].items():
            if file_ext in extensions:
                file_type = category
                break
        
        # Calcular hash del contenido
        if isinstance(file_data, str):
            content_hash = hashlib.sha256(file_data.encode('utf-8')).hexdigest()
            size_bytes = len(file_data.encode('utf-8'))
        else:
            content_hash = hashlib.sha256(file_data).hexdigest()
            size_bytes = len(file_data)
        
        # Generar ID único
        file_id = f"file_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{content_hash[:8]}"
        
        return FileMetadata(
            file_id=file_id,
            original_name=file_name,
            file_type=file_type,
            mime_type=mime_type or "application/octet-stream",
            size_bytes=size_bytes,
            created_at=datetime.now(),
            user_id=user_id,
            session_id=session_id,
            source=source,
            content_hash=content_hash,
            classification={},
            storage_locations=[],
            ai_analysis=None
        )
    
    async def _check_for_duplicates(self, file_metadata: FileMetadata) -> Dict[str, Any]:
        """Verifica si existe un archivo duplicado"""
        try:
            auth_client = get_auth_client()
            
            # Buscar por hash en SharePoint
            search_result = await sharepoint_actions.search_list_items(auth_client, {
                "list_name": "Elite_File_Metadata",
                "search_query": f"content_hash:{file_metadata.content_hash}",
                "top": 1
            })
            
            if search_result.get("success") and search_result.get("data"):
                existing_file = search_result["data"][0]
                return {
                    "is_duplicate": True,
                    "existing_metadata": existing_file,
                    "existing_paths": json.loads(existing_file.get("storage_locations", "[]"))
                }
            
            return {"is_duplicate": False}
            
        except Exception as e:
            logger.error(f"Error verificando duplicados: {e}")
            return {"is_duplicate": False}
    
    async def _classify_file(self, file_metadata: FileMetadata, 
                           additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Clasifica el archivo automáticamente"""
        classification = {
            "category": "general",
            "subcategory": "",
            "tags": [],
            "confidence": 0.5,
            "auto_classified": True
        }
        
        try:
            file_name_lower = file_metadata.original_name.lower()
            
            # Clasificación por reglas
            for category, keywords in self.config["classification_rules"].items():
                for keyword in keywords:
                    if keyword in file_name_lower:
                        classification["category"] = category
                        classification["confidence"] = 0.8
                        classification["tags"].append(keyword)
                        break
            
            # Clasificación por tipo de archivo
            if file_metadata.file_type in ["images", "videos"]:
                classification["subcategory"] = "media"
            elif file_metadata.file_type in ["documents", "presentations", "spreadsheets"]:
                classification["subcategory"] = "office"
            elif file_metadata.file_type == "code":
                classification["subcategory"] = "development"
                classification["category"] = "projects"
            
            # Usar contexto adicional si está disponible
            if additional_context:
                session_context = additional_context.get("session_context", {})
                if "topics" in session_context:
                    for topic in session_context["topics"]:
                        classification["tags"].append(topic)
                        classification["confidence"] = min(classification["confidence"] + 0.1, 1.0)
            
            # Análisis de fecha en el nombre
            date_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
                r'\d{4}_\d{2}_\d{2}'   # YYYY_MM_DD
            ]
            
            for pattern in date_patterns:
                if re.search(pattern, file_name_lower):
                    classification["tags"].append("dated_document")
                    break
            
            return classification
            
        except Exception as e:
            logger.error(f"Error clasificando archivo: {e}")
            return classification
    
    async def _analyze_file_with_ai(self, file_data: Union[bytes, str], 
                                   file_metadata: FileMetadata) -> Optional[Dict[str, Any]]:
        """Analiza el archivo usando IA"""
        try:
            auth_client = get_auth_client()
            
            # Solo analizar ciertos tipos de archivos
            if file_metadata.file_type not in ["images", "documents"]:
                return None
            
            analysis_prompt = f"""
            Analiza este archivo y proporciona:
            1. Descripción del contenido
            2. Temas principales identificados
            3. Clasificación sugerida
            4. Palabras clave relevantes
            5. Nivel de importancia (1-5)
            
            Archivo: {file_metadata.original_name}
            Tipo: {file_metadata.file_type}
            Tamaño: {file_metadata.size_bytes} bytes
            
            Responde en formato JSON con: description, topics, classification, keywords, importance
            """
            
            # Para archivos de texto, incluir contenido
            if file_metadata.file_type == "documents" and isinstance(file_data, str):
                analysis_prompt += f"\n\nContenido (primeros 1000 caracteres):\n{file_data[:1000]}"
            
            analysis_result = await gemini_actions.analyze_conversation(auth_client, {
                "conversation_data": analysis_prompt,
                "analysis_type": "file_content_analysis"
            })
            
            if analysis_result.get("success"):
                return {
                    "ai_description": analysis_result.get("data", {}).get("description", ""),
                    "ai_topics": analysis_result.get("data", {}).get("topics", []),
                    "ai_classification": analysis_result.get("data", {}).get("classification", ""),
                    "ai_keywords": analysis_result.get("data", {}).get("keywords", []),
                    "ai_importance": analysis_result.get("data", {}).get("importance", 3),
                    "analysis_timestamp": datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error analizando archivo con IA: {e}")
            return None
    
    async def _create_organization_plan(self, file_metadata: FileMetadata) -> Dict[str, Any]:
        """Crea un plan de organización para el archivo"""
        organization_plan = {
            "primary_location": "onedrive",
            "backup_locations": ["sharepoint"],
            "folder_structure": [],
            "naming_convention": "",
            "retention_policy": "standard"
        }
        
        try:
            # Determinar ubicación principal basada en clasificación
            category = file_metadata.classification.get("category", "general")
            
            if category in ["work_documents", "projects", "meetings"]:
                organization_plan["primary_location"] = "sharepoint"
                organization_plan["backup_locations"] = ["onedrive", "notion"]
            elif category == "personal":
                organization_plan["primary_location"] = "onedrive"
                organization_plan["backup_locations"] = ["notion"]
            
            # Crear estructura de carpetas
            folder_structure = ["Elite AI Assistant", "Auto Managed Files"]
            
            # Añadir carpeta por año
            folder_structure.append(str(file_metadata.created_at.year))
            
            # Añadir carpeta por tipo
            folder_structure.append(file_metadata.file_type.title())
            
            # Añadir carpeta por categoría
            if category != "general":
                folder_structure.append(category.replace("_", " ").title())
            
            organization_plan["folder_structure"] = folder_structure
            
            # Convención de nombres
            timestamp = file_metadata.created_at.strftime("%Y%m%d_%H%M%S")
            clean_name = re.sub(r'[^a-zA-Z0-9._-]', '_', file_metadata.original_name)
            organization_plan["naming_convention"] = f"{timestamp}_{clean_name}"
            
            # Política de retención basada en importancia
            ai_importance = 3
            if file_metadata.ai_analysis:
                ai_importance = file_metadata.ai_analysis.get("ai_importance", 3)
            
            if ai_importance >= 4:
                organization_plan["retention_policy"] = "long_term"
            elif ai_importance <= 2:
                organization_plan["retention_policy"] = "short_term"
            
            return organization_plan
            
        except Exception as e:
            logger.error(f"Error creando plan de organización: {e}")
            return organization_plan
    
    async def _store_file_intelligently(self, file_data: Union[bytes, str], 
                                       file_metadata: FileMetadata, 
                                       organization_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Almacena el archivo en múltiples ubicaciones inteligentemente"""
        storage_results = {
            "success_paths": [],
            "failed_paths": [],
            "errors": []
        }
        
        try:
            auth_client = get_auth_client()
            
            # Preparar datos del archivo
            if isinstance(file_data, str):
                file_content = file_data.encode('utf-8')
            else:
                file_content = file_data
            
            # Codificar en base64 para transferencia
            file_content_b64 = base64.b64encode(file_content).decode('utf-8')
            
            # Crear estructura de carpetas
            folder_path = "/".join(organization_plan["folder_structure"])
            file_name = organization_plan["naming_convention"]
            
            # Almacenar en ubicación principal
            primary_location = organization_plan["primary_location"]
            
            if primary_location == "onedrive":
                onedrive_result = await self._store_in_onedrive(
                    auth_client, file_content_b64, file_name, folder_path, file_metadata
                )
                if onedrive_result["success"]:
                    storage_results["success_paths"].append(f"onedrive:{onedrive_result['path']}")
                else:
                    storage_results["failed_paths"].append("onedrive")
                    storage_results["errors"].append(onedrive_result.get("error", "Error desconocido"))
            
            elif primary_location == "sharepoint":
                sharepoint_result = await self._store_in_sharepoint(
                    auth_client, file_content_b64, file_name, folder_path, file_metadata
                )
                if sharepoint_result["success"]:
                    storage_results["success_paths"].append(f"sharepoint:{sharepoint_result['path']}")
                else:
                    storage_results["failed_paths"].append("sharepoint")
                    storage_results["errors"].append(sharepoint_result.get("error", "Error desconocido"))
            
            # Almacenar en ubicaciones de respaldo
            for backup_location in organization_plan["backup_locations"]:
                if backup_location == "notion":
                    notion_result = await self._store_in_notion(
                        auth_client, file_metadata, organization_plan
                    )
                    if notion_result["success"]:
                        storage_results["success_paths"].append(f"notion:{notion_result['page_id']}")
                    else:
                        storage_results["failed_paths"].append("notion")
                        storage_results["errors"].append(notion_result.get("error", "Error desconocido"))
                
                elif backup_location == "onedrive" and primary_location != "onedrive":
                    onedrive_result = await self._store_in_onedrive(
                        auth_client, file_content_b64, f"backup_{file_name}", folder_path, file_metadata
                    )
                    if onedrive_result["success"]:
                        storage_results["success_paths"].append(f"onedrive_backup:{onedrive_result['path']}")
                
                elif backup_location == "sharepoint" and primary_location != "sharepoint":
                    sharepoint_result = await self._store_in_sharepoint(
                        auth_client, file_content_b64, f"backup_{file_name}", folder_path, file_metadata
                    )
                    if sharepoint_result["success"]:
                        storage_results["success_paths"].append(f"sharepoint_backup:{sharepoint_result['path']}")
            
            return storage_results
            
        except Exception as e:
            logger.error(f"Error almacenando archivo inteligentemente: {e}")
            storage_results["errors"].append(str(e))
            return storage_results
    
    async def _store_in_onedrive(self, auth_client, file_content_b64: str, 
                                file_name: str, folder_path: str, 
                                file_metadata: FileMetadata) -> Dict[str, Any]:
        """Almacena archivo en OneDrive"""
        try:
            # Crear estructura de carpetas si no existe
            await onedrive_actions.create_folder(auth_client, {
                "folder_path": folder_path
            })
            
            # Subir archivo
            upload_result = await onedrive_actions.upload_file(auth_client, {
                "file_content": file_content_b64,
                "file_name": file_name,
                "folder_path": folder_path,
                "content_type": file_metadata.mime_type
            })
            
            if upload_result.get("success"):
                return {
                    "success": True,
                    "path": f"{folder_path}/{file_name}",
                    "file_id": upload_result.get("data", {}).get("id", "")
                }
            else:
                return {"success": False, "error": upload_result.get("message", "Error subiendo a OneDrive")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _store_in_sharepoint(self, auth_client, file_content_b64: str, 
                                  file_name: str, folder_path: str, 
                                  file_metadata: FileMetadata) -> Dict[str, Any]:
        """Almacena archivo en SharePoint"""
        try:
            # Subir archivo directamente a SharePoint
            upload_result = await sharepoint_actions.upload_file(auth_client, {
                "file_content": file_content_b64,
                "file_name": file_name,
                "folder_path": folder_path,
                "content_type": file_metadata.mime_type,
                "site_name": "Elite AI Assistant"
            })
            
            if upload_result.get("success"):
                return {
                    "success": True,
                    "path": f"{folder_path}/{file_name}",
                    "file_id": upload_result.get("data", {}).get("id", "")
                }
            else:
                return {"success": False, "error": upload_result.get("message", "Error subiendo a SharePoint")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _store_in_notion(self, auth_client, file_metadata: FileMetadata, 
                              organization_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Almacena información del archivo en Notion"""
        try:
            # Crear página en Notion con metadatos del archivo
            notion_data = {
                "database_name": "Elite File Registry",
                "properties": {
                    "File Name": file_metadata.original_name,
                    "File ID": file_metadata.file_id,
                    "File Type": file_metadata.file_type,
                    "Size (MB)": round(file_metadata.size_bytes / 1024 / 1024, 2),
                    "Created At": file_metadata.created_at.isoformat(),
                    "User ID": file_metadata.user_id,
                    "Category": file_metadata.classification.get("category", "general"),
                    "Tags": ", ".join(file_metadata.classification.get("tags", [])),
                    "Storage Locations": ", ".join(file_metadata.storage_locations),
                    "Content Hash": file_metadata.content_hash,
                    "AI Analysis": json.dumps(file_metadata.ai_analysis, indent=2) if file_metadata.ai_analysis else "No analysis available"
                }
            }
            
            result = await notion_actions.create_page(auth_client, notion_data)
            
            if result.get("success"):
                return {
                    "success": True,
                    "page_id": result.get("data", {}).get("id", "")
                }
            else:
                return {"success": False, "error": result.get("message", "Error creando página en Notion")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _save_file_metadata(self, file_metadata: FileMetadata) -> None:
        """Guarda metadatos del archivo en SharePoint"""
        try:
            auth_client = get_auth_client()
            
            metadata_data = {
                "list_name": "Elite_File_Metadata",
                "item_data": {
                    "file_id": file_metadata.file_id,
                    "original_name": file_metadata.original_name,
                    "file_type": file_metadata.file_type,
                    "mime_type": file_metadata.mime_type,
                    "size_bytes": file_metadata.size_bytes,
                    "created_at": file_metadata.created_at.isoformat(),
                    "user_id": file_metadata.user_id,
                    "session_id": file_metadata.session_id,
                    "source": file_metadata.source,
                    "content_hash": file_metadata.content_hash,
                    "classification": json.dumps(file_metadata.classification),
                    "storage_locations": json.dumps(file_metadata.storage_locations),
                    "ai_analysis": json.dumps(file_metadata.ai_analysis) if file_metadata.ai_analysis else ""
                }
            }
            
            await sharepoint_actions.create_list_item(auth_client, metadata_data)
            
        except Exception as e:
            logger.error(f"Error guardando metadatos de archivo: {e}")
    
    async def search_files_intelligently(self, user_id: str, search_query: str, 
                                        filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Busca archivos usando IA y metadatos"""
        try:
            auth_client = get_auth_client()
            
            # Construir consulta de búsqueda
            search_filters = f"user_id:{user_id}"
            
            if filters:
                if filters.get("file_type"):
                    search_filters += f" AND file_type:{filters['file_type']}"
                if filters.get("category"):
                    search_filters += f" AND classification:{filters['category']}"
                if filters.get("date_from"):
                    search_filters += f" AND created_at ge '{filters['date_from']}'"
                if filters.get("date_to"):
                    search_filters += f" AND created_at le '{filters['date_to']}'"
            
            # Buscar en metadatos
            search_result = await sharepoint_actions.search_list_items(auth_client, {
                "list_name": "Elite_File_Metadata",
                "search_query": f"{search_query} AND {search_filters}",
                "top": 50
            })
            
            if not search_result.get("success"):
                return {"success": False, "error": "Error buscando archivos"}
            
            files = search_result.get("data", [])
            
            # Enriquecer resultados con análisis de relevancia
            enriched_files = []
            for file_data in files:
                try:
                    file_info = {
                        "file_id": file_data.get("file_id", ""),
                        "name": file_data.get("original_name", ""),
                        "type": file_data.get("file_type", ""),
                        "size": file_data.get("size_bytes", 0),
                        "created": file_data.get("created_at", ""),
                        "classification": json.loads(file_data.get("classification", "{}")),
                        "storage_locations": json.loads(file_data.get("storage_locations", "[]")),
                        "ai_analysis": json.loads(file_data.get("ai_analysis", "{}")) if file_data.get("ai_analysis") else None,
                        "relevance_score": self._calculate_relevance_score(search_query, file_data)
                    }
                    enriched_files.append(file_info)
                except Exception as e:
                    logger.warning(f"Error procesando archivo en búsqueda: {e}")
                    continue
            
            # Ordenar por relevancia
            enriched_files.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            return {
                "success": True,
                "files": enriched_files,
                "total_found": len(enriched_files),
                "search_query": search_query,
                "filters_applied": filters or {}
            }
            
        except Exception as e:
            logger.error(f"Error en búsqueda inteligente de archivos: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_relevance_score(self, search_query: str, file_data: Dict) -> float:
        """Calcula score de relevancia para un archivo"""
        score = 0.0
        query_lower = search_query.lower()
        
        # Relevancia por nombre
        name = file_data.get("original_name", "").lower()
        if query_lower in name:
            score += 0.5
        
        # Relevancia por clasificación
        classification = json.loads(file_data.get("classification", "{}"))
        for tag in classification.get("tags", []):
            if query_lower in tag.lower():
                score += 0.2
        
        # Relevancia por análisis IA
        ai_analysis = file_data.get("ai_analysis", "")
        if ai_analysis:
            try:
                ai_data = json.loads(ai_analysis)
                for keyword in ai_data.get("ai_keywords", []):
                    if query_lower in keyword.lower():
                        score += 0.3
                
                description = ai_data.get("ai_description", "").lower()
                if query_lower in description:
                    score += 0.4
            except:
                pass
        
        return min(score, 1.0)

# Instancia global del gestor de archivos inteligente
intelligent_file_manager = IntelligentFileManager()
