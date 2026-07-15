"""Prueba de conexión estándar del conector hubspot.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_HUBSPOT_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Verifica el Access Token de HubSpot usando las env vars RUVIC_HUBSPOT_*."""
    try:
        from ruvic_hubspot_connector import (
            HubSpotAuthError,
            HubSpotClient,
            HubSpotDataError,
            HubSpotNetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-hubspot-connector no está instalada. "
            "Instala con: pip install git+https://github.com/tu-org/"
            "conector-hubspot.git#subdirectory=lib",
        )

    try:
        client = HubSpotClient()  # valida que exista la env var del token
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except HubSpotAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except HubSpotNetworkError as exc:
        return False, f"Error de red: {exc}"
    except HubSpotDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return True, f"Conexión exitosa a HubSpot ({client.config.api_base_url})"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
