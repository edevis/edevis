import frappe
import pyodbc

def execute(name=None):
    # update_customer_ids(name)
    # if name:
    name ="%z.o.o%"
    get_lexware_cust_byname(name)
    return



def get_lexware_cust():
    conn = pyodbc.connect("DSN=lexware2")
    cursor=conn.cursor()
    cursor.execute("select KundenNr, Matchcode from FK_Kunde")
    row = cursor.fetchone()
    
    while row:
         print(row)
         row = cursor.fetchone()     


def get_lexware_cust_byname(name):
    print(f"select KundenNr, Matchcode from FK_Kunde where Matchcode = {name}")
    conn = pyodbc.connect("DSN=lexware2")
    cursor=conn.cursor()
    cursor.execute("select KundenNr, Matchcode from FK_Kunde where Matchcode LIKE ?", f"%{name}%")
    row = cursor.fetchone()
    print('found customer in lexware:', row)
    return row    
    # while row:
    #      print(row)
    #      row = cursor.fetchone()   

def update_customer_ids(name):

    filters = {"customer_name": ("like", f"%{name}%")} if name else {}
    
    customers = frappe.get_all(
        "Customer",
        fields=["name", "customer_name", "customer_group"],
        filters=filters,
    )

    for customer in customers:
        if not customer.name.isdigit() and customer.customer_group != "Einzelperson":
            print(f"{customer.name}")
            continue

            cust = get_lexware_cust_byname(customer.customer_name)
            if cust:
                print(f"Found {customer.customer_name}. in Lexware: {cust} ")
                # try:
                #     frappe.rename_doc("Customer", customer.name, cust[0], force=True, merge=False)
                #     print(f"Renamed {customer.customer_name}:    {customer.name} --> {cust[0]}")
                # except Exception as e:
                #     print(f"Error renaming {customer.name}: {e}")
            else:
                print(f"No legacy ID found for {customer.customer_name}")

   
        
    # print(row)

        # if customer.legacy_id and customer.legacy_id.strip():
        #     if customer.legacy_id == customer.name:
        #         print(f"{customer.customer_name}/{customer.name} already OK")
        #         continue
        #     try:
        #         frappe.rename_doc("Customer", customer.name, customer.legacy_id, force=True, merge=False)
        #         print(f"Renamed {customer.customer_name}:    {customer.name} --> {customer.legacy_id}")
        #     except Exception as e:
        #         print(f"Error renaming {customer.name}: {e}")
