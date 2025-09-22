import frappe
from bs4 import BeautifulSoup

logger = frappe.logger("Edevis")
logger.setLevel("INFO")


def parse_email_content(content: str) -> dict:
    soup = BeautifulSoup(content, "html.parser")
    text = soup.get_text(separator="\n")

    field_map = {
        "email": "sender",
        "produkt": "subject",
        "product": "subject",
        # "given-name": "first_name",
        # "family-name": "last_name",
    }

    parsed_data = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    skip_next = False
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        # Spezialfall: email: <leer> + nächste Zeile ist Adresse
        if key == "email" and not value and i + 1 < len(lines):
            value = lines[i + 1].strip()
            skip_next = True

        if key in field_map and value:
            parsed_data[field_map[key]] = value

    # required = ["sender", "subject", "first_name", "last_name"]
    required = ["sender", "subject"]
    missing = [f for f in required if f not in parsed_data]
    if missing:
        raise frappe.ValidationError(f"Missing required fields: {', '.join(missing)}")

    return parsed_data



def handle_software_download_email(doc, method):

    logger.info(f"Email Hook - analyzing communication")    

    # Nur auf eingehende Mails reagieren
    if doc.communication_type != "Communication":
        return


    # Absender prüfen
    # if doc.sender != "download@edevis.de" or not doc.sender.endswith("@example.com"):
    #    return

    logger.info(f"Email Hook - analyzing communication: found matching sender {doc.sender}")
    
    # Email-Text parsen (doc.content)
    content = doc.content
    # Beispiel: Einfache Extraktion von Infos (Name, Software, etc.)
    parsed_data = parse_email_content(content)

    logger.info(f"Email Hook - parsed data {parsed_data}")

    new_request = frappe.new_doc("Software Download Request")

    # parsed_data enthält die passenden Feldnamen
    for field, value in parsed_data.items():
        new_request.set(field, value)

    new_request.insert()
    frappe.db.commit()