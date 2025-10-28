import frappe
from frappe.model.document import Document
from frappe.utils import cstr
from datetime import datetime, timedelta
from edevis.custom_scripts.custom_python.nextcloud_links import NextcloudAPI

logger = frappe.logger("Edevis")
logger.setLevel("DEBUG")

def get_customer_by_email(email):
    logger.info(f"DocType SDR: Pending. Absender: {email}. Searching in customer database...")

    # 1. Kontakt anhand E-Mail finden
    contact = frappe.db.get_value(
        "Contact",
        {"email_id": email},
        ["name"],
        as_dict=True
    )

    if not contact:
        logger.info(f"DocType SDR: Rejected. Absender: {email} not found in customer database!")
        return None

    # 2. Verknüpfung zu Customer prüfen (über Dynamic Link)
    links = frappe.get_all(
        "Dynamic Link",
        filters={
            "link_doctype": "Customer",
            "parenttype": "Contact",
            "parent": contact.name
        },
        fields=["link_name"]
    )

    if not links:
        logger.info(f"DocType SDR: Rejected. Sender: {email} found in customer database but not linked!")
        return None

    # 3. Kundendaten holen
    customers = []
    for link in links:
        customer = frappe.db.get_value(
            "Customer",
            link.link_name,
            ["name", "customer_name"],
            as_dict=True
        )
        if customer:
            logger.info(f"DocType SDR: Found. Sender: {customer.name} found in customer database!")
            customers.append(customer)

    return customers

class SoftwareDownloadRequest(Document):

    def before_insert(self):    
        logger.debug(f"DocType SDR: Neuer Eintrag erstellt. Absender: {self.sender}")

        self.status = "Pending"

    def after_insert(self):
        if self.status != "Pending":
            logger.debug(f"DocType SDR: Status not Pending ({self.status}). Skip checks.")
            return
        
        domain_name = self.sender.split("@")[-1].lower()
        allowed = frappe.get_all("Software Download Whitelist Domains", filters={"domain_name": domain_name}, pluck="domain_name")
        if allowed:
            logger.info(f"DocType SDR: Approved via domain. Sender: {self.sender}")
            if self.release_download():
                self.status = "Approved"
                self.save(ignore_permissions=True)
                return
        else:
            customers = get_customer_by_email(self.sender)  # Nur zum Testen, ob Kunde existiert
            if customers:
                logger.info(f"DocType SDR: Approved via customer for {self.sender}: " + ", ".join([c.customer_name for c in customers]))
                if self.release_download():
                    self.status = "Approved"
                    self.save(ignore_permissions=True)
                    return
            else:
                logger.info(f"DocType SDR: No customer found for {self.sender}")

        self.status = "Rejected"
        self.save(ignore_permissions=True)

    def before_save(self):
        if self.status == "Approved" and not self.release_download():
            frappe.throw("Download konnte nicht freigegeben werden. Status bleibt Pending (nach reload sichtbar).")

    def release_download(self):
        logger.debug(f"DocType SDR: Release download. Search product name: {self.subject}")

        if len(self.items) > 0:
            logger.debug(f"DocType SDR: Already has {len(self.items)} items. Skip.")
            return True  # Bereits freigegeben
        
        try:
            settings = frappe.get_single("Software Download Request Settings")
        except Exception as e:
            logger.error(f"DocType SDR: Settings not found: {str(e)}")
            self.status = "Pending"
            return False        
        
        url = f"{settings.nextcloud_url}"
        auth_user = settings.nextcloud_user
        auth_pass = settings.get_password('nextcloud_password')

        logger.debug(f"DocType SDR: Settings found: {settings.nextcloud_url} / user = {settings.nextcloud_user}")

        api = None
        parent = None
        try:
            api = NextcloudAPI(url, auth_user, auth_pass, logger)
            parent = frappe.get_doc(
                "Software Download Link",
                {"product_name": self.subject}
            )
        except Exception as e:
            parent = None

        if parent is None:
            logger.error(f"DocType SDR: No Software Download Link found for the selected product: {self.subject}")
            self.status = "Pending"
            return False

        if api is None:
            logger.error(f"DocType SDR: No API access to Nextcloud {url}")
            self.status = "Pending"
            return False

        logger.debug(f"DocType SDR: Parent found : {parent.product_name}")
        
        self.description = parent.description

        if not self.expires_on:  # nur wenn leer
            self.expires_on = (datetime.today() + timedelta(days=7)).date()
            logger.debug(f"DocType SDR: Expiry: {self.expires_on}")

        for el in parent.items:
            logger.debug(f"Element found : {el.link_name} - {el.path}")
            result = api.create_nextcloud_share(el.path, self.expires_on)
            if "error" in result:
                logger.error(f"DocType SDR: Error creating share : {result['error']}. Message = {result['message'] if 'message' in result else 'N/A' }")
                share_link =  f"Error creating share : {result['error']}. Message = {result['message'] if 'message' in result else 'N/A' }"
            else:
                share_link = result["url"]
                logger.debug(f"DocType SDR: Download Url: {share_link}")

            self.append("items", {
                "link_name": el.link_name,
                "path": el.path,
                "item_code": el.item_code,
                "description": el.description,
                "download_link": share_link
            })
            logger.debug(f"DocType SDR: Element appended: {share_link}")

        logger.debug(f"DocType SDR: Cleaning up expired shares")
        api.cleanup_expired_shares()
    
        return True    

