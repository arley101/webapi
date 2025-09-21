# app/core/token_refresh_manager.py
"""
Sistema de refresh automático de tokens OAuth
Maneja renovación automática de tokens para Google, YouTube, LinkedIn, Meta, TikTok, etc.
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
import aiofiles
import aiohttp
import schedule
import threading
import time
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class TokenInfo:
    """Información completa de un token OAuth"""
    service: str
    user_id: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    token_type: str = "Bearer"
    created_at: datetime = None
    last_refreshed: Optional[datetime] = None
    refresh_count: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def is_expired(self) -> bool:
        """Verifica si el token está expirado"""
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at
    
    def expires_soon(self, minutes: int = 10) -> bool:
        """Verifica si el token expira pronto"""
        if not self.expires_at:
            return False
        return datetime.now() >= (self.expires_at - timedelta(minutes=minutes))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario serializable"""
        result = asdict(self)
        # Convertir datetimes a ISO strings
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenInfo':
        """Crea instancia desde diccionario"""
        # Convertir ISO strings a datetime
        datetime_fields = ['expires_at', 'created_at', 'last_refreshed']
        for field in datetime_fields:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        return cls(**data)

class EncryptedTokenStorage:
    """Storage seguro y encriptado para tokens"""
    
    def __init__(self, storage_path: str = "tokens_encrypted.json"):
        self.storage_path = storage_path
        self.encryption_key = self._get_or_create_key()
        self.fernet = Fernet(self.encryption_key)
        
    def _get_or_create_key(self) -> bytes:
        """Obtiene o crea clave de encriptación"""
        key_path = "token_encryption.key"
        
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, 'wb') as f:
                f.write(key)
            logger.info("🔐 Nueva clave de encriptación generada")
            return key
    
    async def save_token(self, token_info: TokenInfo):
        """Guarda token encriptado"""
        try:
            # Cargar tokens existentes
            tokens = await self.load_all_tokens()
            
            # Actualizar o agregar token
            key = f"{token_info.service}_{token_info.user_id}"
            tokens[key] = token_info.to_dict()
            
            # Encriptar y guardar
            encrypted_data = self.fernet.encrypt(json.dumps(tokens).encode())
            
            async with aiofiles.open(self.storage_path, 'wb') as f:
                await f.write(encrypted_data)
                
            logger.info(f"💾 Token {token_info.service} guardado para user {token_info.user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando token: {e}")
    
    async def load_token(self, service: str, user_id: str) -> Optional[TokenInfo]:
        """Carga token específico"""
        try:
            tokens = await self.load_all_tokens()
            key = f"{service}_{user_id}"
            
            if key in tokens:
                return TokenInfo.from_dict(tokens[key])
            return None
            
        except Exception as e:
            logger.error(f"❌ Error cargando token {service}: {e}")
            return None
    
    async def load_all_tokens(self) -> Dict[str, Dict]:
        """Carga todos los tokens"""
        try:
            if not os.path.exists(self.storage_path):
                return {}
            
            async with aiofiles.open(self.storage_path, 'rb') as f:
                encrypted_data = await f.read()
            
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
            
        except Exception as e:
            logger.error(f"❌ Error cargando tokens: {e}")
            return {}
    
    async def delete_token(self, service: str, user_id: str):
        """Elimina token específico"""
        try:
            tokens = await self.load_all_tokens()
            key = f"{service}_{user_id}"
            
            if key in tokens:
                del tokens[key]
                
                encrypted_data = self.fernet.encrypt(json.dumps(tokens).encode())
                async with aiofiles.open(self.storage_path, 'wb') as f:
                    await f.write(encrypted_data)
                    
                logger.info(f"🗑️ Token {service} eliminado para user {user_id}")
                
        except Exception as e:
            logger.error(f"❌ Error eliminando token: {e}")

class OAuthRefreshService:
    """Servicio para renovar tokens OAuth específicos"""
    
    def __init__(self):
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtiene sesión HTTP reutilizable"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def refresh_google_token(self, token_info: TokenInfo) -> Optional[TokenInfo]:
        """Refresca token de Google/YouTube"""
        if not token_info.refresh_token:
            logger.error("❌ No refresh token disponible para Google")
            return None
        
        try:
            session = await self._get_session()
            
            data = {
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'refresh_token': token_info.refresh_token,
                'grant_type': 'refresh_token'
            }
            
            async with session.post('https://oauth2.googleapis.com/token', data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    
                    # Actualizar token info
                    token_info.access_token = token_data['access_token']
                    token_info.expires_at = datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
                    token_info.last_refreshed = datetime.now()
                    token_info.refresh_count += 1
                    
                    # Actualizar refresh token si se proporciona uno nuevo
                    if 'refresh_token' in token_data:
                        token_info.refresh_token = token_data['refresh_token']
                    
                    logger.info(f"✅ Token Google/{token_info.service} refrescado exitosamente")
                    return token_info
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Error refrescando Google token: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"💥 Error refrescando Google token: {e}")
            return None
    
    async def refresh_meta_token(self, token_info: TokenInfo) -> Optional[TokenInfo]:
        """Refresca token de Meta/Facebook"""
        try:
            session = await self._get_session()
            
            # Meta tokens se refrescan intercambiando por uno nuevo
            url = f"https://graph.facebook.com/oauth/access_token"
            params = {
                'grant_type': 'fb_exchange_token',
                'client_id': settings.META_APP_ID,
                'client_secret': settings.META_APP_SECRET,
                'fb_exchange_token': token_info.access_token
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    token_data = await response.json()
                    
                    token_info.access_token = token_data['access_token']
                    expires_in = token_data.get('expires_in', 5184000)  # 60 días por defecto
                    token_info.expires_at = datetime.now() + timedelta(seconds=expires_in)
                    token_info.last_refreshed = datetime.now()
                    token_info.refresh_count += 1
                    
                    logger.info(f"✅ Token Meta refrescado exitosamente")
                    return token_info
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Error refrescando Meta token: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"💥 Error refrescando Meta token: {e}")
            return None
    
    async def refresh_linkedin_token(self, token_info: TokenInfo) -> Optional[TokenInfo]:
        """Refresca token de LinkedIn"""
        if not token_info.refresh_token:
            logger.error("❌ No refresh token disponible para LinkedIn")
            return None
        
        try:
            session = await self._get_session()
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': token_info.refresh_token,
                'client_id': settings.LINKEDIN_CLIENT_ID,
                'client_secret': settings.LINKEDIN_CLIENT_SECRET,
            }
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            
            async with session.post('https://www.linkedin.com/oauth/v2/accessToken', 
                                    data=data, headers=headers) as response:
                if response.status == 200:
                    token_data = await response.json()
                    
                    token_info.access_token = token_data['access_token']
                    token_info.expires_at = datetime.now() + timedelta(seconds=token_data.get('expires_in', 5184000))
                    token_info.last_refreshed = datetime.now()
                    token_info.refresh_count += 1
                    
                    if 'refresh_token' in token_data:
                        token_info.refresh_token = token_data['refresh_token']
                    
                    logger.info(f"✅ Token LinkedIn refrescado exitosamente")
                    return token_info
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Error refrescando LinkedIn token: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"💥 Error refrescando LinkedIn token: {e}")
            return None
    
    async def close(self):
        """Cierra la sesión HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()

class TokenRefreshManager:
    """Manager principal para refresh automático de tokens"""
    
    def __init__(self):
        self.storage = EncryptedTokenStorage()
        self.refresh_service = OAuthRefreshService()
        self.scheduler_thread = None
        self.is_running = False
        
        # Mapeo de servicios a métodos de refresh
        self.refresh_methods = {
            'google': self.refresh_service.refresh_google_token,
            'youtube': self.refresh_service.refresh_google_token,
            'gmail': self.refresh_service.refresh_google_token,
            'meta': self.refresh_service.refresh_meta_token,
            'facebook': self.refresh_service.refresh_meta_token,
            'instagram': self.refresh_service.refresh_meta_token,
            'linkedin': self.refresh_service.refresh_linkedin_token,
        }
    
    async def save_token(self, token_info: TokenInfo):
        """Guarda token en storage seguro"""
        await self.storage.save_token(token_info)
    
    async def get_valid_token(self, service: str, user_id: str = "default") -> Optional[TokenInfo]:
        """Obtiene un token válido, refrescándolo si es necesario"""
        token_info = await self.storage.load_token(service, user_id)
        
        if not token_info:
            logger.warning(f"⚠️ No se encontró token para {service}")
            return None
        
        # Si el token expira pronto, refrescarlo
        if token_info.expires_soon():
            logger.info(f"🔄 Token {service} expira pronto, refrescando...")
            refreshed_token = await self.refresh_token(token_info)
            if refreshed_token:
                await self.storage.save_token(refreshed_token)
                return refreshed_token
            else:
                logger.error(f"❌ No se pudo refrescar token {service}")
                return token_info  # Devolver el expirado como último recurso
        
        return token_info
    
    async def refresh_token(self, token_info: TokenInfo) -> Optional[TokenInfo]:
        """Refresca un token específico"""
        refresh_method = self.refresh_methods.get(token_info.service.lower())
        
        if not refresh_method:
            logger.warning(f"⚠️ No hay método de refresh para {token_info.service}")
            return None
        
        try:
            return await refresh_method(token_info)
        except Exception as e:
            logger.error(f"💥 Error refrescando token {token_info.service}: {e}")
            return None
    
    async def refresh_all_expiring_tokens(self):
        """Refresca todos los tokens que expiran pronto"""
        logger.info("🔄 Revisando tokens que necesitan refresh...")
        
        all_tokens = await self.storage.load_all_tokens()
        refresh_count = 0
        
        for key, token_data in all_tokens.items():
            try:
                token_info = TokenInfo.from_dict(token_data)
                
                if token_info.expires_soon(minutes=15):  # 15 minutos antes
                    logger.info(f"🔄 Refrescando token {token_info.service} para {token_info.user_id}")
                    
                    refreshed_token = await self.refresh_token(token_info)
                    if refreshed_token:
                        await self.storage.save_token(refreshed_token)
                        refresh_count += 1
                        logger.info(f"✅ Token {token_info.service} refrescado exitosamente")
                    else:
                        logger.error(f"❌ Fallo refrescando token {token_info.service}")
                        
            except Exception as e:
                logger.error(f"💥 Error procesando token {key}: {e}")
        
        logger.info(f"🔄 Refresh automático completado: {refresh_count} tokens refrescados")
        return refresh_count
    
    def start_automatic_refresh(self, interval_minutes: int = 15):
        """Inicia el sistema de refresh automático"""
        if self.is_running:
            logger.warning("⚠️ Sistema de refresh ya está ejecutándose")
            return
        
        logger.info(f"🚀 Iniciando sistema de refresh automático cada {interval_minutes} minutos")
        
        # Configurar schedule
        schedule.every(interval_minutes).minutes.do(self._schedule_refresh)
        
        # Ejecutar la primera vez inmediatamente
        self._schedule_refresh()
        
        # Iniciar thread del scheduler
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("✅ Sistema de refresh automático iniciado")
    
    def stop_automatic_refresh(self):
        """Detiene el sistema de refresh automático"""
        self.is_running = False
        schedule.clear()
        logger.info("🛑 Sistema de refresh automático detenido")
    
    def _schedule_refresh(self):
        """Ejecuta refresh en el event loop principal"""
        try:
            # Crear nuevo event loop en el thread del scheduler
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.refresh_all_expiring_tokens())
            loop.close()
        except Exception as e:
            logger.error(f"💥 Error en refresh automático: {e}")
    
    def _run_scheduler(self):
        """Ejecuta el scheduler en un thread separado"""
        logger.info("📅 Scheduler de tokens iniciado")
        
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
        
        logger.info("📅 Scheduler de tokens terminado")
    
    async def get_token_status(self) -> Dict[str, Any]:
        """Obtiene estado de todos los tokens"""
        all_tokens = await self.storage.load_all_tokens()
        status = {
            'total_tokens': len(all_tokens),
            'tokens': [],
            'expiring_soon': 0,
            'expired': 0,
            'healthy': 0
        }
        
        for key, token_data in all_tokens.items():
            try:
                token_info = TokenInfo.from_dict(token_data)
                
                token_status = {
                    'service': token_info.service,
                    'user_id': token_info.user_id,
                    'expires_at': token_info.expires_at.isoformat() if token_info.expires_at else None,
                    'is_expired': token_info.is_expired,
                    'expires_soon': token_info.expires_soon(),
                    'refresh_count': token_info.refresh_count,
                    'last_refreshed': token_info.last_refreshed.isoformat() if token_info.last_refreshed else None
                }
                
                status['tokens'].append(token_status)
                
                if token_info.is_expired:
                    status['expired'] += 1
                elif token_info.expires_soon():
                    status['expiring_soon'] += 1
                else:
                    status['healthy'] += 1
                    
            except Exception as e:
                logger.error(f"💥 Error procesando estado de token {key}: {e}")
        
        return status
    
    async def cleanup(self):
        """Limpia recursos"""
        self.stop_automatic_refresh()
        await self.refresh_service.close()

# Instancia global
token_refresh_manager = TokenRefreshManager()