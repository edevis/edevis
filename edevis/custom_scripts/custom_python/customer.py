import frappe
from frappe.model.mapper import get_mapped_doc
from frappe import _

log = frappe.logger("Edevis")
log.setLevel("DEBUG")

def after_insert(doc, method):
    log.debug(f"customer: after_insert({doc})")

    company = getattr(doc, 'company', None)
    if not company:
        company = frappe.defaults.get_user_default("Company") or frappe.db.get_value("Company", {}, "name")
    create_and_link_debit_account(doc, company)

def create_and_link_debit_account(doc, company):
    create_debit_account = frappe.db.get_single_value("Edevis Settings", "auto_create_customer_accounts")

    if create_debit_account:
        debit_account = create_debit_account_for_customer(doc, company)

        if not debit_account:
            return

        account_doc = frappe.new_doc("Party Account")
        account_doc.update({
            "parent": doc.name,
            "company": company,
            "account": debit_account,
            "parenttype": "Customer",
            "parentfield": "accounts"
        })
        account_doc.insert(ignore_permissions=True)

def create_debit_account_for_customer(doc, company):
    log.debug(f"customer: create_debit_account_for_customer({doc})")
    parent_account = frappe.db.get_single_value("Edevis Settings", "debitors_parent_account")

    if not parent_account:
        frappe.log_error(
            _("Failed to create Debit Account for customer {} as no Debitors Parent Account is setup in the {}"
              .format(
                  frappe.utils.get_link_to_form("Customer", doc.name),
                  frappe.utils.get_link_to_form("Edevis Settings", "Edevis Settings")
              )),
            _("failed to create customer debit account")
        )
        frappe.throw(
            _("Failed to create Debit Account for this customer, please set up Debitors Parent Account in {}.")
            .format(frappe.utils.get_link_to_form("Edevis Settings", "Edevis Settings"))
        )
        return None

    account_account_name = f"{doc.name} - {doc.customer_name}"

    try:
        existing_account = frappe.db.exists("Account", {
            "account_name": account_account_name,
            "company": company
        })
        if existing_account:
            return existing_account

        new_account_doc = frappe.get_doc({
            'doctype': 'Account',
            'account_name': account_account_name,
            'parent_account': parent_account,
            'company': company,
            'account_type': "Receivable"
        })
        new_account_doc.insert()
        log.debug(f"customer : create_debit_account_for_customer : new account created : ({account_account_name})")
        return new_account_doc.name

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            _("Something went wrong while creating debit account for {}"
              .format(frappe.utils.get_link_to_form("Customer", doc.name)))
        )
        return None


@frappe.whitelist()
def create_opportunity(source_name, target_doc=None):
	def postprocess(source, doc):
		pass

	doc = get_mapped_doc(
		"Customer",
		source_name,
		{
			"Customer": {
				"doctype": "Opportunity",
				"validation": {
					
				},
				"field_map": {
					"doctype": "opportunity_from",
					"name": "party_name",
					"Open": "status",
					"lead_name":"custom_lead",
				},
			},
			
		},
		target_doc,
		postprocess
	)

	return doc