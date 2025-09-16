import frappe
from frappe.model.document import Document
from email import message_from_string
from bs4 import BeautifulSoup

logger = frappe.logger("Edevis")
logger.setLevel("INFO")

def parse_email_content(content: str) -> dict:
    soup = BeautifulSoup(content, "html.parser")
    text = soup.get_text(separator="\n")
    # logger.debug(f"API: Email content text: {text}")

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

@frappe.whitelist(allow_guest=False)
def newrequest():
    logger.debug(f"API: newrequest")
    raw_email = frappe.form_dict.get("raw_email")
    if not raw_email:
        frappe.throw("No raw_email provided")

    msg = message_from_string(raw_email)
    
    # logger.debug(f"Email message: {msg}")

    subject = msg.get("Subject", "")
    sender = msg.get("From", "")

    if msg.is_multipart():
        # Falls MIME Multipart (z. B. HTML + Plaintext)
        parts = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                parts.append(part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace"))
        content = "\n".join(parts)
    else:
        # Einfacher Text
        content = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")

    # recipient = msg.get("To", "")

    logger.info(f"API: New download request by API - parsing...")

    parsed_data = parse_email_content(content)

    logger.info(f"API: Email Hook - parsed data {parsed_data}")

    try:
        new_request = frappe.new_doc("Software Download Request")
    except Exception as e:
        logger.error(f"API: Error creating new Software Download Request: {str(e)}")
        raise

    # parsed_data enthält die passenden Feldnamen
    for field, value in parsed_data.items():
        new_request.set(field, value)

    new_request.insert()
    frappe.db.commit()

    # doc.insert(ignore_permissions=True)

    logger.info(f"API: New download request created: {new_request.name}")
