# app/shared/helpers/http_client.py
# VERSIÓN FINAL Y COMPLETA

import httpx
from azure.identity.aio import DefaultAzureCredential
from typing import Any, Dict, Optional

class AuthenticatedHttpClient:
    def __init__(self, credential: DefaultAzureCredential):
        self._credential = credential
        self._token = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _get_token(self) -> str:
        # En el futuro, se puede añadir lógica para refrescar el token si expira.
        if not self._token or self._token.is_expired:
            self._token = await self._credential.get_token("https://graph.microsoft.com/.default")
        return self._token.token

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        token = await self._get_token()
        headers = kwargs.pop('headers', {})
        headers.setdefault("Authorization", f"Bearer {token}")
        headers.setdefault("Content-Type", "application/json")
        
        return await self._client.request(method, url, headers=headers, **kwargs)

    # --- MÉTODOS DE CONVENIENCIA AÑADIDOS ---
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        return await self.request("GET", url, params=params)

    async def post(self, url: str, json: Optional[Dict[str, Any]] = None, data: Any = None) -> httpx.Response:
        return await self.request("POST", url, json=json, data=data)

    async def patch(self, url: str, json: Optional[Dict[str, Any]] = None) -> httpx.Response:
        return await self.request("PATCH", url, json=json)

    async def put(self, url: str, content: Any, headers: Optional[Dict[str, Any]] = None) -> httpx.Response:
        return await self.request("PUT", url, content=content, headers=headers)

    async def delete(self, url: str) -> httpx.Response:
        return await self.request("DELETE", url)