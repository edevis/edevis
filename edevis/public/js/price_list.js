frappe.ui.form.on('Price List', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button('Export Excel', function() {

                // Anzahl der Einträge abfragen
                frappe.call({
                    method: "frappe.client.get_count",
                    args: {
                        doctype: "Item Price",
                        filters: { "price_list": frm.doc.name }
                    },
                    callback: function(r) {
                        let count = r.message;

                        // Info anzeigen: Export kann kurz dauern
                        frappe.msgprint(`Hinweis: Der Export der Preisliste (${count} Einträge) kann kurz dauern.`);

                        // Warnung bei >200 Einträgen
                        if (count > 200) {
                            frappe.confirm(
                                `Die Preisliste enthält ${count} Einträge. Wirklich exportieren?`,
                                function() {
                                    // User klickt "Yes"
                                    start_export(frm.doc.name);
                                },
                                function() {
                                    // User klickt "No"
                                    frappe.msgprint("Export abgebrochen.");
                                }
                            );
                        } else {
                            // Weniger als 200 → direkt exportieren
                            start_export(frm.doc.name);
                        }
                    }
                });

            }, __("Actions"));  // optional Dropdown "Actions"

            frm.add_custom_button(__('Price Transfer'), function() {

                // Dialog zum Abfragen von Parametern
                let d = new frappe.ui.Dialog({
                    title: 'Preise übertragen',
                    fields: [
                        {
                            label: "Hinweis",
                            fieldname: "info_text",
                            fieldtype: "HTML",
                            options: `
                                <p>
                                Mit diesem Werkzeug lassen sich Preise aus einer Quell-Preisliste in eine Ziel-Preisliste kopieren.
                                Es wird dabei jeweils der aktuell gültige Preis aus der Quellliste übernommen – jedoch nur für Artikel, die bereits in der Ziel-Preisliste existieren (es werden keine neuen Artikel angelegt).
                                </p>
                                <p>
                                Wenn der bisherige Zielpreis kein <i>Gültig-bis</i>-Datum hat, wird er beim Kopieren automatisch zum <b>Startdatum – 1 Tag</b> geschlossen.
                                </p>
                                <p><b>Parameter:</b></p>
                                <ul>
                                <li><b>Quell-Preisliste</b>: Preisquelle, aus der die gültigen Preise übernommen werden.</li>
                                <li><b>Ziel-Preisliste</b>: Preisliste, in die die Preise eingespielt werden. Nur bestehende Artikel werden aktualisiert.</li>
                                <li><b>Startdatum</b>: Datum, ab dem der neue Preis in der Ziel-Preisliste gelten soll.</li>
                                </ul>
                            `
                        },
                        {
                            fieldname: 'source_price_list',
                            fieldtype: 'Link',
                            options: 'Price List',
                            label: 'Quell-Preisliste',
                            reqd: 1,
                            get_query: () => { return { filters: { selling: 1 } } }
                        },
                        {
                            fieldname: 'target_price_list',
                            fieldtype: 'Link',
                            options: 'Price List',
                            label: 'Ziel-Preisliste',
                            reqd: 1,
                            default: frm.doc.name,
                            get_query: () => { return { filters: { selling: 1, name: ['!=', 'Standard-Vertrieb'] } } }
                        },
                        {
                            fieldname: 'start_date',
                            fieldtype: 'Date',
                            label: 'Startdatum',
                            reqd: 1,
                            default: frappe.datetime.get_today()
                        }
                    ],
                    primary_action_label: 'Start',
                    primary_action: function(values) {
                        d.hide();

                        // Hinweis: Prozess kann kurz dauern
                        frappe.msgprint(`Update startet, kann je nach Größe der Preisliste kurz dauern...`);

                        // Aufruf Python Backend
                        frappe.call({
                            method: "edevis.custom_scripts.custom_python.price_list_actions.update_price_list",
                            args: {
                                source_price_list: values.source_price_list,
                                target_price_list: values.target_price_list,
                                start_date: values.start_date
                            },
                            callback: function(r) {
                                if(r.message) {
                                    frappe.msgprint(`Ergebnis: ${r.message}`);
                                }
                            }
                        });
                    }
                });

                d.show();

            }, __("Actions"));
			
        }
    }
});

function start_export(price_list_name) {
    frappe.call({
        method: "edevis.custom_scripts.custom_python.price_list_actions.export_price_list",
        args: { price_list_name: price_list_name },
        callback: function(r) {
            if(r.message) {
                frappe.msgprint(`<a href='${r.message}' target='_blank'>Download Excel</a>`);
            }
        }
    });
}
