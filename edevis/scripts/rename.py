# import frappe

# def update_customer_ids():
#     customers = frappe.get_all("Customer", fields=["name", "legacy_id", "customer_name"])
    
#     for customer in customers:
#         if customer.legacy_id and customer.legacy_id.strip():
#             if customer.legacy_id == customer.name:
#                 print(f"{customer.customer_name}/{customer.name} already OK")
#                 continue
#             try:
#                 frappe.rename_doc("Customer", customer.name, customer.legacy_id, force=True, merge=False)
#                 print(f"Renamed {customer.customer_name}:    {customer.name} --> {customer.legacy_id}")
#             except Exception as e:
#                 print(f"Error renaming {customer.name}: {e}")
                        
#     frappe.db.commit()

# def update_supplier_ids():
#     suppliers = frappe.get_all("Supplier", fields=["name", "legacy_id", "supplier_name"])
    
#     for supplier in suppliers:
#         if supplier.legacy_id and supplier.legacy_id.strip():
#             if supplier.legacy_id == supplier.name:
#                 print(f"{supplier.supplier_name}/{supplier.name} already OK")
#                 continue
#             try:
#                 frappe.rename_doc("Supplier", supplier.name, supplier.legacy_id, force=True, merge=False)
#                 print(f"Renamed {supplier.supplier_name}:    {supplier.name} --> {supplier.legacy_id}")
#             except Exception as e:
#                 print(f"Error renaming {supplier.name}: {e}")
                        
#     frappe.db.commit()

# update_customer_ids()
