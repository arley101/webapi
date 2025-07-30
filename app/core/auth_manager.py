import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class TokenManager:
    """Gestor automático de tokens que regenera access tokens desde refresh tokens"""
    
    def __init__(self):
        self._cached_tokens = {}
        self._token_expiry = {}
    
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
        wp_username = settings.WP_JWT_USERNAME or settings.WP_USERNAME or "Arleyadmin"
        wp_password = settings.WP_JWT_PASSWORD or settings.WP_PASSWORD or "U7M0$f34@Ju@N90|2=2=*|"
        
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
        username = getattr(settings, 'WP_USERNAME', None) or getattr(settings, 'WP_JWT_USERNAME', None)
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

# Instancia global
token_manager = TokenManager()
