"""Cliente para gestionar contactos y negocios (deals) en HubSpot.

Capacidades:
- upsert_contact():    crear o actualizar un contacto identificándolo por email.
- get_contact():       obtener un contacto por Id o por email.
- search_contacts():   buscar contactos por texto libre.
- create_deal():       crear un negocio, opcionalmente asociado a un contacto.
- delete_contact() / delete_deal():  NO soportados — lanzan HubSpotDataError.

Autenticación: Private App Access Token (Bearer estático) u OAuth 2.0 con
usuario (refresh token gestionado por la plataforma), según cómo se haya
configurado el conector. Las credenciales SIEMPRE provienen de variables
de entorno RUVIC_HUBSPOT_* (ver config.HubSpotConfig.from_env). Prohibido
hardcodearlas.
"""

from __future__ import annotations

import time
from typing import Any

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

from .config import HubSpotConfig
from .exceptions import HubSpotAuthError, HubSpotDataError, HubSpotNetworkError
from .logging_utils import get_logger

# Propiedades por defecto que se piden al buscar/leer contactos, para no
# traer únicamente el Id.
_DEFAULT_CONTACT_PROPERTIES = ("email", "firstname", "lastname", "phone", "company")


class HubSpotClient:
    """Cliente de HubSpot autenticado con Private App Access Token u OAuth2.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_HUBSPOT_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = HubSpotClient()  # lee RUVIC_HUBSPOT_* del entorno
        >>> client.search_contacts("Acme")
        [{'id': '12345', 'properties': {'email': '...', ...}}]
    """

    def __init__(self, config: HubSpotConfig | None = None) -> None:
        self.config = config or HubSpotConfig.from_env()
        self._logger = get_logger()
        self._oauth_access_token: str | None = None
        self._oauth_token_expires_at: float = 0.0

    # ------------------------------------------------------------------ #
    # OAuth2: obtención/renovación de access token vía refresh_token
    # ------------------------------------------------------------------ #

    def _get_oauth_access_token(self) -> str:
        """Obtiene un access token válido, renovándolo con el refresh_token
        si no hay uno en caché o si está por expirar."""
        if self._oauth_access_token and time.time() < self._oauth_token_expires_at - 30:
            return self._oauth_access_token

        try:
            resp = requests.post(
                self.config.oauth_token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "refresh_token": self.config.refresh_token,
                },
                timeout=self.config.timeout,
            )
        except Timeout as exc:
            raise HubSpotNetworkError(
                f"Tiempo de espera agotado renovando el token OAuth2 de HubSpot."
            ) from exc
        except RequestsConnectionError as exc:
            raise HubSpotNetworkError(
                f"No se pudo conectar a {self.config.oauth_token_url} para renovar el token."
            ) from exc
        except RequestException as exc:
            raise HubSpotNetworkError(f"Error de red renovando token OAuth2: {exc}") from exc

        if resp.status_code != 200:
            raise HubSpotAuthError(
                f"No se pudo renovar el token OAuth2 de HubSpot (HTTP {resp.status_code}): "
                f"{resp.text[:300]}. Puede que la autorización haya sido revocada — "
                "re-autoriza el conector en Settings → Conectores."
            )

        payload = resp.json()
        self._oauth_access_token = payload["access_token"]
        self._oauth_token_expires_at = time.time() + int(payload.get("expires_in", 1800))
        return self._oauth_access_token

    # ------------------------------------------------------------------ #
    # Peticiones HTTP
    # ------------------------------------------------------------------ #

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.config.api_base_url}{path}"
        headers = kwargs.pop("headers", {})
        token = (
            self._get_oauth_access_token()
            if self.config.auth_mode == "oauth2"
            else self.config.access_token
        )
        headers["Authorization"] = f"Bearer {token}"
        headers.setdefault("Content-Type", "application/json")
        try:
            return requests.request(
                method, url, headers=headers, timeout=self.config.timeout, **kwargs
            )
        except Timeout as exc:
            raise HubSpotNetworkError(
                f"Tiempo de espera agotado ({self.config.timeout}s) llamando a "
                f"la API de HubSpot ({path})."
            ) from exc
        except RequestsConnectionError as exc:
            raise HubSpotNetworkError(
                f"No se pudo conectar a {self.config.api_base_url}. Verifica la "
                "conectividad de red y la URL base configurada."
            ) from exc
        except RequestException as exc:
            raise HubSpotNetworkError(f"Error de red: {exc}") from exc

    def _raise_for_error(self, resp: requests.Response, context: str) -> None:
        """Traduce una respuesta de error de la API a una excepción propia."""
        try:
            payload = resp.json()
        except ValueError:
            payload = {}

        message = payload.get("message") or resp.text[:300] or "Error desconocido"
        category = payload.get("category")

        if resp.status_code == 401:
            raise HubSpotAuthError(
                f"Autenticación fallida en {context}: {message}. Revisa que el "
                "Access Token sea correcto y no haya sido revocado."
            )
        if resp.status_code == 403:
            raise HubSpotAuthError(
                f"Permisos insuficientes en {context}: {message}. La Private App "
                "necesita el scope correspondiente (ej. crm.objects.contacts.write)."
            )
        if resp.status_code == 429:
            raise HubSpotDataError(
                f"Se alcanzó el límite de peticiones a la API de HubSpot ({context}). "
                "Reintenta en unos segundos (rate limit por portal)."
            )
        if resp.status_code == 404 or category == "OBJECT_NOT_FOUND":
            raise HubSpotDataError(f"No encontrado en {context}: {message}")
        if resp.status_code == 400 or category == "VALIDATION_ERROR":
            raise HubSpotDataError(f"Solicitud inválida en {context}: {message}")
        raise HubSpotDataError(
            f"Error de HubSpot en {context} (HTTP {resp.status_code}, "
            f"categoría {category or 'N/D'}): {message}"
        )

    # ------------------------------------------------------------------ #
    # Ping / prueba de conexión
    # ------------------------------------------------------------------ #

    def ping(self) -> bool:
        """Verifica el token consultando 1 contacto (barato, no expone datos sensibles).

        Returns:
            True si la autenticación y la llamada funcionan.
        """
        resp = self._request("GET", "/crm/v3/objects/contacts?limit=1")
        if resp.status_code != 200:
            self._raise_for_error(resp, "ping")
        self._logger.info("Ping exitoso a HubSpot")
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: crear o actualizar un contacto (upsert por email)
    # ------------------------------------------------------------------ #

    def upsert_contact(self, email: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        """Crea el contacto si no existe, o lo actualiza si ya existe, usando
        el email como identificador único. No duplica contactos.

        Args:
            email: correo del contacto (identificador).
            properties: otras propiedades a crear/actualizar (ej. firstname,
                lastname, phone, company). No hace falta repetir "email" aquí.

        Returns:
            Dict con "id", "created" (True/False) y "properties" del contacto.

        Ejemplo:
            >>> client.upsert_contact("ana@acme.com", {"firstname": "Ana", "lastname": "Pérez"})
            {'id': '12345', 'created': True, 'properties': {...}}
        """
        if not email or "@" not in email:
            raise HubSpotDataError(f"Email inválido para upsert_contact: {email!r}")

        props = dict(properties or {})
        props["email"] = email

        body = {"inputs": [{"idProperty": "email", "id": email, "properties": props}]}
        resp = self._request("POST", "/crm/v3/objects/contacts/batch/upsert", json=body)
        if resp.status_code != 200:
            self._raise_for_error(resp, f"upsert_contact {email}")

        results = resp.json().get("results", [])
        if not results:
            raise HubSpotDataError(f"HubSpot no retornó resultado para upsert_contact {email}")

        result = results[0]
        created = bool(result.get("new", False))
        self._logger.info(
            "Contacto %s en HubSpot (email=%s, id=%s)",
            "creado" if created else "actualizado", email, result.get("id"),
        )
        return {
            "id": result.get("id"),
            "created": created,
            "properties": result.get("properties", {}),
        }

    # ------------------------------------------------------------------ #
    # Capacidad 2: obtener un contacto por Id o por email
    # ------------------------------------------------------------------ #

    def get_contact(
        self,
        contact_id: str,
        by_email: bool = False,
        properties: list[str] | None = None,
    ) -> dict[str, Any]:
        """Obtiene un contacto por su Id interno de HubSpot, o por email.

        Args:
            contact_id: Id numérico del contacto, o el email si by_email=True.
            by_email: si es True, busca por email en vez de por Id.
            properties: propiedades a traer (default: email, firstname,
                lastname, phone, company).

        Returns:
            Dict con "id" y "properties" del contacto.

        Ejemplo:
            >>> client.get_contact("ana@acme.com", by_email=True)
            {'id': '12345', 'properties': {'email': 'ana@acme.com', ...}}
        """
        if not contact_id or not str(contact_id).strip():
            raise HubSpotDataError("contact_id no puede estar vacío.")

        props = list(properties) if properties else list(_DEFAULT_CONTACT_PROPERTIES)
        params: dict[str, Any] = {"properties": ",".join(props)}
        if by_email:
            params["idProperty"] = "email"

        resp = self._request(
            "GET", f"/crm/v3/objects/contacts/{contact_id}", params=params
        )
        if resp.status_code != 200:
            self._raise_for_error(resp, f"get_contact {contact_id}")

        payload = resp.json()
        return {"id": payload.get("id"), "properties": payload.get("properties", {})}

    # ------------------------------------------------------------------ #
    # Capacidad 3: buscar contactos por texto libre
    # ------------------------------------------------------------------ #

    def search_contacts(
        self,
        query: str,
        properties: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Busca contactos por texto libre (nombre, email, empresa, teléfono...).

        Args:
            query: término de búsqueda.
            properties: propiedades a traer por resultado (default: email,
                firstname, lastname, phone, company).
            limit: máximo de resultados (default 10, máximo 100).

        Returns:
            Lista de dicts {"id": ..., "properties": {...}}.

        Ejemplo:
            >>> client.search_contacts("Acme")
            [{'id': '12345', 'properties': {'company': 'Acme Inc', ...}}]
        """
        if not query or not query.strip():
            raise HubSpotDataError("El término de búsqueda no puede estar vacío.")

        props = list(properties) if properties else list(_DEFAULT_CONTACT_PROPERTIES)
        limit = max(1, min(int(limit), 100))

        body = {"query": query.strip(), "properties": props, "limit": limit}
        resp = self._request("POST", "/crm/v3/objects/contacts/search", json=body)
        if resp.status_code != 200:
            self._raise_for_error(resp, "search_contacts")

        results = resp.json().get("results", [])
        cleaned = [
            {"id": r.get("id"), "properties": r.get("properties", {})} for r in results
        ]
        self._logger.info("Búsqueda de contactos ejecutada: %d resultado(s)", len(cleaned))
        return cleaned

    # ------------------------------------------------------------------ #
    # Capacidad 4: crear un negocio (deal), opcionalmente asociado a un contacto
    # ------------------------------------------------------------------ #

    def create_deal(
        self,
        deal_name: str,
        properties: dict[str, Any] | None = None,
        contact_id: str | None = None,
    ) -> dict[str, Any]:
        """Crea un negocio (deal) nuevo, opcionalmente asociado a un contacto.

        Args:
            deal_name: nombre del negocio.
            properties: otras propiedades (ej. amount, dealstage, pipeline,
                closedate). No hace falta repetir "dealname" aquí.
            contact_id: si se indica, asocia el negocio a ese contacto usando
                la asociación por defecto de HubSpot (deal ↔ contact).

        Returns:
            Dict con "id" y "properties" del negocio creado.

        Ejemplo:
            >>> client.create_deal("Acme - Licencias Enterprise", {"amount": "50000"}, contact_id="12345")
            {'id': '98765', 'properties': {...}}
        """
        if not deal_name or not deal_name.strip():
            raise HubSpotDataError("El nombre del negocio (deal_name) no puede estar vacío.")

        props = dict(properties or {})
        props["dealname"] = deal_name.strip()

        resp = self._request("POST", "/crm/v3/objects/deals", json={"properties": props})
        if resp.status_code != 201:
            self._raise_for_error(resp, f"create_deal {deal_name}")

        payload = resp.json()
        deal_id = payload.get("id")
        self._logger.info("Negocio creado en HubSpot: %s (id=%s)", deal_name, deal_id)

        if contact_id:
            assoc_resp = self._request(
                "PUT",
                f"/crm/v4/objects/deals/{deal_id}/associations/default/contacts/{contact_id}",
            )
            if assoc_resp.status_code not in (200, 201):
                self._logger.info(
                    "El negocio se creó (id=%s) pero no se pudo asociar al contacto %s",
                    deal_id, contact_id,
                )
                self._raise_for_error(assoc_resp, f"create_deal (asociación con contacto {contact_id})")

        return {"id": deal_id, "properties": payload.get("properties", {})}

    # ------------------------------------------------------------------ #
    # Eliminación: explícitamente NO soportada en esta versión
    # ------------------------------------------------------------------ #

    def delete_contact(self, contact_id: str) -> None:
        """La eliminación de contactos no está soportada en esta versión del conector.

        Raises:
            HubSpotDataError: siempre.
        """
        raise HubSpotDataError(
            "La eliminación de contactos no está soportada en esta versión del "
            "conector HubSpot. Elimínalo directamente en HubSpot si es necesario."
        )

    def delete_deal(self, deal_id: str) -> None:
        """La eliminación de negocios no está soportada en esta versión del conector.

        Raises:
            HubSpotDataError: siempre.
        """
        raise HubSpotDataError(
            "La eliminación de negocios no está soportada en esta versión del "
            "conector HubSpot. Elimínalo directamente en HubSpot si es necesario."
        )
