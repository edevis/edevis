import frappe
import pyodbc
import json
from datetime import date, datetime
from ..custom_scripts.custom_python.supplier import create_and_link_credit_account

# process x data-sets, then stop
breakcond = 2

def execute(name=None):
    if not name:
        name ="%"
    # get_table(name)
    
	# Get suppliers from Lexware and create missing ones in ERPNext
    lexware_suppliers = get_suppliers_lexware(name)
    for sup in lexware_suppliers:
        create_missing_suppliers(sup)


    suppliers = frappe.get_all(
        "Supplier",
        fields=["name", "supplier_name"],
        # filters=filters,
    )

	# Create missing supplier accounts
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_value("Company", {}, "name")
    it = 0
    for supplier in suppliers:
        doc = frappe.get_doc("Supplier", supplier.name)
        if doc.accounts:
            continue  # Skip if accounts already exist
        create_and_link_credit_account(doc, company)
        it  += 1
        if it >= breakcond:
            print(f"Abbruch nach {breakcond} verarbeiteten Lieferanten.")
            return
        
        print(f"Processed Supplier Account {doc.name}")
        

    return


COUNTRY_MAP = {
    "Deutschland": "Germany",
    "IRLAND": "Ireland",
    "Irland": "Ireland",
    "DE": "Germany",
    "UK": "United Kingdom",
    "Tschechische Republik": "Czech Republic",
    "Polen": "Poland",
    "Österreich": "Austria",
    "Schweiz": "Switzerland",
    "Frankreich": "France",
    "USA": "United States",
    "Taiwan (R.O.C.)": "Taiwan",
    "Italien": "Italy",
    "Spanien": "Spain",
    "Niederlande": "Netherlands",
    "Belgien": "Belgium",
    "Luxemburg": "Luxembourg",
    "Estland": "Estonia",
    # weitere Länder hier ergänzen
}

DE_LANG_COUNTRIES = ["Germany", "Austria", "Switzerland", "Luxembourg"]

def get_language(country):
    """
    Liefert 'de' für deutschsprachige Länder, sonst 'en'.
    """
    if country in DE_LANG_COUNTRIES:
        return "de"
    return "en"


def parse_payment_terms(konditionen, country):
    """
    Ermittelt die Zahlungsbedingung basierend auf der Zahl am Anfang.
    - konditionen: String, z.B. "14 Tage netto"
    - country: Übersetztes Land ("Germany" etc.)
    Gibt den passenden Standard Payment Terms Wert zurück.
    """
    if not konditionen:
        return None

    # Erste Zahl extrahieren
    import re
    match = re.match(r"(\d+)", konditionen.strip())
    if not match:
        return None

    days = int(match.group(1))

    # Sprache: deutsch oder englisch
    lang = "de" if country == "Germany" else "en"

    # Map Tage -> Zahlungsbedingung
    payment_terms_map = {
        14: {"de": "14 Tage netto", "en": "14 days net"},
        30: {"de": "30 Tage netto", "en": "30 days net"},
        60: {"de": "60 Tage netto", "en": "60 days net"},
    }

    return payment_terms_map.get(days, {}).get(lang)

def translate_country(country_de):
    if not country_de:
        return None
    return COUNTRY_MAP.get(country_de.strip(), country_de) 


def parse_tax_category(ust_id, country):
    """
    Liefert die Steuerkategorie basierend auf der Umsatzsteuer-ID.
    DE -> Deutschland, EU -> innergemeinschaftlicher Erwerb, sonst International
    """
    if not ust_id:
        return "Drittland" if country != "Germany" else "Inland"

    ust_id = ust_id.strip().upper()
    
    # Prüfen auf Deutschland
    if ust_id.startswith("DE"):
        return "Inland"
    else:
        return "EU"

def add_bank_account(supplier_doc, sup):
    """
    Fügt dem Supplier ein Bankkonto hinzu.
    sup sollte die Bankdaten aus Lexware enthalten, z.B.:
    'BankName', 'IBAN', 'BIC', 'Kontonummer'
    """
    try:
        # Prüfen, ob Konto bereits existiert
        if frappe.db.exists('Supplier Bank', {'supplier': supplier_doc.name, 'account_number': sup.get('szIBAN')}):
            print(f"Bankkonto bereits vorhanden für {supplier_doc.name}: {sup.get('IBAN')}")
            return None

        bank_account = frappe.new_doc('Supplier Bank')
        bank_account.supplier = supplier_doc.name
        bank_account.bank = sup.get('Bank_Institut')
        bank_account.account_number = sup.get('szIBAN')
        bank_account.swift_code = sup.get('szBIC')
        bank_account.primary_account = 1  # Optional: Hauptkonto markieren
        bank_account.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"Bankkonto erfolgreich angelegt für {supplier_doc.name}: {bank_account.account_number}")
        return bank_account

    except Exception as e:
        print(f"Fehler beim Anlegen des Bankkontos für {supplier_doc.name}: {e}")
        return None


def add_address(supplier_doc, sup):
    try:
        address = frappe.new_doc('Address')
        address.address_title = f"{sup.get('Matchcode')} Billing"
        address.address_line1 = sup.get('Anschrift_Strasse')
        address.city = sup.get('Anschrift_Ort')
        address.pincode = sup.get('Anschrift_Plz')
        address.country = translate_country(sup.get('Anschrift_Land'))
        address.is_primary_address = 1
        address.is_shipping_address = 1

        if not address.address_line1:
            print(f"Lieferant {supplier_doc.name} hat keine Straße in der Adresse.")
            return
        
        # Verlinkung zum Supplier
        address.append('links', {
            'link_doctype': 'Supplier',
            'link_name': supplier_doc.name
        })
        address.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        print(f"Fehler beim Anlegen der Adresse für {supplier_doc.name}: {e}")
        return None

def create_missing_suppliers(sup):
    it = 0
    """Prüft, ob Lieferanten in ERPNext existieren, und legt neue an."""
    lieferanten_nr = str(sup.get("LieferantenNr"))        
    country = translate_country(sup.get("Anschrift_Land") or sup.get("Liefer_Land"))
    language = get_language(country)
    payment_terms = parse_payment_terms(sup.get("Konditionen_Zahlungsbedingung"), language)
    tax_id = sup.get("Kontierung_EG_ID_Nr")
    tax_category = parse_tax_category(tax_id, country)        
    cref = sup.get("KundenNr_beim_Lieferanten")
    disabled = sup.get("bInaktiv") == 1

    if not frappe.db.exists("Supplier", lieferanten_nr):
        print(f"Verarbeite Lieferant {lieferanten_nr}: Land={country}, Sprache={language}, Zahlungsbedingungen={payment_terms}, Steuerkategorie={tax_category}")

        # Lieferant anlegen
        new_supplier = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": lieferanten_nr,
            "name": lieferanten_nr, 
            "legacy_id": lieferanten_nr,
            "country": country,
            "default_currency": "EUR",
            "default_price_list": "Standard-Kauf",
            "tax_id": tax_id,
            "language": language,
            "custom_supplier_customer_ref": cref,
            "supplier_group": "Lieferant",
            "tax_category": tax_category,
            "payment_terms": payment_terms,
            "disabled": disabled,
        })

        new_supplier.insert(ignore_permissions=True)
        frappe.db.commit()

        try:
            add_address(new_supplier, sup)
        except ValueError as e:
            print(f"Fehler beim Hinzufügen der Adresse für Lieferant {lieferanten_nr}: {e}")
        
        doc = frappe.get_doc("Supplier", lieferanten_nr)
        doc.supplier_name = sup.get("Anschrift_Firma") or sup.get("Liefer_Firma") or sup.get("Matchcode")
        doc.save()

        print(f"Neuer Lieferant angelegt: {lieferanten_nr} / {sup.get('Liefer_Firma')}")

        it += 1
        if it >= breakcond:
            raise(f"Abbruch nach {breakcond} neu angelegten Lieferanten.")
                        
    else:
    # Lieferant existiert → leere Felder ergänzen
        doc = frappe.get_doc("Supplier", lieferanten_nr)
        updated = False

        # Mapping: Feldname -> Wert aus Lexware / Standard
        fields_to_check = {
            "supplier_name": sup.get("Liefer_Firma") or sup.get("Matchcode"),
            "country": country,
            "language": language,
            "tax_id": tax_id,
            "tax_category": tax_category,
            "payment_terms": payment_terms,
            "custom_supplier_customer_ref": cref,
            "supplier_group": "Lieferant",
            "default_currency": "EUR",
            "default_price_list": "Standard-Kauf",
            "disabled": disabled,
        }

        for field, value in fields_to_check.items():
            if getattr(doc, field) == None and value is not None:
                setattr(doc, field, value)
                updated = True
                print(f"{lieferanten_nr}: Feld '{field}' gesetzt auf '{value}'")

        if updated:
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            print(f"{lieferanten_nr}: Lieferant aktualisiert mit fehlenden Feldern.\n")
            it += 1
            if it >= breakcond:
                raise(f"Abbruch nach {breakcond} neu angelegten Lieferanten.")
                

def get_suppliers_lexware(name):
    """Holt Lieferanten aus Lexware und gibt sie als Liste von Dictionaries zurück."""
    conn = pyodbc.connect("DSN=lexware2")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM FK_Lieferant WHERE Matchcode LIKE ?", (f"%{name}%",))
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


def get_table(name):
    conn = pyodbc.connect("DSN=lexware2")
    cursor=conn.cursor()
    cursor.execute("select * from FK_Lieferant where Matchcode LIKE ?", f"%{name}%")
    columns = [desc[0] for desc in cursor.description]    
    rows = cursor.fetchall()
    def serialize_row(row):
        new_row = {}
        for col, val in zip(columns, row):
            if val is None:
                 continue
            if isinstance(val, (date, datetime)):
                new_row[col] = val.isoformat()  # z.B. "2025-11-07T14:32:00"
            else:
                new_row[col] = val
        return new_row

    results = [serialize_row(row) for row in rows]

    json_output = json.dumps(results, indent=4, ensure_ascii=False)
    print(json_output)

def get_lexware_cust():
    conn = pyodbc.connect("DSN=lexware2")
    cursor=conn.cursor()
    cursor.execute("select * from FK_Kunde")
    row = cursor.fetchone()
    
    while row:
         print(row)
         row = cursor.fetchone()     


def get_lexware_cust_byname(name):
    print(f"select KundenNr, Matchcode from FK_Kunde where Matchcode = {name}")
    conn = pyodbc.connect("DSN=lexware2")
    cursor=conn.cursor()
    cursor.execute("select * from FK_Kunde where Matchcode LIKE ?", f"%{name}%")
    row = cursor.fetchone()
    print('found customer in lexware:', row)
    return row    
    # while row:
    #      print(row)
    #      row = cursor.fetchone()   

def update_customer_ids(name):

    filters = {"customer_name": ("like", f"%{name}%")} if name else {}
    
    customers = frappe.get_all(
        "Customer",
        fields=["name", "customer_name", "customer_group"],
        filters=filters,
    )

    for customer in customers:
        if not customer.name.isdigit() and customer.customer_group != "Einzelperson":
            print(f"{customer.name}")
            continue

            cust = get_lexware_cust_byname(customer.customer_name)
            if cust:
                print(f"Found {customer.customer_name}. in Lexware: {cust} ")
                # try:
                #     frappe.rename_doc("Customer", customer.name, cust[0], force=True, merge=False)
                #     print(f"Renamed {customer.customer_name}:    {customer.name} --> {cust[0]}")
                # except Exception as e:
                #     print(f"Error renaming {customer.name}: {e}")
            else:
                print(f"No legacy ID found for {customer.customer_name}")

