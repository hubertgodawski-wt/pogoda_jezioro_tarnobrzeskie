import streamlit as st
import requests
import pandas as pd
import altair as alt

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

st.title("🌊 Warunki na wodzie")
st.link_button("🚗 Sprawdź korki dojazdowe", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie")

LAT = "50.555"
LON = "21.652"
url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,windspeed_10m,windgusts_10m,precipitation_probability&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max&windspeed_unit=kn&timezone=Europe%2FWarsaw&forecast_days=7"

# --- FUNKCJE POMOCNICZE ---
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

def beaufort_opis(bft):
    opisy = {0: "Cisza", 1: "Zefirek", 2: "Słaby", 3: "Łagodny", 4: "Umiarkowany", 5: "Dość silny", 6: "Silny", 7: "Wicher", 8: "Sztorm"}
    return opisy.get(bft, "Sztorm")

def ocena_aktywnosci(bft, bft_szkwal, temp, deszcz):
    oceny = {}
    if 2 <= bft <= 4 and bft_szkwal < 6: oceny["⛵ Żeglarstwo"] = "Idealnie"
    elif bft > 4 or bft_szkwal >= 6: oceny["⛵ Żeglarstwo"] = "Trudno"
    else: oceny["⛵ Żeglarstwo"] = "Słaby"
    
    if bft <= 1: oceny["🏄 SUP"] = "Idealnie"
    elif bft == 2: oceny["🏄 SUP"] = "Wymagająco"
    else: oceny["🏄 SUP"] = "Niebezpiecznie"
    
    if temp >= 20 and bft <= 2 and deszcz < 30: oceny["🏖️ Plażowanie"] = "Idealnie"
    elif temp < 18 or deszcz >= 50: oceny["🏖️ Plażowanie"] = "Unikaj"
    else: oceny["🏖️ Plażowanie"] = "Wietrznie"
    return oceny

def ocena_zeglarska_punktowa(bft, bft_szkwal, deszcz):
    if bft_szkwal >= 6 or deszcz >= 60: return 1, "Trudno / Szkwały"
    elif 2 <= bft <= 4 and bft_szkwal < 6 and deszcz < 40: return 3, "Idealnie"
    elif bft == 1 or bft == 5: return 2, "Można pływać"
    else: return 0, "Słaby wiatr"

# --- GŁÓWNA LOGIKA ---
try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        
        tab1, tab2 = st.tabs(["Dziś (godzinowo)", "Prognoza na 7 dni"])
        
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
            
            oceny = ocena_aktywnosci(wiatr_bft[0], szkwal_bft[0], temp[0], deszcz[0])
            cols = st.columns(3)
            for i, (akt, oc) in enumerate(oceny.items()): cols[i].metric(akt, oc)
            
            najlepszy_sup, najlepszy_zeglarz = None, None
            for t, b, bs, d in zip(formatted_times, wiatr_bft, szkwal_bft, deszcz):
                if b < 2 and d < 40 and not najlepszy_sup: najlepszy_sup = t
                if 2 <= b <= 4 and bs < 6 and d < 30 and not najlepszy_zeglarz: najlepszy_zeglarz = t
            
            st.info(f"🏄 SUP: **{najlepszy_sup or 'brak'}** | ⛵ Żagle: **{najlepszy_zeglarz or 'brak'}**")
            
            st.subheader("Ocena żeglarska godzinowa")
            sailing_data = [{"Godzina": t, "Ocena": ocena_zeglarska_punktowa(b, bs, d)[0], "Status": ocena_zeglarska_punktowa(b, bs, d)[1]} for t, b, bs, d in zip(formatted_times, wiatr_bft, szkwal_bft, deszcz)]
            st.altair_chart(alt.Chart(pd.DataFrame(sailing_data)).mark_bar().encode(x='Godzina:N', y='Ocena:Q', color='Status:N').properties(height=150), use_container_width=True)
            
            st.subheader("Pogoda (Wiatr i Szkwały)")
            wind_df = pd.DataFrame({"Godzina": formatted_times*2, "Bft": wiatr_bft+szkwal_bft, "Typ": ["Wiatr"]*12+["Szkwały"]*12})
            st.altair_chart(alt.Chart(wind_df).mark_area(opacity=0.4).encode(x='Godzina:N', y='Bft:Q', color='Typ:N').properties(height=200), use_container_width=True)
            
            st.subheader("Szczegóły godzinowe")
            df = pd.DataFrame({"Godzina": formatted_times, "Wiatr": [f"{b} Bft" for b in wiatr_bft], "Szkwały": [f"{bs} Bft" for bs in szkwal_bft], "Temp": [f"{round(t, 1)}°C" for t in temp], "Deszcz (%)": deszcz})
            st.dataframe(df, use_container_width=True, hide_index=True)

        # --- TAB 2: PROGNOZA NA 7 DNI ---
        with tab2:
            st.subheader("Prognoza warunków na najbliższe dni")
            daily = data['daily']
            
            daily_sailing_status = []
            for w_max, rain in zip(daily['windspeed_10m_max'], daily['precipitation_sum']):
                bft_max = knots_to_beaufort(w_max)
                if bft_max >= 5 or rain >= 5.0:
                    daily_sailing_status.append("Trudno / Szkwały")
                elif 2 <= bft_max <= 4 and rain < 2.0:
                    daily_sailing_status.append("⛵ Idealnie")
                elif bft_max == 1 or bft_max == 5:
                    daily_sailing_status.append("Można pływać")
                else:
                    daily_sailing_status.append("Słaby wiatr")

            df_daily = pd.DataFrame({
                "Data": daily['time'],
                "Max Temp": [f"{round(t, 1)}°C" for t in daily['temperature_2m_max']],
                "Wiatr Max": [f"{knots_to_beaufort(w)} Bft" for w in daily['windspeed_10m_max']],
                "Deszcz": [f"{round(r, 1)} mm" for r in daily['precipitation_sum']],
                "Żeglarstwo": daily_sailing_status
            })
            st.dataframe(df_daily, use_container_width=True, hide_index=True)
            st.info("💡 Wskazówka: Dni oznaczone jako '⛵ Idealnie' łączą stabilny wiatr (2-4 Bft) z brakiem większych opadów.")

    else: st.error("Błąd połączenia.")
except Exception as e: st.error(f"Błąd: {e}")
