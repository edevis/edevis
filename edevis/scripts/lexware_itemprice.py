import pyodbc

class LxItemprice:
    baseFilters = ""

    def __init__(self, art_no):
        self.lxconn = pyodbc.connect("DSN=lexware2")
        self.lxcur=self.lxconn.cursor()
        self.sql_base_filters = { "P.PreisgrpNr = 1", "P.MengeNr = 1", }
        sql_filter = self.sql_base_filters
        sql_filter.add (f"""P.ArtikelNr like '{art_no}'""")
        # sqlquery = f"""SELECT ArtikelNr,Vk_preis_eur FROM "F1"."FK_Preismatrix" """;
        sqlquery = f"""SELECT P.ArtikelNr,A.Matchcode,P.Vk_preis_eur FROM FK_Preismatrix P INNER JOIN FK_Artikel A ON A.ArtikelNr = P.ArtikelNr """;
        first_el = sql_filter.pop()
        if first_el is not None:
            sqlquery += " where "
            sqlquery += first_el

            for f in sql_filter:
                sqlquery += " and "
                sqlquery += f

        #print(sqlquery)
        self.lxcur.execute(sqlquery)        
    
    def __iter__(self):
            return self
    
    def __next__(self):
        row = self.lxcur.fetchone()
        if row == None:
            raise StopIteration
        
        return row

    # commit updates to database
    def commit(self):
        self.lxconn.commit()

    # update prices
    def update(self, row, priceGroupIndex, quantityGroupIndex, value):
        updatecur=self.lxconn.cursor()
        sqlquery = f"""UPDATE "F1"."FK_Preismatrix" SET "Vk_preis_eur" = {value} WHERE "PreisgrpNr" = '{priceGroupIndex}' AND "MengeNr" = '{quantityGroupIndex}' AND "ArtikelNr" = '{row[0]}' """;
        updatecur.execute(sqlquery)