# Auftragssync

import frappe
import pyodbc
import json
from datetime import date, datetime
from .terminal_color import Colors
import re
from .country_conversion import translate_country

class LexwareOrder:
	def __init__(self, filter=None):
		self._conn = pyodbc.connect("DSN=lexware2")
		self._erp_class = "Sales Order"          # ERPNext-Klasse
		self._lexware_table = "FK_Auftrag"      # Lexware-Auftragstabelle
		self._lexware_unique_key = "AuftragsNr" # Eindeutiges Feld für Aufträge
		self._filter = filter

	def get_orders_lexware(self):
		"""Holt Aufträge aus Lexware und gibt sie als Liste von Dictionaries zurück."""
		cursor = self._conn.cursor()
		
		cursor.execute(
			f"""
			SELECT A.SheetNr, A.AuftragsNr, A.KundenMatchcode
			FROM {self._lexware_table} A
			WHERE A.AuftragsNr LIKE ?
			""",
			(f"%{self._filter}%",)
		)
		
		orders = []
		columns = [column[0] for column in cursor.description]
		for row in cursor.fetchall():			
			orders.append(dict(zip(columns, row)))

		return orders
