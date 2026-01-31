"""HTTP client wrapper for the Bambuddy REST API."""

import os

import httpx


class BambuddyAPIError(Exception):
    """Raised when the Bambuddy REST API returns a non-2xx response."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class BambuddyClient:
    """Async HTTP client for the Bambuddy REST API.

    Configuration via environment variables:
        BAMBUDDY_URL     - Base URL (default: http://localhost:8000)
        BAMBUDDY_API_KEY - API key for authentication (optional)
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.base_url = (
            base_url or os.environ.get("BAMBUDDY_URL", "http://localhost:8000")
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("BAMBUDDY_API_KEY", "")
        self.api_prefix = "/api/v1"
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {"Accept": "application/json"}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _url(self, path: str) -> str:
        return f"{self.api_prefix}{path}"

    async def get(self, path: str, params: dict | None = None) -> dict | list:
        client = await self._ensure_client()
        resp = await client.get(self._url(path), params=params)
        if resp.status_code >= 400:
            raise BambuddyAPIError(resp.status_code, resp.text[:500])
        return resp.json()

    async def post(
        self, path: str, json: dict | None = None, params: dict | None = None
    ) -> dict | list:
        client = await self._ensure_client()
        resp = await client.post(self._url(path), json=json, params=params)
        if resp.status_code >= 400:
            raise BambuddyAPIError(resp.status_code, resp.text[:500])
        return resp.json()

    async def patch(self, path: str, json: dict | None = None) -> dict | list:
        client = await self._ensure_client()
        resp = await client.patch(self._url(path), json=json)
        if resp.status_code >= 400:
            raise BambuddyAPIError(resp.status_code, resp.text[:500])
        return resp.json()

    async def delete(self, path: str, params: dict | None = None) -> dict | list:
        client = await self._ensure_client()
        resp = await client.delete(self._url(path), params=params)
        if resp.status_code >= 400:
            raise BambuddyAPIError(resp.status_code, resp.text[:500])
        return resp.json()
