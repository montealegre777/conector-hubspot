"""Validación local del conector hubspot: ejercita las 4 capacidades.

Requiere la env var RUVIC_HUBSPOT_ACCESS_TOKEN exportada contra un portal
de prueba (usa un portal Developer/Sandbox, no producción de un cliente real).
"""

from ruvic_hubspot_connector import HubSpotClient, setup_logging

setup_logging("INFO")
client = HubSpotClient()

print("== 1. Crear o actualizar un contacto de prueba ==")
contacto = client.upsert_contact(
    "prueba.ruvic@validate-local.test",
    {"firstname": "Ruvic", "lastname": "Prueba", "company": "Ruvic AI - validate_local.py"},
)
print(f"  {contacto}")

print("== 2. Obtener ese mismo contacto por email ==")
leido = client.get_contact("prueba.ruvic@validate-local.test", by_email=True)
print(f"  {leido}")

print("== 3. Buscar contactos con 'Ruvic' ==")
resultados = client.search_contacts("Ruvic", limit=5)
for r in resultados:
    print(f"  {r['id']}: {r['properties'].get('email')}")

print("== 4. Crear un negocio de prueba asociado al contacto ==")
negocio = client.create_deal(
    "Ruvic - Negocio de prueba (validate_local.py)",
    contact_id=contacto["id"],
)
print(f"  {negocio}")

print("== 5. Confirmar upsert_contact NO duplica (segunda llamada, mismo email) ==")
contacto2 = client.upsert_contact(
    "prueba.ruvic@validate-local.test", {"lastname": "Prueba (actualizado)"}
)
assert contacto2["id"] == contacto["id"], "Se creó un contacto distinto - algo falló"
assert contacto2["created"] is False, "Debió actualizar, no crear"
print(f"  OK, mismo id ({contacto2['id']}), created=False como se espera")

print("== 6. Confirmar que la eliminación NO está soportada ==")
try:
    client.delete_contact(contacto["id"])
except Exception as exc:
    print(f"  OK, rechazada como se espera: {exc}")

print(
    "\nRecuerda borrar manualmente el contacto y el negocio de prueba en HubSpot, "
    "ya que este conector no elimina registros."
)
