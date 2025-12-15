import frappe
import re

def normalize(text):
    # HTML-Tags entfernen
    return re.sub(r'<[^>]+>', '', text or '').strip()


def execute():
    i = 0
    translations = frappe.get_all(
        "Translation",
        fields=["name", "source_text"],
        filters={"source_text": ["like", "%description not available in this language"]}
    )

    if not translations:
        print(f"Keine Übersetzungen gefunden.")                    
    else:
        if len(translations) > 1:
            print(f"{len(translations)} Übersetzungen gefunden!")

    for tr in translations:
        # new_source = f'{item.item_code} Datasheet'
        
        target = tr.source_text.replace("description not available in this language", "Datasheet")
        print(f"Updated {i}th Translation {tr.name}: '{tr.source_text}' → {target}")
        frappe.db.set_value("Translation", tr.name, "source_text", target)

    i += 1


