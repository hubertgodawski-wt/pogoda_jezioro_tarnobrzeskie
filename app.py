import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

st.title("🌊 Warunki na wodzie")
st.link_button("🚗 Sprawdź korki dojazdowe", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie")

# Zabezpieczenie przed niewidocznymi spacjami przy kopiowaniu
SPOT_ID = "30390".strip()
url = f"https://www.windguru.cz/int/iapi.php?q=forecast&id_spot={SPOT_ID}"

# Pełny nagłówek udający prawdziwą przeglądarkę (omija zabezpieczenia przed botami)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"https://www.windguru.cz/{SPOT_ID}",
    "Accept": "application/json"
}

def ocena_aktywnosci(wiatr, szkwal, temp):
    oceny = {}
    if 5 <= wiatr <= 15 and szkwal < 20: oceny["⛵ Żeglarstwo"] = "Idealnie"
    elif wiatr > 20: oceny["⛵ Żeglarstwo"] = "Trudno (refowanie)"
    else: oceny["⛵ Żeglarstwo"] = "Słaby wiatr"
    
    if wiatr <= 8: oceny["🏄 SUP"] = "Idealnie"
    elif wiatr <= 12: oceny["🏄 SUP"] = "Wymagająco"
    else: oceny["🏄 SUP"] = "Niebezpiecznie"
    
    if temp >= 20 and wiatr <= 10: oceny["🏖️ Plażowanie"] = "Idealnie"
    elif temp < 18: oceny["🏖️ Plażowanie"] = "Za chłodno"
    else: oceny["🏖️ Plażowanie"] = "Wietrznie"
    
    return oceny

try:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        
        # NOWOŚĆ: Zabezpieczenie, które pokaże Ci dokładny powód, jeśli Windguru nie wyśle pogody
        if 'fcst' not in data:
            st.error("Serwer odrzucił zapytanie i nie zwrócił danych. Poniżej znajduje się to, co nam odesłał:")
            st.json(data)
            st.stop()
            
        model_key = list(data['fcst'].keys())[0]
        forecast = data['fcst'][model_key]
        
        limit = min(6, len(forecast.get('hr_h', [])))
        wiatr = forecast.get('WINDSPD', [])[:limit]
        szkwal = forecast.get('GUST', [])[:limit]
        temp = forecast.get('TMP', [])[:limit]
        
        st.subheader("Ocena warunków (na teraz)")
        # Zabezpieczenie na wypadek brakujących danych w pierwszej kolumnie
        oceny = ocena_aktywnosci(wiatr[0] if wiatr else 0, szkwal[0] if szkwal else 0, temp[0] if temp else 0)
        
        cols = st.columns(3)
        for i, (aktywnosc, ocena) in enumerate(oceny.items()):
            cols[i].metric(aktywnosc, ocena)
        
        st.subheader("Prognoza godzinowa")
        df = pd.DataFrame({
            "Godzina": forecast.get('hr_h', [])[:limit], 
            "Wiatr (węzły)": wiatr, 
            "Szkwały": szkwal, 
            "Temp": temp
        })
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.error(f"Błąd połączenia z serwerem. Kod statusu: {response.status_code}")
except Exception as e:
    st.error(f"Problem: {e}")
