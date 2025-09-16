import frappe
import requests
import json
from datetime import datetime, timedelta
from edevis.custom_scripts.custom_python.nextcloud_links import NextcloudAPI


def create_nextcloud_share(path, expire_date = datetime.now() + timedelta(days=7)):        
    url = "https://cloud.edevis.eu/ocs/v1.php/apps/files_sharing/api/v1/shares"
    auth_user = "erpnext_api"
    auth_pass = "Ayvpex-tivbig-topmy9"

    headers = {
        "OCS-APIRequest": "true",
        "Accept": "application/json"
    }

    data = {
        "path": path,                         # z.B. /Software/Produkt_XYZ.exe
        "shareType": 3,                       # 3 = public link
        "expireDate": expire_date.strftime("%Y-%m-%d"),
        "password": ""                 # Falls du wirklich ein Passwort vergeben willst
    }

    try:
        r = requests.post(url, headers=headers, auth=(auth_user, auth_pass), data=data, timeout=10)                
        r.raise_for_status()  # HTTP-Fehler (4xx/5xx) -> Exception    

        # Versuche JSON zu parsen, sonst fallback XML
        try:
            resp = r.json()
        except json.JSONDecodeError:
            return {"error": "Nextcloud lieferte keine JSON-Daten", "response": r.text}

        # Prüfen, ob die Nextcloud-API einen Fehlercode liefert
        ocs_meta = resp.get("ocs", {}).get("meta", {})
        if ocs_meta.get("status") != "ok":
            return {
                "error": "Nextcloud API Fehler",
                "status": ocs_meta.get("status"),
                "statuscode": ocs_meta.get("statuscode"),
                "message": ocs_meta.get("message"),
                "raw": resp
            }

        # URL zurückgeben
        return {"url": resp["ocs"]["data"]["url"]}

    except requests.exceptions.Timeout:
        return {"error": "Timeout bei Anfrage an Nextcloud"}

    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP Fehler: {str(e)}", "response": r.text}

    except requests.exceptions.RequestException as e:
        return {"error": f"Request fehlgeschlagen: {str(e)}"}

    except Exception as e:
        return {"error": f"Unerwarteter Fehler: {str(e)}"}
    
if __name__ == "__main__":
    try:
        print("Test create_nextcloud_share function")
        result = create_nextcloud_share("/edevis.com Software Downloads/Drivers/Signal Generator (ESGx)/ESG3/ESG USB Driver/ESG3 Driver.exe")
        if "error" in result:
            share_link =  f"Error creating share : {result['error']}. Message = {result['message'] if 'message' in result else 'N/A' }"
            print(f"Nextcloud error:\n{share_link}")
        else:
            share_link = result["url"]                    
            print(f"Nextcloud Public Share Link:\n{share_link}")

        print("\nTest NextcloudAPI class")
        api = NextcloudAPI("https://cloud.edevis.eu", "erpnext_api", "Ayvpex-tivbig-topmy9")

        result = api.create_nextcloud_share("/edevis.com Software Downloads/Drivers/Signal Generator (ESGx)/ESG3/ESG USB Driver/ESG3 Driver.exe")

        # result = create_nextcloud_share("/edevis.com Software Downloads/Software/DisplayImg 7/DisplayImg 7 Professional/Setup DisplayImg 7.exe")
        if "error" in result:
            share_link =  f"Error creating share : {result['error']}. Message = {result['message'] if 'message' in result else 'N/A' }"
            print(f"Nextcloud error:\n{share_link}")
        else:
            share_link = result["url"]                    
            print(f"Nextcloud Public Share Link:\n{share_link}")
    except Exception as e:
        print(f"Fehler: {e}")