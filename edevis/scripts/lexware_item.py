import frappe
import pyodbc
import json
from datetime import date, datetime
from .terminal_color import Colors
import re
from .country_conversion import translate_country

class LexwareItems:
	def __init__(self, filter=None):
		self._conn = pyodbc.connect("DSN=lexware2")
		self._erpnext_unique_key = "item_code"
		self._erp_class = "Item"
		self._lexware_table = "FK_Artikel"
		self._lexware_unique_key = "ArtikelNr"
		self._filter = filter
		pass

	def get_missing_items_lexware(self, items):
		"""Gibt eine Liste von eindeutigen Schlüsseln der Elemente zurück, die in ErpNext, aber nicht in Lexware existieren."""
		cursor = self._conn.cursor()
		print(f"SELECT {self._lexware_unique_key} FROM {self._lexware_table} WHERE {self._lexware_unique_key} LIKE ?", (f"%{self._filter}%"))
		cursor.execute(f"SELECT {self._lexware_unique_key} FROM {self._lexware_table} WHERE {self._lexware_unique_key} LIKE ?", (f"%{self._filter}%",))
		# columns = [desc[0] for desc in cursor.description]
		rows = cursor.fetchall()

		missing_items = []
		for item in items:
			key = str(item.get(self._erpnext_unique_key))
			if not key in [str(row[0]) for row in rows]:
				
				missing_items.append((key, item.get("item_name"), "GESPERRT" if item.get("disabled") else ""))

		return missing_items

	def get_item_group_lexware(self):
		cursor = self._conn.cursor()
		cursor.execute(f"SELECT WarengrpNr, Bezeichnung FROM FK_Warengruppe")

		columns = [desc[0] for desc in cursor.description]
		rows = cursor.fetchall()

		def serialize_row(row):
			# print(row)
			new_row = {}
			for col, val in zip(columns, row):
				if val is None or val == 0:
					continue
				if isinstance(val, (date, datetime)):
					val = val.isoformat()
				new_row[col] = val
			return new_row

		return [serialize_row(row) for row in rows]		

	def get_items_lexware(self):
		"""Holt Elemente aus Lexware und gibt sie als Liste von Dictionaries zurück."""
		
		cursor = self._conn.cursor()
		# print(f"SELECT * FROM {self._lexware_table} WHERE {self._lexware_unique_key} LIKE ?", (f"%{self._filter}%"))
		# cursor.execute(f"SELECT * FROM {self._lexware_table} WHERE {self._lexware_unique_key} LIKE ?", (f"%{self._filter}%",))
		priceGroupIndex = 1
		quantityGroupIndex = 1
		cursor.execute(
			f"""
			SELECT 
				A.*,
				P.Vk_preis_eur,       -- Verkaufspreis aus Preismatrix
				B.BestellNr,          -- Lieferanten-Bestellnummer
				B.Ek_preis_eur,       -- Einkaufspreis aus Bezugstabelle
				B.Lieferzeit,         -- Lieferzeit
				L.LieferantenNr AS LieferantenNr,    -- LieferantenNr
				W.Bezeichnung AS Warengruppe
			FROM {self._lexware_table} A
			LEFT JOIN FK_Preismatrix P
				ON A.{self._lexware_unique_key} = P.ArtikelNr
			AND P.PreisgrpNr = ?
			AND P.MengeNr = ?
			LEFT JOIN FK_ArtikelBezugsQ B
				ON A.{self._lexware_unique_key} = B.ArtikelNr
			LEFT JOIN FK_Lieferant L
				ON B.LieferantenNr = L.LieferantenNr
			LEFT JOIN FK_Warengruppe W
				ON A.WarengrpNr = W.WarengrpNr
			WHERE A.{self._lexware_unique_key} LIKE ?
			""",
			(priceGroupIndex, quantityGroupIndex, f"%{self._filter}%")
		)

		columns = [desc[0] for desc in cursor.description]
		rows = cursor.fetchall()

		def serialize_row(row):
			#print(row)
			new_row = {}
			for col, val in zip(columns, row):
				if val is None or val == 0:
					continue
				if isinstance(val, (date, datetime)):
					val = val.isoformat()
				new_row[col] = val

			country = new_row.get("CountryOfOrigin")
			if country:
				new_row["CountryOfOrigin"] =  translate_country(country)
				
			hscode = new_row.get("HSCode")

			beschreibung = new_row.get("Beschreibung")
			if beschreibung:
				text = " ".join(beschreibung.split())

				# Einzelne Patterns für jede Eigenschaft
				country_match = re.search(r"Country of origin:\s*([A-Za-z]+)", text, re.IGNORECASE)
				code_match = re.search(r"Commodity code:\s*([0-9]+)", text, re.IGNORECASE)
				eccn_match = re.search(r"ECCN:\s*([A-Za-z0-9]+)", text, re.IGNORECASE)

				if country_match and not country:
					country = country_match.group(1)
				if code_match and not hscode:
					hscode = code_match.group(1)
				if eccn_match:
					new_row["ECCN"] = eccn_match.group(1)
				
				text_cleaned = re.sub(
					r"(Country of origin:\s*[A-Za-z]+)|(Commodity code:\s*[0-9]+)|(ECCN:\s*[A-Za-z0-9]+)",
					"",
					beschreibung,
					flags=re.IGNORECASE
				).strip()

				# Verkürzte, bereinigte Beschreibung speichern
				new_row["Beschreibung"] = text_cleaned
				new_row["CountryOfOrigin"] =  translate_country(country)
				new_row["HSCode"] = hscode

			return new_row

		return [serialize_row(row) for row in rows]

	def update(self, item, target):
		"""
		Ändert den Verkaufspreis eines Artikels in Lexware.
		"""

		if 'sales_price' in target:				
			sql_update = """
				UPDATE FK_Preismatrix
				SET Vk_preis_eur = ?
				WHERE ArtikelNr = ? AND PreisgrpNr = ? AND MengeNr = ?
			"""
			price_group=1
			quantity_group=1
			cursor = self._conn.cursor()
			cursor.execute(sql_update, (item.get('Vk_preis_eur'), item.get('ArtikelNr'), price_group, quantity_group))
			cursor.connection.commit()  # 🔹 Persistenz
			
			print(f"Preis für {item.get('ArtikelNr')} auf {item.get('Vk_preis_eur')} EUR gesetzt")
		else:
			print(f"{Colors.FAIL}Error:{Colors.ENDC} target not implemented {' '.join(target)}")

	def update_items_lexware(self):
			"""Ändere Elemente aus Lexware und gibt sie als Liste von Dictionaries zurück."""
			
			cursor = self._conn.cursor()
			try:
				print(f"UPDATE {self._lexware_table} SET fGesperrt = ? WHERE {self._lexware_unique_key} LIKE ?", (1, f"%{self._filter}%"))
				cursor.execute(
					"UPDATE FK_Artikel SET fGesperrt = ? WHERE ArtikelNr LIKE ?",
					(1, f"{self._filter}")  # 1 = Wert für fGesperrt, Filter für LIKE
				)
								
				print(f"{cursor.rowcount} Zeilen geändert.")

				# 2. Bestätigung vom Benutzer oder Bedingung prüfen
				user_confirm = input("Änderungen übernehmen? (j/n): ").lower()
				if user_confirm == "j":
					self._conn.commit()
					print("Änderungen gespeichert.")
				else:
					self._conn.rollback()
					print("Änderungen zurückgesetzt.")

			except Exception as e:
				print("Fehler aufgetreten:", e)
				self._conn.rollback()