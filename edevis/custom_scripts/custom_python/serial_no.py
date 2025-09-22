import frappe
from frappe import _
from frappe.utils import flt
from erpnext.stock.serial_batch_bundle import SerialBatchCreation, get_serial_nos_batch

def update_serial_no(doc, method):
    item_code = (doc.get("item_code") or "").strip()
    serial_no = (doc.get("serial_no") or doc.get("sr_no") or "").strip()

    # If required fields are missing, skip custom naming
    if not item_code or not serial_no:
        return

    new_name = f"{item_code}:{serial_no}"

    # Enforce uniqueness
    if frappe.db.exists("Serial No", new_name):
        frappe.throw(_("Serial No with same Item Code and Serial No already exists."))

    # Set the document name
    doc.name = new_name

def _custom_set_serial_batch_entries(self, doc):
    incoming_rate = self.get("incoming_rate")
    precision = frappe.get_precision("Serial and Batch Entry", "qty")

    if self.get("serial_nos"):
        serial_no_wise_batch = frappe._dict({})
        if self.has_batch_no:
            serial_no_wise_batch = get_serial_nos_batch(self.serial_nos)

        qty = -1 if self.type_of_transaction == "Outward" else 1

        for serial_no in self.serial_nos:
            if self.get("serial_nos_valuation"):
                incoming_rate = self.get("serial_nos_valuation").get(serial_no)

            # Fast lookup of Serial No document name from serial_no field
            actual_serial_no_name = frappe.db.get_value("Serial No", {"serial_no": serial_no}, "name") or serial_no

            doc.append(
                "entries",
                {
                    "serial_no": actual_serial_no_name,
                    "qty": qty,
                    "batch_no": serial_no_wise_batch.get(serial_no) or self.get("batch_no"),
                    "incoming_rate": incoming_rate,
                },
            )

    elif self.get("batches"):
        for batch_no, batch_qty in self.batches.items():
            if self.get("batches_valuation"):
                incoming_rate = self.get("batches_valuation").get(batch_no)

            doc.append(
                "entries",
                {
                    "batch_no": batch_no,
                    "qty": flt(batch_qty, precision) * (-1 if self.type_of_transaction == "Outward" else 1),
                    "incoming_rate": incoming_rate,
                },
            )

def patch_set_serial_batch_entries():
    SerialBatchCreation.set_serial_batch_entries = _custom_set_serial_batch_entries

def _custom_make_serial_nos(self, serial_nos):
    batch_no = None
    if getattr(self, "batches", None):
        batch_no = next(iter(self.batches.keys()))

    for serial_no in serial_nos:
        doc = frappe.new_doc("Serial No")
        doc.serial_no = serial_no
        doc.item_code = self.item_code
        doc.item_name = getattr(self, "item_name", None)
        doc.description = getattr(self, "description", None)
        doc.company = self.company
        doc.status = "Active"
        doc.batch_no = batch_no
        doc.save(ignore_permissions=True)

def _custom_get_auto_created_serial_nos(self):
    from frappe.model.naming import make_autoname
    sr_nos = []

    if not getattr(self, "serial_no_series", None):
        frappe.throw(_(f"Please set Serial No Series in the item {self.item_code} or create Serial and Batch Bundle manually."))

    voucher_no = ""
    if getattr(self, "voucher_no", None):
        voucher_no = self.voucher_no

    for _i in range(abs(int(self.actual_qty))):
        serial_no = make_autoname(self.serial_no_series, "Serial No")
        sr_nos.append(serial_no)

        doc = frappe.new_doc("Serial No")
        doc.serial_no = serial_no
        doc.item_code = self.item_code
        doc.item_name = getattr(self, "item_name", None)
        doc.description = getattr(self, "description", None)
        doc.company = self.company
        doc.status = "Active"
        doc.batch_no = getattr(self, "batch_no", None)
        doc.purchase_document_no = voucher_no
        doc.save(ignore_permissions=True)

    return sr_nos

def patch_serial_creation_methods():
    SerialBatchCreation.make_serial_nos = _custom_make_serial_nos
    SerialBatchCreation.get_auto_created_serial_nos = _custom_get_auto_created_serial_nos

    # Also patch Work Order make_serial_nos to per-doc so autoname runs
    try:
        from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder

        def _custom_wo_make_serial_nos(self, args):
            from frappe.model.naming import make_autoname
            from erpnext.stock.doctype.serial_no.serial_no import get_available_serial_nos

            item_details = frappe.get_cached_value(
                "Item", self.production_item, ["serial_no_series", "item_name", "description"], as_dict=1
            )

            batches = []
            if getattr(self, "has_batch_no", None):
                batches = frappe.get_all(
                    "Batch", filters={"reference_name": self.name}, order_by="creation", pluck="name"
                )

            serial_list = []
            if item_details.get("serial_no_series"):
                serial_list = get_available_serial_nos(item_details.serial_no_series, int(self.qty))
            else:
                for _ in range(int(self.qty)):
                    serial_list.append(make_autoname("SR-.########", "Serial No"))

            if not serial_list:
                return

            index = 0
            remaining_batches = list(batches)

            for serial_no in serial_list:
                index += 1
                batch_no = None
                if remaining_batches and getattr(self, "batch_size", None):
                    batch_no = remaining_batches[0]
                    if self.batch_size and index % int(self.batch_size) == 0:
                        remaining_batches.pop(0)

                doc = frappe.new_doc("Serial No")
                doc.serial_no = serial_no
                doc.item_code = self.production_item
                doc.item_name = item_details.item_name
                doc.description = item_details.description
                doc.company = self.company
                doc.status = "Inactive"
                doc.work_order = self.name
                doc.batch_no = batch_no
                doc.save(ignore_permissions=True)

        WorkOrder.make_serial_nos = _custom_wo_make_serial_nos
    except Exception:
        try:
            frappe.log_error(title="edevis WO serial patch error")
        except Exception:
            pass

def patch_work_order_serial_creation():
    """Expose a dedicated patch function for Work Order monkey patching."""
    try:
        from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder

        def _custom_wo_make_serial_nos(self, args):
            from frappe.model.naming import make_autoname
            from erpnext.stock.doctype.serial_no.serial_no import get_available_serial_nos

            item_details = frappe.get_cached_value(
                "Item", self.production_item, ["serial_no_series", "item_name", "description"], as_dict=1
            )

            batches = []
            if getattr(self, "has_batch_no", None):
                batches = frappe.get_all(
                    "Batch", filters={"reference_name": self.name}, order_by="creation", pluck="name"
                )

            serial_list = []
            if item_details.get("serial_no_series"):
                serial_list = get_available_serial_nos(item_details.serial_no_series, int(self.qty))
            else:
                for _ in range(int(self.qty)):
                    serial_list.append(make_autoname("SR-.########", "Serial No"))

            if not serial_list:
                return

            index = 0
            remaining_batches = list(batches)

            for serial_no in serial_list:
                index += 1
                batch_no = None
                if remaining_batches and getattr(self, "batch_size", None):
                    batch_no = remaining_batches[0]
                    if self.batch_size and index % int(self.batch_size) == 0:
                        remaining_batches.pop(0)

                doc = frappe.new_doc("Serial No")
                doc.serial_no = serial_no
                doc.item_code = self.production_item
                doc.item_name = item_details.item_name
                doc.description = item_details.description
                doc.company = self.company
                doc.status = "Inactive"
                doc.work_order = self.name
                doc.batch_no = batch_no
                doc.save(ignore_permissions=True)

        WorkOrder.make_serial_nos = _custom_wo_make_serial_nos
    except Exception:
        try:
            frappe.log_error(title="edevis WO serial patch error")
        except Exception:
            pass