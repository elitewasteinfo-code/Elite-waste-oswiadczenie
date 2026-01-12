import streamlit as st
from docxtpl import DocxTemplate
import datetime
# Jeśli masz bibliotekę gusregon: from gusregon import GUS
# Jeśli nie, użyjemy prostej symulacji lub requests

# --- KONFIGURACJA ---
# Aby to działało w pełni automatycznie z GUS, potrzebujesz biblioteki gusregon
# pip install gusregon streamlit docxtpl

def get_gus_data(nip_input):
    """
    Tu wpinamy Twoje API GUS. 
    Na potrzeby testu zwraca przykładowe dane, żebyś widział efekt od razu.
    """
    # W wersji finalnej odkomentuj i wpisz swój klucz API:
    # gus = GUS(api_key='TWOJ_KLUCZ_GUS')
    # data = gus.search(nip=nip_input)
    
    # Mock danych (symulacja):
    return {
        "nazwa": f"FIRMA TESTOWA NIP {nip_input} SP. Z O.O.",
        "adres_caly": "ul. Przemysłowa 10, 00-001 Warszawa",
        "miejscowosc": "Warszawa",
        "kod_pocztowy": "00-001",
        "ulica": "ul. Przemysłowa 10",
        "regon": "123456789",
        "data_start": "2020-01-15",
        "pkd": "38.11.Z" 
    }

st.set_page_config(page_title="Generator BDO - Elite Waste", layout="wide")

st.image("https://via.placeholder.com/800x100.png?text=Elite+Waste+Generator", use_column_width=True)
st.title(" 📄 Generator Oświadczeń BDO")

# --- SEKCJA 1: DANE KLIENTA ---
st.header("1. Dane Podmiotu")

col1, col2 = st.columns(2)

with col1:
    nip = st.text_input("Podaj NIP klienta:", max_chars=10)
    if st.button("Pobierz dane z GUS"):
        if len(nip) == 10:
            st.session_state['gus_data'] = get_gus_data(nip)
            st.success("Dane pobrane!")
        else:
            st.error("Podaj poprawny NIP")

    # Dane ręczne
    imie_nazwisko = st.text_input("Imię i Nazwisko (do wniosku):")
    telefon = st.text_input("Telefon kontaktowy:", value="+48 ")

with col2:
    # Wyświetlanie pobranych danych (lub pustych pól do edycji)
    gus_data = st.session_state.get('gus_data', {})
    
    email = st.text_input("Adres e-mail:", value="biuro@elitewaste.pl") # Domyślny email?
    nazwa_firmy = st.text_input("Nazwa Firmy:", value=gus_data.get('nazwa', ''))
    adres_firmy = st.text_input("Adres (Miejscowość, Ulica):", value=gus_data.get('adres_caly', ''))
    miejscowosc = st.text_input("Miejscowość (do nagłówka):", value=gus_data.get('miejscowosc', ''))
    regon = st.text_input("REGON:", value=gus_data.get('regon', ''))
    pkd = st.text_input("Wiodące PKD:", value=gus_data.get('pkd', ''))
    data_rozpoczecia = st.text_input("Data rozpoczęcia dział.:", value=gus_data.get('data_start', ''))


# --- SEKCJA 2: TABELA BDO (CHECKBOXY) ---
st.header("2. Zakres Działalności (Tabela)")
st.caption("Zaznacz to, co wykonujemy dla klienta. Odznaczone = 'NIE', Zaznaczone = 'TAK'.")

# Używamy kolumn dla lepszej czytelności
t_col1, t_col2 = st.columns(2)

vars_bdo = {}

with t_col1:
    vars_bdo['bdo_wytworca'] = st.checkbox("Wytwórca odpadów (Ewidencja)", value=False)
    vars_bdo['bdo_transport'] = st.checkbox("Transportujący odpady", value=False)
    vars_bdo['bdo_kody'] = st.checkbox("Deklarowane kody odpadów", value=False)
    vars_bdo['bdo_obszar'] = st.checkbox("Obszar działalności (Ogólny)", value=False)
    vars_bdo['bdo_jakosc'] = st.checkbox("Wdrożony system jakości", value=False)
    vars_bdo['bdo_srodowisko'] = st.checkbox("Wdrożony system zarz. środowiskowego", value=False)
    vars_bdo['bdo_oplata'] = st.checkbox("Ustawa o obow. przedsiębiorc. (Opłata)", value=False)
    vars_bdo['bdo_pojazdy'] = st.checkbox("Recykling pojazdów", value=False)

with t_col2:
    vars_bdo['bdo_sprzedawca'] = st.checkbox("Sprzedawca odpadów", value=False)
    vars_bdo['bdo_posrednik'] = st.checkbox("Pośrednik w obrocie", value=False)
    vars_bdo['bdo_elektro'] = st.checkbox("Zużyty sprzęt elektr./elektroniczny", value=False)
    vars_bdo['bdo_baterie'] = st.checkbox("Baterie i akumulatory", value=False)
    vars_bdo['bdo_opakowania'] = st.checkbox("Gosp. opakowaniami", value=False)
    vars_bdo['bdo_zwolniony'] = st.checkbox("Posiadacz zwolniony z zezwolenia", value=False)
    vars_bdo['bdo_urzad'] = st.checkbox("Wpis z urzędu (Art. 51)", value=False)
    vars_bdo['bdo_statki'] = st.checkbox("Recykling statków", value=False)


# --- GENEROWANIE ---
st.divider()
if st.button("🖨️ Generuj Oświadczenie", type="primary"):
    # Przygotuj słownik zmiennych (context)
    context = {
        'miejscowosc': miejscowosc,
        'data': datetime.date.today().strftime("%d.%m.%Y"),
        'nazwa_firmy': nazwa_firmy,
        'adres_firmy': adres_firmy,
        'nip': nip,
        'regon': regon,
        'imie_nazwisko': imie_nazwisko,
        'email': email,
        'telefon': telefon,
        'pkd': pkd,
        'data_rozpoczecia': data_rozpoczecia,
    }
    
    # Dodaj logikę TAK/NIE dla tabeli
    # Jeśli checkbox zaznaczony -> 'TAK', jeśli nie -> 'NIE'
    for key, value in vars_bdo.items():
        context[key] = "TAK" if value else "NIE"

    try:
        # Wczytaj Twój szablon
        doc = DocxTemplate("Oświadczenie - wpis wzor.docx")
        doc.render(context)
        
        # Nazwa pliku wyjściowego
        out_name = f"Oswiadczenie_{nip}_{datetime.date.today()}.docx"
        doc.save(out_name)
        
        # Przycisk pobierania
        with open(out_name, "rb") as f:
            st.download_button("📥 Pobierz gotowy plik", f, file_name=out_name)
            
        st.balloons()
        st.success("Dokument wygenerowany poprawnie!")
        
    except Exception as e:
        st.error(f"Błąd generowania. Czy plik 'Oświadczenie - wpis wzor.docx' jest w tym samym folderze? Szczegóły: {e}")
