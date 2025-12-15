import frappe

def execute():
    # Beispiel: Patch läuft über alle Items
    items = frappe.get_all("Item", 
                           fields=["name", "custom_dual_use_export_item_number", "country_of_origin"],
                           filters={"item_code": ["like", 'EDP 06%']})
    
    for item in items:
        doc = frappe.get_doc("Item", item.name)
        
        dual_use_items = doc.get("custom_dual_use_items")
                
        if not dual_use_items:
            #print(f"SKIP {item}   --->  {dual_use_items}")

            if item.custom_dual_use_export_item_number == "6A003b4b":
                doc.append("custom_dual_use_items", {
                    "dual_use_template": "Dual-Use (EG-VO 2021/821)"
                })
                doc.append("custom_dual_use_items", {
                    "dual_use_template": "Dual-Use (Embargo)"
                })
                print(f"Dual Use Items (2) for Microbolometer {item.country_of_origin} product: {item.name}.")

            if item.custom_dual_use_export_item_number == "6A003b4a" and item.country_of_origin != "United States":
                doc.append("custom_dual_use_items", {
                    "dual_use_template": "Dual-Use (EG-VO 2021/821)"
                })
                doc.append("custom_dual_use_items", {
                    "dual_use_template": "Dual-Use (Embargo)"
                })
                print(f"Dual Use Items (2) for {item.country_of_origin} product: {item.name}.")

            if item.custom_dual_use_export_item_number == "6A003b4a" and item.country_of_origin == "United States":
                doc.append("custom_dual_use_items", {
                	"dual_use_template": "Dual-Use (EG-VO 2021/821)"
            	})
                doc.append("custom_dual_use_items", {
                    "dual_use_template": "Dual-Use (Embargo)"
                })
                doc.append("custom_dual_use_items", {
                    "dual_use_template": "Dual-Use (ECCN License exception STA)"
                })
                
                print(f"Dual Use Items (3) for {item.country_of_origin} product: {item.name}.")

            doc.save()

        frappe.db.commit()

    frappe.logger().info("Dual Use Template patch erfolgreich ausgeführt.")
