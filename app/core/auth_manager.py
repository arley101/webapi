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

# Instancia global
token_manager = TokenManager()
