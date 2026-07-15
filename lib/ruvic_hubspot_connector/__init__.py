"""Conector Ruvic para HubSpot (gestión de contactos y negocios)."""

from .client import HubSpotClient
from .config import ENV_PREFIX, HubSpotConfig
from .exceptions import (
    HubSpotAuthError,
    HubSpotConnectorError,
    HubSpotDataError,
    HubSpotNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "HubSpotAuthError",
    "HubSpotClient",
    "HubSpotConfig",
    "HubSpotConnectorError",
    "HubSpotDataError",
    "HubSpotNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
