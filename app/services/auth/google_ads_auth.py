"""
Sistema de autenticación automática para Google Ads API
Maneja renovación automática de tokens OAuth2
"""

import os
import logging
from typing import Optional
from datetime import datetime, timedelta
from google.ads.googleads.client import GoogleAdsClient
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

class GoogleAdsAuthManager:
    """
    Gestor de autenticación para Google Ads con renovación automática de tokens
    """
    
    _instance = None
    _client = None
    _credentials = None
    _token_expiry = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializar el gestor de autenticación"""
        self.client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
        self.refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
        self.developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
        self.login_customer_id = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    
    def _create_credentials(self) -> Credentials:
        """
        Crear objeto Credentials de Google OAuth2
        """
        credentials = Credentials(
            token=None,  # El access token se obtendrá automáticamente
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=["https://www.googleapis.com/auth/adwords"]
        )
        
        return credentials
    
    def _refresh_access_token(self, credentials: Credentials) -> Credentials:
        """
        Renovar el access token usando el refresh token
        """
        try:
            request = Request()
            credentials.refresh(request)
            
            # Actualizar tiempo de expiración
            self._token_expiry = datetime.now() + timedelta(seconds=3600)
            
            logger.info("✅ Access token renovado exitosamente")
            logger.info(f"   Expira en: {self._token_expiry.isoformat()}")
            
            return credentials
            
        except Exception as e:
            logger.error(f"❌ Error renovando access token: {e}")
            raise ValueError(
                f"No se pudo renovar el access token. "
                f"El refresh_token podría estar expirado. "
                f"Error: {str(e)}"
            )
    
    def _is_token_expired(self) -> bool:
        """
        Verificar si el token está expirado o próximo a expirar
        """
        if self._token_expiry is None:
            return True
        
        # Considerar expirado si faltan menos de 5 minutos
        buffer = timedelta(minutes=5)
        return datetime.now() >= (self._token_expiry - buffer)
    
    def get_client(self) -> GoogleAdsClient:
        """
        Obtener cliente de Google Ads con renovación automática de tokens
        """
        # Si ya existe un cliente y el token no está expirado, retornarlo
        if self._client and not self._is_token_expired():
            logger.debug("✅ Usando cliente de Google Ads existente (token válido)")
            return self._client
        
        logger.info("🔄 Inicializando nuevo cliente de Google Ads...")
        
        # Validar credenciales
        if not all([
            self.client_id,
            self.client_secret,
            self.refresh_token,
            self.developer_token
        ]):
            raise ValueError(
                "Faltan credenciales de Google Ads. Verifica que estén configuradas: "
                "GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET, "
                "GOOGLE_ADS_REFRESH_TOKEN, GOOGLE_ADS_DEVELOPER_TOKEN"
            )
        
        try:
            # Crear credenciales OAuth2
            credentials = self._create_credentials()
            
            # Renovar access token
            credentials = self._refresh_access_token(credentials)
            
            # Crear configuración para Google Ads Client
            config = {
                "developer_token": self.developer_token,
                "use_proto_plus": True,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
            }
            
            # Agregar login_customer_id si existe
            if self.login_customer_id:
                config["login_customer_id"] = self.login_customer_id.replace("-", "")
            
            # Crear cliente
            self._client = GoogleAdsClient.load_from_dict(config)
            self._credentials = credentials
            
            logger.info("✅ Cliente de Google Ads inicializado correctamente")
            logger.info(f"   Login Customer ID: {self.login_customer_id}")
            logger.info(f"   Token expira: {self._token_expiry.isoformat()}")
            
            return self._client
            
        except Exception as e:
            logger.error(f"❌ Error inicializando cliente de Google Ads: {e}")
            
            # Si el error es por token expirado, dar instrucciones claras
            if "invalid_grant" in str(e).lower() or "expired" in str(e).lower():
                error_msg = (
                    "❌ El REFRESH_TOKEN de Google Ads está EXPIRADO o REVOCADO.\n\n"
                    "Para generar un nuevo token, ejecuta:\n\n"
                    "python3 -c \"\n"
                    "from google_auth_oauthlib.flow import InstalledAppFlow\n"
                    "flow = InstalledAppFlow.from_client_config(\n"
                    "    {'installed': {\n"
                    f"        'client_id': '{self.client_id}',\n"
                    f"        'client_secret': '{self.client_secret}',\n"
                    "        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',\n"
                    "        'token_uri': 'https://oauth2.googleapis.com/token'\n"
                    "    }},\n"
                    "    scopes=['https://www.googleapis.com/auth/adwords']\n"
                    ")\n"
                    "creds = flow.run_local_server(port=0)\n"
                    "print(f'\\\\nNuevo REFRESH_TOKEN:\\\\n{creds.refresh_token}')\n"
                    "\"\n\n"
                    "Luego actualiza GOOGLE_ADS_REFRESH_TOKEN en tu .env y en Azure."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            raise ValueError(f"Error inicializando Google Ads Client: {str(e)}")
    
    def refresh_client(self) -> GoogleAdsClient:
        """
        Forzar renovación del cliente y del token
        """
        logger.info("🔄 Forzando renovación del cliente de Google Ads...")
        self._client = None
        self._token_expiry = None
        return self.get_client()


# Instancia global del gestor
_auth_manager = GoogleAdsAuthManager()


def get_google_ads_client() -> GoogleAdsClient:
    """
    Función pública para obtener el cliente de Google Ads
    con renovación automática de tokens
    """
    return _auth_manager.get_client()


def refresh_google_ads_client() -> GoogleAdsClient:
    """
    Función pública para forzar renovación del cliente
    """
    return _auth_manager.refresh_client()
