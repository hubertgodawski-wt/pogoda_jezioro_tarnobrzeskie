import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

st.title("🌊 Warunki na wodzie")
st.link_button("🚗 Sprawdź korki dojazdowe", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie")

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
        
        current_time_str = pd.Timestamp.now(tz='Europe/Warsaw').strftime('%Y-%m-%dT%H:00')
        
        if current_time_str in hourly['time']:
            start_idx = hourly['time'].index(current_time_str)
        else:
            start_idx = 0
            
        times = hourly['time'][start_idx:start_idx+12] # Pobieramy 12 godzin do analizy
        wiatr = hourly['windspeed_10m'][start_idx:start_idx+12]
        szkwal = hourly['windgusts_10m'][start_idx:start_idx+12]
        temp = hourly['temperature_2m'][start_idx:start_idx+12]
        
        formatted_times = [t[-5:] for t in times]
        
        st.subheader("Ocena warunków (na teraz)")
        oceny = ocena_aktywnosci(wiatr[0], szkwal[0], temp[0])
        
        cols = st.columns(3)
        for i, (aktywnosc, ocena) in enumerate(oceny.items()):
            cols[i].metric(aktywnosc, ocena)
            
        # --- ALGORYTM ZNAJDUJĄCY NAJLEPSZY CZAS ---
        najlepszy_sup = None
        najlepszy_zeglarz = None
        min_wiatr_sup = 999
        najlepszy_wynik_zeglarz = -1
        
        for t, w, s in zip(formatted_times, wiatr, szkwal):
            # Dla SUP: szukamy najmniejszego wiatru (najgładziej na wodzie)
            if w < min_wiatr_sup:
                min_wiatr_sup = w
                najlepszy_sup = t
            # Dla Żeglarstwa: szukamy wiatru w przedziale 6-14 węzłów z małymi szkwałami
            if 5 <= w <= 15 and s < 20:
                # Punktacja: im bliżej 10 węzłów, tym lepiej
                score = 10 - abs(10 - w)
                if score > najlepszy_wynik_zeglarz:
                    najlepszy_wynik_zeglarz = score
                    najlepszy_zeglarz = t

        st.info(f"💡 **Sugerowane okno czasowe na dziś:**\n\n"
                f"🏄 **Najlepszy moment na SUP:** ok. **{najlepszy_sup}** (najspokojniejsza woda)\n\n"
                f"⛵ **Najlepszy moment na żagle:** ok. **{najlepszy_zeglarz if najlepszy_zeglarz else 'brak idealnych warunków'}**")
        # ------------------------------------------
        
        st.divider()
        st.subheader("Wykres wiatru i szkwałów")
        
        chart_data = pd.DataFrame({
            "Wiatr (węzły)": [round(w, 1) for w in wiatr], 
            "Szkwały (węzły)": [round(s, 1) for s in szkwal]
        }, index=formatted_times)
        
        st.area_chart(chart_data)
        
        st.subheader("Szczegóły godzinowe")
        df = pd.DataFrame({
            "Godzina": formatted_times, 
            "Wiatr (kt)": [round(w, 1) for w in wiatr], 
            "Szkwały (kt)": [round(s, 1) for s in szkwal], 
            "Temp (°C)": [round(t, 1) for t in temp]
        })
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.error("Błąd pobierania danych pogodowych z serwerów Open-Meteo.")
except Exception as e:
    st.error(f"Wystąpił nieoczekiwany problem: {e}")
