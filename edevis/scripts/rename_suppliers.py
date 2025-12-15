import frappe


def execute():
    update_supplier_ids()


def update_supplier_ids():
    suppliers = frappe.get_all("Supplier", fields=["name", "legacy_id", "supplier_name"])
    allsuppliers = []
    i = 0
    for supplier in suppliers:
        i += 1
        allsuppliers.append(supplier.name)
        if i>50:
            break

    for supplier in allsuppliers:
        doc = frappe.get_doc("Supplier", supplier)
        oldname = doc.supplier_name
        if not doc.default_price_list:
            doc.default_price_list = "Standard-Kauf"
            print(f"Set default price list to Standard Buying for {doc.name}")

        if not doc.default_currency:
            doc.default_currency = "EUR"
            print(f"Set billing currency to EUR for {doc.name}")

            
        # Hol alle Dynamic Links zu diesem Supplier
        links = frappe.get_all(
            "Dynamic Link",
            filters={"link_doctype": "Supplier", "link_name": doc.name, "parenttype": "Address"},
            fields=["parent"]
        )

        addresses = []
        if links:
            address_names = [l.parent for l in links]
            addresses = frappe.get_all(
                "Address",
                filters={"name": ["in", address_names]},
                fields=["name", "address_type", "country"]
            )

        if addresses and addresses[0].country != doc.country:
            if not addresses[0].country:
                print(f"Address for {addresses} has no country set, skipping country update.")
                continue            
            
            doc.country = addresses[0].country
            print(f"Set country for {doc.name} to {addresses[0].country}")

        # --- Set primary address if empty but delivery address exists ---
        if not doc.supplier_primary_address:
            # Alle Adressen des Lieferanten holen

            if addresses:
                doc.supplier_primary_address = addresses[0].name
                print(f"Set primary_address for {doc.name} to {addresses[0].name}")
            else:
                print(f"No address found to set as primary for {doc.name}")

        doc.save()        

        if doc.legacy_id and doc.legacy_id.strip():
            if doc.legacy_id == doc.name:
                # print(f"{doc.supplier_name}/{doc.name} already OK")
                continue
            try:
                frappe.rename_doc("Supplier", supplier, doc.legacy_id, force=True, merge=False)
                print(f"Renamed {doc.supplier_name}:    {doc.name} --> {doc.legacy_id}")
                
                doc = frappe.get_doc("Supplier", doc.legacy_id)
                doc.supplier_name = oldname
                doc.save()
                print(f"Restored supplier_name for {doc.legacy_id} to {oldname}")
                
            except Exception as e:
                print(f"Error renaming {supplier.name}: {e}")
                        
    # frappe.db.commit()
