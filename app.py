import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

st.title("🌊 Warunki na wodzie")
st.link_button("🚗 Sprawdź korki dojazdowe", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie")

# Używamy Open-Meteo (całkowicie darmowe i stabilne) ze współrzędnymi Jeziora Tarnobrzeskiego
LAT = "50.555"
LON = "21.652"
url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,windspeed_10m,windgusts_10m&windspeed_unit=kn&timezone=Europe%2FWarsaw&forecast_days=2"

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
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        hourly = data['hourly']
        
        # Pobieramy obecną godzinę w strefie czasowej dla Polski
        current_time_str = pd.Timestamp.now(tz='Europe/Warsaw').strftime('%Y-%m-%dT%H:00')
        
        # Znajdujemy od którego momentu na liście zaczyna się nasza godzina
        if current_time_str in hourly['time']:
            start_idx = hourly['time'].index(current_time_str)
        else:
            start_idx = 0
            
        # Wyciągamy dane na 6 najbliższych godzin
        times = hourly['time'][start_idx:start_idx+6]
        wiatr = hourly['windspeed_10m'][start_idx:start_idx+6]
        szkwal = hourly['windgusts_10m'][start_idx:start_idx+6]
        temp = hourly['temperature_2m'][start_idx:start_idx+6]
        
        # Formatujemy godziny, żeby w tabeli wyglądały ładnie (np. z "2023-10-25T14:00" robimy "14:00")
        formatted_times = [t[-5:] for t in times]
        
        st.subheader("Ocena warunków (na teraz)")
        oceny = ocena_aktywnosci(wiatr[0], szkwal[0], temp[0])
        
        cols = st.columns(3)
        for i, (aktywnosc, ocena) in enumerate(oceny.items()):
            cols[i].metric(aktywnosc, ocena)
        
        st.subheader("Prognoza godzinowa")
        df = pd.DataFrame({
            "Godzina": formatted_times, 
            "Wiatr (węzły)": [round(w, 1) for w in wiatr], 
            "Szkwały": [round(s, 1) for s in szkwal], 
            "Temp (°C)": [round(t, 1) for t in temp]
        })
        
        # Wyświetlamy tabelę rozciągniętą na całą szerokość ekranu
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.error("Błąd pobierania danych pogodowych z serwerów Open-Meteo.")
except Exception as e:
    st.error(f"Wystąpił nieoczekiwany problem: {e}")
