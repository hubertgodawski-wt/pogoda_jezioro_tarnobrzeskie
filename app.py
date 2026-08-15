import streamlit as st
import requests
import pandas as pd
import altair as alt

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

st.title("🌊 Jezioro Tarnobrzeskie - warunki na wodzie")

btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    st.link_button("🚗 Dojazd", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie", use_container_width=True)
with btn_col2:
    st.link_button("📹 Kamery online (MOSiR)", "https://mosir.tarnobrzeg.pl/jezioro-tarnobrzeskie/kamery-on-line/", use_container_width=True)

LAT, LON = "50.555", "21.652"
url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,windspeed_10m,windgusts_10m,precipitation_probability&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max&windspeed_unit=kn&timezone=Europe%2FWarsaw&forecast_days=7"

def knots_to_beaufort(kt):
    if kt < 1: return 0
    elif kt <= 3: return 1
    elif kt <= 6: return 2
    elif kt <= 10: return 3
    elif kt <= 16: return 4
    elif kt <= 21: return 5
    elif kt <= 27: return 6
    else: return 7

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
            
            times = [t[-5:] for t in hourly['time'][start:start+12]]
            w_bft = [knots_to_beaufort(w) for w in hourly['windspeed_10m'][start:start+12]]
            s_bft = [knots_to_beaufort(s) for s in hourly['windgusts_10m'][start:start+12]]
            temp = hourly['temperature_2m'][start:start+12]
            rain = hourly['precipitation_probability'][start:start+12]
            
            def draw_chart(data, domain, colors, title):
                st.subheader(title)
                st.altair_chart(alt.Chart(pd.DataFrame(data)).mark_bar().encode(
                    x='Godzina:N', y=alt.Y('Ocena:Q', scale=alt.Scale(domain=[0, 3])), 
                    color=alt.Color('Status:N', scale=alt.Scale(domain=domain, range=colors))
                ).properties(height=150), use_container_width=True)

            # Logika ZALEŻNA OD ZMIENNYCH
            sail_data = [{"Godzina": t, "Ocena": (3 if 2<=b<=4 and bs<6 and d<30 else (2 if b>=5 else (1 if b==1 else 0))), "Status": ("✅ Idealne" if 2<=b<=4 and bs<6 and d<30 else ("⛵ Wymagający" if b>=5 else ("🐢 Zbyt słabo" if b==1 else "😶 Cisza")))} for t, b, bs, d in zip(times, w_bft, s_bft, rain)]
            sup_data = [{"Godzina": t, "Ocena": (3 if d<30 and b<=2 else (2 if d<30 and b==3 else (1 if d<50 else 0))), "Status": ("✅ Idealne" if d<30 and b<=2 else ("🐢 Wymagająco" if d<30 and b==3 else ("⛵ Trudno" if d<50 else "⚠️ Unikaj")))} for t, b, d in zip(times, w_bft, rain)]
            beach_data = [{"Godzina": t, "Ocena": (3 if d<30 and tm>=20 else (2 if d<50 and tm>=18 else (1 if b<=3 else 0))), "Status": ("✅ Idealnie" if d<30 and tm>=20 else ("❄️ Chłodno" if d<50 and tm>=18 else ("🌬️ Wietrznie" if b<=3 else "⚠️ Unikaj")))} for t, tm, b, d in zip(times, temp, w_bft, rain)]

            draw_chart(sail_data, ['✅ Idealne', '⛵ Wymagający', '🐢 Zbyt słabo', '😶 Cisza'], ['#2ca02c', '#ff7f0e', '#87CEEB', '#808080'], "⛵ Żeglarstwo")
            draw_chart(sup_data, ['✅ Idealnie', '🐢 Wymagająco', '⛵ Trudno', '⚠️ Unikaj'], ['#2ca02c', '#87CEEB', '#ff7f0e', '#d62728'], "🏄 SUP")
            draw_chart(beach_data, ['✅ Idealnie', '❄️ Chłodno', '🌬️ Wietrznie', '⚠️ Unikaj'], ['#2ca02c', '#1f77b4', '#ff7f0e', '#d62728'], "🏖️ Plażowanie")

        with tab2:
            st.subheader("Prognoza na 7 dni")
            # ... (logika prognozy 7-dniowej)
    else: st.error("Błąd połączenia.")
except Exception as e: st.error(f"Błąd: {e}")
