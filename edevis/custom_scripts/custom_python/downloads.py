import frappe
from datetime import date, timedelta

def check_approval(sender):
    if sender == "alexander.dillenz@edevis.de":
        return True
    return False

def send_download_links(doc, method):        
    pass
