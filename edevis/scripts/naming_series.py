import frappe

"""Modul zur Verwaltung von Naming Series in Frappe/ERPNext."""
class NamingSeries:
    def __init__(self, name):
        self.name = name
        
    def set_counter(self, counter):
        """
        Setzt den Counter einer Naming Series auf einen bestimmten Wert.    
        """
        # Prüfen, ob die Series-Tabelle das Feld 'current' hat
        # if not frappe.db.has_column("Series", "current"):
        #     raise Exception("Tabelle 'Series' ist nicht korrekt. Feld 'current' fehlt.")

        # Aktualisieren oder Einfügen des Wertes
        frappe.db.sql(
            """
            UPDATE `tabSeries`
            SET `current` = %s
            WHERE `name` = %s
            """,
            (counter, self.name)
        )

        frappe.db.commit()        


    def get_counter(self):
        """
        Gibt den aktuellen Counter einer Naming Series zurück.
        Falls die Serie noch nicht existiert, wird 0 zurückgegeben.
        """
        # # Prüfen, ob die Series-Tabelle das Feld 'current' hat
        # if not frappe.db.has_column("Series", "current"):
        #     raise Exception("Tabelle 'Series' ist nicht korrekt. Feld 'current' fehlt.")

        # Abrufen des aktuellen Wertes
        #counter = frappe.db.get_value("Series", series_name, "current")
        counter = frappe.db.sql(
            """
            SELECT `current`
            FROM `tabSeries`
            WHERE `name` = %s
            """,
            (self.name,),
            pluck=True
        )
        if counter is None:
            # Serie existiert noch nicht
            counter = 0

        return int(counter[0])
