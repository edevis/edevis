import frappe

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
	#if not doc.items[0].position is None:
	#	pass
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
					item.qty = 1
					item.uom =  "Unit"

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