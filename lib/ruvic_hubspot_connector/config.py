"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_HUBSPOT_.

Soporta dos modos de autenticación:
- "private_app_token": token estático de una Private App de HubSpot.
- "oauth2": OAuth 2.0 con usuario (login + consentimiento), gestionado
  por la plataforma vía el campo oauth2_authorization del manifest.
  Requiere CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN (capturado y guardado
  automáticamente por la plataforma al conectar).
El modo activo se detecta por la presencia de RUVIC_HUBSPOT_REFRESH_TOKEN.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_HUBSPOT_"

_DEFAULT_BASE_URL = "https://api.hubapi.com"
_OAUTH_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"


@dataclass(frozen=True)
class HubSpotConfig:
    """Parámetros de conexión a HubSpot: Private App Access Token u OAuth2."""

    auth_mode: str = "private_app_token"  # "private_app_token" | "oauth2"
    access_token: str = ""
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    api_base_url: str = _DEFAULT_BASE_URL
    timeout: int = 20

    @property
    def oauth_token_url(self) -> str:
        return _OAUTH_TOKEN_URL

    @classmethod
    def from_env(cls) -> "HubSpotConfig":
        """Construye la configuración desde las variables RUVIC_HUBSPOT_*.

        Detecta automáticamente el modo: si existe RUVIC_HUBSPOT_REFRESH_TOKEN,
        usa OAuth2; si no, exige RUVIC_HUBSPOT_ACCESS_TOKEN (Private App).

        Raises:
            ValueError: si faltan las variables obligatorias del modo detectado.

        Ejemplo:
            >>> config = HubSpotConfig.from_env()
        """
        refresh_token = os.environ.get(f"{ENV_PREFIX}REFRESH_TOKEN", "").strip()
        base_url = os.environ.get(f"{ENV_PREFIX}API_BASE_URL", "").strip() or _DEFAULT_BASE_URL
        timeout = int(os.environ.get(f"{ENV_PREFIX}REQUEST_TIMEOUT", "20"))

        if refresh_token:
            client_id = os.environ.get(f"{ENV_PREFIX}CLIENT_ID", "")
            client_secret = os.environ.get(f"{ENV_PREFIX}CLIENT_SECRET", "")
            if not client_id or not client_secret:
                raise ValueError(
                    f"El modo OAuth2 requiere {ENV_PREFIX}CLIENT_ID y "
                    f"{ENV_PREFIX}CLIENT_SECRET además de {ENV_PREFIX}REFRESH_TOKEN."
                )
            return cls(
                auth_mode="oauth2",
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                api_base_url=base_url.rstrip("/"),
                timeout=timeout,
            )

        access_token = os.environ.get(f"{ENV_PREFIX}ACCESS_TOKEN")
        if not access_token:
            raise ValueError(
                f"Falta la variable de entorno del conector hubspot: "
                f"{ENV_PREFIX}ACCESS_TOKEN. Configura el conector en Settings → Conectores."
            )

        return cls(
            auth_mode="private_app_token",
            access_token=access_token,
            api_base_url=base_url.rstrip("/"),
            timeout=timeout,
        )

