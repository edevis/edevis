import frappe
import os
import zipfile

def run(quotation: str):
	"""
	Exportiert für alle Items eines Quotation automatisch PDF-Drucke (Datasheets),
	legt sie in einem Ordner ab, erstellt ein ZIP und gibt Download-Links zurück.

	Aufruf:
	bench execute erpnext_custom.scripts.export_datasheets.run --kwargs "{'quotation': 'QTN-0001'}"
	"""

	if not quotation:
		frappe.throw("Bitte quotation='QTN-XXXX' angeben.")

	# Quotation laden
	qtn = frappe.get_doc("Quotation", quotation)

	# Verzeichnisse vorbereiten
	export_base = frappe.utils.get_site_path("public", "files", "datasheet_export")
	export_dir = os.path.join(export_base, quotation)
	os.makedirs(export_dir, exist_ok=True)

	pdf_files = []

	# PDF erzeugen für jedes Item
	for item in qtn.items:
		item_code = item.item_code

		# Druck-PDF für das Item erzeugen (benutze die Standard-Print-Format-Namen, z.B. "Item Datasheet")
		# Du musst ggf. das Print-Format vorher in ERPNext anlegen
		pdf_content = frappe.get_print(
			doctype="Item",
			name=item_code,
			print_format="Datasheet - ED (V3)",  # <--- Name deiner Druckvorlage
			as_pdf=True
		)

		pdf_filename = f"{item_code}.pdf"
		pdf_path = os.path.join(export_dir, pdf_filename)

		with open(pdf_path, "wb") as f:
			f.write(pdf_content)

		pdf_files.append(pdf_path)

	# ZIP erstellen
	zip_path = os.path.join(export_base, f"{quotation}.zip")
	with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
		for fpath in pdf_files:
			zf.write(fpath, os.path.basename(fpath))

	# Download-Link (öffentlicher Link, falls public Files) oder Pfad
	zip_url = f"/public/files/datasheet_export/{quotation}.zip"
	print("https://erp.e1.edevis.com" + zip_url)
	
	return {
		"quotation": quotation,
		"pdf_count": len(pdf_files),
		"pdf_folder": export_dir,
		"zip_file": zip_path,
		"zip_download_link": zip_url
	}
