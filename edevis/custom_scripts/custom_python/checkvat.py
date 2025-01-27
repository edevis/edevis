import frappe
from frappe import _
from suds.client import Client

# used for BBF-ONLINE request
import xmlrpc.client
from datetime import datetime
import xml.etree.ElementTree as ET

# used for VIES request
VIES_URL = "https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl"

error_dict = {
    "200" : "Die angefragte USt-IdNr. ist gültig.",
    "201" : "Die angefragte USt-IdNr. ist ungültig.",
    "202" : "Die angefragte USt-IdNr. ist ungültig. Sie ist nicht in der Unternehmerdatei des betreffenden EU-Mitgliedstaates registriert.\nHinweis:\nIhr Geschäftspartner kann seine gültige USt-IdNr. bei der für ihn zuständigen Finanzbehörde in Erfahrung bringen. Möglicherweise muss er einen Antrag stellen, damit seine USt-IdNr. in die Datenbank aufgenommen wird.",
    "203" : "Die angefragte USt-IdNr. ist ungültig. Sie ist erst ab dem ... gültig (siehe Feld 'Gueltig_ab').",
    "204" : "Die angefragte USt-IdNr. ist ungültig. Sie war im Zeitraum von ... bis ... gültig (siehe Feld 'Gueltig_ab' und 'Gueltig_bis').",
    "205" : "Ihre Anfrage kann derzeit durch den angefragten EU-Mitgliedstaat oder aus anderen Gründen nicht beantwortet werden. Bitte versuchen Sie es später noch einmal. Bei wiederholten Problemen wenden Sie sich bitte an das Bundeszentralamt für Steuern - Dienstsitz Saarlouis.",
    "206" : "Ihre deutsche USt-IdNr. ist ungültig. Eine Bestätigungsanfrage ist daher nicht möglich. Den Grund hierfür können Sie beim Bundeszentralamt für Steuern - Dienstsitz Saarlouis - erfragen.",
    "207" : "Ihnen wurde die deutsche USt-IdNr. ausschliesslich zu Zwecken der Besteuerung des innergemeinschaftlichen Erwerbs erteilt. Sie sind somit nicht berechtigt, Bestätigungsanfragen zu stellen.",
    "208" : "Für die von Ihnen angefragte USt-IdNr. läuft gerade eine Anfrage von einem anderen Nutzer. Eine Bearbeitung ist daher nicht möglich. Bitte versuchen Sie es später noch einmal.",
    "209" : "Die angefragte USt-IdNr. ist ungültig. Sie entspricht nicht dem Aufbau der für diesen EU-Mitgliedstaat gilt. ( Aufbau der USt-IdNr. aller EU-Länder)",
    "210" : "Die angefragte USt-IdNr. ist ungültig. Sie entspricht nicht den Prüfziffernregeln die für diesen EU-Mitgliedstaat gelten.",
    "211" : "Die angefragte USt-IdNr. ist ungültig. Sie enthält unzulässige Zeichen.",
    "212" : "Die angefragte USt-IdNr. ist ungültig. Sie enthält ein unzulässiges Länderkennzeichen.",
    "213" : "Die Abfrage einer deutschen USt-IdNr. ist nicht möglich.",
    "214" : "Ihre deutsche USt-IdNr. ist fehlerhaft. Sie beginnt mit 'DE' gefolgt von 9 Ziffern.",
    "215" : "Ihre Anfrage enthält nicht alle notwendigen Angaben für eine einfache Bestätigungsanfrage (Ihre deutsche USt-IdNr. und die ausl. USt-IdNr.).\nIhre Anfrage kann deshalb nicht bearbeitet werden.",
    "216" : "Ihre Anfrage enthält nicht alle notwendigen Angaben für eine qualifizierte Bestätigungsanfrage (Ihre deutsche USt-IdNr., die ausl. USt-IdNr., Firmenname einschl. Rechtsform und Ort).\nEs wurde eine einfache Bestätigungsanfrage durchgeführt mit folgenden Ergebnis:\nDie angefragte USt-IdNr. ist gültig.",
    "217" : "Bei der Verarbeitung der Daten aus dem angefragten EU-Mitgliedstaat ist ein Fehler aufgetreten. Ihre Anfrage kann deshalb nicht bearbeitet werden.",
    "218" : "Eine qualifizierte Bestätigung ist zur Zeit nicht möglich. Es wurde eine einfache Bestätigungsanfrage mit folgendem Ergebnis durchgeführt:\nDie angefragte USt-IdNr. ist gültig.",
    "219" : "Bei der Durchführung der qualifizierten Bestätigungsanfrage ist ein Fehler aufgetreten. Es wurde eine einfache Bestätigungsanfrage mit folgendem Ergebnis durchgeführt:\nDie angefragte USt-IdNr. ist gültig.",
    "220" : "Bei der Anforderung der amtlichen Bestätigungsmitteilung ist ein Fehler aufgetreten. Sie werden kein Schreiben erhalten.",
    "999" : "Eine Bearbeitung Ihrer Anfrage ist zurzeit nicht möglich. Bitte versuchen Sie es später noch einmal."
}

@frappe.whitelist()
def ask_bbf_online(vat_id_us, vat_id_them, company_name, place, zip, street):
    server = xmlrpc.client.ServerProxy('https://evatr.bff-online.de/')
    rpc = server.evatrRPC(vat_id_us, vat_id_them, company_name, place, zip, street)
    xmlRoot = ET.fromstring(rpc)

    # results to dict
    elements={}
    for xmlElement in xmlRoot.findall("param"):
        keyvalue = []
        for child in xmlElement.iter('string'):
            keyvalue.append( child.text )
        elements[keyvalue[0]] = keyvalue[1]

    return elements

@frappe.whitelist()
def ask_vies(vat_id_them):
    country_code = vat_id_them[:2]
    tax_id = vat_id_them[2:]
    client = Client(VIES_URL)
    return client.service.checkVat(country_code, tax_id)

@frappe.whitelist()
def checkvat(name, tax_id=None, address=None, fromDoctype='Customer'):    
    
    if fromDoctype == 'Customer':
        if address is None:
            message = _('Customer Primary Address') + ' is missing!'
            frappe.throw(message)
            
        if tax_id is None:            
            message = _('Tax ID') + ' is missing!'
            frappe.throw(message)   
            
    customer = frappe.get_doc('Customer', name)
            
    if customer and address == '':
        address = customer.customer_primary_address            
       
    tax_id = customer.tax_id  
    if tax_id is None or tax_id == '':
        #return 'Kunde hat keine Umsatzsteueridentnummer'
        message = _('Tax ID') + ' is missing!'
        frappe.throw(message)
    
    mycompany = frappe.defaults.get_user_default("Company")
    mytin = frappe.get_value('Company', mycompany, 'tax_id')
    doc = frappe.get_doc('Address', address)
    
       
    # ask the German server
    result = ask_bbf_online(mytin, tax_id, customer.customer_name, doc.city, doc.pincode, doc.address_line1)
    # evaluate the response
    testresult = False
    customer.tax_id_validation_date =  datetime.strptime(result["Datum"], '%d.%m.%Y') 
    if result['Erg_Name'] == "A" and result['Erg_PLZ'] == "A" and result['Erg_Ort'] == "A" and result['Erg_Str'] == "A" and result["ErrorCode"] == "200":
        customer.tax_id_validation_result =  'Ergebnis: Gültig'
        testresult=True
    else:
        customer.tax_id_validation_result = 'Ergebnis: Ungültig'
        testresult=False

    
    # just in case we got a confirmation that tax id is valid, but other entries (street, zip, name) dowesn't macth -> ask European Union VIES service for details
    # Remark: some contries doesnn't allo to retrieve company informations using a valid tax id. The result for address and name then will be '---'

    vies_info=''
    frappe.log_error(frappe.as_json(result, indent=4), "Test")
    if not testresult and result["ErrorCode"]=='200':
        response = ask_vies(tax_id)
        vies_info = f'''
            <tr>
                <td>
                    Company name retrieved from VIES
                </td>
                <td>
                    <span style="color: {'gray'};">{response.name}<b>
                </td>
            </tr>
            <tr>
                <td>
                    Address retrieved from VIES
                </td>
                <td>
                    <span style="color: {'gray'};">{response.address}<b>
                </td>
            </tr>
        '''

    str = f'''    
    <table style="border: collapse;">
        <tr>
            <td>
                <b>VAT ID</b>
            </td>
            <td>
                <span style="color: {'gray' if result["ErrorCode"] == "200" else 'red'};">{result["UstId_2"]}<b>
            </td>
        </tr>
        <tr>
            <td>
                Validation date
            </td>
            <td>
                <span style="color: gray">{result["Datum"]}</span>
            </td>
        </tr>
        <tr>
            <td>
                Validation time
            </td>
            <td>
                <span style="color: gray">{result["Uhrzeit"]}</span>
            </td>
        </tr>
        <tr>
            <td>
                Company ID
            </td>
            <td>
                <span style="color: {'gray' if result['Erg_Name'] == "A" else 'red'};">{name}<b>
            </td>
        </tr>
        <tr>
            <td>
                Company
            </td>
            <td>
                <span style="color: {'gray' if result['Erg_Name'] == "A" else 'red'};">{customer.customer_name}<b>
            </td>
        </tr>
        <tr>
            <td>
                Zip code
            </td>
            <td>
                <span style="color: {'gray' if result['Erg_PLZ'] == "A" else 'red'};">{doc.pincode}<b>
            </td>
        </tr>
        <tr>
            <td>
                City
            </td>
            <td>
                <span style="color: {'gray' if result['Erg_Ort'] == "A" else 'red'};">{doc.city}<b>
            </td>
        </tr>
        <tr>
            <td>
                Street
            </td>
            <td>
                <span style="color: {'gray' if result['Erg_Str'] == "A" else 'red'};">{doc.address_line1}<b>
            </td>
        </tr>
        {vies_info}
    </table>
    '''

    customer.save()
    if testresult:
        validation_doc = frappe.get_doc(dict(
            doctype='VAT ID Validation', 
            customer=name,
            company_name=name, 
            validation_taxid=result["ErrorCode"],
            validation_result='Valid' if testresult else 'Invalid',
            validation_name='Valid' if result['Erg_Name'] == "A" else 'Invalid',
            validation_street='Valid' if result['Erg_Str'] == "A" else 'Invalid',
            validation_zipcode='Valid' if result['Erg_PLZ'] == "A" else 'Invalid',
            validation_city='Valid' if result['Erg_Ort'] == "A" else 'Invalid',
            address_line_1=doc.address_line1,
            zip_code=doc.pincode,
            city=doc.city,
        )).insert(ignore_permissions=True)        
        validation_doc.submit()
        # save result to customer fields
        customer.save()
        customer.notify_update()
    
    # show results to the user
    frappe.msgprint(str, title=customer.tax_id_validation_result, indicator='green' if testresult else 'red')  
    
  
