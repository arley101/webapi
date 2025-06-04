# app/core/config.py
import os
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

class Settings(BaseSettings):
    APP_NAME: str = "EliteDynamicsAPI"
    APP_VERSION: str = "1.1.0" 
    API_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO" 

    GRAPH_API_BASE_URL: HttpUrl = "https://graph.microsoft.com/v1.0" # type: ignore
    AZURE_MGMT_API_BASE_URL: HttpUrl = "https://management.azure.com" # type: ignore

    GRAPH_API_DEFAULT_SCOPE: List[str] = ["https://graph.microsoft.com/.default"]
    AZURE_MGMT_DEFAULT_SCOPE: List[str] = ["https://management.azure.com/.default"]
    POWER_BI_DEFAULT_SCOPE: List[str] = ["https://analysis.windows.net/powerbi/api/.default"]

    AZURE_OPENAI_RESOURCE_ENDPOINT: Optional[str] = None 
    OPENAI_API_DEFAULT_SCOPE: Optional[List[str]] = None 
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview" 

    MEMORIA_LIST_NAME: str = "AsistenteMemoria" 
    SHAREPOINT_DEFAULT_SITE_ID: Optional[str] = None 
    SHAREPOINT_DEFAULT_DRIVE_ID_OR_NAME: Optional[str] = "Documents" 

    DEFAULT_API_TIMEOUT: int = 90 
    MAILBOX_USER_ID: str = "me" 

    GITHUB_PAT: Optional[str] = None 

    PBI_TENANT_ID: Optional[str] = None
    PBI_CLIENT_ID: Optional[str] = None
    PBI_CLIENT_SECRET: Optional[str] = None

    AZURE_CLIENT_ID_MGMT: Optional[str] = Field(default=None, validation_alias='AZURE_CLIENT_ID') 
    AZURE_CLIENT_SECRET_MGMT: Optional[str] = Field(default=None, validation_alias='AZURE_CLIENT_SECRET')
    AZURE_TENANT_ID_MGMT: Optional[str] = Field(default=None, validation_alias='AZURE_TENANT_ID')
    AZURE_SUBSCRIPTION_ID: Optional[str] = None 
    AZURE_RESOURCE_GROUP: Optional[str] = None  

    GOOGLE_ADS: GoogleAdsCredentials = GoogleAdsCredentials()
    META_ADS: MetaAdsCredentials = MetaAdsCredentials()
    TIKTOK_ADS: TikTokAdsCredentials = TikTokAdsCredentials()
    
    LINKEDIN_ACCESS_TOKEN: Optional[str] = None
    DEFAULT_LINKEDIN_AD_ACCOUNT_ID: Optional[str] = None 

    NOTION_API_TOKEN: Optional[str] = None 
    NOTION_API_VERSION: str = "2022-06-28" 
    
    HUBSPOT_PRIVATE_APP_TOKEN: Optional[str] = None 
    
    YOUTUBE_API_KEY: Optional[str] = None 
    YOUTUBE_ACCESS_TOKEN: Optional[str] = None
    YOUTUBE_CLIENT_ID: Optional[str] = None # Añadido para consistencia con tus datos
    YOUTUBE_CLIENT_SECRET: Optional[str] = None # Añadido para consistencia con tus datos


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

    model_config = SettingsConfigDict(
        env_file='.env', 
        env_file_encoding='utf-8',
        extra='ignore', 
        case_sensitive=False 
    )

settings = Settings()