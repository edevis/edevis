
COUNTRY_MAP = {
    "Deutschland": "Germany",
    "IRLAND": "Ireland",
    "Irland": "Ireland",
    "DE": "Germany",
    "UK": "United Kingdom",
    "GB": "United Kingdom",
    "Tschechische Republik": "Czech Republic",
    "Polen": "Poland",
    "Österreich": "Austria",
    "Schweiz": "Switzerland",
    "Frankreich": "France",
    "USA": "United States",
    "US": "United States",
    "Taiwan (R.O.C.)": "Taiwan",
    "Italien": "Italy",
    "Spanien": "Spain",
    "Niederlande": "Netherlands",
    "Belgien": "Belgium",
    "Luxemburg": "Luxembourg",
    "Estland": "Estonia",
    # weitere Länder hier ergänzen
}

DE_LANG_COUNTRIES = ["Germany", "Austria", "Switzerland", "Luxembourg"]


def get_language(country):
    """
    Liefert 'de' für deutschsprachige Länder, sonst 'en'.
    """
    if country in DE_LANG_COUNTRIES:
        return "de"
    return "en"

def translate_country(country_de):
    if not country_de:
        return None
    result = COUNTRY_MAP.get(country_de.strip(), country_de) 
    
    return result
