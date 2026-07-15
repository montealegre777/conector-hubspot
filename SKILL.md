---
name: hubspot
description: Usa la librería ruvic_hubspot_connector para gestionar contactos y negocios en HubSpot - crear o actualizar contactos por email (upsert_contact), obtener un contacto (get_contact), buscar contactos por texto libre (search_contacts) y crear negocios/deals (create_deal). Úsala cuando el usuario pida crear, actualizar, buscar o consultar contactos, leads o negocios en HubSpot. NO soporta eliminar contactos ni negocios.
triggers:
- hubspot
- crm
- contactos hubspot
- negocios hubspot
- deals hubspot
- pipeline
---

# Conector HubSpot (ruvic_hubspot_connector)

Librería Python para gestionar contactos y negocios en HubSpot vía CRM API v3, autenticada con un **Private App Access Token**. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/tu-org/conector-hubspot.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `hubspot` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_HUBSPOT_ACCESS_TOKEN` | Access Token de la Private App |
| `RUVIC_HUBSPOT_API_BASE_URL` | (opcional) URL base, default `https://api.hubapi.com` |
| `RUVIC_HUBSPOT_REQUEST_TIMEOUT` | (opcional) timeout en segundos, default `20` |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## Conexión (siempre igual)

```python
from ruvic_hubspot_connector import HubSpotClient

client = HubSpotClient()  # lee RUVIC_HUBSPOT_* del entorno automáticamente
```

El conector soporta dos formas de autenticación configuradas por el admin (transparente para el código que generes): **Private App Token** (estático) u **OAuth2 con usuario** (el admin autorizó desde Settings → Conectores; la librería renueva el access token automáticamente con el refresh token cuando hace falta). No necesitas saber cuál de los dos está activo.

## Capacidad 1 — Crear o actualizar un contacto (sin duplicar)

Úsala siempre que el usuario pida "agrega/actualiza este contacto" — identifica por email, así que si ya existe lo actualiza en vez de duplicarlo.

```python
resultado = client.upsert_contact("ana@acme.com", {"firstname": "Ana", "lastname": "Pérez", "company": "Acme Inc"})
print(resultado)
# {'id': '12345', 'created': True, 'properties': {...}}  -> si era nuevo
# {'id': '12345', 'created': False, 'properties': {...}} -> si ya existía
```

## Capacidad 2 — Obtener un contacto

Por Id interno de HubSpot, o por email:

```python
contacto = client.get_contact("12345")
contacto = client.get_contact("ana@acme.com", by_email=True)
```

## Capacidad 3 — Buscar contactos por texto libre

Úsala cuando el usuario pida "busca contactos de X" sin un Id exacto:

```python
resultados = client.search_contacts("Acme")
for c in resultados:
    print(c["properties"].get("email"), c["properties"].get("company"))
```

## Capacidad 4 — Crear un negocio (deal), opcionalmente asociado a un contacto

```python
negocio = client.create_deal(
    "Acme - Licencias Enterprise",
    properties={"amount": "50000", "dealstage": "appointmentscheduled"},
    contact_id="12345",  # opcional: lo asocia automáticamente
)
print(negocio)  # {'id': '98765', 'properties': {...}}
```

Si no conoces los `dealstage`/`pipeline` exactos de la cuenta del cliente, no los inventes: pídele al usuario que los confirme o usa solo `dealname` y deja que HubSpot aplique el pipeline/etapa por defecto.

## Eliminación: NO soportada

```python
client.delete_contact("12345")  # o client.delete_deal("98765")
# Lanza HubSpotDataError: "La eliminación de ... no está soportada..."
```

Si el usuario pide borrar un contacto o negocio, **informa que esta versión del conector no soporta eliminación** y que debe hacerse directamente en HubSpot.

## Manejo de errores

```python
from ruvic_hubspot_connector import HubSpotAuthError, HubSpotDataError, HubSpotNetworkError

try:
    client.upsert_contact("ana@acme.com", {"firstname": "Ana"})
except HubSpotAuthError:
    print("Token inválido o sin el scope necesario — revisa la configuración del conector")
except HubSpotNetworkError:
    print("No se pudo alcanzar HubSpot — revisa la red")
except HubSpotDataError as e:
    print(f"Error de datos: {e}")  # ej. propiedad inválida, rate limit
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_HUBSPOT_*` (el constructor de `HubSpotClient` ya lo hace).
2. Nunca imprimas `RUVIC_HUBSPOT_ACCESS_TOKEN` en logs ni en la salida.
3. No intentes eliminar contactos/negocios: `delete_contact`/`delete_deal` siempre fallan a propósito en esta versión.
4. Para crear contactos, prefiere siempre `upsert_contact` sobre intentar "crear directo" — evita duplicados si el contacto ya existía.
5. No inventes valores de `dealstage` o `pipeline`: varían por cuenta de HubSpot. Si no los conoces, omítelos y deja que HubSpot use los valores por defecto, o pregúntale al usuario.
6. La API de búsqueda de HubSpot tiene un límite más estricto (4 peticiones/segundo por portal) que el resto de endpoints — evita loops de `search_contacts` sin necesidad.
