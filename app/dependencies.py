# app/dependencies.py

from fastapi import HTTPException, status
from azure.identity import DefaultAzureCredential
from app.shared.helpers.http_client import AuthenticatedHttpClient
import logging

logger = logging.getLogger(__name__)

# Se crea una única instancia del cliente al iniciar la aplicación.
# Esto es mucho más eficiente que crear uno nuevo para cada solicitud,
# ya que aprovecha la caché de tokens de DefaultAzureCredential y las conexiones de red.
try:
    logger.info("Inicializando DefaultAzureCredential para el cliente HTTP...")
    credential = DefaultAzureCredential()
    http_client_instance = AuthenticatedHttpClient(credential)
    logger.info("✅ Cliente HTTP autenticado creado exitosamente.")
except Exception as e:
    # Si la app no puede crear la credencial al inicio, no puede funcionar.
    # Es mejor que falle rápido y claramente.
    logger.error(f"FATAL: No se pudo inicializar DefaultAzureCredential: {e}")
    raise RuntimeError(f"Fallo crítico al inicializar DefaultAzureCredential: {e}") from e

def get_authenticated_http_client() -> AuthenticatedHttpClient:
    """
    Dependencia de FastAPI que provee la instancia compartida
    del cliente HTTP autenticado a cada endpoint que lo necesite.
    """
    if not http_client_instance:
         raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El cliente HTTP autenticado no está disponible."
        )
    return http_client_instance