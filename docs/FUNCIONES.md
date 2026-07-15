# Conector HubSpot — Qué hace cada función

Este documento explica, en lenguaje simple, qué hace cada una de las 4 funciones del conector `ruvic_hubspot_connector`.

---

## 1. `upsert_contact()` — Crear o actualizar en un solo paso

**¿Qué hace?** Crea un contacto si no existe, o lo actualiza si ya existe — identificándolo por su **email**. Nunca duplica.

**¿Cuándo se usa?** Es la función por defecto para "agregar/guardar" un contacto, salvo que sepas con certeza que es 100% nuevo y quieras forzar la creación.

**Necesita:**
- El email del contacto (identificador)
- (Opcional) otras propiedades: nombre, apellido, teléfono, empresa...

**Ejemplo:**
```python
client.upsert_contact("ana@acme.com", {"firstname": "Ana", "lastname": "Pérez"})
```

**Te devuelve:** el Id del contacto, y si fue creado (`created: True`) o actualizado (`created: False`).

**Analogía:** le dices al archivista "si esta persona ya tiene ficha, actualízala; si no, ábrele una nueva" — sin que tú tengas que revisar primero.

---

## 2. `get_contact()` — Traer un contacto puntual

**¿Qué hace?** Trae un solo contacto, buscándolo por su Id interno de HubSpot o por su email.

**¿Cuándo se usa?** Cuando ya sabes exactamente cuál contacto quieres ver.

**Necesita:**
- El Id o el email
- Si usas email, indicar `by_email=True`

**Ejemplo:**
```python
client.get_contact("ana@acme.com", by_email=True)
```

**Te devuelve:** un diccionario con el Id y las propiedades del contacto.

**Analogía:** sacar una ficha específica del archivador, sabiendo su nombre o número exacto.

---

## 3. `search_contacts()` — Buscar por texto libre

**¿Qué hace?** Busca contactos que coincidan con una palabra o frase (nombre, empresa, email, teléfono), sin que tengas que saber el dato exacto.

**¿Cuándo se usa?** Cuando el usuario pide "busca los contactos de X" de forma general.

**Necesita:**
- El término de búsqueda

**Ejemplo:**
```python
client.search_contacts("Acme")
```

**Te devuelve:** una lista de contactos que coinciden.

**Analogía:** usar el buscador del archivador en vez de ir ficha por ficha.

---

## 4. `create_deal()` — Crear un negocio

**¿Qué hace?** Crea un negocio nuevo (una oportunidad de venta) y, si se lo pides, lo asocia automáticamente a un contacto.

**¿Cuándo se usa?** Cuando el usuario pide registrar una oportunidad de venta o negocio en el pipeline.

**Necesita:**
- El nombre del negocio
- (Opcional) monto, etapa, pipeline
- (Opcional) el Id de un contacto para asociarlo

**Ejemplo:**
```python
client.create_deal("Acme - Licencias Enterprise", {"amount": "50000"}, contact_id="12345")
```

**Te devuelve:** el Id del negocio creado.

**Analogía:** abrir un nuevo expediente de negocio y grapar dentro la ficha del cliente al que pertenece.

---

## Funciones bloqueadas a propósito: `delete_contact()` y `delete_deal()`

**¿Qué hacen?** Nada — siempre lanzan un error explicando que la eliminación no está soportada en esta versión del conector.

**¿Por qué existen entonces?** Para que, si alguien le pide al agente "borra este contacto/negocio", el conector responda con un mensaje claro en vez de fallar de forma confusa.

---

## Resumen rápido — ¿cuál función usar según lo que pida el usuario?

| El usuario pide... | Función a usar |
|---|---|
| "Agrega/guarda este contacto" | `upsert_contact()` |
| "Dame los datos de este contacto puntual" | `get_contact()` |
| "Busca contactos de tal empresa/nombre" | `search_contacts()` |
| "Crea un negocio para este cliente" | `create_deal()` |
| "Borra este contacto/negocio" | (no soportado — se hace directamente en HubSpot) |
