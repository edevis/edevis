__version__ = "v15.1.0"
# Ensure custom serial patches load early for web and workers
try:
    from edevis.custom_scripts.custom_python.serial_no import (
       patch_set_serial_batch_entries,
        patch_serial_creation_methods,
        patch_work_order_serial_creation
    )

    # Idempotent: safe to call multiple times
    patch_set_serial_batch_entries()
    patch_serial_creation_methods()
    patch_work_order_serial_creation()

except Exception:
    try:
        import frappe
        frappe.log_error(title="edevis init patch error")
    except Exception:
        # If frappe isn't ready yet, silently ignore
        pass