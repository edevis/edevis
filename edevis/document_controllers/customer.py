'''

Customer Document Controller
Inherits the Base Class of Customer DocType into Custom Class 
using the hooks override_doctype_class method

'''

import frappe
from frappe.utils import cint, cstr
from frappe.query_builder.functions import _max as get_max_value
from erpnext.selling.doctype.customer.customer import Customer as ERPNextCustomer
import re


from frappe import _
class Customer(ERPNextCustomer):
    
    #overrides existing autoname function in standard Customer Class from ERPNext
    def autoname(self):
        customer_id = 10001
        last_customer_id = self.get_last_customer_id()
        
        #validates if the max customer id is greater than 10000, as the 10000 is the starting ID for Customer
        if last_customer_id >= 10001:
            customer_id = last_customer_id + 1
        
        #sets customer ID
        self.name = cstr(customer_id)

    # Preserve display name when renaming the document ID
    def before_rename(self, old_name, new_name, merge=False):
        # store current customer_name to restore later in after_rename
        self._preserved_customer_name = self.customer_name
        return {"new": new_name}

    def after_rename(self, old_name, new_name, merge=False):
        # restore customer_name if it got changed during rename
        preserved = getattr(self, "_preserved_customer_name", None)
        if preserved and self.customer_name != preserved:
            self.db_set("customer_name", preserved, update_modified=False)
        # clean up in-memory attribute
        if hasattr(self, "_preserved_customer_name"):
            delattr(self, "_preserved_customer_name")


    def get_last_customer_id(self) -> int:
        customer = frappe.qb.DocType("Customer")
        
        #returns the max customer ID using SQL MAX() function
        return cint(get_max_value(customer, "name", customer.name.regexp(r"1[0-9]{4}")))


    #overrides and inherits existing after_insert function in standard Customer Class from ERPNext
    def after_insert(self):
        super(Customer, self).after_insert()
        
        #gets default company
        company = frappe.defaults.get_global_default("company")

        #creates and links a debit account with the customer
        self.create_and_link_debit_account(company)
        
        self.link_contact()
        
    def validate(self):
         super(Customer, self).validate()
         self.validate_tax_category()
         
    def validate_tax_category(self): 
        
        tax_category = self.tax_category or ''
        tax_id = self.tax_id or ''
        
        if tax_category == "Inland" and tax_id != '':           
            
            vatPatternGermany = '(DE)?[0-9]{9}'
            result = re.match(vatPatternGermany, tax_id)
            
            if not result:
                
                self.tax_id = ''
                
                frappe.msgprint(
                _("The provided VAT <strong>{}</strong> is not valid in Germany.<br/><br/>It should start with 'DE' followed by nine single digit numbers (e.g. <strong>DE123456789</strong>)"
                .format(
                    tax_id
                ))
            )       

    def link_contact(self):
        #fetches  Primary Contact from Lead
        if self.lead_name:
            if frappe.db.exists("Contact", frappe.db.get_value("Dynamic Link", {"link_name": self.lead_name}, "parent")):
                contact = frappe.get_doc("Contact", frappe.db.get_value("Dynamic Link", {"link_name": self.lead_name}, "parent"))
                contact.append("links", {
                    "link_doctype": "Customer",
                    "link_name": self.name
                })
                contact.save()
                self.customer_primary_contact = contact.name
                self.save()

    def create_and_link_debit_account(self, company):
        #get the value for auto debit account creation from settings 
        create_debit_account = frappe.db.get_single_value("Edevis Settings", "auto_create_customer_accounts")

         #validates if auto debit account creation is enabled in the settings
        if create_debit_account:

            #create_debit_account() creates debit account as customer_id - customer_name - company_abbr eg. 10001 - Nasir Khan - NKC
            debit_account = self.create_debit_account(company)
            
            #link account with the customer
            account_doc = frappe.new_doc("Party Account")
            account_doc.update(
                {
                    "parent": self.name, 
                    "conpany": company, 
                    "account": debit_account,
                    "parenttype": "Customer",
                    "parentfield": "accounts"
                }
            )
            account_doc.insert(ignore_permissions=True)


    def create_debit_account(self, company):
        #gets Debitors Parent Account from Account Settings
        parent_account = frappe.db.get_single_value("Edevis Settings", "debitors_parent_account")
        
        #validates if Debitors Parent Account is setup in Account Settings
        if not parent_account:

            #logs and throws error in case of missing Debitors Parent Account in the Account Settings.
            frappe.log_error(
                _("Failed to create Debit Account for customer {} as no Debitors Parent Account is setup in the {}"
                .format(
                    frappe.utils.get_link_to_form("Customer", self.name), 
                    frappe.utils.get_link_to_form("Edevis Settings", "Edevis Settings")
                )), 
                _("failed to create customer debit account")
            )
            frappe.throw(
                "Failed to create Debit Account for this customer, please set up Debitors Parent Account in {}."
                .format(frappe.utils.get_link_to_form("Edevis Settings", "Edevis Settings"))
            )
            return
            
        
        #sets account name using customer_id - customer_name - company_abbr eg. 10001 - Nasir Khan - NKC
        account_account_name = f"{self.name} - {self.customer_name}"
        
        #creates New Debit Account document in the system
        try:
            new_account_doc = frappe.get_doc({
                'doctype': 'Account',
                'account_name': account_account_name,
                'parent_account': parent_account,
                'company': company,
                'account_type': "Receivable"
            })
            new_account_doc.insert()

            #returns newly created Debit account name
            return new_account_doc.name
        
        #handles exception and logs error in case of failure while creating a debit account
        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(), 
                _("something went wrong while creating debit account for {}"
                .format(frappe.utils.get_link_to_form("Customer", self.name)))
            )


    def before_insert(self):
        #validates if same named customer exists in the system
        self.validate_customer_name()


    def validate_customer_name(self):
        existing_customer = frappe.db.get_value("Customer", {"customer_name": self.customer_name}, "name")
        if existing_customer:

            #shows warning that a same named customer already exists in the system
            frappe.msgprint(
                _("Customer <strong>{}</strong> with same name as <strong>{}</strong> already exists, please make sure it is not a duplicate."
                .format(
                    frappe.utils.get_link_to_form("Customer", existing_customer),
                    self.customer_name
                ))
            )

    def check_vat(self):
        from edevis.custom_scripts.custom_python.checkvat import checkvat
        return checkvat(self.name, self.tax_id, self.customer_primary_address, popup_flag=False)