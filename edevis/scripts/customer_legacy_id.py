import frappe
import pyodbc
import json
from datetime import date, datetime
from ..custom_scripts.custom_python.customer import create_and_link_debit_account
from .get_key import getchar
from .get_key import Esc
from .get_key import input_char
from .get_key import EscPressedException
from .terminal_color import Colors


menu = f"""

=== ERPNext <> Lexware Kundenplege ===
(1) Filter für Kunden-Nr setzen.

=== Fehlende Kunden anzeigen ===
(2) In ERPNext fehlende Kunden anzeigen
(3) In ERPNext Debitoren-Konto zu Kunden anlegen

=== Aktualisierung von Lexware ===
(4) Adressen anzeigen, fehlende Primäradresse
(5) Lexware Kunden sperren

"""

# process x data-sets, then stop
breakcond = 20
name = None

def main_menu():
    name = None
    while True:		
        try:
            choice = input_char(menu, [str(x) for x in range(1, 9)] + ['w'])
            match choice:
                case '1':
                    name = input("Filter für Kunden-Namen eingeben (z.B. 'BMW%'): ").strip()
                    getchar('Press any key to continue')
                
                case '2':
                    it = 0
                    lexware_customers = get_customers_lexware(name)
                    for sup in lexware_customers:
                        
                        if it >= breakcond:
                            print(f"Abbruch nach {breakcond} neu angelegten Lieferanten.")            
                            break

                        it += create_missing_customers(sup)

                case '3':
                    if not name:
                        print("Filter für Kunden-Namen eingeben (z.B. 'BMW%'): ")
                        continue

                    customers = frappe.get_all(
                        "Customer",
                        fields=["name", "customer_name"],
                        filters=[
                            ["customer_name", "like", f"{name}"]
                        ],
                    )
                    print(f"Found {len(customers)} customers to process.")

                    company = frappe.defaults.get_user_default("Company") or frappe.db.get_value("Company", {}, "name")
                    it = 0
                    for customer in customers:
                        # print(f"Processing customer {customer.name}...", end=' ')
                        doc = frappe.get_doc("Customer", customer.name)
                        if doc.accounts:
                            if doc.accounts[0].account is not None:
                                # print(f"Customer {doc.name} already has accounts {doc.accounts[0].as_json()}, skipping.")
                                # print(f"already has accounts {doc.accounts[0].account}, skipping.")
                                continue  # Skip if accounts already exist
                            else:
                                print(f"Processing customer {customer.name}...", end=' ')
                                print(f"{Colors.FAIL}already has empty accounts, skipping. Action required: remove empty account!{Colors.ENDC}")
                                continue  # Skip if accounts already exist

                        create_and_link_debit_account(doc, company)
                        it  += 1
                        print(f"Processing customer {customer.name}...", end=' ')
                        print(f"{Colors.LIGHTGREEN_EX}processed Customer Account {doc.name}{Colors.ENDC}")
                        if it >= breakcond:
                            print(f"Abbruch nach {breakcond} verarbeiteten Kunden.")
                            return
                case '4':
                    if not name:
                        print("Filter für Kunden-Namen eingeben (z.B. 'BMW%'): ")
                        continue    
                    customers = frappe.get_all(
                        "Customer",
                        fields=["name", "customer_name"],
                        filters=[
                            ["customer_name", "like", f"{name}"]
                        ],
                    )
                    print(f"Found {len(customers)} customers to process.")  

                    it = 0                    
                    
                    for customer in customers:
                        doc = frappe.get_doc("Customer", customer.name)
                        addresses = get_addresses(doc.name)
                        if not addresses:
                            print(f"Kunde {doc.name} hat keine Adressen und ist aktiv = {doc.disabled}.")
                            lexware_cust = get_customers_lexware (doc.customer_name)
                            if lexware_cust and len(lexware_cust) == 1:
                                l = lexware_cust[0]                                

                                add_address(doc, l)
                                it += 1

                                if it >= breakcond:
                                    print(f"Abbruch nach {breakcond} verarbeiteten Kunden.")
                                    break

                            continue
                        sorted_addresses = sort_addresses(addresses)
                        if doc.customer_primary_address:
                            # print(f"Kunde {doc.name} hat bereits die primäre Adresse gesetzt: {doc.primary_address}.")
                            continue

                        primary_address = sorted_addresses[0]
                        set_primary_address(doc, primary_address)
                        print(f"Kunde {doc.name} primäre Adresse gesetzt auf {sorted_addresses[0]}.")
                        it += 1
                        if it >= breakcond:
                            print(f"Abbruch nach {breakcond} verarbeiteten Kunden.")
                            break
                        

        except EscPressedException as e:
            break

def execute(name=None):
    main_menu()                
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

def parse_payment_terms(konditionen, language):
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

    # Map Tage -> Zahlungsbedingung
    payment_terms_map = {
        14: {"de": "14 Tage netto", "en": "14 days net"},
        30: {"de": "30 Tage netto", "en": "30 days net"},
        60: {"de": "60 Tage netto", "en": "60 days net"},
    }

    return payment_terms_map.get(days, {}).get(language)

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

def add_bank_account(customer_doc, sup):
    """
    Fügt dem Kunden ein Bankkonto hinzu.
    sup sollte die Bankdaten aus Lexware enthalten, z.B.:
    'BankName', 'IBAN', 'BIC', 'Kontonummer'
    """
    try:
        # Prüfen, ob Konto bereits existiert
        if frappe.db.exists('Customer Bank', {'customer': customer_doc.name, 'account_number': sup.get('szIBAN')}):
            print(f"Bankkonto bereits vorhanden für {customer_doc.name}: {sup.get('IBAN')}")
            return None

        bank_account = frappe.new_doc('Customer Bank')
        bank_account.customer = customer_doc.name
        bank_account.bank = sup.get('Bank_Institut')
        bank_account.account_number = sup.get('szIBAN')
        bank_account.swift_code = sup.get('szBIC')
        bank_account.primary_account = 1  # Optional: Hauptkonto markieren
        bank_account.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"Bankkonto erfolgreich angelegt für {customer_doc.name}: {bank_account.account_number}")
        return bank_account

    except Exception as e:
        print(f"Fehler beim Anlegen des Bankkontos für {customer_doc.name}: {e}")
        return None


def add_address(customer_doc, sup):
    try:
        address = frappe.new_doc('Address')
        address.address_title = f"{sup.get('Matchcode')}"
        address.address_line1 = sup.get('Anschrift_Strasse')
        address.city = sup.get('Anschrift_Ort')
        address.pincode = sup.get('Anschrift_Plz')
        address.country = translate_country(sup.get('Anschrift_Land'))
        address.is_primary_address = 1
        address.is_shipping_address = 1

        if not address.address_line1:
            print(f"{Colors.FAIL}Fehler: {Colors.ENDC}Kunde {customer_doc.name} hat keine Straße in der Adresse.")
            return
        
        # Verlinkung zum Kunden
        address.append('links', {
            'link_doctype': 'Customer',
            'link_name': customer_doc.name
        })
        address.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"Adresse erfolgreich angelegt für {customer_doc.name}: {address.name}")
    except Exception as e:
        print(f"Fehler beim Anlegen der Adresse für {customer_doc.name}: {e}")
        return None

def sort_addresses(addresses):
    """Sortiert Adressen so, dass billing  Adressen zuerst kommen."""
    return sorted(addresses, key=lambda addr: (not addr.get('is_primary_address'), not addr.get('is_shipping_address')))    


import frappe

def get_addresses(customer_doc):
    """
    Liefert die Liste aller Address-IDs (name) für einen Customer.

    :param customer_doc: Customer DocType-Objekt oder Customer-Name
    :return: Liste von Address-Namen (IDs)
    """
    # Wenn ein Doc-Objekt übergeben wurde, den Namen verwenden

    # 1) Alle Dynamic Links für diesen Customer holen
    
    links = frappe.get_all(
        "Dynamic Link",
        filters={
            "link_doctype": "Customer",
            "link_name": customer_doc,
            "parenttype": "Address"
        },
        fields=["link_name", "parent"]
    )
    
    # 2) Nur die Adressen-Namen extrahieren
    address_names = [l.parent for l in links]
    addresses = []
    for a in address_names:        
        address = frappe.get_doc("Address", a)
        addresses.append(address)

    return addresses

    
def set_primary_address(customer_doc, address_doc):
    try:
        customer_doc.customer_primary_address = address_doc.name
        customer_doc.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"Primäre Adresse gesetzt für {customer_doc.name}: {address_doc.name}")
    except Exception as e:
        print(f"Fehler beim Setzen der primären Adresse für {customer_doc.name}: {e}")
        return None

def create_missing_customers(cust):    
    """Prüft, ob Kunden in ERPNext existieren, und legt neue an."""
    Kunden_nr = str(cust.get("KundenNr"))
    country = translate_country(cust.get("Anschrift_Land") or cust.get("Liefer_Land"))
    language = get_language(country)
    payment_terms = parse_payment_terms(cust.get("Konditionen_Zahlungsbedingung"), language=language)
    tax_id = cust.get("Kontierung_EG_ID_Nr")
    tax_category = parse_tax_category(tax_id, country)        
    cref = cust.get("LieferantenNr_beim_Kunden")
    disabled = cust.get("bInaktiv") == 1
    customer_name = cust.get("Anschrift_Firma") or cust.get("Liefer_Firma") or cust.get("Matchcode")

    if not frappe.db.exists("Customer", Kunden_nr):
        print(f"Lege an Kunde {customer_name} / {Kunden_nr}: Land={country}, Sprache={language}, Zahlungsbedingungen={payment_terms}, Steuerkategorie={tax_category}")

        # Lieferant anlegen
        new_customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "name": Kunden_nr,
            "legacy_id": Kunden_nr,            
            "default_currency": "EUR",
            "default_price_list": "Standard-Vertrieb",
            "tax_id": tax_id,            
            "language": language,
            "supp_no_ref_cust_no": cref,
            "customer_group": "Endkunde",
            "tax_category": tax_category,
            "payment_terms": payment_terms,
            "disabled": disabled,
        })

        new_customer.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.rename_doc("Customer", new_customer.name, Kunden_nr, force=True, merge=False)
    
        print(f"Neuer Kunde angelegt: {new_customer.name}")

        doc = frappe.get_doc("Customer", Kunden_nr)
        print(f"Neuer Kunde geholt: {Kunden_nr}")
        
        try:
            add_address(doc, cust)
        except ValueError as e:
            print(f"Fehler beim Hinzufügen der Adresse für Kunde {Kunden_nr}: {e}")
        finally:
            print(f"Hinzufügen der Adresse für Kunde {Kunden_nr} ok")

        print(f"Neuer Kunde angelegt: {Kunden_nr} / {doc.customer_name}")
        return 1

    else:
    # Lieferant existiert → leere Felder ergänzen
        doc = frappe.get_doc("Customer", Kunden_nr)

        updated = False

        # Mapping: Feldname -> Wert aus Lexware / Standard
        fields_to_check = {
            "customer_name": cust.get("Anschrift_Firma") or cust.get("Liefer_Firma") or cust.get("Matchcode"),            
            "language": language,
            "tax_id": tax_id,
            "tax_category": tax_category,
            "payment_terms": payment_terms,
            "supp_no_ref_cust_no": cref,
            "customer_group": "Endkunde",
            "default_currency": "EUR",
            "default_price_list": "Standard-Vertrieb",
            "disabled": disabled,
        }

        for field, value in fields_to_check.items():
            if field == "payment_terms" and value:
                # Spezieller Check für payment_terms, da es ein Link-Feld ist
                if doc.get(field) != value:
                    setattr(doc, field, value)
                    updated = True
                    print(f"{Kunden_nr}: Feld '{field}' gesetzt auf '{value}'")


            if getattr(doc, field) == None and value is not None:
                setattr(doc, field, value)
                updated = True
                print(f"{Kunden_nr}: Feld '{field}' gesetzt auf '{value}'")
            

        if updated:            
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            print(f"Aktualisiere Kunde {customer_name} / {Kunden_nr}: Land={country}, Sprache={language}, Zahlungsbedingungen={payment_terms}, Steuerkategorie={tax_category}")

            return 1
            
    return 0

def get_customers_lexware(name):
    """Holt Kunden aus Lexware und gibt sie als Liste von Dictionaries zurück."""
    conn = pyodbc.connect("DSN=lexware2")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM FK_Kunde WHERE Matchcode LIKE ? OR KundenNr LIKE ?", (f"%{name}%",f"%{name}%"))
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
    cursor.execute("select * from FK_Kunde where Matchcode LIKE ?", f"%{name}%")
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

