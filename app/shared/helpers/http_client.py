# app/shared/helpers/http_client.py
import httpx
from azure.identity.aio import DefaultAzureCredential

class AuthenticatedHttpClient:
    def __init__(self, credential: DefaultAzureCredential):
        self._credential = credential
        self._token = None
        # Usamos un cliente asíncrono
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _get_token(self):
        # En un futuro, se podría añadir lógica para refrescar el token si expira
        if not self._token:
            self._token = await self._credential.get_token("https://graph.microsoft.com/.default")
        return self._token.token

    async def request(self, method: str, url: str, **kwargs):
        token = await self._get_token()
        headers = kwargs.pop('headers', {})
        headers["Authorization"] = f"Bearer {token}"
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        response = await self._client.request(method, url, headers=headers, **kwargs)
        return response