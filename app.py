import streamlit as st
import requests
import pandas as pd
import altair as alt

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

st.title("🌊 Jezioro Tarnobrzeskie - warunki na wodzie")

# Panel przycisków
btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    st.link_button("🚗 Dojazd", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie", use_container_width=True)
with btn_col2:
    st.link_button("📹 Kamery online (MOSiR)", "https://mosir.tarnobrzeg.pl/jezioro-tarnobrzeskie/kamery-on-line/", use_container_width=True)

LAT = "50.555"
LON = "21.652"
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
    else: return 9

def ocena_zeglarska_szczegolowa(bft, bft_szkwal, deszcz):
    if bft_szkwal >= 6 or deszcz >= 50: return 4, "⚠️ Niebezpiecznie"
    elif bft >= 5: return 3, "⛵ Wymagający wiatr"
    elif 2 <= bft <= 4 and bft_szkwal < 6 and deszcz < 30: return 2, "✅ Idealne warunki"
    elif bft == 1: return 1, "🐢 Zbyt słabo"
    else: return 0, "😶 Cisza / Słaby wiatr"

def ocena_sup_szczegolowa(bft, deszcz):
    if deszcz >= 50: return 3, "⚠️ Unikaj (deszcz)"
    elif bft > 2: return 2, "⛵ Trudno (wiatr)"
    elif bft == 2: return 1, "🐢 Wymagająco"
    else: return 0, "✅ Idealne warunki"

def ocena_plazowania_szczegolowa(temp, bft, deszcz):
    if deszcz >= 50: return 3, "⚠️ Unikaj (deszcz)"
    elif temp < 20: return 2, "❄️ Chłodno"
    elif bft > 3: return 1, "🌬️ Wietrznie"
    else: return 0, "✅ Idealne warunki"

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
            fmt_t = [t[-5:] for t in times]
            w_bft = [knots_to_beaufort(w) for w in hourly['windspeed_10m'][start:start+12]]
            s_bft = [knots_to_beaufort(s) for s in hourly['windgusts_10m'][start:start+12]]
            temp = hourly['temperature_2m'][start:start+12]
            rain = hourly['precipitation_probability'][start:start+12]
            
            # Wykresy (Wspólna funkcja rysująca)
            def plot_chart(data, domain, range_colors, title):
                st.subheader(title)
                st.altair_chart(alt.Chart(pd.DataFrame(data)).mark_bar().encode(
                    x='Godzina:N', y=alt.Y('Ocena:Q', scale=alt.Scale(domain=[0, 3])), 
                    color=alt.Color('Status:N', scale=alt.Scale(domain=domain, range=range_colors)),
                    tooltip=['Godzina', 'Status']
                ).properties(height=150), use_container_width=True)

            sail_data = [{"Godzina": t, "Ocena": ocena_zeglarska_szczegolowa(b, bs, d)[0], "Status": ocena_zeglarska_szczegolowa(b, bs, d)[1]} for t, b, bs, d in zip(fmt_t, w_bft, s_bft, rain)]
            sup_data = [{"Godzina": t, "Ocena": ocena_sup_szczegolowa(b, d)[0], "Status": ocena_sup_szczegolowa(b, d)[1]} for t, b, d in zip(fmt_t, w_bft, rain)]
            beach_data = [{"Godzina": t, "Ocena": ocena_plazowania_szczegolowa(tm, b, d)[0], "Status": ocena_plazowania_szczegolowa(tm, b, d)[1]} for t, tm, b, d in zip(fmt_t, temp, w_bft, rain)]

            plot_chart(sail_data, ['⚠️ Niebezpiecznie', '⛵ Wymagający wiatr', '✅ Idealne warunki', '🐢 Zbyt słabo', '😶 Cisza / Słaby wiatr'], ['#d62728', '#ff7f0e', '#2ca02c', '#87CEEB', '#808080'], "⛵ Ocena żeglarska")
            plot_chart(sup_data, ['⚠️ Unikaj (deszcz)', '⛵ Trudno (wiatr)', '🐢 Wymagająco', '✅ Idealne warunki'], ['#d62728', '#ff7f0e', '#87CEEB', '#2ca02c'], "🏄 Ocena SUP")
            plot_chart(beach_data, ['⚠️ Unikaj (deszcz)', '❄️ Chłodno', '🌬️ Wietrznie', '✅ Idealne warunki'], ['#d62728', '#1f77b4', '#ff7f0e', '#2ca02c'], "🏖️ Ocena plażowania")

        with tab2:
            st.info("Sekcja prognozy 7-dniowej pozostaje bez zmian.")
    else: st.error("Błąd połączenia.")
except Exception as e: st.error(f"Błąd: {e}")
