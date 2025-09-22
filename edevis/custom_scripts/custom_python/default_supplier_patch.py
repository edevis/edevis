import frappe

def execute():
    # Hole alle Artikel mit genau einem Supplier
    items = frappe.get_all(
        "Item",
        filters={},
        fields=["name"]
    )

    updated = []

    for item in items:
        suppliers = frappe.get_all(
            "Item Supplier",
            filters={"parent": item.name},
            fields=["supplier"]
        )

        if len(suppliers) == 1:
            supplier = suppliers[0].supplier

            # Hole Item Defaults für diesen Artikel
            item_defaults = frappe.get_all(
                "Item Default",
                filters={"parent": item.name},
                fields=["name", "default_supplier"]
            )

            # Setze Supplier nur dort, wo er noch fehlt
            for idef in item_defaults:
                if not idef.default_supplier:
                    frappe.db.set_value("Item Default", idef.name, "default_supplier", supplier)
                    updated.append(f"{item.name} / {idef.name} -> {supplier}")
                    frappe.db.commit()
                    print(f"Updated Item Default: {item.name} / {idef.name} -> {supplier}")
    
                    
