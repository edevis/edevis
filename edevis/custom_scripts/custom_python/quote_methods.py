import frappe
import re

# check if a quotation is well formated, especially using seciton items
def check_quoteitems(doc):
	inSection = False
	# check consistency
	i=0
	cnt=0
	for item in doc.items:
		i+=1
		if item.item_group == "Format Elemente" and item.amount != 0: 		
			return ("ERROR: Section Element (POS " + str(i) + ") must have a price (amount) of 0 EUR")
		if item.item_group == "Format Elemente" and item.item_code == "Section Header":
			if inSection == True: 
				return ("ERROR: Nested Section Header at POS" + str(i))
			inSection=True
		if item.item_group == "Format Elemente" and item.item_code == "Section End":
			if inSection==False:
				return ("ERROR: Section END without Section Header at POS" + str(i))
			if cnt==0:
				return ("ERROR: Section without elements inside before POS" + str(i))
			cnt=0
			inSection=False
		if item.item_group != "Format Elemente" and inSection:
			cnt+=1

	if inSection==True:
		return ("ERROR: closing Section END missing")
	return None


def has_custom_pos(doc):
	cnt=0
	for item in doc.items:
		if bool(item.custom_position):
			return True
	return False

def quote_checkpaymentterms(doc):
	if doc.payment_terms_template is None:
		frappe.throw("ERROR: payment_terms_template not set")
	pass

def quoteitem_is_header(quoteitem):
	if quoteitem.item_group == "Format Elemente" and quoteitem.item_code == "Section Header":
		return True
	else:
		return False

def is_sectionend(quoteitem):
	if quoteitem.item_group == "Format Elemente" and quoteitem.item_code == "Section End":
		return True
	else:
		return False

def quoteitem_has_discount(doc):
	items = structurize_quoteitem(doc)
	for item in items:
		if item.discount_percentage > 0:
			return True
	return False

### quoteitem position enumeration
def structurize_quoteitem(doc):
	if not check_quoteitems(doc):		
		pass
	
	curheader=None
	p1=0
	p2=0			
	itemList = []
	for item in doc.items:
		if curheader is not None:
			p2+=1
			item.position = str(p1) + "." + str(p2)
			item.parent_item = curheader
		else:
			p1+=1
			item.position = str(p1)

		if item.item_group == "Format Elemente": 
			if item.item_code == "Section Header":
				curheader = item
				if not doc.hide_item_price_within_section:
					curheader.qty = 0
				p2 = 0
				itemList.append(curheader)
			elif item.item_code == "Section End":				
				curheader=None
				# don't append section end to the list of items
		else:
			if curheader is not None and doc.hide_item_price_within_section:				
				curheader.amount += item.amount
				curheader.rate += item.rate*item.qty
				curheader.discount_percentage=0 if (curheader.amount==0 or curheader.rate==0) else (curheader.rate-curheader.amount)/curheader.rate*100
				curheader.discount_amount = item.rate-item.amount
				item.amount=0
				item.net_amount=0
				item.rate=0
				item.net_rate=0
				item.discount_percentage=0
				item.discount_amount=0
				if item.item_group == 'Lohnleistungen' and doc.hide_hour_rates_for_services:					
					item.qty = 1
					item.uom =  "Unit"
			else:
				if item.item_group == 'Lohnleistungen' and doc.hide_hour_rates_for_services:
					item.net_amount *= item.qty
					item.rate *= item.qty
					item.net_rate *= item.qty
					item.price_list_rate *= item.qty					
					item.qty = 1
					item.uom =  "Unit"

			# weight_info = calculate_total_weight(doc.item_code, target_uom="Kg")
			# item.weight_per_unit = weight_info["total_weight"]
			# item.weight_uom = weight_info["weight_uom"]
			itemList.append(item)
	return itemList


def get_contacts(self):
	groups = ["Format Elemente"]
	contacts = []
	for d in self.items:
		if d.item_group not in groups:
			groups.append(d.item_group)
			contact_name = frappe.db.get_value("Item Group", d.item_group, "custom_technical_contact")
			if contact_name:
				contact = frappe.get_doc("Contact", contact_name)
				contacts.append({
					"full_name": contact.full_name,
					"email": contact.email_ids[0].email_id if contact.email_ids else '',
					"phone":contact.phone_nos[0].phone if contact.phone_nos else ''
				})

	return contacts


def get_dual_use(self):
	all_templates = []
	templates = []
	i = 1
	items = []
	
	
	for d in self.items:
		if not frappe.db.exists("Product Bundle", d.item_code):
			item_templates = frappe.db.get_all("Item Dual Use Item", filters={"parent": d.item_code}, fields=["dual_use_template"])
			
			if item_templates:
				for template in item_templates:
					template = template.dual_use_template
					if template not in all_templates:
						all_templates.append(template)
						templates.append(frappe.db.get_values("Dual Use Template", template, ["en", "de", "name"], as_dict=1)[0])
					templates = set_item(templates, d.item_code, template)

		else:
			for pb in frappe.get_all("Product Bundle Item", {"parent": d.item_code}, ["item_code"]):
				item_templates = frappe.db.get_all("Item Dual Use Item", filters={"parent": pb.item_code}, fields=["dual_use_template"])
			
				if item_templates:
					for template in item_templates:
						template = template.dual_use_template
						if template not in all_templates:
							all_templates.append(template)
							templates.append(frappe.db.get_values("Dual Use Template", template, ["en", "de", "name"], as_dict=1)[0])
						templates = set_item(templates, d.item_code, template)
	return templates

def set_item(templates, item, template):
	
	for d in templates:
		
		if d.get("name") == template:
			
			if not d.get("itemss"):
				d['itemss'] = item
				
			else:
				if item not in d["itemss"]:
					d["itemss"] = f"{d['itemss']}, {item}"
	return templates

def normalize(text):
	# HTML-Tags entfernen
	return re.sub(r'<[^>]+>', '', text or '').strip()
	
def get_item_datasheet(item, language=None):
	"""
	Liefert das passende Datenblatt für einen Artikel basierend auf:
	1. Template Artikel - 'ITEM_CODE Datasheet'
	2. Artikel - 'ITEM_CODE Datasheet'
	3. Template Artikel - 'item.description'
	4. Artikel - 'item.description'
	5. fallback: item.description
	"""

	language = language or frappe.local.lang

	if not item or not item.item_code:
		return None

	item_code = item.item_code
	datasheet = None


	# Hilfsfunktion, um Übersetzung zu bekommen
	def get_translation(source_value, language, for_item=None):
		filters = {
			"language": language,
			"source_text": source_value
		}
		if for_item:
			filters["name"] = for_item  # optional, falls du Template/Item unterscheiden willst
		return frappe.get_value("Translation", filters, "translated_text")

	# 1. Template Artikel Datasheet
	variant_of = getattr(item, "variant_of", None)
	if variant_of:
		template_code = variant_of
		datasheet = get_translation(f"{template_code} Datasheet", language)		
		if datasheet:
			return insert_att_table_html(item, datasheet)
			
	else:
		desc = 'Item is no variant<br>'

	# 2. Artikel Datasheet
	datasheet = get_translation(f"{item_code} Datasheet", language)
	if datasheet:
		return datasheet

	# 4. Artikel description
	datasheet = frappe._(item.description)
	return datasheet	

def insert_att_table_html(item, html):	
	"""
	Fügt die übergebene table_html zwischen dem letzten </div>
	und dem <table class="table table-condensed spec"> ein.
	
	html: Original HTML-String
	table_html: die einzufügende Tabelle als HTML-String
	"""

	def get_item_attributes(item, language=None):
		"""
		Gibt eine Liste von Tupeln (Attribut, Wert) zurück,
		wobei der Attributname übersetzt ist (falls Übersetzung existiert).
		"""
		if not item:
			return []

		language = language or frappe.local.lang

		attributes = []
		for att in getattr(item, "attributes", []):
			# Übersetzte Attributbezeichnung holen
			translated_attr = frappe.get_value(
				"Translation",
				{"source_text": att.attribute, "language": language},
				"translated_text"
			) or att.attribute  # fallback: original

			attributes.append((translated_attr, att.attribute_value))

		return attributes
	
	table_html = '<table class="table table-condensed spec">\n'
	table_html += f"<tr><th>{frappe._('Technical Data')}</th><th>{item.item_code}</th></tr>\n"
	for attr, value in get_item_attributes(item):
		table_html += f"<tr><td>{attr}:</td><td>{value}</td></tr>"
	table_html += "</table>"

	last_div_index = html.rfind("</div>")
	if last_div_index == -1:
		last_div_index = 0  # fallback: Anfang des Strings
	else:
		last_div_index += len("</div>")  # nach </div> einfügen

	# Index des <table ...> finden (nach last_div_index)
	table_index = html.find('<table class="table table-condensed spec">', last_div_index)	
	if table_index == -1:
		# fallback: Tabelle ans Ende hängen
		return html + table_html

	# Alles zwischen last_div_index und table_index entfernen, Whitespaces strippen
	before = html[:last_div_index].rstrip()
	after = html[table_index:]

	# Neue HTML zusammensetzen
	return f"{before}\n{table_html}\n{after}"

