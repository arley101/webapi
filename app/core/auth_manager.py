import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class AuthenticatedUser:
    """Representación de un usuario autenticado"""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: list = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []

# Security scheme
security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthenticatedUser:
    """
    Obtiene el usuario actual desde el token de autorización
    Por ahora es una implementación básica, puede ser extendida con validación real de tokens
    """
    if not credentials:
        # Usuario por defecto para desarrollo
        return AuthenticatedUser(
            user_id="default_user",
            email="default@example.com",
            name="Default User",
            tenant_id="default_tenant"
        )
    
    # Aquí puedes agregar validación real del token
    # Por ejemplo, validar JWT, Azure AD, etc.
    
    try:
        # Simular extracción de información del token
        user_id = "user_from_token"  # Extraer del token real
        return AuthenticatedUser(
            user_id=user_id,
            email="user@example.com",
            name="Token User",
            tenant_id="tenant_from_token"
        )
    except Exception as e:
        logger.error(f"Error validando token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

class TokenManager:
    """Gestor automático de tokens que regenera access tokens desde refresh tokens"""
    
    def __init__(self):
        self._cached_tokens = {}
        self._token_expiry = {}
        self._refresh_in_progress = {}  # Evitar múltiples refresh simultáneos
    
    def get_google_access_token(self, service: str = "google_ads") -> str:
        """Genera automáticamente access token desde refresh token"""
        
        # Determinar qué refresh token usar
        if service == "youtube":
            client_id = settings.YOUTUBE_CLIENT_ID or settings.GOOGLE_ADS_CLIENT_ID
            client_secret = settings.YOUTUBE_CLIENT_SECRET or settings.GOOGLE_ADS_CLIENT_SECRET
            refresh_token = settings.YOUTUBE_REFRESH_TOKEN or settings.GOOGLE_ADS_REFRESH_TOKEN
        else:
            client_id = settings.GOOGLE_ADS_CLIENT_ID
            client_secret = settings.GOOGLE_ADS_CLIENT_SECRET
            refresh_token = settings.GOOGLE_ADS_REFRESH_TOKEN
        
        # Verificar si ya tenemos un token válido en cache
        cache_key = f"{service}_access_token"
        if cache_key in self._cached_tokens:
            expiry = self._token_expiry.get(cache_key, datetime.now())
            if datetime.now() < expiry:
                return self._cached_tokens[cache_key]
        
        # Generar nuevo access token
        try:
            response = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                
                # Cachear token por 50 minutos (10 min antes de expirar)
                self._cached_tokens[cache_key] = access_token
                self._token_expiry[cache_key] = datetime.now() + timedelta(seconds=expires_in - 600)
                
                logger.info(f"✅ Token {service} generado automáticamente")
                return access_token
            else:
                logger.error(f"❌ Error generando token {service}: {response.text}")
                raise Exception(f"Error OAuth: {response.status_code}")
                
        except Exception as e:
            logger.error(f"💥 Fallo generando token {service}: {str(e)}")
            raise Exception(f"Token generation failed: {str(e)}")
    
    def get_wordpress_jwt_token(self, site_url: str = None) -> str:
        """Genera automáticamente JWT token para WordPress"""
        
        # Usar site_url del parámetro o variable de entorno
        wp_site = site_url or settings.WP_SITE_URL or "https://elitecosmeticdental.com"
        wp_username = getattr(settings, "WP_JWT_USER", None) or getattr(settings, "WP_USERNAME", None)
        wp_password = getattr(settings, "WP_JWT_PASS", None) or getattr(settings, "WP_PASSWORD", None)
        if not wp_username or not wp_password:
            raise ValueError("WP_JWT_USER/WP_USERNAME y WP_JWT_PASS/WP_PASSWORD deben estar configurados en variables de entorno.")
        
        # Cache key único por sitio
        cache_key = f"wp_jwt_{wp_site.replace('https://', '').replace('http://', '').replace('/', '_')}"
        
        # Verificar si ya tenemos un token válido en cache
        if cache_key in self._cached_tokens:
            expiry = self._token_expiry.get(cache_key, datetime.now())
            if datetime.now() < expiry:
                return self._cached_tokens[cache_key]
        
        # Generar nuevo JWT token
        try:
            response = requests.post(
                f"{wp_site.rstrip('/')}/wp-json/jwt-auth/v1/token",
                json={
                    "username": wp_username,
                    "password": wp_password
                },
                timeout=15
            )
            
            if response.status_code == 200:
                token_data = response.json()
                jwt_token = token_data["token"]
                
                # Cachear token por 50 minutos (JWT dura ~1h, renovamos antes)
                self._cached_tokens[cache_key] = jwt_token
                self._token_expiry[cache_key] = datetime.now() + timedelta(minutes=50)
                
                logger.info(f"✅ WordPress JWT token generado automáticamente para {wp_site}")
                return jwt_token
            else:
                logger.error(f"❌ Error generando WordPress JWT: {response.text}")
                raise Exception(f"WordPress JWT Error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"💥 Fallo generando WordPress JWT: {str(e)}")
            raise Exception(f"WordPress JWT generation failed: {str(e)}")
    
    def get_wordpress_auth(self, site_url: str = None, auth_mode: str = None) -> Dict[str, Any]:
        """Sistema inteligente de autenticación WordPress con múltiples modos"""
        
        # Determinar modo de autenticación
        mode = auth_mode or getattr(settings, 'WP_AUTH_MODE', 'jwt')
        wp_site = site_url or getattr(settings, 'WP_SITE_URL', None)
        
        if not wp_site:
            raise ValueError("WP_SITE_URL es requerido para autenticación WordPress")
        
        try:
            if mode == "jwt":
                return self._get_wordpress_jwt_auth(wp_site)
            elif mode == "app_password":
                return self._get_wordpress_app_password_auth()
            elif mode == "woocommerce":
                return self._get_woocommerce_auth()
            else:
                raise ValueError(f"Modo de autenticación WordPress no válido: {mode}")
        except Exception as e:
            logger.error(f"Error en autenticación WordPress ({mode}): {str(e)}")
            raise
    
    def _get_wordpress_jwt_auth(self, site_url: str) -> Dict[str, Any]:
        """Autenticación JWT (método preferido)"""
        try:
            token = self.get_wordpress_jwt_token(site_url)
            return {
                "type": "jwt",
                "headers": {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            }
        except Exception as e:
            logger.error(f"Error obteniendo JWT token: {str(e)}")
            raise
    
    def _get_wordpress_app_password_auth(self) -> Dict[str, Any]:
        """Autenticación con Application Password"""
        username = getattr(settings, 'WP_USERNAME', None) or getattr(settings, 'WP_JWT_USER', None)
        app_password = getattr(settings, 'WP_APP_PASSWORD', None)
        
        if not username or not app_password:
            raise ValueError("Username y App Password requeridos para autenticación App Password")
        
        import base64
        auth_string = f"{username}:{app_password}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        return {
            "type": "app_password",
            "headers": {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json"
            }
        }
    
    def _get_woocommerce_auth(self) -> Dict[str, Any]:
        """Autenticación WooCommerce"""
        consumer_key = getattr(settings, 'WC_CONSUMER_KEY', None)
        consumer_secret = getattr(settings, 'WC_CONSUMER_SECRET', None)
        
        if not consumer_key or not consumer_secret:
            raise ValueError("Consumer Key y Secret requeridos para WooCommerce")
        
        return {
            "type": "woocommerce",
            "auth": (consumer_key, consumer_secret),
            "headers": {
                "Content-Type": "application/json"
            }
        }
    
    def get_runway_headers(self) -> Dict[str, Any]:
        """
        Headers para autenticación de Runway (RunwayML).
        Requiere variable de entorno RUNWAY_API_KEY.
        """
        api_key = getattr(settings, "RUNWAY_API_KEY", None)
        if not api_key:
            raise ValueError("Falta RUNWAY_API_KEY en variables de entorno de Azure.")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_meta_access_token(self) -> str:
        """Genera automáticamente access token para Meta desde refresh token"""
        cache_key = "meta_access_token"
        
        # Verificar si ya tenemos un token válido
        if cache_key in self._cached_tokens:
            expiry = self._token_expiry.get(cache_key, datetime.now())
            if datetime.now() < expiry:
                return self._cached_tokens[cache_key]
        
        # Evitar múltiples refresh simultáneos
        if self._refresh_in_progress.get(cache_key, False):
            # Esperar un momento y reintentar
            import time
            time.sleep(2)
            return self.get_meta_access_token()
        
        self._refresh_in_progress[cache_key] = True
        
        try:
            # Para Meta, el access token de larga duración se obtiene diferente
            app_id = getattr(settings, "META_ADS_APP_ID", None) or getattr(settings, "META_APP_ID", None)
            app_secret = getattr(settings, "META_ADS_APP_SECRET", None) or getattr(settings, "META_APP_SECRET", None)
            base_token = getattr(settings, "META_ADS_ACCESS_TOKEN", None) or getattr(settings, "META_SYSTEM_USER_TOKEN", None) or getattr(settings, "META_ACCESS_TOKEN", None)
            if not (app_id and app_secret and base_token):
                logger.warning("Variables META_* incompletas. Usando token configurado como fallback.")
                if base_token:
                    self._cached_tokens[cache_key] = base_token
                    self._token_expiry[cache_key] = datetime.now() + timedelta(days=30)
                    return base_token
                return ""
            response = requests.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "fb_exchange_token": base_token
                },
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 5184000)  # 60 días default
                
                # Cachear token
                self._cached_tokens[cache_key] = access_token
                self._token_expiry[cache_key] = datetime.now() + timedelta(seconds=expires_in - 3600)
                
                logger.info("✅ Meta token renovado automáticamente")
                return access_token
            else:
                logger.error(f"❌ Error renovando token Meta: {response.text}")
                # Retornar el token existente como fallback
                return base_token or ""
                
        except Exception as e:
            logger.error(f"💥 Fallo renovando token Meta: {str(e)}")
            return base_token or ""
        finally:
            self._refresh_in_progress[cache_key] = False
    
    def get_linkedin_access_token(self) -> str:
        """Obtiene access token para LinkedIn (por ahora usa el token fijo)"""
        # LinkedIn requiere un flujo OAuth más complejo
        # Por ahora retornamos el token configurado
        return settings.LINKEDIN_ACCESS_TOKEN
    
    def get_tiktok_access_token(self) -> str:
        """Obtiene access token para TikTok"""
        # TikTok también usa tokens de larga duración
        return getattr(settings, "TIKTOK_ADS_ACCESS_TOKEN", None) or getattr(settings, "TIKTOK_ACCESS_TOKEN", None) or ""
    
    def refresh_all_tokens(self) -> Dict[str, bool]:
        """Refresca todos los tokens disponibles"""
        results = {}
        
        # Google (ya implementado)
        try:
            self.get_google_access_token()
            results["google"] = True
        except:
            results["google"] = False
        
        # YouTube
        try:
            self.get_google_access_token("youtube")
            results["youtube"] = True
        except:
            results["youtube"] = False
        
        # Meta
        try:
            self.get_meta_access_token()
            results["meta"] = True
        except:
            results["meta"] = False
        
        # WordPress
        try:
            self.get_wordpress_jwt_token()
            results["wordpress"] = True
        except:
            results["wordpress"] = False
        
        return results

# Instancia global
token_manager = TokenManager()

def get_auth_client():
    """Función helper para compatibilidad con action_mapper"""
    return token_manager
