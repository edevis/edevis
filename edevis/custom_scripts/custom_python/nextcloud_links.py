#!/usr/bin/env python3
"""
Nextcloud API Script zum Löschen abgelaufener Download-Links
Für gehostete Nextcloud-Instanzen ohne Shell-Zugriff
Kompatibel mit ERPNext/Frappe
"""

# import frappe
import requests
import json
from datetime import datetime
import logging
from typing import List, Dict, Optional

class NextcloudAPI:
    def __init__(self, base_url: str, username: str, password: str, logger = None):
        """
        Initialisiert die Nextcloud API Verbindung
        
        Args:
            base_url: Nextcloud Base URL (z.B. https://ihre-domain.de)
            username: Nextcloud Benutzername
            password: Nextcloud Passwort oder App-Token
        """

        # Logging konfigurieren
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel("INFO")

        self.base_url = base_url.rstrip('/')

        self.auth = (username, password)
        self.headers = {
            'OCS-APIRequest': 'true',
            'Accept': 'application/json'
        }
        
    
    def create_nextcloud_share(self, path, expire_date):
        self.logger.info(f"Creating Download Link in Nextcloud...")
                
        data = {
            "path": path,                         # z.B. /Software/Produkt_XYZ.exe
            "shareType": 3,                       # 3 = public link
            "expireDate": expire_date,            # Expiry date in 'YYYY-MM-DD' format
            "password": ""                        # Customer download password (if needed)
        }

        try:
            url = f"{self.base_url}/ocs/v2.php/apps/files_sharing/api/v1/shares"
            # Versuche JSON zu parsen, sonst fallback XML
            try:
                self.logger.info(f"POST {url} with auth {self.auth}")
                r = requests.post(url, headers=self.headers, auth=self.auth, data=data, timeout=10)
                r.raise_for_status()  # HTTP-Fehler (4xx/5xx) -> Exception    
                resp = r.json()
            except json.JSONDecodeError:
                self.logger.error(f"Nextcloud lieferte keine JSON-Daten: {r.text}")
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
            self.logger.error(f"Timeout bei Anfrage an Nextcloud")
            return {"error": "Timeout bei Anfrage an Nextcloud"}

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP Fehler: {str(e)}. Response = {r.text}")
            return {"error": f"HTTP Fehler: {str(e)}", "response": r.text}

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request fehlgeschlagen: {str(e)}")
            return {"error": f"Request fehlgeschlagen: {str(e)}"}

        except Exception as e:
            self.logger.error(f"Unerwarteter Fehler: {str(e)}")
            return {"error": f"Unerwarteter Fehler: {str(e)}"}


    def get_all_shares(self) -> List[Dict]:
        """
        Ruft alle Shares von der Nextcloud API ab
        
        Returns:
            Liste aller Shares
        """
        url = f"{self.base_url}/ocs/v2.php/apps/files_sharing/api/v1/shares"
        # url = f"{self.base_url}/ocs/v1.php/apps/files_sharing/api/v1/shares"
        
        try:
            response = requests.get(
                url, 
                auth=self.auth, 
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            shares = data.get('ocs', {}).get('data', [])
            
            self.logger.info(f"Gefunden: {len(shares)} Shares")
            return shares
            
        except requests.RequestException as e:
            self.logger.error(f"Fehler beim Abrufen der Shares: {e}")
            raise
    
    def delete_share(self, share_id: int) -> bool:
        """
        Löscht einen Share über die API
        
        Args:
            share_id: ID des zu löschenden Shares
            
        Returns:
            True wenn erfolgreich gelöscht, False sonst
        """
        url = f"{self.base_url}/ocs/v2.php/apps/files_sharing/api/v1/shares/{share_id}"
        
        try:
            response = requests.delete(
                url, 
                auth=self.auth, 
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info(f"Share {share_id} erfolgreich gelöscht")
                return True
            else:
                self.logger.error(f"Fehler beim Löschen von Share {share_id}: HTTP {response.status_code}")
                return False
                
        except requests.RequestException as e:
            self.logger.error(f"Fehler beim Löschen von Share {share_id}: {e}")
            return False
    
    def is_expired(self, expiration_date: str) -> bool:
        """
        Prüft ob ein Share abgelaufen ist
        
        Args:
            expiration_date: Datum im Format 'YYYY-MM-DD HH:MM:SS'
            
        Returns:
            True wenn abgelaufen, False sonst
        """
        try:
            # Nextcloud gibt manchmal verschiedene Datumsformate zurück
            for date_format in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                try:
                    expiration = datetime.strptime(expiration_date, date_format)
                    return expiration < datetime.now()
                except ValueError:
                    continue
            
            self.logger.warning(f"Unbekanntes Datumsformat: {expiration_date}")
            return False
            
        except Exception as e:
            self.logger.error(f"Fehler beim Parsen des Datums {expiration_date}: {e}")
            return False
    
    def cleanup_expired_shares(self, dry_run: bool = True) -> int:
        """
        Findet und löscht abgelaufene Shares
        
        Args:
            dry_run: Wenn True, werden keine Shares gelöscht, nur angezeigt
            
        Returns:
            Anzahl der gelöschten/zu löschenden Shares
        """
        shares = self.get_all_shares()
        deleted_count = 0
        
        mode = "DRY RUN - Keine Änderungen" if dry_run else "ECHTE AUSFÜHRUNG"
        self.logger.info(f"=== {mode} ===")
        
        for share in shares:
            # Nur Public Links (share_type = 3) mit Ablaufzeit prüfen
            if share.get('share_type') == 3 and share.get('expiration'):
                expiration_date = share['expiration']
                
                if self.is_expired(expiration_date):
                    file_name = share.get('file_target', share.get('path', 'Unbekannt'))
                    
                    self.logger.info(f"Abgelaufener Share gefunden:")
                    self.logger.info(f"  - ID: {share['id']}")
                    self.logger.info(f"  - Datei: {file_name}")
                    self.logger.info(f"  - Token: {share['token']}")
                    self.logger.info(f"  - Abgelaufen am: {expiration_date}")
                    
                    if not dry_run:
                        if self.delete_share(share['id']):
                            deleted_count += 1
                            self.logger.info("  ✓ Erfolgreich gelöscht")
                        else:
                            self.logger.error("  ✗ Fehler beim Löschen")
                    else:
                        deleted_count += 1
                        self.logger.info("  → Würde gelöscht werden")
        
        action = "würden gelöscht werden" if dry_run else "wurden gelöscht"
        self.logger.info(f"Zusammenfassung: {deleted_count} abgelaufene Shares {action}")
        
        return deleted_count
    
    def get_expired_shares_info(self) -> List[Dict]:
        """
        Gibt Informationen über abgelaufene Shares zurück (für Frappe Integration)
        
        Returns:
            Liste mit Details der abgelaufenen Shares
        """
        shares = self.get_all_shares()
        expired_shares = []
        
        for share in shares:
            if share.get('share_type') == 3 and share.get('expiration'):
                if self.is_expired(share['expiration']):
                    expired_shares.append({
                        'id': share['id'],
                        'token': share['token'],
                        'file_name': share.get('file_target', share.get('path', 'Unbekannt')),
                        'expiration_date': share['expiration'],
                        'url': f"{self.base_url}/s/{share['token']}"
                    })
        
        return expired_shares
