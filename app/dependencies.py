from fastapi import HTTPException, status
from azure.identity.aio import DefaultAzureCredential
from app.shared.helpers.http_client import AuthenticatedHttpClient
import logging

logger = logging.getLogger(__name__)

http_client_instance: AuthenticatedHttpClient = None

async def initialize_http_client():
    """Crea la instancia del cliente HTTP al arrancar la aplicación."""
    global http_client_instance
    if http_client_instance is None:
        try:
            credential = DefaultAzureCredential()
            http_client_instance = AuthenticatedHttpClient(credential)
            logger.info("✅ Cliente HTTP autenticado creado exitosamente.")
        except Exception as e:
            logger.error(f"FATAL: No se pudo inicializar DefaultAzureCredential: {e}")
            http_client_instance = None

async def shutdown_http_client():
    """Cierra la sesión del cliente HTTP al apagar la aplicación."""
    global http_client_instance
    if http_client_instance:
        await http_client_instance.close()
        logger.info("Cliente HTTP cerrado exitosamente.")

def get_authenticated_http_client() -> AuthenticatedHttpClient:
    """Dependencia de FastAPI que provee la instancia del cliente."""
    if http_client_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cliente HTTP no disponible. Revisar logs de arranque."
        )
    return http_client_instance