import frappe
import re

def normalize(text):
    # HTML-Tags entfernen
    return re.sub(r'<[^>]+>', '', text or '').strip()


def execute():
    """
    Update Translation.source_text für alle Items,
    sodass statt item.description nun item.item_code + ' Datasheet' steht.
    """
    items = frappe.get_all(
        "Item",
        fields=["name", "item_code", "description"],
        filters={"description": ["!=", ""]}
    )

    i = 0
    for item in items:
        translations = frappe.get_all(
            "Translation",
            fields=["name", "source_text"],
            filters={"source_text": normalize(item.description)}
        )
        if not translations:
            print(f"{i}th Item {item.item_code}: Keine Übersetzungen gefunden.")
            i += 1
            continue
        else:
            if len(translations) > 1:
                print(f"{i}th Item {item.item_code}: Mehrere Übersetzungen gefunden!")
            else:
                print(f"WARNING: {i}th Item {item.item_code}: {len(translations)} Übersetzungen gefunden.")

        for tr in translations:
            new_source = f'{item.item_code} Datasheet'
            #  frappe.db.set_value("Translation", tr.name, "source_text", new_source)
            print(
                f"SIMULATED Updated {i}th Translation {tr.name}: '{tr.source_text}' → '{new_source}'"
            )

        i += 1
        break

    # frappe.db.rollback()
    print(f"Update abgeschlossen für {i} Elemente.")

