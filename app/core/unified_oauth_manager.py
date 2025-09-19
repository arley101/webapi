# app/core/unified_oauth_manager.py
"""
🔒 SISTEMA OAUTH UNIFICADO Y AUTOMATIZADO
Reemplaza todos los módulos de autenticación fragmentados.
Maneja refresh automático de tokens para Google, YouTube, Meta, LinkedIn, etc.
"""

import os
import json
import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

@dataclass
class TokenInfo:
    """Información de token con metadata"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = "Bearer"
    scopes: List[str] = field(default_factory=list)
    service: str = ""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None

class UnifiedOAuthManager:
    """
    🎯 GESTOR OAUTH UNIFICADO
    - Maneja TODOS los servicios OAuth desde un solo lugar
    - Refresh automático en background
    - Cache inteligente con expiración
    - Fallback a tokens de backup
    """
    
    def __init__(self):
        self._tokens: Dict[str, TokenInfo] = {}
        self._refresh_locks: Dict[str, asyncio.Lock] = {}
        self._refresh_tasks: Dict[str, asyncio.Task] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._background_task = None
        
        # Configurar servicios
        self._setup_service_configs()
        
        # El background task se iniciará cuando se use por primera vez
        self._background_started = False
    
    def _setup_service_configs(self):
        """Configura todos los servicios OAuth"""
        self.service_configs = {
            "google": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_ADS_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
                "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN") or os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": [
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/calendar',
                    'https://www.googleapis.com/auth/drive.file',
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/adwords'
                ]
            },
            "youtube": {
                "client_id": os.getenv("YOUTUBE_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET"), 
                "refresh_token": os.getenv("YOUTUBE_REFRESH_TOKEN") or os.getenv("GOOGLE_REFRESH_TOKEN"),
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": [
                    'https://www.googleapis.com/auth/youtube.upload',
                    'https://www.googleapis.com/auth/youtube.readonly',
                    'https://www.googleapis.com/auth/youtube.force-ssl'
                ]
            },
            "meta": {
                "app_id": os.getenv("META_ADS_APP_ID") or os.getenv("META_APP_ID"),
                "app_secret": os.getenv("META_ADS_APP_SECRET") or os.getenv("META_APP_SECRET"),
                "access_token": os.getenv("META_ADS_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN"),
                "token_url": "https://graph.facebook.com/v18.0/oauth/access_token"
            },
            "linkedin": {
                "access_token": os.getenv("LINKEDIN_ACCESS_TOKEN"),
                "client_id": os.getenv("LINKEDIN_CLIENT_ID"),
                "client_secret": os.getenv("LINKEDIN_CLIENT_SECRET")
            },
            "tiktok": {
                "access_token": os.getenv("TIKTOK_ADS_ACCESS_TOKEN") or os.getenv("TIKTOK_ACCESS_TOKEN"),
                "client_id": os.getenv("TIKTOK_CLIENT_ID"),
                "client_secret": os.getenv("TIKTOK_CLIENT_SECRET")
            }
        }
    
    async def get_access_token(self, service: str) -> str:
        """
        🎯 MÉTODO PRINCIPAL - Obtiene access token válido para cualquier servicio
        Maneja refresh automático y cache inteligente
        """
        service = service.lower()
        
        # Iniciar background task si no está iniciado
        if not self._background_started:
            try:
                self._background_task = asyncio.create_task(self._background_refresh_loop())
                self._background_started = True
                logger.info("🔄 Background refresh task iniciado")
            except RuntimeError:
                # No hay event loop activo, será manejado más tarde
                pass
        
        # Verificar si ya tenemos token válido en cache
        if service in self._tokens:
            token_info = self._tokens[service]
            if token_info.expires_at and datetime.now() < token_info.expires_at:
                logger.debug(f"✅ Token {service} válido desde cache")
                return token_info.access_token
        
        # Obtener o crear lock para este servicio
        if service not in self._refresh_locks:
            self._refresh_locks[service] = asyncio.Lock()
        
        async with self._refresh_locks[service]:
            # Double-check por si otro thread ya refrescó
            if service in self._tokens:
                token_info = self._tokens[service]
                if token_info.expires_at and datetime.now() < token_info.expires_at:
                    return token_info.access_token
            
            # Refresh token según el tipo de servicio
            if service in ["google", "youtube"]:
                return await self._refresh_google_token(service)
            elif service == "meta":
                return await self._refresh_meta_token()
            elif service == "linkedin":
                return self._get_linkedin_token()
            elif service == "tiktok":
                return self._get_tiktok_token()
            else:
                raise ValueError(f"Servicio OAuth no soportado: {service}")
    
    async def _refresh_google_token(self, service: str) -> str:
        """Refresca tokens Google/YouTube de forma unificada"""
        config = self.service_configs.get(service, {})
        
        if not all([config.get("client_id"), config.get("client_secret"), config.get("refresh_token")]):
            raise ValueError(f"Configuración OAuth incompleta para {service}")
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                lambda: requests.post(
                    config["token_url"],
                    data={
                        "client_id": config["client_id"],
                        "client_secret": config["client_secret"],
                        "refresh_token": config["refresh_token"],
                        "grant_type": "refresh_token"
                    },
                    timeout=10
                )
            )
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                
                # Cachear token con 10 min de buffer
                self._tokens[service] = TokenInfo(
                    access_token=access_token,
                    refresh_token=config["refresh_token"],
                    expires_at=datetime.now() + timedelta(seconds=expires_in - 600),
                    service=service,
                    scopes=config.get("scopes", []),
                    client_id=config["client_id"],
                    client_secret=config["client_secret"]
                )
                
                logger.info(f"✅ Token {service} refrescado automáticamente")
                return access_token
            else:
                logger.error(f"❌ Error refrescando token {service}: {response.text}")
                raise Exception(f"OAuth refresh failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"💥 Fallo crítico refrescando token {service}: {str(e)}")
            raise
    
    async def _refresh_meta_token(self) -> str:
        """Refresca token Meta/Facebook"""
        config = self.service_configs.get("meta", {})
        
        app_id = config.get("app_id")
        app_secret = config.get("app_secret") 
        base_token = config.get("access_token")
        
        if not all([app_id, app_secret, base_token]):
            logger.warning("Configuración Meta incompleta, usando token estático")
            if base_token:
                # Cachear token estático por 30 días
                self._tokens["meta"] = TokenInfo(
                    access_token=base_token,
                    expires_at=datetime.now() + timedelta(days=30),
                    service="meta"
                )
                return base_token
            raise ValueError("Token Meta no disponible")
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                lambda: requests.get(
                    config["token_url"],
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": app_id,
                        "client_secret": app_secret,
                        "fb_exchange_token": base_token
                    },
                    timeout=10
                )
            )
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 5184000)  # 60 días
                
                self._tokens["meta"] = TokenInfo(
                    access_token=access_token,
                    expires_at=datetime.now() + timedelta(seconds=expires_in - 3600),
                    service="meta"
                )
                
                logger.info("✅ Token Meta renovado automáticamente")
                return access_token
            else:
                logger.error(f"❌ Error renovando token Meta: {response.text}")
                # Fallback al token base
                return base_token
                
        except Exception as e:
            logger.error(f"💥 Fallo renovando token Meta: {str(e)}")
            return base_token or ""
    
    def _get_linkedin_token(self) -> str:
        """Obtiene token LinkedIn (por ahora estático)"""
        config = self.service_configs.get("linkedin", {})
        token = config.get("access_token", "")
        
        if token:
            # Cachear por 60 días (LinkedIn tokens duran mucho)
            self._tokens["linkedin"] = TokenInfo(
                access_token=token,
                expires_at=datetime.now() + timedelta(days=60),
                service="linkedin"
            )
        
        return token
    
    def _get_tiktok_token(self) -> str:
        """Obtiene token TikTok (por ahora estático)"""
        config = self.service_configs.get("tiktok", {})
        token = config.get("access_token", "")
        
        if token:
            # Cachear por 60 días  
            self._tokens["tiktok"] = TokenInfo(
                access_token=token,
                expires_at=datetime.now() + timedelta(days=60),
                service="tiktok"
            )
        
        return token
    
    async def _background_refresh_loop(self):
        """
        🔄 BUCLE DE REFRESH AUTOMÁTICO EN BACKGROUND
        Se ejecuta cada 30 minutos para renovar tokens próximos a vencer
        """
        while True:
            try:
                await asyncio.sleep(1800)  # 30 minutos
                
                current_time = datetime.now()
                refresh_threshold = current_time + timedelta(minutes=30)  # Renovar si vence en 30 min
                
                for service, token_info in self._tokens.items():
                    if token_info.expires_at and token_info.expires_at < refresh_threshold:
                        logger.info(f"🔄 Renovando token {service} en background...")
                        try:
                            await self.get_access_token(service)
                        except Exception as e:
                            logger.error(f"Error en refresh background {service}: {e}")
                
            except Exception as e:
                logger.error(f"Error en bucle background refresh: {e}")
                await asyncio.sleep(300)  # Esperar 5 min si hay error
    
    def get_google_service(self, service_name: str, version: str = None):
        """
        🔧 CONSTRUCTOR DE SERVICIOS GOOGLE UNIFICADO
        Reemplaza los constructores duplicados en módulos separados
        """
        versions = {
            "gmail": "v1",
            "calendar": "v3", 
            "drive": "v3",
            "sheets": "v4",
            "youtube": "v3"
        }
        
        version = version or versions.get(service_name, "v1")
        
        try:
            # Obtener token sincrónicamente (para compatibilidad)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Si hay un loop corriendo, crear una tarea
                    token = asyncio.run_coroutine_threadsafe(
                        self.get_access_token("google" if service_name != "youtube" else "youtube"),
                        loop
                    ).result(timeout=30)
                else:
                    token = loop.run_until_complete(self.get_access_token("google" if service_name != "youtube" else "youtube"))
            except RuntimeError:
                # No hay event loop, crear uno nuevo
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    token = loop.run_until_complete(self.get_access_token("google" if service_name != "youtube" else "youtube"))
                finally:
                    loop.close()
            
            # Construir credenciales  
            config = self.service_configs.get("google" if service_name != "youtube" else "youtube")
            credentials = Credentials(
                token=token,
                refresh_token=config["refresh_token"],
                id_token=None,
                token_uri=config["token_url"],
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                scopes=config["scopes"]
            )
            
            return build(service_name, version, credentials=credentials)
            
        except Exception as e:
            logger.error(f"Error construyendo servicio Google {service_name}: {e}")
            raise
    
    async def get_headers(self, service: str) -> Dict[str, str]:
        """Obtiene headers de autorización para HTTP requests"""
        token = await self.get_access_token(service)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def refresh_all_tokens(self) -> Dict[str, bool]:
        """Refresca todos los tokens configurados"""
        results = {}
        
        for service in self.service_configs.keys():
            try:
                await self.get_access_token(service)
                results[service] = True
                logger.info(f"✅ Token {service} refrescado exitosamente")
            except Exception as e:
                results[service] = False
                logger.error(f"❌ Error refrescando {service}: {e}")
        
        return results
    
    def get_token_status(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene estado de todos los tokens"""
        status = {}
        current_time = datetime.now()
        
        for service, token_info in self._tokens.items():
            if token_info.expires_at:
                time_left = token_info.expires_at - current_time
                status[service] = {
                    "valid": time_left.total_seconds() > 0,
                    "expires_in_minutes": int(time_left.total_seconds() / 60),
                    "expires_at": token_info.expires_at.isoformat(),
                    "scopes": token_info.scopes
                }
            else:
                status[service] = {
                    "valid": bool(token_info.access_token),
                    "expires_in_minutes": "unknown",
                    "expires_at": "never",
                    "scopes": token_info.scopes
                }
        
        return status

# 🌟 INSTANCIA GLOBAL UNIFICADA
unified_oauth = UnifiedOAuthManager()

# 🔄 FUNCIONES DE COMPATIBILIDAD (para no romper código existente)
async def get_google_access_token(service: str = "google") -> str:
    """Compatibilidad con código existente"""
    return await unified_oauth.get_access_token(service)

async def get_youtube_access_token() -> str:
    """Compatibilidad con código existente"""
    return await unified_oauth.get_access_token("youtube")

async def get_meta_access_token() -> str:
    """Compatibilidad con código existente"""
    return await unified_oauth.get_access_token("meta")

def get_google_service(service_name: str, version: str = None):
    """Compatibilidad con código existente"""
    return unified_oauth.get_google_service(service_name, version)