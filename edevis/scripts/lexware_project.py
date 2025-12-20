import frappe
import pyodbc
from datetime import date, datetime
from edevis.scripts.naming_series import NamingSeries

def execute(name=None):
    if name is None:
        name ="%"
        print("Kein Name angegeben, verwende Wildcard '%' für alle Projekte.")

    series = NamingSeries("PROJ-")
    current_counter = series.get_counter()
    print(f"Aktueller Counter für {series.name}: {current_counter}")
    
    projects = Project(filter=name)
    
    results = projects.get_items_lexware(name)
    for result in results:
        if projects.exists_in_erp(result):
            print(f"{result['ProjektNr']}: {result['Bezeichnung']} (exists)")
            continue

        if projects.create_missing_item(result):
            print(f"{result['ProjektNr']}: {result['Bezeichnung']}")
            break
    return


class Project:
    def __init__(self, filter=None):
        self._unique_key = "name"
        self._erp_class = "Project"
        self.lexware_table = "FK_Projekt"
        self.lexware_unique_key = "ProjektNr"
        self.filter = filter
        self.series = NamingSeries("PROJ-")
        pass

    def format_lexware_date(self, lexware_date):
        """Konvertiert ein Lexware-Datum im Format JJJJMMTT in ein ISO-Datum JJJJ-MM-TT."""
        dt = datetime.fromisoformat(lexware_date)
        formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
        return formatted
       
    def exists_in_erp(self, item):
        """Prüft, ob ein Element bereits in ERPNext existiert."""
        ukey = self.series.name + str(item.get(self.lexware_unique_key))
        return frappe.db.exists(self._erp_class, ukey)
    
    def create_missing_item(self, item):
        """Prüft, ob Elemente in ERPNext existieren, und legt neue an."""
        project_no = int(item.get(self.lexware_unique_key))
        print(f"Processing project no: {project_no}")

        if self.series.get_counter() != project_no-1:
            self.series.set_counter(project_no -1)
            print(f"Naming Series Counter für {self.series.name} auf {project_no-1} gesetzt.")

        ukey = self.series.name + str(item.get(self.lexware_unique_key))
        if not frappe.db.exists(self._erp_class, ukey):
            

            full_name = item.get("Bearbeiter")  # aus Lexware

            # Suche den User
            user = frappe.db.get_value("User", {"full_name": full_name, "enabled": 1}, "name")
            print(f"User found for '{full_name}': {user}")

            new_proj = frappe.get_doc({
                "doctype": self._erp_class,
                "project_name": item.get("Bezeichnung"),
                #"name": ukey,
                "notes": item.get("Beschreibung"),
                "project_type": "External" if project_no < 8000 else "Internal",
                "expected_start_date": item.get("Datum_StartSoll"),
                "expected_end_date": item.get("Datum_EndeSoll"),
                "is_active": "No" if item.get('bAbgeschlossen') == 1 else "Yes",
                "status": "Completed" if item.get('bAbgeschlossen') == 1 else "Open",
                "customer": item.get("KundenNr"),
                "project_manager": user,
                #"naming_series": self.series.name,

                # Optional: weitere Felder aus Lexware mappen, z.B. Adresse
                # "supplier_type": sup.get("Typ"),
                # "tax_id": sup.get("Steuernummer"),
            })
            #json_output = json.dumps(new_supplier, indent=4, ensure_ascii=False)
            print(f"Aktiv: {item.get('bAbgeschlossen') == 1}")

            try:
                new_proj.insert(ignore_permissions=True)
            except Exception as e:
                print(f"Fehler beim Anlegen des Projekts {ukey}: {e}")
                return False
            
            # frappe.db.commit()
            return True
        else:                
            return False


    def get_items_lexware(self, name):
        """Holt Elemente aus Lexware und gibt sie als Liste von Dictionaries zurück."""
        print("getting items from lexware...")
        conn = pyodbc.connect("DSN=lexware2")
        cursor = conn.cursor()
        print(f"SELECT * FROM {self.lexware_table} WHERE {self.lexware_unique_key} LIKE ?", (f"%{self.filter}%",))
        cursor.execute(f"SELECT * FROM {self.lexware_table} WHERE {self.lexware_unique_key} LIKE ?", (f"%{self.filter}%",))
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        def serialize_row(row):
            new_row = {}
            for col, val in zip(columns, row):
                if val is None or val == 0:
                    continue
                if isinstance(val, (date, datetime)):
                    val = val.isoformat()
                new_row[col] = val
            return new_row

        return [serialize_row(row) for row in rows]
