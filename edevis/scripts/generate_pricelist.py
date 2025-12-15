import frappe
from datetime import date, datetime
from tabulate import tabulate
from .get_key import getchar
from .get_key import Esc
from .get_key import input_char
from .get_key import EscPressedException
from .terminal_color import Colors
from .price_list_exporter import PriceListExporter
from frappe.utils import add_days, getdate
from frappe.model.document import Document


menu = f"""

(1) OEM Preisliste von Excel einlesen
(2) Preisliste als Excel ausgeben

"""

url = "https://erp.e1.edevis.com/files/edevis%20Price%20List%202025-10-15.xlsx"

def execute(name=None):
	main_menu()
	return


def main_menu():
	while True:
		try:
			choice = input_char(menu, [str(x) for x in range(1, 9)] + ['w'])
			match choice:
				case '1':				
					site_path = "/home/frappe/frappe-bench/sites/erp.e1.edevis.com/"
					file_relative = "edevis_Price _List_2025-10-15.xlsx"

					# Vollständiger Pfad
					excel_path = os.path.join(site_path, "public", "files", file_relative)	
					#excel_path = "/files/edevis Price List 2025-10-15.xlsx"
					
					update_item_prices_from_excel(excel_path)
					getchar('Press any key to continue')
			
				case "2":
					exporter = PriceListExporter("OEM Verkauf 2025")
					download_url = exporter.export()
					print("Download:", download_url)
					getchar('Press any key to continue')

				case "3":
					result = update_price_list ("Standard-Vertrieb", "Reseller Test", "2025-11-30")
					print(result)
					getchar('Press any key to continue')

		except Exception as e:
			print(e)
			break


@frappe.whitelist()
def update_price_list(source_price_list: str, target_price_list: str, start_date: str):
	"""
	Aktualisiert eine Ziel-Preisliste aus einer Quell-Preisliste.
	
	Args:
		source_price_list (str): Name der Quell-Preisliste (Standard Verkauf)
		target_price_list (str): Name der Ziel-Preisliste
		start_date (str): Startdatum der neuen Preise (YYYY-MM-DD)
	
	Returns:
		str: Ergebnis-Meldung
	"""
	
	# --- Prüfen: Ziel darf nicht die Standard-Verkauf sein ---
	if target_price_list == "Standard-Vertrieb":
		frappe.throw("Die Ziel-Preisliste darf nicht 'Standard-Vertrieb' sein.")
	
	start_date = getdate(start_date)	

	# --- Alte Preise in Ziel-Preisliste beenden ---
	target_prices = frappe.get_all(
		"Item Price",
		filters={"price_list": target_price_list},
		fields=["name", "item_code", "valid_from", "valid_upto"]
	)
	
	for price in target_prices:
		frappe.db.set_value("Item Price", price.name, "valid_upto", add_days(start_date, -1))
		print(f"Item Price {price.name}, valid_upto, {add_days(start_date, -1)}")
	
	# --- Neue Preise aus Quell-Preisliste übernehmen ---
	# Hole jeweils aktuell gültigen Preis aus der Quell-Preisliste
	source_prices = frappe.get_all(
		"Item Price",
		filters={"price_list": source_price_list},
		fields=["item_code", "price_list_rate", "currency", "valid_from", "valid_upto"]
	)
	
	for target_price in target_prices:
		# Filter: Quelle = aktuell gültig für Startdatum
		valid_prices = [
			p for p in source_prices
			if p["item_code"] == target_price["item_code"]
			and (not p["valid_from"] or p["valid_from"] <= start_date)
			and (not p["valid_upto"] or p["valid_upto"] >= start_date)
		]
		
		if valid_prices:
			price_to_use = valid_prices[-1]  # letzte gültige
		else:
			frappe.msgprint(f"Warnung: Kein gültiger Preis für Item {target_price['item_code']} am {start_date}, letzter gültiger Preis wird verwendet.")
			# letzten bekannten Preis aus Quelle verwenden
			all_prices_for_item = [p for p in source_prices if p["item_code"] == target_price["item_code"]]
			price_to_use = sorted(all_prices_for_item, key=lambda x: x["valid_from"] or frappe.utils.getdate("1900-01-01"))[-1]
		
		# Neuen Item Price-Eintrag anlegen
		new_price_doc = frappe.get_doc({
			"doctype": "Item Price",
			"item_code": target_price["item_code"],
			"price_list": target_price_list,
			"price_list_rate": price_to_use["price_list_rate"],
			"currency": price_to_use["currency"],
			"valid_from": start_date,
			"valid_upto": None
		})
		new_price_doc.insert(ignore_permissions=True)
	
	frappe.db.commit()
	
	return f"Preisliste '{target_price_list}' erfolgreich aktualisiert."



def update_item_prices_from_excel(file_path, price_list_name="OEM Verkauf 2025"):
	"""
	Liest eine Excel-Datei ein und aktualisiert die Preise in einer Preisliste.
	
	Args:
		file_path (str): Pfad zur Excel-Datei.
		price_list_name (str): Name der Preisliste in ERPNext.
	"""
	# Excel-Datei einlesen
	try:
		df = pd.read_excel(file_path)
	except Exception as e:
		frappe.throw(f"Fehler beim Einlesen der Excel-Datei: {e}")

	# Prüfen, ob die Spalten existieren
	required_columns = ['A', 'C']  # Spalte A = Item Code, Spalte C = Preis
	if df.shape[1] < 3:
		frappe.throw("Excel-Datei hat nicht genug Spalten. Spalte A = Item Code, Spalte C = Preis wird benötigt.")
	
	# Spalten zuweisen
	item_codes = df.iloc[:, 0]  # Spalte A
	prices = df.iloc[:, 2]      # Spalte C

	for item_code, price in zip(item_codes, prices):
		if not str(item_code).startswith('ED'):
			continue  # ignorieren, wenn nicht mit 'ED' beginnt
		
		# Prüfen, ob Item existiert
		if not frappe.db.exists("Item", item_code):
			frappe.log_error(f"Item {item_code} existiert nicht.")
			continue

		# Prüfen, ob Price List Entry existiert
		price_entry = frappe.get_all(
			"Item Price",
			filters={
				"item_code": item_code,
				"price_list": price_list_name
			},
			fields=["name"]
		)
		

		if price_entry:
			# Existierendes Price Entry aktualisieren
			doc = frappe.get_doc("Item Price", price_entry[0]['name'])
			doc.price_list_rate = price
			doc.save()
			print(f"Preis existiert für {item_code} eingetragen in {price_list_name}")

		else:
			# Neues Price Entry erstellen
			doc = frappe.get_doc({
				"doctype": "Item Price",
				"item_code": item_code,
				"price_list": price_list_name,
				"price_list_rate": price,
				"buying": 0,
				"selling": 1
			})
			doc.insert()
			print(f"Preis neu für {item_code} eingetragen in {price_list_name}")
	
	frappe.db.commit()
	frappe.msgprint(f"Preise aus {file_path} erfolgreich aktualisiert!")

