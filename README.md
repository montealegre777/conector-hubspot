# conector-hubspot

Conector Ruvic para HubSpot: gestión de contactos y negocios vía CRM API v3, autenticado con un **Private App Access Token**.

## Capacidades

`upsert_contact` (crear-o-actualizar por email), `get_contact`, `search_contacts`, `create_deal` (con asociación opcional a un contacto). `delete_contact`/`delete_deal` existen pero rechazan siempre (eliminación fuera de alcance).

## Instalación

Requiere **Python ≥ 3.10**.

```bash
pip install git+https://github.com/tu-org/conector-hubspot.git#subdirectory=lib
```

Para desarrollo local (editable, en un venv limpio):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib
```

## Variables de entorno

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_HUBSPOT_ACCESS_TOKEN` | Sí | Token de una Private App de HubSpot |
| `RUVIC_HUBSPOT_API_BASE_URL` | No | Default `https://api.hubapi.com`; usar `https://api-eu1.hubapi.com` si la cuenta tiene residencia de datos en la UE |
| `RUVIC_HUBSPOT_REQUEST_TIMEOUT` | No | Timeout en segundos, default `20` |
| `RUVIC_HUBSPOT_REFRESH_TOKEN` | No | Si está presente (junto con `CLIENT_ID`/`CLIENT_SECRET`), activa el modo OAuth2 con usuario en vez de Private App Token — la plataforma la gestiona automáticamente al usar el botón "Autorizar" |

## Permisos / prerrequisitos en HubSpot

1. En HubSpot: **Settings → Integrations → Private Apps → Create a private app**.
2. En la pestaña **Scopes**, otorga como mínimo:
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`
   - `crm.objects.deals.read`
   - `crm.objects.deals.write`
3. Guarda y copia el **Access Token** — HubSpot solo lo muestra completo una vez.
4. Solo usuarios con permiso de **Super Admin** pueden crear Private Apps.

Este conector **no soporta eliminación** de contactos ni negocios en esta versión (fuera de alcance a propósito).

## Cómo correr las pruebas locales

```bash
export RUVIC_HUBSPOT_ACCESS_TOKEN=pat-na1-xxxxxxxx
python test_connection.py
python validate_local.py
```

Prueba también el caso de error:

```bash
RUVIC_HUBSPOT_ACCESS_TOKEN=invalido python test_connection.py
# FALLO: Autenticación fallida: ...
```

## Límites de la API a tener en cuenta

- **100 peticiones / 10 segundos** por portal (todas las superficies de API combinadas).
- **4 peticiones / segundo** específicamente para el endpoint de búsqueda (`search_contacts`).
- HTTP 429 se traduce a `HubSpotDataError` — el conector no reintenta automáticamente; si el agente hace muchas búsquedas seguidas, debe esperar.

## Limitaciones conocidas

- No soporta eliminación de contactos ni negocios.
- No cubre objetos personalizados, tickets, ni las APIs de Marketing/CMS/Workflows — solo Contacts y Deals.
- `create_deal` usa la asociación por defecto de HubSpot (deal ↔ contact); no permite elegir un tipo de asociación distinto.
- No valida que `dealstage`/`pipeline` existan en la cuenta del cliente antes de enviarlos — HubSpot los rechaza con un error claro si no existen.

## Notas de integración

- El paquete pip es `ruvic-hubspot-connector`; el import name es `ruvic_hubspot_connector`.
- Única dependencia externa: `requests`.
- Ver `SKILL.md` para los ejemplos de uso que consume el agente.
