# app/core/config.py
import os
import logging  # ← YA TIENES ESTE IMPORT CORRECTO
from typing import List, Optional, Union 
from pydantic import HttpUrl, field_validator, Field 
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv() 

class GoogleAdsCredentials(BaseSettings):
    CLIENT_ID: Optional[str] = None
    CLIENT_SECRET: Optional[str] = None
    DEVELOPER_TOKEN: Optional[str] = None
    REFRESH_TOKEN: Optional[str] = None 
    LOGIN_CUSTOMER_ID: Optional[str] = None 
    model_config = SettingsConfigDict(env_prefix='GOOGLE_ADS_', env_file='.env', extra='ignore')

class MetaAdsCredentials(BaseSettings):
    APP_ID: Optional[str] = None
    APP_SECRET: Optional[str] = None 
    ACCESS_TOKEN: Optional[str] = None 
    BUSINESS_ACCOUNT_ID: Optional[str] = None 
    model_config = SettingsConfigDict(env_prefix='META_ADS_', env_file='.env', extra='ignore')

class TikTokAdsCredentials(BaseSettings):
    ACCESS_TOKEN: Optional[str] = None
    APP_ID: Optional[str] = None
    DEFAULT_ADVERTISER_ID: Optional[str] = None
    model_config = SettingsConfigDict(env_prefix='TIKTOK_ADS_', env_file='.env', extra='ignore')

class XAdsCredentials(BaseSettings):
    CONSUMER_KEY: Optional[str] = None
    CONSUMER_SECRET: Optional[str] = None
    ACCESS_TOKEN: Optional[str] = None
    ACCESS_TOKEN_SECRET: Optional[str] = None
    ACCOUNT_ID: Optional[str] = None
    model_config = SettingsConfigDict(env_prefix='X_ADS_', env_file='.env', extra='ignore')

class Settings(BaseSettings):
    # App Configuration
    APP_NAME: str = "EliteDynamicsAPI"
    APP_VERSION: str = "1.1.0"  # ⬅️ Actualizar versión
    API_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Environment Detection
    ENVIRONMENT: str = Field(default="development", description="Current environment")
    
    # Microsoft Graph API
    GRAPH_API_BASE_URL: HttpUrl = "https://graph.microsoft.com/v1.0" # type: ignore
    AZURE_MGMT_API_BASE_URL: HttpUrl = "https://management.azure.com" # type: ignore

    GRAPH_API_DEFAULT_SCOPE: List[str] = ["https://graph.microsoft.com/.default"]
    AZURE_MGMT_DEFAULT_SCOPE: List[str] = ["https://management.azure.com/.default"]
    POWER_BI_DEFAULT_SCOPE: str = "https://analysis.windows.net/powerbi/api/.default"

    # Azure OpenAI
    AZURE_OPENAI_RESOURCE_ENDPOINT: Optional[str] = None 
    OPENAI_API_DEFAULT_SCOPE: Optional[List[str]] = None 
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview" 

    # SharePoint & Lists
    MEMORIA_LIST_NAME: str = "AsistenteMemoria" 
    SHAREPOINT_DEFAULT_SITE_ID: Optional[str] = None 
    SHAREPOINT_DEFAULT_DRIVE_ID_OR_NAME: Optional[str] = "Documents" 

    # API Configuration
    DEFAULT_API_TIMEOUT: int = 90 
    MAILBOX_USER_ID: str = "me" 

    # GitHub
    GITHUB_PAT: Optional[str] = None 

    # Power BI
    PBI_TENANT_ID: Optional[str] = None
    PBI_CLIENT_ID: Optional[str] = None
    PBI_CLIENT_SECRET: Optional[str] = None

    # Azure / Entra ID
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    AZURE_SUBSCRIPTION_ID: Optional[str] = None 
    AZURE_RESOURCE_GROUP: Optional[str] = None  

    # Social Media & Ads Credentials
    GOOGLE_ADS: GoogleAdsCredentials = GoogleAdsCredentials()
    META_ADS: MetaAdsCredentials = MetaAdsCredentials()
    TIKTOK_ADS: TikTokAdsCredentials = TikTokAdsCredentials()
    X_ADS: XAdsCredentials = XAdsCredentials()
    
    LINKEDIN_ACCESS_TOKEN: Optional[str] = None
    DEFAULT_LINKEDIN_AD_ACCOUNT_ID: Optional[str] = None 

    # Third Party APIs
    NOTION_API_KEY: Optional[str] = Field(default=None, alias="NOTION_API_TOKEN")
    NOTION_API_VERSION: str = "2022-06-28"

    HUBSPOT_PRIVATE_APP_KEY: Optional[str] = Field(default=None, alias="HUBSPOT_PRIVATE_APP_TOKEN")

    YOUTUBE_API_KEY: Optional[str] = None
    YOUTUBE_ACCESS_TOKEN: Optional[str] = None

    # Runway (IA de video)
    RUNWAY_API_KEY: Optional[str] = None

    GEMINI_API_KEY: Optional[str] = Field(None, env="GEMINI_API_KEY")
    GEMINI_API_URL: str = Field(
        "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
        env="GEMINI_API_URL"
    )
    GEMINI_PROJECT_ID: Optional[str] = Field(None, env="GEMINI_PROJECT_ID")
    GEMINI_LOCATION: str = Field("us-central1", env="GEMINI_LOCATION")
    GEMINI_MODEL: str = Field("gemini-1.5-flash", env="GEMINI_MODEL")
    GEMINI_TEMPERATURE: float = Field(0.7, env="GEMINI_TEMPERATURE")
    GEMINI_MAX_TOKENS: int = Field(8192, env="GEMINI_MAX_TOKENS")

    # Google Ads Configuration
    GOOGLE_ADS_CLIENT_ID: Optional[str] = Field(None, env="GOOGLE_ADS_CLIENT_ID")
    GOOGLE_ADS_CLIENT_SECRET: Optional[str] = Field(None, env="GOOGLE_ADS_CLIENT_SECRET")
    GOOGLE_ADS_REFRESH_TOKEN: Optional[str] = Field(None, env="GOOGLE_ADS_REFRESH_TOKEN")
    GOOGLE_ADS_LOGIN_CUSTOMER_ID: Optional[str] = Field(None, env="GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    GOOGLE_ADS_DEVELOPER_TOKEN: Optional[str] = Field(None, env="GOOGLE_ADS_DEVELOPER_TOKEN")
    
    # YouTube Configuration - SEPARADAS DE GOOGLE ADS
    YOUTUBE_CLIENT_ID: Optional[str] = Field(None, env="YOUTUBE_CLIENT_ID")
    YOUTUBE_CLIENT_SECRET: Optional[str] = Field(None, env="YOUTUBE_CLIENT_SECRET")
    YOUTUBE_REFRESH_TOKEN: Optional[str] = Field(None, env="YOUTUBE_REFRESH_TOKEN")

    # WordPress Authentication Configuration
    WP_AUTH_MODE: Optional[str] = Field(default="jwt", description="WordPress auth mode: jwt|app_password|woocommerce")
    
    # WordPress JWT Configuration (método preferido y que funciona)
    WP_SITE_URL: Optional[str] = Field(default="https://elitecosmeticdental.com")
    WP_JWT_USERNAME: Optional[str] = Field(default="Arleyadmin")
    WP_JWT_PASSWORD: Optional[str] = Field(default="U7M0$f34@Ju@N90|2=2=*|")

    # Alternate env var names seen in Azure settings
    WP_JWT_USER: Optional[str] = None
    WP_JWT_PASS: Optional[str] = None
    WP_JWT_SECRET: Optional[str] = None
    
    # WordPress App Password (fallback)
    WP_USERNAME: Optional[str] = None
    WP_PASSWORD: Optional[str] = None
    WP_APP_PASSWORD: Optional[str] = None
    
    # WooCommerce REST API (para e-commerce)
    WC_CONSUMER_KEY: Optional[str] = None
    WC_CONSUMER_SECRET: Optional[str] = None
    
    # NUEVO: Validator para mostrar el estado de configuración
    def model_post_init(self, __context) -> None:
        """Post-initialization para logging de configuración."""
        logger = logging.getLogger(__name__)
        
        # Log estado de YouTube vs Google Ads credentials
        youtube_configured = bool(self.YOUTUBE_CLIENT_ID and self.YOUTUBE_CLIENT_SECRET and self.YOUTUBE_REFRESH_TOKEN)
        google_ads_configured = bool(self.GOOGLE_ADS_CLIENT_ID and self.GOOGLE_ADS_CLIENT_SECRET and self.GOOGLE_ADS_REFRESH_TOKEN)
        
        if youtube_configured:
            logger.info("🎥 YouTube: Credenciales específicas configuradas")
        elif google_ads_configured:
            logger.info("🎥 YouTube: Usando credenciales de Google Ads como fallback")
        else:
            logger.warning("⚠️ YouTube: Sin credenciales configuradas")

    @field_validator("OPENAI_API_DEFAULT_SCOPE", mode='before')
    @classmethod
    def assemble_openai_scope(cls, v: Optional[List[str]], values) -> Optional[List[str]]: 
        current_values_data = values.data if hasattr(values, 'data') else values 
        if current_values_data.get("AZURE_OPENAI_RESOURCE_ENDPOINT") and not v: 
            endpoint = str(current_values_data["AZURE_OPENAI_RESOURCE_ENDPOINT"])
            if endpoint.startswith("https://"): 
                return [f"{endpoint.rstrip('/')}/.default"]
        return v 

    @field_validator("LOG_LEVEL")
    @classmethod
    def log_level_must_be_valid(cls, value: str) -> str:
        valid_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]
        if value.upper() not in valid_levels:
            raise ValueError(f"Invalid LOG_LEVEL: '{value}'. Must be one of {valid_levels}.")
        return value.upper()
    
    # ⬅️ NUEVO: Validator para environment
    @field_validator("ENVIRONMENT")
    @classmethod
    def environment_must_be_valid(cls, value: str) -> str:
        valid_envs = ["development", "staging", "production"]
        if value.lower() not in valid_envs:
            raise ValueError(f"Invalid ENVIRONMENT: '{value}'. Must be one of {valid_envs}.")
        return value.lower()

    model_config = SettingsConfigDict(
        env_file='.env', 
        env_file_encoding='utf-8',
        extra='ignore', 
        case_sensitive=False 
    )

# ⬅️ NUEVO: Environment detection helper
def get_environment() -> str:
    """Detect current environment based on Azure App Service environment variables"""
    if os.getenv('WEBSITE_SITE_NAME'):  # Azure App Service
        return "production"
    elif os.getenv('GITHUB_ACTIONS'):   # GitHub Actions
        return "staging"
    else:
        return "development"

# Settings instance with environment detection
settings = Settings(ENVIRONMENT=get_environment())

# Logging de configuración cargada
logger = logging.getLogger(__name__)
logger.info(f"Configuración cargada para {settings.APP_NAME} v{settings.APP_VERSION}")
logger.info(f"SharePoint Site ID: {'Configurado' if settings.SHAREPOINT_DEFAULT_SITE_ID else 'No configurado'}")
logger.info(f"Notion configurado: {'Sí' if settings.NOTION_API_KEY else 'No'}")
logger.info(f"Gemini configurado: {'Sí' if settings.GEMINI_API_KEY else 'No'}")
logger.info(f"Runway configurado: {'Sí' if settings.RUNWAY_API_KEY else 'No'}")

# Cargar variables desde .env en desarrollo local
from pathlib import Path
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    import dotenv
    dotenv.load_dotenv(env_path)
    logger.info("Variables de entorno cargadas desde .env")

# Mejora para debugging de YouTube
logger.info(f"YouTube: {'Credenciales configuradas' if settings.YOUTUBE_CLIENT_ID else 'Sin credenciales configuradas'}")