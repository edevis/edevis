frappe.ui.form.on("Sales Order", {
    tc_name: function (frm) {
        if (!frm.doc.tc_name) {
            frm.set_value("terms", "");
        }
    },

    before_save: function(frm) {	
        var customerName = frm.doc.customer;

        if(customerName) {
            frappe.call({
                method: "edevis.custom_scripts.custom_python.checkvat.checkvat",
                args: {                    
                  name: customerName,
                  tax_id: '',
                  address: '',
                  fromDoctype: 'Sales Order'
                },
                freeze: true,
                freeze_message: __('Retrieving VAT Information from server...'),
                callback: function(r) {
                  frappe.msgprint(r)
                }
              }); 

        } else {  
          frappe.msgprint(_("Customer is missing"))
        }
	},

  before_submit: function(frm) {	
    var customerName = frm.doc.customer;

    if(customerName) {
        frappe.call({
            method: "edevis.custom_scripts.custom_python.checkvat.checkvat",
            args: {                    
              name: customerName,
              tax_id: '',
              address: '',
              fromDoctype: 'Sales Order'
            },
            freeze: true,
            freeze_message: __('Retrieving VAT Information from server...'),
            callback: function(r) {
              frappe.msgprint(r)
            }
          }); 

    } else {  
      frappe.msgprint(_("Customer is missing"))
    }
}
});