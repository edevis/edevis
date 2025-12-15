import frappe
from datetime import datetime, timedelta
from .country_conversion import translate_country
from .terminal_color import Colors
from frappe.utils import get_datetime
import json

class ErpItems:
	def __init__(self, filter=None):
		self._erpnext_unique_key = "item_code"
		self._erp_class = "Item"
		self._lexware_table = "FK_Artikel"
		self._lexware_unique_key = "ArtikelNr"
		self._filter = filter

	def get_items_erpnext(self):
		"""Holt Elemente aus ERPNext und gibt sie als Liste von Dictionaries zurück."""
		
		items = frappe.get_all(
			self._erp_class,
			filters={self._erpnext_unique_key: ["like", f"%{self._filter}%"]},
			fields=[self._erpnext_unique_key, "item_name", "disabled"]
		)
		return items

	def get_missing_items_erpnext(self, items):
		"""Gibt eine Liste von eindeutigen Schlüsseln der Elemente zurück, die in Lexware, aber nicht in ERPNext existieren."""
		
		missing_items = []
		for item in items:
			key = str(item.get(self._lexware_unique_key))
			if not frappe.db.exists(self._erp_class, key):
				missing_items.append(item)

		return missing_items
	
	def create_missing_item_erpnext(self, item, maintain_Stock = 0, has_serial = 0):
		"""Prüft, ob Lieferanten in ERPNext existieren, und legt neue an."""			
		
		lxkey = str(item.get(self._lexware_unique_key))

		supplier_info = []
		if item.get("LieferantenNr"):
			supplier_info = [
				{
					"supplier": item.get("LieferantenNr") or None,
					"supplier_part_no": item.get("BestellNr") or None,
				}
			]

		uom = None
		match item.get("Einheit"):
			case "set":
				uom = "Pcs"
			case "PCS":
				uom = "Pcs"
			case "Lizenz":
				uom = "License"
			case _:
				raise Exception(f"Unknown unit {item.get('Einheit')}")
				
		if not frappe.db.exists(self._erp_class, lxkey):
			new_item = frappe.get_doc({
				"doctype": self._erp_class,
				"item_name": item.get("Bezeichnung") if item.get("Bezeichnung") != item.get("Beschreibung") and item.get("Beschreibung") else item.get("Matchcode"),
				"description": item.get("Beschreibung") or item.get("Bezeichnung"),
				"name": lxkey,
				"disabled": True if item.get("fGesperrt") else False,
				"item_code": lxkey,
				"has_serial_no": has_serial,
				"maintain_stock": maintain_Stock,
				"standard_rate": item.get("Vk_preis_eur"),
				"valuation_rate": item.get("Ek_preis_eur"),
				"warranty_period": 365,
				"weight_uom": "kg" if item.get("Gewicht") else None,
				"weight_per_unit": item.get("Gewicht") or 0,
				"purchase_uom": uom,
				"sales_uom": uom,
				"country_of_origin": item.get("CountryOfOrigin") or None,
				"customs_tariff_number": item.get("HSCode") or None,
				"custom_dual_use_export_item_number": item.get("ECCN") or None,
				"item_group": item.get("Warengruppe"),
				"is_purchase_item": 1 if item.get("LieferantenNr") else 0,
				"include_item_in_manufacturing": 0 if item.get("LieferantenNr") else 1,
				"supplier_items": supplier_info,
			})			
			new_item.insert(ignore_permissions=True)

			if new_item.valuation_rate and item.get("LieferantenNr"):
				price = frappe.get_doc({
					"doctype": "Item Price",
					"item_code": lxkey,
					"price_list": "Standard-Kauf",
					"buying": 1,
					"price_list_rate": new_item.valuation_rate,
					"supplier": item.get("LieferantenNr") or None,
				})

				price.insert()
			frappe.db.commit()
			return True
		else:
			raise FileExistsError(f"Element bereits vorhanden: {lxkey}")	


	def update(self, lxitem, targets, patch=False):
		changes = None
		"""Prüft, ob Lieferanten in ERPNext existieren, und legt neue an."""			
		
		lxkey = str(lxitem.get(self._lexware_unique_key))

		if not frappe.db.exists(self._erp_class, lxkey):
			raise FileExistsError(f"Element nicht vorhanden: {lxkey}")
		
		item = frappe.get_doc(self._erp_class, lxkey)
		if item.disabled:
			return False
		
		if 'weight' in targets:
			# weight
			actual_weight = item.get("weight_per_unit") or 0
			w = lxitem.get("Gewicht")
			if w and w > 0:
				w = round(w, 0) if w > 100 else round(w, 1) if w > 1 else round(w, 2) if w > 0.1 else round(w, 3)
				if lxitem.get("Gewicht") and actual_weight != w:
					item.weight_per_unit = w
					item.weight_uom = "kg"
					if not patch:
						print(f"ErpNext weight {Colors.OKBLUE}{item.weight_per_unit} {item.weight_uom} {Colors.ENDC} to item {lxkey} - {actual_weight}")
					changes	= 'erpnext'
			if actual_weight > 0 and (not w or w == 0):
				print(f"Lexware weight {Colors.OKGREEN}{item.weight_per_unit} {item.weight_uom} {Colors.ENDC} to item {lxkey} - {actual_weight}")
				changes = 'lexware'

		elif 'supplier' in targets:
			# supplier
			supplier_data = []
			suppitems = item.get("supplier_items")
			# print(suppitems)
			if not suppitems and lxitem.get("LieferantenNr"):
				supplier_data = {
					"supplier": lxitem.get("LieferantenNr") or None,
					"supplier_part_no": lxitem.get("BestellNr") or None,
				}

			if supplier_data:
				item.append("supplier_items", supplier_data)
				if not patch:
					print(f"Missing supplier {Colors.OKBLUE}{item.weight_per_unit} {lxitem.get('LieferantenNr')} {Colors.ENDC} for item {lxkey}")
				changes	= 'erpnext'

		elif 'purchase_price' in targets:
			price = frappe.db.get_value(
				"Item Price",
				{
					"item_code": lxkey,
					"price_list": "Standard-Einkauf",
					# optional:
					# "selling": 1,   # oder "buying": 1
				},
				"price_list_rate"
			)

			if price is None and lxitem.get("Ek_preis_eur"):
				print(f"{Colors.OKCYAN}No Price{Colors.ENDC} for item {lxkey}\n\tLexware: {lxitem.get('Ek_preis_eur')}\n\tErpNext: None")
				if patch:
					raise NotImplementedError("Inserting new price not finished")

			if price > lxitem.get("Ek_preis_eur"):
				print(f"{Colors.FAIL}ErpNext price higher{Colors.ENDC} for item {lxkey} {item.item_name}: \n\tLexware: {lxitem.get('Ek_preis_eur')}\n\tErpNext: {price}")

				if patch:
					raise NotImplementedError("Changing price not finished")
				
			elif price < lxitem.get("Ek_preis_eur"):
				print(f"{Colors.WARNING}ErpNext price lower{Colors.ENDC} for item {lxkey} {item.item_name}: \n\tLexware: {lxitem.get('Ek_preis_eur')}\n\tErpNext: {price}")

				if patch:
					raise NotImplementedError("Changing price not finished")

				
		elif 'sales_price' in targets:
			price_list = "Standard-Vertrieb"

			if not lxitem.get("fGesperrt"):
				prices = frappe.get_all(
					"Item Price",
					filters={"item_code": lxkey, "selling": 1, "price_list": price_list},
					fields=["name", "price_list", "price_list_rate", "valid_from", "valid_upto"]
				)
				latest_price_entry = self.select_latest_price(prices)
				
				latest_erpnext_price = (latest_price_entry.get('price_list_rate') or 0) if latest_price_entry else 0
				lexware_price = lxitem.get('Vk_preis_eur') or 0

				if latest_erpnext_price == 0 and lexware_price == 0:
					print(f"{Colors.FAIL}Warning: No prices set (Lexware/ErpNext){Colors.ENDC} for item {lxkey}")

				if latest_erpnext_price == 0 and lexware_price > 0:
					if not patch:
						print(f"{Colors.LIGHTRED_EX}No ErpNext price{Colors.ENDC} for item {lxkey}\n\tLexware: {lxitem.get('Vk_preis_eur')}")
						changes = 'erpnext'
					else:
						print(f"{Colors.OKGREEN}Added ErpNext price{Colors.ENDC} for item {lxkey}\n\tLexware: {lxitem.get('Vk_preis_eur')}")
						new_price = frappe.get_doc({
							"doctype": "Item Price",
							"item_code": lxkey,
							"price_list": price_list,
							"selling": 1,
							"price_list_rate": lxitem.get("Vk_preis_eur"),
							"valid_from": datetime.today().strftime("%Y-%m-%d")  # heute
						})

						# Speichern
						new_price.insert()
						frappe.db.commit()						

				elif latest_erpnext_price > 0 and lexware_price == 0:
					print(f"{Colors.FAIL}No Lexware price{Colors.ENDC} for item {lxkey}\n\tLexware: {lxitem.get('Vk_preis_eur')}")
					lxitem["Vk_preis_eur"] = price.get('price_list_rate')
					changes = 'lexware'
					if patch:
						raise NotImplementedError("Changing price not possible in this class")

				elif latest_erpnext_price > lexware_price:
					print(f"{Colors.WARNING}ErpNext price higher{Colors.ENDC} for item {lxkey} {item.item_name}: \n\tLexware: {lxitem.get('Vk_preis_eur')}\n\tErpNext: {price.price_list_rate}")
					lxitem["Vk_preis_eur"] = price.get('price_list_rate')
					changes	= 'lexware'					
					if patch:
						raise NotImplementedError("Changing price not possible in this class")
					
				elif latest_erpnext_price < lexware_price:
					
					try:
						price = latest_erpnext_price
					
						print(f"{Colors.OKCYAN}ErpNext price lower{Colors.ENDC} for item {lxkey} {item.item_name}: \n\tLexware: {lxitem.get('Vk_preis_eur')}\n\tErpNext: {price.price_list_rate}")
						changes	= 'erpnext'

						if patch:
							no_enddate_prices = [p for p in prices if not p.get("valid_upto")]
							old_price_data = no_enddate_prices[0]

							# Hole das Doc
							old_price = frappe.get_doc("Item Price", old_price_data["name"])

							# Setze valid_upto auf gestern
							yesterday = datetime.today() - timedelta(days=1)
							old_price.valid_upto = yesterday.strftime("%Y-%m-%d")  # Date-Feld im Frappe-Format
							old_price.save()

							new_price = frappe.get_doc({
								"doctype": "Item Price",
								"item_code": lxkey,
								"price_list": price_list,
								"selling": 1,
								"price_list_rate": lxitem.get("Vk_preis_eur"),
								"valid_from": datetime.today().strftime("%Y-%m-%d")  # heute
							})

							# Speichern
							new_price.insert()
							frappe.db.commit()
					except ValueError as e:
						print(f"{Colors.FAIL}{e} {lxitem.get('ArtikelNr')} {lxkey}{Colors.ENDC}")


			else:
				print(f"{Colors.LIGHTBLACK_EX}Ignoriere gesperrten Artikel {lxkey}{Colors.ENDC}")

		else:
			print(f"Update no target found in {targets}")

		if patch:
			item.save()
			frappe.db.commit()
		
		return changes

	def select_latest_price(self, prices):
		
		def sort_price(p):
			valid_from = p.get("valid_from")
			valid_upto = p.get("valid_upto")

			if valid_from:
				valid_from = get_datetime(valid_from)
			if valid_upto:
				valid_upto = get_datetime(valid_upto)

			# Für die Sortierung: None behandeln als "maximales Datum"
			valid_upto_sort = valid_upto or frappe.utils.get_datetime("9999-12-31")
			valid_from_sort = valid_from or frappe.utils.get_datetime("1900-01-01")

			# Sortierkriterium: jüngstes Enddatum zuerst, dann jüngstes Anfangsdatum
			return (valid_upto_sort, valid_from_sort)

		if not prices:
			return None

		# Prüfen: wie viele Preise haben kein valid_upto?
		no_valid_upto_count = sum(1 for p in prices if not p.get("valid_upto"))		
			
		if no_valid_upto_count >= 2:
			raise ValueError(f"Es gibt mindestens zwei Preise ohne valid_upto – bitte ändern! {[p for p in prices if not p.get('valid_upto')]}")

		# Sortieren: jüngster Endzeitpunkt zuerst → reverse=True
		prices_sorted = sorted(prices, key=sort_price, reverse=True)

		# Aktuellster Preis ist der erste in der Liste
		latest_price = prices_sorted[0]
		return latest_price
