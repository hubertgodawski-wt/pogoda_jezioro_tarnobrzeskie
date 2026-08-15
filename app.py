import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

st.title("🌊 Warunki na wodzie")
# Przycisk do szybkiego sprawdzenia trasy w Google Maps
st.link_button("🚗 Sprawdź korki dojazdowe", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie")

# UWAGA: Podmień ten tekst poniżej na numer ID Twojego spotu na Windguru!
SPOT_ID = "WPISZ_TUTAJ_NUMER_SPOTU" 
url = f"https://www.windguru.cz/int/iapi.php?q=forecast&id_spot={SPOT_ID}"

headers = {"User-Agent": "Mozilla/5.0", "Referer": f"https://www.windguru.cz/{SPOT_ID}"}

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
        model_key = list(data['fcst'].keys())[0]
        forecast = data['fcst'][model_key]
        
        limit = min(6, len(forecast.get('hr_h', [])))
        wiatr = forecast.get('WINDSPD', [])[:limit]
        szkwal = forecast.get('GUST', [])[:limit]
        temp = forecast.get('TMP', [])[:limit]
        
        st.subheader("Ocena warunków (na teraz)")
        oceny = ocena_aktywnosci(wiatr[0], szkwal[0], temp[0])
        
        cols = st.columns(3)
        for i, (aktywnosc, ocena) in enumerate(oceny.items()):
            cols[i].metric(aktywnosc, ocena)
        
        st.subheader("Prognoza godzinowa")
        df = pd.DataFrame({"Godzina": forecast.get('hr_h', [])[:limit], "Wiatr (węzły)": wiatr, "Szkwały": szkwal, "Temp": temp})
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.error("Błąd połączenia.")
except Exception as e:
    st.error(f"Problem: {e}")
