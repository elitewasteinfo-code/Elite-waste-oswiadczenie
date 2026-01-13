import streamlit as st
from docxtpl import DocxTemplate
from gusregon import GUS
import datetime
import os

# --- KONFIGURACJA ---
API_KEY = 'd75dd615254847b4b9c9'

def safe_get(d, keys, default=''):
    """Szuka wartości pod różnymi kluczami."""
    for k in keys:
        if k in d and d[k]: return d[k]
        if k.lower() in d and d[k.lower()]: return d[k.lower()]
    return default

def pobierz_dane_z_gus(nip_input):
    try:
        gus = GUS(api_key=API_KEY)
        clean_nip = nip_input.replace('-', '').replace(' ', '').strip()
        
        # KROK 1: Podstawowe dane (Adresy, Nazwy)
        dane = gus.search(nip=clean_nip)
        
        if not dane:
            return None, "GUS nic nie zwrócił dla tego NIP."

        raw_debug = dane.copy()

        # --- PARSOWANIE PODSTAWOWE ---
        nazwa = safe_get(dane, ['nazwa', 'Nazwa'])
        miejscowosc = safe_get(dane, ['adsiedzmiejscowosc_nazwa', 'miejscowosc', 'Miejscowosc'])
        ulica_raw = safe_get(dane, ['adsiedzulica_nazwa', 'ulica', 'Ulica'])
        nr_domu = safe_get(dane, ['adsiedznumerieruchomosci', 'nrNieruchomosci', 'nr_domu'])
        nr_lokalu = safe_get(dane, ['adsiedznumerlokalu', 'nrLokalu', 'nr_lokalu'])
        kod = safe_get(dane, ['adsiedzkodpocztowy', 'kodPocztowy', 'KodPocztowy'])
        regon = safe_get(dane, ['regon9', 'regon14', 'regon', 'Regon'])
        typ = safe_get(dane, ['typ', 'Typ'])

        data_start = safe_get(dane, [
            'datarozpoczeciadzialalnosci',
            'dataRozpoczeciaDzialalnosci',
            'dataPowstania'
        ])

        # Próba PKD z podstawowego widoku
        pkd = safe_get(dane, ['silos_pkd', 'kod_pkd'])
        if isinstance(pkd, dict): pkd = pkd.get('kod', '')

        # --- KROK 2: BRUTAL FORCE CEIDG (Dla JDG) ---
        # Jeśli nie ma PKD i mamy REGON, strzelamy do raportu szczegółowego
        if not pkd and regon:
            try:
                # Raport specyficzny dla działalności fizycznej
                raport_ceidg = gus.get_full_report(regon, 'BIR11OsFizycznaDzialalnoscCeidg')
                
                # Czasem GUS zwraca listę, jeśli było wiele wpisów. Bierzemy pierwszy (aktualny)
                if isinstance(raport_ceidg, list) and len(raport_ceidg) > 0:
                    raport_ceidg = raport_ceidg[0]
                
                # Dodajemy do debuga, żebyś widział co przyszło
                raw_debug['RAPORT_CEIDG_FULL'] = raport_ceidg

                # Szukamy PKD w tym nowym raporcie (klucze specyficzne dla tego raportu)
                pkd = safe_get(raport_ceidg, [
                    'fiz_pkd_kod', 
                    'fiz_pkdKod', 
                    'fiz_przewazajace_pkd_kod',
                    'fiz_pkd_nazwa' # czasem kod jest sklejony z nazwą
                ])
                
                # Jeśli to nie zadziałało, próbujemy jeszcze innego raportu (PKD dedykowane)
                if not pkd:
                    raport_pkd = gus.get_full_report(regon, 'BIR11OsFizycznaPkd')
                    if isinstance(raport_pkd, list) and len(raport_pkd) > 0:
                        # Szukamy tego z przeważającym = tak
                        for r in raport_pkd:
                            if r.get('fiz_pkd_przewazajace') == '1' or r.get('fiz_pkdPrzewazajace') == '1':
                                pkd = safe_get(r, ['fiz_pkd_kod', 'fiz_pkdKod'])
                                break
                        # Jak nie znaleziono przeważającego, bierzemy pierwszy
                        if not pkd:
                            pkd = safe_get(raport_pkd[0], ['fiz_pkd_kod', 'fiz_pkdKod'])
                            
                    raw_debug['RAPORT_PKD_FULL'] = raport_pkd

            except Exception as e:
                raw_debug['ERROR_FETCHING_REPORT'] = str(e)

        # --- BUDOWANIE ADRESU ---
        adres_full = ""
        if ulica_raw:
            if "ul." in ulica_raw.lower():
                adres_full = f"{ulica_raw} {nr_domu}"
            else:
                adres_full = f"ul. {ulica_raw} {nr_domu}"
        else:
            adres_full = f"{miejscowosc} {nr_domu}"
            
        if nr_lokalu: adres_full += f"/{nr_lokalu}"
        adres_caly_z_kodem = f"{miejscowosc}, {adres_full}, {kod}"

        wynik = {
            "nazwa": nazwa,
            "adres_caly": adres_caly_z_kodem,
            "miejscowosc": miejscowosc,
            "regon": regon,
            "data_start": data_start,
            "pkd": pkd
        }
        
        return wynik, raw_debug

    except Exception as e:
        return None, str(e)

# --- UI APLIKACJI ---
st.set_page_config(page_title="Generator BDO - Elite Waste", layout="wide")
st.title("📄 Generator Oświadczeń BDO (Elite Waste)")

# --- SEKCJA 1 ---
st.header("1. Dane Podmiotu")
col1, col2 = st.columns(2)

if 'gus_data' not in st.session_state:
    st.session_state['gus_data'] = {}

with col1:
    nip_input = st.text_input("Podaj NIP klienta:", max_chars=13)
    
    if st.button("🔍 Pobierz dane z GUS"):
        if len(nip_input) >= 10:
            with st.spinner('Pobieram dane (Deep Search PKD)...'):
                parsed_data, raw_debug = pobierz_dane_z_gus(nip_input)
                
                if parsed_data:
                    st.session_state['gus_data'] = parsed_data
                    st.success("Dane pobrane!")
                    
                    # DEBUGGER - ZOBACZYSZ TU PEŁNY RAPORT JEŚLI PKD NADAL PUSTE
                    with st.expander("🕵️ Pokaż surowe dane (Debug Raportów)"):
                        st.write("To co wstawiam do Worda:", parsed_data)
                        st.write("Surowe dane z GUS:", raw_debug)
                else:
                    st.error(f"Błąd: {raw_debug}")
        else:
            st.warning("Wpisz poprawny NIP.")

    imie_nazwisko = st.text_input("Imię i Nazwisko (Reprezentant):")
    telefon = st.text_input("Telefon kontaktowy:", value="+48 ")

with col2:
    dane = st.session_state['gus_data']
    
    email = st.text_input("Adres e-mail:", value="biuro@elitewaste.pl")
    nazwa_firmy = st.text_input("Nazwa Firmy:", value=dane.get('nazwa', ''))
    adres_firmy = st.text_input("Adres:", value=dane.get('adres_caly', ''))
    miejscowosc_dok = st.text_input("Miejscowość:", value=dane.get('miejscowosc', ''))
    regon = st.text_input("REGON:", value=dane.get('regon', ''))
    pkd = st.text_input("Wiodące PKD:", value=dane.get('pkd', ''))
    data_rozpoczecia = st.text_input("Data rozpoczęcia:", value=dane.get('data_start', ''))

# --- SEKCJA 2 ---
st.divider()
st.header("2. Zakres Działalności")
st.info("ℹ️ Zaznacz tylko TAK.")

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
        
        for key, value in vars_bdo.items():
            context[key] = "TAK" if value else "NIE"

        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(current_dir, "oswiadczenie.docx")
            
            if not os.path.exists(template_path):
                st.error(f"Nie widzę pliku! Szukam tutaj: {template_path}")
                st.stop()
                
            doc = DocxTemplate(template_path)
            doc.render(context)
            
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
            st.success(f"Gotowe! Plik dla: {nazwa_firmy}")
            
        except Exception as e:
            st.error(f"Błąd generowania: {e}")
