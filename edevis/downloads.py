import frappe
import requests
from datetime import date, timedelta
import xml.etree.ElementTree as ET


NC_URL = "https://cloud.edevis.eu"
NC_USER = "erpnext-api"
NC_APP_PASS = frappe.get_password("Nextcloud Settings", None, "password")

logger = frappe.logger("Software Download Request") 


def create_nextcloud_share(path, expire_days=7, password=None):
    url = f"{NC_URL}/ocs/v1.php/apps/files_sharing/api/v1/shares"
    headers = {"OCS-APIRequest": "true"}
    data = {
        "path": path,
        "shareType": 3,
        "expireDate": (date.today() + timedelta(days=expire_days)).strftime("%Y-%m-%d")
    }
    if password:
        data["password"] = password

    r = requests.post(url, headers=headers, auth=(NC_USER, NC_APP_PASS), data=data)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    return root.find(".//url").text


def send_download_links(doc, method):        
    pass

    # # doc.status = "Approved"
    # links_html = ""
    # for item in doc.items:
    #     share_link = create_nextcloud_share(item.path, expire_days=7)
    #     item.share_link = share_link
    #     links_html += f"<li><strong>{item.name}:</strong> <a href='{share_link}'>{share_link}</a></li>"

    # html_message = f"""
    # <html>
    # <body>
    #     <h2>Hallo {doc.customer_name or doc.from_email},</h2>
    #     <p>Hier sind Ihre verfügbaren Downloads:</p>
    #     <ul>
    #     {links_html}
    #     </ul>
    #     <p>Die Links sind gültig bis {doc.expires_on or (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')}.</p>
    #     <p>Mit freundlichen Grüßen<br>Ihr Support-Team</p>
    # </body>
    # </html>
    # """

    # frappe.sendmail(
    #     recipients=[doc.from_email],
    #     subject=f"Ihre Software Downloads für {doc.name}",
    #     message=html_message,
    #     reference_doctype=doc.doctype,
    #     reference_name=doc.name,
    #     now=True
    #     )

    # doc.status = "Completed"
    # doc.save(ignore_permissions=True)