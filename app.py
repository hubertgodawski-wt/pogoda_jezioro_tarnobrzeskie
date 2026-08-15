import streamlit as st
import requests
import pandas as pd
import altair as alt

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

st.title("🌊 Jezioro Tarnobrzeskie - warunki na wodzie")

# Panel przycisków
btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    st.link_button("🚗 Sprawdź korki dojazdowe", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie", use_container_width=True)
with btn_col2:
    st.link_button("📹 Kamery online (MOSiR)", "https://mosir.tarnobrzeg.pl/jezioro-tarnobrzeskie/kamery-on-line/", use_container_width=True)

LAT = "50.555"
LON = "21.652"
url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,windspeed_10m,windgusts_10m,precipitation_probability&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max&windspeed_unit=kn&timezone=Europe%2FWarsaw&forecast_days=7"

# --- FUNKCJE ---
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
    else: return 9

def beaufort_opis(bft):
    opisy = {0: "Cisza", 1: "Zefirek", 2: "Słaby", 3: "Łagodny", 4: "Umiarkowany", 5: "Dość silny", 6: "Silny"}
    return opisy.get(bft, "Wicher")

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
    if bft_szkwal >= 6 or deszcz >= 50: return 0, "Niebezpiecznie (szkwały/deszcz)"
    elif 2 <= bft <= 4 and bft_szkwal < 6 and deszcz < 30: return 3, "Idealne warunki"
    elif bft == 5: return 2, "Wymagający wiatr"
    elif bft == 1: return 1, "Zbyt słabo"
    else: return 0, "Cisza / Słaby wiatr"

# --- LOGIKA ---
try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tab1, tab2 = st.tabs(["Dziś (godzinowo)", "Prognoza na 7 dni"])
        
        with tab1:
            hourly = data['hourly']
            curr = pd.Timestamp.now(tz='Europe/Warsaw').strftime('%Y-%m-%dT%H:00')
            start = hourly['time'].index(curr) if curr in hourly['time'] else 0
            
            times = hourly['time'][start:start+12]
            w_kt = hourly['windspeed_10m'][start:start+12]
            s_kt = hourly['windgusts_10m'][start:start+12]
            temp = hourly['temperature_2m'][start:start+12]
            rain = hourly['precipitation_probability'][start:start+12]
            fmt_t = [t[-5:] for t in times]
            
            w_bft = [knots_to_beaufort(w) for w in w_kt]
            s_bft = [knots_to_beaufort(s) for s in s_kt]
            
            cols = st.columns(3)
            oceny = ocena_aktywnosci(w_bft[0], s_bft[0], temp[0], rain[0])
            for i, (a, o) in enumerate(oceny.items()): cols[i].metric(a, o)
            
            sup, sail = None, None
            for t, b, bs, d in zip(fmt_t, w_bft, s_bft, rain):
                if b < 2 and d < 40 and not sup: sup = t
                if 2 <= b <= 4 and bs < 6 and d < 30 and not sail: sail = t
            st.info(f"🏄 SUP: **{sup or 'brak'}** | ⛵ Żagle: **{sail or 'brak'}**")
            
            st.subheader("Ocena żeglarska godzinowa")
            sail_data = [{"Godzina": t, "Ocena": ocena_zeglarska_punktowa(b, bs, d)[0], "Status": ocena_zeglarska_punktowa(b, bs, d)[1]} for t, b, bs, d in zip(fmt_t, w_bft, s_bft, rain)]
            st.altair_chart(alt.Chart(pd.DataFrame(sail_data)).mark_bar().encode(x='Godzina:N', y=alt.Y('Ocena:Q', scale=alt.Scale(domain=[0,3])), color='Status:N', tooltip=['Godzina', 'Status']).properties(height=150), use_container_width=True)
            
            st.subheader("Pogoda (Wiatr i Szkwały)")
            wind_df = pd.DataFrame({"Godzina": fmt_t*2, "Bft": w_bft+s_bft, "Typ": ["Wiatr"]*12+["Szkwały"]*12})
            st.altair_chart(alt.Chart(wind_df).mark_area(opacity=0.4).encode(x='Godzina:N', y='Bft:Q', color='Typ:N').properties(height=200), use_container_width=True)
            
            st.subheader("Szczegóły godzinowe")
            df = pd.DataFrame({"Godzina": fmt_t, "Wiatr": [f"{b} Bft" for b in w_bft], "Szkwały": [f"{bs} Bft" for bs in s_bft], "Temp": [f"{round(t, 1)}°C" for t in temp], "Deszcz (%)": rain})
            st.dataframe(df, use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("Prognoza na 7 dni")
            daily = data['daily']
            daily_data = []
            for t, w, r in zip(daily['time'], daily['windspeed_10m_max'], daily['precipitation_sum']):
                bft = knots_to_beaufort(w)
                # Bardziej szczegółowa logika dla dniówki
                if bft >= 6 or r > 5.0: status = "⚠️ Niebezpiecznie / Sztormowo"
                elif bft == 5: status = "⛵ Wymagający wiatr"
                elif 2 <= bft <= 4 and r < 2.0: status = "⛵ Idealne warunki"
                elif bft == 1: status = "🐢 Zbyt słabo"
                else: status = "Cisza / Słaby wiatr"
                
                daily_data.append({"Data": t, "Temp": f"{round(daily['temperature_2m_max'][daily['time'].index(t)], 1)}°C", "Wiatr": f"{bft} Bft", "Deszcz": f"{round(r, 1)} mm", "Ocena": status})
            
            st.dataframe(pd.DataFrame(daily_data), use_container_width=True, hide_index=True)
            st.info("💡 Kliknij nagłówki kolumn w tabeli, aby posortować dni.")

    else: st.error("Błąd pobierania danych.")
except Exception as e: st.error(f"Błąd: {e}")
