from datetime import date
import frappe
from .price_list_export import PriceListExporter
from frappe.utils import add_days, getdate
from frappe.model.document import Document
from collections import OrderedDict
import logging


log = frappe.logger("Edevis")
log.setLevel("DEBUG")


@frappe.whitelist()
def export_price_list(price_list_name):
    exporter = PriceListExporter(price_list_name)
    download_url = exporter.export()
    return download_url


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
	log.debug(f"Running update_price_list(source_price_list={source_price_list},target_price_list={target_price_list},start_date={start_date})")

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
		
	# Sortieren: aktuellste Gültigkeit zuerst
	target_prices.sort(
		key=lambda p: (
			p.get("valid_upto") is not None,       # False für None -> zuerst
			p.get("valid_upto") or date.min,       # spätester Endtermin
			p.get("valid_from") or date.min        # spätester Starttermin
		),
		reverse=True
	)

	# Nur aktuellsten Preis pro Artikel
	latest_prices = OrderedDict()
	for p in target_prices:
		item_code = p["item_code"]
		if item_code not in latest_prices:
			latest_prices[item_code] = p

	for price in target_prices:
		if not price.get("valid_upto"):
			new_valid_upto = add_days(start_date, -1)
			if new_valid_upto <= price.valid_from:
				raise ValueError(f"Validity from {price.valid_from} must be before validty up to {new_valid_upto}")
			frappe.db.set_value("Item Price", price.name, "valid_upto", add_days(start_date, -1))
			log.debug(f"Item Price {price.name}, valid_upto, {add_days(start_date, -1)}")
	
	# --- Neue Preise aus Quell-Preisliste übernehmen ---
	# Hole jeweils aktuell gültigen Preis aus der Quell-Preisliste
	source_prices = frappe.get_all(
		"Item Price",
		filters={"price_list": source_price_list},
		fields=["item_code", "price_list_rate", "currency", "valid_from", "valid_upto", "uom", "item_name", "customer", "packing_unit", "batch_no"]
	)
	
	
	for target_price in latest_prices.values():
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
		
		log.debug(f"New price for {target_price['item_code']} to target_price_list={target_price_list}, start_date={start_date})")
		

		exists = frappe.db.exists("Item Price", {
			"price_list": target_price_list,
			"item_code": target_price["item_code"],
			"currency": price_to_use["currency"],		
			"valid_from": ["<=", start_date],
			"valid_upto": [">=", start_date]
		})
		if exists:
			frappe.throw(f"Überschneidung erkannt für Item {target_price['item_code']}")


		log.debug("NEW_DOC ITEM PRICE")
		# Price List, Supplier/Customer, Currency, Item, Batch, UOM, Qty, and Dates.
		# Neuen Item Price-Eintrag anlegen
		new_price_doc = frappe.get_doc({
			"doctype": "Item Price",
			"item_code": target_price["item_code"],
			"item_name": price_to_use["item_name"],
			"price_list": target_price_list,
			"price_list_rate": price_to_use["price_list_rate"],
			"currency": price_to_use["currency"],
			"uom":price_to_use["uom"],
			"qty":"1",
			"customer":price_to_use["customer"],
			"supplier": "",
			"packing_unit": price_to_use["packing_unit"],
			"batch_no" : price_to_use["batch_no"],
			"valid_from": start_date,
			"valid_upto": None
		})
		log.debug(new_price_doc.valid_from)
		log.debug(new_price_doc.valid_upto)
		new_price_doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
	
	frappe.db.commit()
	
	return f"Preisliste '{target_price_list}' erfolgreich aktualisiert."