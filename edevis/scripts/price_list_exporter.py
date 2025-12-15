import frappe
import os
import re
import pandas as pd
import xlsxwriter


class PriceListExporter:

	FONT = "Univers LT Std"
	MAX_DESC_LENGTH = 300

	COLOR_LEVEL0 = "#FFFFFF"     # Weiß
	COLOR_LEVEL1 = "#CA5B31"     # Orange
	COLOR_LEVEL2 = "#457CC8"     # Blau
	COLOR_ITEM   = "#C7E5F3"     # Hellblau
	COLOR_PRICE  = "#5E6464"
	COLOR_COND   = "#B7BDB7"
	COLOR_LEVEL1D = "#325220"     # Orange
	COLOR_LEVEL2D = "#0F1D2E"     # Blau
	COLOR_ITEMD   = "#9CB2C8"     # Hellblau


	def __init__(self, price_list):
		self.price_list = price_list
		self.site_path = frappe.get_site_path()
		self.output_filename = f"Preisliste_{price_list}.xlsx".replace(' ', '_')
		self.output_path = os.path.join(self.site_path, "public", "files", self.output_filename)

	# -------------------------------------------------------------
	# Hilfsfunktionen
	# -------------------------------------------------------------
	def clean_html(self, html):
		if not html:
			return ""
		# <br> -> newline
		html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
		html = re.sub(r"</p>", "\n", html, flags=re.I)
		html = re.sub(r"<p.*?>", "", html, flags=re.I)
		html = re.sub(r"<.*?>", "", html)
		html = html.strip()

		if len(html) > self.MAX_DESC_LENGTH:
			html = html[:self.MAX_DESC_LENGTH] + "…"

		return html

	def get_item_hierarchy(self, group_name):
		"""Gibt eine Liste zurück: [TopGroup, Level1, Level2, ...]"""
		hierarchy = []
		current = group_name

		while current:
			hierarchy.insert(0, current)
			try:
				g = frappe.get_doc("Item Group", current)
				if not g.parent_item_group or g.parent_item_group == current:
					break
				current = g.parent_item_group
			except:
				break

		return hierarchy

	# -------------------------------------------------------------
	# Daten sammeln
	# -------------------------------------------------------------
	def load_data(self):
		item_prices = frappe.get_all(
			"Item Price",
			filters={"price_list": self.price_list},
			fields=["item_code", "price_list_rate"]
		)

		rows = []

		for ip in item_prices:
			item = frappe.get_doc("Item", ip["item_code"])
			desc = self.clean_html(item.description)

			hierarchy = self.get_item_hierarchy(item.item_group or "Allgemein")

			level0 = hierarchy[0] if len(hierarchy) > 0 else None
			level1 = hierarchy[1] if len(hierarchy) > 1 else None
			level2 = hierarchy[2] if len(hierarchy) > 2 else None
			level3 = hierarchy[3] if len(hierarchy) > 3 else None

			rows.append({
				"item_code": item.name,
				"name": item.item_name,
				"description": desc,
				"price": ip["price_list_rate"],
				"delivery": getattr(item, "lead_time_days", 0),
				"discount": getattr(item, "max_discount", 0),
				"level0": level1,
				"level1": level2,
				"level2": level3
			})

		df = pd.DataFrame(rows)
		df.sort_values(by=["level0", "level1", "level2", "item_code"], inplace=True)
		df.reset_index(drop=True, inplace=True)

		return df

	# -------------------------------------------------------------
	# Excel Export
	# -------------------------------------------------------------
	def export_excel(self, df):
		wb = xlsxwriter.Workbook(self.output_path)
		ws = wb.add_worksheet(self.price_list)


		# -------- Formate --------
		fmt_level0 = wb.add_format({
			"font_name": self.FONT, "font_size": 18,
			"top": 1, "bottom": 1, "top_color": "white", "bottom_color": "white",
			"bold": True, "color": "FF0000", "bg_color": "#FFFFFF"
		})

		fmt_level1 = wb.add_format({
			"font_name": self.FONT, "bold": True,
			"top": 1, "bottom": 1, "top_color": "white", "bottom_color": "white",
			"font_size": 14, "color": "#FFFFFF", "bg_color": self.COLOR_LEVEL1
		})

		fmt_level1s = wb.add_format({
			"font_name": self.FONT, "bold": False,
			"align": "right",
			"top": 1, "bottom": 1, "top_color": "white", "bottom_color": "white",
			"font_size": 11, "color": "#FFFFFF", "bg_color": self.COLOR_LEVEL1
		})

		fmt_level1d = wb.add_format({
			"font_name": self.FONT, "bold": False,
			"align": "right",
			"top": 1, "bottom": 1, "top_color": "white", "bottom_color": "white",
			"font_size": 11, "color": "#FFFFFF", "bg_color": self.COLOR_LEVEL1D
		})

		fmt_level2 = wb.add_format({
			"font_name": self.FONT, "bold": True,
			"top": 1, "bottom": 1, "top_color": "white", "bottom_color": "white",
			"font_size": 12, "color": "#FFFFFF", "bg_color": self.COLOR_LEVEL2
		})

		fmt_level2d = wb.add_format({
			"font_name": self.FONT, "bold": True,
			"top": 1, "bottom": 1, "top_color": "white", "bottom_color": "white",
			"font_size": 12, "color": "#FFFFFF", "bg_color": self.COLOR_LEVEL2D
		})

		fmt_item_bg = wb.add_format({
			"font_name": self.FONT, "font_size": 11,
			"top": 1, "bottom": 1, "top_color": "white", "bottom_color": "white",
			"bg_color": self.COLOR_ITEM,
			"text_wrap": True,
			"valign": "top"
		})

		fmt_price = wb.add_format({
			"font_name": self.FONT, "font_size": 11,
			"top": 1, "bottom": 1, "top_color": "white", "bottom_color": "white",
			"bg_color": self.COLOR_PRICE, "color": "white",
			"num_format": '€#,##0.00',
			"valign": "top"
		})

		fmt_discount = wb.add_format({
			"font_name": self.FONT, "font_size": 11,
			"top": 1, "bottom": 1, "top_color": "white", "bottom_color": "white",
			"bg_color": self.COLOR_COND,
			"num_format": '0.00%',
			"valign": "top"
		})

		fmt_delivery = wb.add_format({
			"font_name": self.FONT, "font_size": 11,
			"top": 1, "bottom": 1, "top_color": "white", "bottom_color": "white",
			"bg_color": self.COLOR_COND,
			"num_format": '0.0 "Wochen"',
			"valign": "top"
		})

		fmt_name = wb.add_format({
			"font_name": self.FONT, "font_size": 11,
			"top": 1, "bottom": 1, "top_color": "white", "bottom_color": "white",
			"bg_color": self.COLOR_ITEM,
			"text_wrap": True
		})

		fmt_desc = wb.add_format({
			"font_name": self.FONT, "font_size": 8,
			"top": 1, "bottom": 1, "top_color": "white", "bottom_color": "white",
			"bg_color": self.COLOR_ITEM,
			"text_wrap": True
		})

		fmt_descsm = wb.add_format({
			"font_name": self.FONT, "font_size": 8,
			"bg_color": "#FFFFFF"
		})

		# -------- Schreiben --------
		row_idx = 0
		curr0 = curr1 = curr2 = None


		def write_header(ws, row_idx, text, level, cols=5, height=None):
			"""Schreibt eine Überschrift über mehrere Spalten hinweg."""

			textarr = []
			fmtarr = []
			match level:
				case 0:
					fmtarr = [fmt_level0, fmt_level0, fmt_level0, fmt_level0, fmt_level0]
					textarr = ["", text, "", "", ""]
				case 1:
					fmtarr = [fmt_level1, fmt_level1s, fmt_level1d, fmt_level1s, fmt_level1s]
					textarr = [text, "", "Price", "Delivery time", "Discount"]
				case 2:
					fmtarr = [fmt_level2, fmt_level2, fmt_level2d, fmt_level2, fmt_level2]
					textarr = [text, "", "", "", ""]
			
			for col in range(cols):
				ws.write(row_idx, col, textarr[col], fmtarr[col])

			if height:
				ws.set_row(row_idx, height)

			if level == 0:
				row_idx += 1
				ws.write(row_idx, 0, "Part #", fmt_descsm)
				ws.write(row_idx, 1, "Description", fmt_descsm)

			return row_idx + 1
		
		for _, r in df.iterrows():

			# Level 0
			if r["level0"] != curr0:
				curr0 = r["level0"]
				row_idx = write_header(ws, row_idx, curr0, 0, cols=5, height=28)

			# Level 1
			if r["level1"] and r["level1"] != curr1:
				curr1 = r["level1"]
				row_idx = write_header(ws, row_idx, curr1, 1, cols=5, height=22)

			# Level 2
			if r["level2"] and r["level2"] != curr2:
				curr2 = r["level2"]
				row_idx = write_header(ws, row_idx, curr2, 2, cols=5, height=20)

			# Artikelzeile
			ws.write(row_idx, 0, r["item_code"], fmt_item_bg)
		
			rich_parts = [
				fmt_name, r["name"] + "\n",
				fmt_desc, r["description"]
			]

			ws.write_rich_string(row_idx, 1, *rich_parts, fmt_item_bg)

			ws.write(row_idx, 2, r["price"], fmt_price)
			ws.write(row_idx, 3, r["delivery"] / 7 if r["delivery"] else "", fmt_delivery)

			discount = r["discount"] or 20
			discount = min(discount, 20) if r["item_code"].startswith("EDP") else 10

			ws.write(row_idx, 4, discount / 100, fmt_discount)
			# ws.write(row_idx, 5, r["level0"], fmt_discount)
			# ws.write(row_idx, 6, r["level1"], fmt_discount)
			# ws.write(row_idx, 7, r["level2"], fmt_discount)
			# ws.set_row(row_idx, 32)
			row_idx += 1

		# Spaltenbreiten
		ws.set_column(0, 0, 18)
		ws.set_column(1, 1, 50)
		ws.set_column(2, 4, 18)

		wb.close()

	# -------------------------------------------------------------
	# Hauptfunktion
	# -------------------------------------------------------------
	def export(self):
		df = self.load_data()
		self.export_excel(df)
		return f"https://erp.e1.edevis.com/files/{self.output_filename}"
