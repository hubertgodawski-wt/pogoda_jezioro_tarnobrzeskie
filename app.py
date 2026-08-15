import streamlit as st
import requests
import pandas as pd
import altair as alt

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

st.title("🌊 Warunki na wodzie")
st.link_button("🚗 Sprawdź korki dojazdowe", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie")

LAT = "50.555"
LON = "21.652"
# Rozszerzamy zapytanie o parametry 'daily' dla prognozy na 7 dni
url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,windspeed_10m,windgusts_10m,precipitation_probability&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max&windspeed_unit=kn&timezone=Europe%2FWarsaw&forecast_days=7"

def knots_to_beaufort(kt):
    if kt < 1: return 0
    elif kt <= 3: return 1
    elif kt <= 6: return 2
    elif kt <= 10: return 3
    elif kt <= 16: return 4
    elif kt <= 21: return 5
    elif kt <= 27: return 6
    elif kt <= 33: return 7
    elif kt <= 40: return 8
    elif kt <= 47: return 9
    elif kt <= 55: return 10
    elif kt <= 63: return 11
    else: return 12

def ocena_aktywnosci(bft, bft_szkwal, temp, deszcz):
    oceny = {}
    if 2 <= bft <= 4 and bft_szkwal < 6: oceny["⛵ Żeglarstwo"] = "Idealnie"
    elif bft > 4 or bft_szkwal >= 6: oceny["⛵ Żeglarstwo"] = "Trudno (refowanie)"
    else: oceny["⛵ Żeglarstwo"] = "Słaby wiatr"
    
    if bft <= 1: oceny["🏄 SUP"] = "Idealnie"
    elif bft == 2: oceny["🏄 SUP"] = "Wymagająco"
    else: oceny["🏄 SUP"] = "Niebezpiecznie"
    
    if temp >= 20 and bft <= 2 and deszcz < 30: oceny["🏖️ Plażowanie"] = "Idealnie"
    elif temp < 18 or deszcz >= 50: oceny["🏖️ Plażowanie"] = "Unikaj"
    else: oceny["🏖️ Plażowanie"] = "Wietrznie"
    
    return oceny

try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        
        # Używamy zakładek dla lepszej przejrzystości
        tab1, tab2 = st.tabs(["Dziś (godzinowo)", "Prognoza (dniowa)"])
        
        # --- TAB 1: DZIŚ ---
        with tab1:
            hourly = data['hourly']
            current_time_str = pd.Timestamp.now(tz='Europe/Warsaw').strftime('%Y-%m-%dT%H:00')
            start_idx = hourly['time'].index(current_time_str) if current_time_str in hourly['time'] else 0
                
            times = hourly['time'][start_idx:start_idx+12]
            wiatr_kt = hourly['windspeed_10m'][start_idx:start_idx+12]
            szkwal_kt = hourly['windgusts_10m'][start_idx:start_idx+12]
            temp = hourly['temperature_2m'][start_idx:start_idx+12]
            deszcz = hourly['precipitation_probability'][start_idx:start_idx+12]
            formatted_times = [t[-5:] for t in times]
            
            wiatr_bft = [knots_to_beaufort(w) for w in wiatr_kt]
            szkwal_bft = [knots_to_beaufort(s) for s in szkwal_kt]
            
            # Statystyki na górze
            oceny = ocena_aktywnosci(wiatr_bft[0], szkwal_bft[0], temp[0], deszcz[0])
            cols = st.columns(3)
            for i, (aktywnosc, ocena) in enumerate(oceny.items()):
                cols[i].metric(aktywnosc, ocena)
            
            st.divider()
            
            # Wykres żeglarski
            st.subheader("⛵ Ocena żeglarska")
            sailing_data = []
            for t, b, bs, d in zip(formatted_times, wiatr_bft, szkwal_bft, deszcz):
                status = "Idealnie" if (2<=b<=4 and bs<6 and d<30) else "Trudno/Słabo"
                sailing_data.append({"Godzina": t, "Status": status})
            
            sail_df = pd.DataFrame(sailing_data)
            chart_sailing = alt.Chart(sail_df).mark_bar().encode(
                x='Godzina:N', y='count():Q', color='Status:N'
            ).properties(height=150)
            st.altair_chart(chart_sailing, use_container_width=True)
            
            # Wykres wiatru
            wind_df = pd.DataFrame({"Godzina": formatted_times*2, "Bft": wiatr_bft+szkwal_bft, "Typ": ["Wiatr"]*12+["Szkwały"]*12})
            chart_wind = alt.Chart(wind_df).mark_area(opacity=0.4).encode(
                x='Godzina:N', y='Bft:Q', color='Typ:N'
            ).properties(height=200)
            st.altair_chart(chart_wind, use_container_width=True)

        # --- TAB 2: PROGNOZA DNIOWA ---
        with tab2:
            st.subheader("Prognoza na 7 dni")
            daily = data['daily']
            df_daily = pd.DataFrame({
                "Data": daily['time'],
                "Max Temp (°C)": daily['temperature_2m_max'],
                "Min Temp (°C)": daily['temperature_2m_min'],
                "Wiatr Max (Bft)": [knots_to_beaufort(w) for w in daily['windspeed_10m_max']],
                "Deszcz (mm)": daily['precipitation_sum']
            })
            st.dataframe(df_daily, use_container_width=True, hide_index=True)
            st.info("💡 Wskazówka: Dni z wiatrem powyżej 4 Bft są bardziej wymagające.")

    else:
        st.error("Błąd pobierania danych.")
except Exception as e:
    st.error(f"Wystąpił problem: {e}")
