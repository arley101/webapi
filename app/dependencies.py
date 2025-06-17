# app/dependencies.py
from fastapi import HTTPException, status
from azure.identity.aio import DefaultAzureCredential
from app.shared.helpers.http_client import AuthenticatedHttpClient
import logging

logger = logging.getLogger(__name__)
http_client_instance: AuthenticatedHttpClient = None

async def initialize_http_client():
    global http_client_instance
    if http_client_instance is None:
        try:
            logger.info("Inicializando DefaultAzureCredential de forma asíncrona...")
            credential = DefaultAzureCredential()
            http_client_instance = AuthenticatedHttpClient(credential)
            logger.info("✅ Cliente HTTP autenticado creado exitosamente.")
        except Exception as e:
            logger.error(f"FATAL: No se pudo inicializar DefaultAzureCredential: {e}")
            http_client_instance = None

def get_authenticated_http_client() -> AuthenticatedHttpClient:
    if http_client_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El cliente HTTP autenticado no está disponible. Revisa los logs de arranque."
        )
    return http_client_instance