"""Excepciones propias del conector HubSpot.

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red y datos/permisos.
"""


class HubSpotConnectorError(Exception):
    """Error base del conector."""


class HubSpotAuthError(HubSpotConnectorError):
    """Access Token inválido, expirado, revocado, o sin el scope necesario
    para la operación solicitada."""


class HubSpotNetworkError(HubSpotConnectorError):
    """No se pudo alcanzar la API de HubSpot (DNS, timeout, TLS, red)."""


class HubSpotDataError(HubSpotConnectorError):
    """La operación es válida pero el registro no existe, los datos enviados
    no cumplen las reglas de HubSpot (propiedad inválida, tipo incorrecto),
    o se alcanzó un límite de tasa (rate limit)."""
