import json
from datetime import date, datetime
from tabulate import tabulate
from .get_key import getchar
from .get_key import Esc
from .get_key import input_char
from .get_key import EscPressedException
from .terminal_color import Colors
from .lexware_salesorder import LexwareOrder


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
(1) Aufträge abrufen

"""

# def show_menu(items):
# 	print (menu)


def main_menu():

	lexware = LexwareOrder()

	while True:		
		try:
			choice = input_char(menu, [str(x) for x in range(1, 9)] + ['w'])
			match choice:
				case '1':				
					filter_input = input("Filter für Auftrag-Namen eingeben (z.B. '45500'): ").strip()
					
					lexware._filter = filter_input if filter_input else "%"
					print(f"Filter gesetzt auf: {lexware._filter}")
					getchar('Press any key to continue')
				case '2':
					orders = lexware.get_orders_lexware()
					print_table(orders)
					#for order in orders:
						
						
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

	

