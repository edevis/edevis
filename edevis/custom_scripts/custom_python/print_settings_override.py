import frappe

@frappe.whitelist()
def get_print_settings_to_show(doctype, docname):
    """Override to use document field values as default for print preview checkboxes"""
    doc = frappe.get_doc(doctype, docname)
    print_settings = frappe.get_single("Print Settings")

    if hasattr(doc, "get_print_settings"):
        fields = doc.get_print_settings() or []
    else:
        return []

    print_settings_fields = []
    for fieldname in fields:
        df = print_settings.meta.get_field(fieldname)
        if not df:
            continue
        
        # Use document's custom field value as default if it exists
        custom_field_name = f"custom_{fieldname}"
        if hasattr(doc, custom_field_name):
            df.default = doc.get(custom_field_name)
        else:
            # Fall back to global print settings
            df.default = print_settings.get(fieldname)
            
        print_settings_fields.append(df)

    return print_settings_fields
