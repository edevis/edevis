import json
from datetime import date, datetime
from tabulate import tabulate
from .get_key import getchar
from .get_key import Esc
from .get_key import input_char
from .get_key import EscPressedException
from .terminal_color import Colors
from .lexware_item import LexwareItems
from .erpnext_item import ErpItems

import frappe

def execute(name=None):
	main_menu()
	return

def print_table(items, title="Artikel"):
	if items:
		print(f"\n--- {title} ---")
		print(tabulate(items, headers="keys", tablefmt="grid"))
	else:
		print(f"\n--- {title} ---\nKeine {title} gefunden.")


menu = f"""

=== ERPNext <> Lexware Artikelpflege ===
(1) Filter für Artikel-Nr setzen.

=== Fehlende Artikel anzeigen ===
(2) In ERPNext fehlende Artikel anzeigen
(3) In Lexware fehlende Artikel anzeigen

=== Aktualisierung von Lexware ===
(4) Lexware Artikel anzeigen
(5) Lexware Artikel sperren
(w) Lexware Warengruppen anzeigen

=== Aktualisierung von ErpNext ===
(6) In ERPNext Lieferanten aktualisieren aus Lexware
(7) In ERPNext Gewichte aktualisieren aus Lexware
(8) In ERPNext VK-Preise aktualisieren aus Lexware
(9) In ERPNext EK-Preise aktualisieren aus Lexware
"""

# def show_menu(items):
# 	print (menu)


def main_menu():
	erpitems = ErpItems("EDP")
	lexware = LexwareItems("EDP")

	while True:		
		try:
			choice = input_char(menu, [str(x) for x in range(1, 9)] + ['w'])
			match choice:
				case '1':				
					filter_input = input("Filter für Item-Namen eingeben (z.B. 'EDP 03%'): ").strip()
					erpitems._filter = filter_input if filter_input else "EDP%"
					lexware._filter = filter_input if filter_input else "EDP%"
					print(f"Filter gesetzt auf: {erpitems._filter}")
					getchar('Press any key to continue')
			
				case "2":
					lex_items = lexware.get_items_lexware()
					missing_erp = erpitems.get_missing_items_erpnext(lex_items)
					rows_to_print = [(d["ArtikelNr"], d["Matchcode"], d.get("fGesperrt", "") ) for d in missing_erp]
					print_table(rows_to_print, "Fehlende Items in ERPNext")
					
					if missing_erp:
						for item in missing_erp:
							user_confirm = input_char(f"{item.get('ArtikelNr')} // {item.get('Bezeichnung')} // {'GESPERRT' if item.get('fGesperrt') else ''} // {item.get('LieferantenNr')}\n{item.get('CountryOfOrigin')}\n{item.get('Beschreibung')}\n* Fehlenden Artikel zu ErpNext hinzufügen?")
							if user_confirm == "j":
								print(f"Zusätzliche Einstellungen:")
								maintain_Stock = 1 if input_char("Lagerartikel?") == "j" else 0
								if maintain_Stock:
									has_serial = 1 if input_char("Serien-Nr?") == "j" else 0
								else:
									has_serial = 0

								try:
									erpitems.create_missing_item_erpnext(item, maintain_Stock=maintain_Stock, has_serial=has_serial)
									print(f"Artikel {item.get('ArtikelNr')} hinzugefügt.")
									print("\n==================================================================\n")
								except FileExistsError as e:
									print(f"{Colors.FAIL}Error: {Colors.ENDC}Fehler beim Hinzufügen des Artikels {item.get('ArtikelNr')}: {e}")
								except frappe.exceptions.LinkValidationError as e:
									print(f"{Colors.FAIL}Error: {Colors.ENDC}Link-Validierungsfehler beim Hinzufügen des Artikels {item.get('ArtikelNr')}: {e}")
								except Exception as e:
									print(f"{Colors.FAIL}Error: {Colors.ENDC}Unerwarteter Fehler beim Hinzufügen des Artikels {item.get('ArtikelNr')}: {e}")
							else:
								print("\n==================================================================\n")
					getchar('Press any key to continue')
				
				case "3":
					erp_items = erpitems.get_items_erpnext()
					missing_lex = lexware.get_missing_items_lexware(erp_items)
					print_table(missing_lex, "Fehlende Items in Lexware")
					getchar('Press any key to continue')
			
				case "4":
					lex_items = lexware.get_items_lexware()			
					json_output = json.dumps(lex_items, indent=4, ensure_ascii=False) 
					print(json_output)
					getchar('Press any key to continue')

				case "5":
					lexware.update_items_lexware()
					getchar('Press any key to continue')

				case "6":
					# Artikel Stammdaten
					target = ['supplier']
					
					change_item(target, erpitems, lexware)
					getchar('Press any key to continue')

				case "7":
					# Artikel Stammdaten
					target = ['weight']
					
					change_item(target, erpitems, lexware)
					getchar('Press any key to continue')

				case "8":
					# Artikel Stammdaten
					target = ['sales_price']
					
					change_item(target, erpitems, lexware)
					getchar('Press any key to continue')

				case "w":					
					print("Lexware Warengruppen ausgeben.")
					json_output = lexware.get_item_group_lexware()
					print(json_output)
					getchar('Press any key to continue')
				
		except EscPressedException as e:
			break



def change_item(target, erpitems, lexware):
	print(f"Prüfe ErpNext Artikel {erpitems._filter} aus Lexware auf {target}.")
	lexwareitems = lexware.get_items_lexware()
	update_erpnext_items = []
	update_lexware_items = []
	count = 0
	for item in lexwareitems:
		try:					
			res = erpitems.update(item, target, False) 
			if res == 'erpnext':
				update_erpnext_items.append(item)
			elif res == 'lexware':
				update_lexware_items.append(item)

		except FileExistsError as e:
			print(f"{Colors.LIGHTBLACK_EX}Error: {Colors.ENDC} {e}")
			continue
	if update_erpnext_items:
		try:
			input = input_char(f"{len(update_erpnext_items)} Artikel können geändert werden ({target}). Aktualisieren?", ['j','n','a'])
			if input != "n":
				for item in update_erpnext_items:
					if input == 'j' and input_char(f"{item.get('ArtikelNr')} Artikel ändern ({target})?") == 'j':
						if erpitems.update(item, target, True):
							count += 1
				
		except EscPressedException as e:
			print(f"{e}")

	if update_lexware_items:
		try:
			input = input_char(f"{len(update_lexware_items)} Artikel können geändert werden ({target}). Aktualisieren?", ['j','n','a'])
			if input != "n":
				for item in update_lexware_items:
					if input == 'j' and input_char(f"{item.get('ArtikelNr')} Artikel ändern ({target})?") == 'j':
						if lexware.update(item, target):
							print(f"Änderung an {item.get('ArtikelNr')} :: {item.get('Vk_preis_eur')}")
						count += 1
				
		except EscPressedException as e:
			print(f"{e}")

	if count > 0:
		print(f"{count} Änderungen durchgeführt.")
	else:
		print(f"Keine Änderungen in {target}")

	
