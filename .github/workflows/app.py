import streamlit as st
from docxtpl import DocxTemplate
from gusregon import GUS
import datetime
import os

# --- KONFIGURACJA ---
# Twój klucz API GUS
API_KEY = 'd75dd615254847b4b9c9'

def pobierz_dane_z_gus(nip_input):
    """
    Łączy się z GUS i pobiera dane firmy.
    """
    try:
        gus = GUS(api_key=API_KEY)
        clean_nip = nip_input.replace('-', '').replace(' ', '').strip()
        
        dane = gus.search(nip=clean_nip)
        
        if not dane:
            return None
            
        # Formatowanie adresu
        ulica = dane.get('ulica', '')
        nr_domu = dane.get('nrNieruchomosci', '')
        nr_lokalu = dane.get('nrLokalu', '')
        miejscowosc = dane.get('miejscowosc', '')
        kod = dane.get('kodPocztowy', '')
        
        adres_full = f"{ulica} {nr_domu}"
        if nr_lokalu:
            adres_full += f"/{nr_lokalu}"
        
        adres_caly_z_kodem = f"{miejscowosc}, {adres_full}, {kod}"
        
        # Data rozpoczęcia
        start_date = dane.get('dataRozpoczeciaDzialalnosci') or dane.get('dataPowstania', '')

        return {
            "nazwa": dane.get('nazwa', ''),
            "adres_caly": adres_caly_z_kodem,
            "miejscowosc": miejscowosc,
            "regon": dane.get('regon', ''),
            "data_start": start_date,
            "pkd": dane.get('silos_pkd', {}).get('kod', '') 
        }
    except Exception as e:
        st.error(f"Błąd połączenia z GUS: {str(e)}")
        return None

# --- UI APLIKACJI ---
st.set_page_config(page_title="Generator BDO - Elite Waste", layout="wide")
st.title("📄 Generator Oświadczeń BDO (Elite Waste)")

# --- SEKCJA 1: DANE ---
st.header("1. Dane Podmiotu")
col1, col2 = st.columns(2)

if 'gus_data' not in st.session_state:
    st.session_state['gus_data'] = {}

with col1:
    nip_input = st.text_input("Podaj NIP klienta:", max_chars=13)
    
    if st.button("🔍 Pobierz dane z GUS"):
        if len(nip_input) >= 10:
            with st.spinner('Pobieram dane...'):
                wynik = pobierz_dane_z_gus(nip_input)
                if wynik:
                    st.session_state['gus_data'] = wynik
                    st.success("Dane pobrane!")
                else:
                    st.error("Nie znaleziono firmy lub błąd.")
        else:
            st.warning("Wpisz poprawny NIP.")

    imie_nazwisko = st.text_input("Imię i Nazwisko (Reprezentant):")
    telefon = st.text_input("Telefon kontaktowy:", value="+48 ")

with col2:
    dane = st.session_state['gus_data']
    
    email = st.text_input("Adres e-mail:", value="biuro@elitewaste.pl")
    nazwa_firmy = st.text_input("Nazwa Firmy:", value=dane.get('nazwa', ''))
    adres_firmy = st.text_input("Adres (Ulica, Kod, Miasto):", value=dane.get('adres_caly', ''))
    miejscowosc_dok = st.text_input("Miejscowość (nagłówek):", value=dane.get('miejscowosc', ''))
    regon = st.text_input("REGON:", value=dane.get('regon', ''))
    pkd = st.text_input("Wiodące PKD:", value=dane.get('pkd', ''))
    data_rozpoczecia = st.text_input("Data rozpoczęcia:", value=dane.get('data_start', ''))

# --- SEKCJA 2: CHECKBOXY ---
st.divider()
st.header("2. Zakres Działalności")
st.info("ℹ️ Zaznacz tylko to, co ma być na TAK. Reszta będzie na NIE.")

t_col1, t_col2 = st.columns(2)
vars_bdo = {}

with t_col1:
    vars_bdo['bdo_wytworca'] = st.checkbox("Wytwórca odpadów", value=False)
    vars_bdo['bdo_transport'] = st.checkbox("Transportujący odpady", value=False)
    vars_bdo['bdo_kody'] = st.checkbox("Deklarowane kody odpadów", value=False)
    vars_bdo['bdo_obszar'] = st.checkbox("Obszar działalności", value=False)
    vars_bdo['bdo_jakosc'] = st.checkbox("Wdrożony system jakości", value=False)
    vars_bdo['bdo_srodowisko'] = st.checkbox("System środowiskowy", value=False)
    vars_bdo['bdo_oplata'] = st.checkbox("Opłata produktowa", value=False)
    vars_bdo['bdo_pojazdy'] = st.checkbox("Recykling pojazdów", value=False)

with t_col2:
    vars_bdo['bdo_sprzedawca'] = st.checkbox("Sprzedawca odpadów", value=False)
    vars_bdo['bdo_posrednik'] = st.checkbox("Pośrednik w obrocie", value=False)
    vars_bdo['bdo_elektro'] = st.checkbox("Zużyty sprzęt elektro", value=False)
    vars_bdo['bdo_baterie'] = st.checkbox("Baterie i akumulatory", value=False)
    vars_bdo['bdo_opakowania'] = st.checkbox("Gosp. opakowaniami", value=False)
    vars_bdo['bdo_zwolniony'] = st.checkbox("Zwolniony z zezwolenia", value=False)
    vars_bdo['bdo_urzad'] = st.checkbox("Wpis z urzędu (Art. 51)", value=False)
    vars_bdo['bdo_statki'] = st.checkbox("Recykling statków", value=False)

# --- GENEROWANIE ---
st.divider()
if st.button("🖨️ Generuj Dokument WORD", type="primary"):
    if not nazwa_firmy:
        st.error("Uzupełnij nazwę firmy!")
    else:
        # Kontekst danych
        context = {
            'miejscowosc': miejscowosc_dok,
            'data': datetime.date.today().strftime("%d.%m.%Y"),
            'nazwa_firmy': nazwa_firmy,
            'adres_firmy': adres_firmy,
            'nip': nip_input,
            'regon': regon,
            'imie_nazwisko': imie_nazwisko,
            'email': email,
            'telefon': telefon,
            'pkd': pkd,
            'data_rozpoczecia': data_rozpoczecia,
        }
        
        # Logika TAK/NIE
        for key, value in vars_bdo.items():
            context[key] = "TAK" if value else "NIE"

        try:
            # --- FIX ŚCIEŻKI DO PLIKU ---
            # 1. Pobierz folder, w którym jest ten skrypt
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 2. Sklej folder z nazwą pliku
            template_path = os.path.join(current_dir, "oswiadczenie.docx")
            
            # Sprawdzenie debugowe
            if not os.path.exists(template_path):
                st.error(f"Nie widzę pliku! Szukam tutaj: {template_path}")
                st.text(f"Pliki w folderze: {os.listdir(current_dir)}")
                st.stop()
                
            doc = DocxTemplate(template_path)
            doc.render(context)
            
            # Zapis pliku wynikowego
            safe_name = nazwa_firmy.replace('"', '').replace('/', '-').strip()[:20]
            out_filename = f"Oswiadczenie_{safe_name}.docx"
            out_path = os.path.join(current_dir, out_filename)
            
            doc.save(out_path)
            
            with open(out_path, "rb") as f:
                st.download_button(
                    label="📥 POBIERZ PLIK",
                    data=f,
                    file_name=out_filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            
            st.success(f"Gotowe! Plik wygenerowany dla: {nazwa_firmy}")
            
        except Exception as e:
            st.error(f"Wystąpił błąd: {e}")
