# app/dependencies.py
from fastapi import Request, HTTPException, status
from azure.identity import DefaultAzureCredential, CredentialUnavailableError
from app.shared.helpers.http_client import AuthenticatedHttpClient

def get_authenticated_http_client(request: Request) -> AuthenticatedHttpClient:
    """
    Crea y provee una instancia del cliente HTTP autenticado con DefaultAzureCredential.
    Reutiliza la instancia si ya existe en el estado de la solicitud actual para eficiencia.
    """
    if hasattr(request.state, "auth_http_client"):
        return request.state.auth_http_client
    
    try:
        credential = DefaultAzureCredential()
        # Aquí puedes añadir lógica para verificar si la credencial es válida si es necesario
        client = AuthenticatedHttpClient(credential=credential)
        request.state.auth_http_client = client
        return client
    except CredentialUnavailableError as e:
        # Este error es crítico y significa que el backend no puede autenticarse con Azure.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo inicializar la credencial de Azure: {e}"
        )
    except Exception as e:
        # Captura cualquier otro error inesperado durante la inicialización
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al crear el cliente de autenticación: {e}"
        )