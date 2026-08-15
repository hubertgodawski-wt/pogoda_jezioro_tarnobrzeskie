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

def plot_chart(data, domain, range_colors, title):
    st.subheader(title)
    st.altair_chart(alt.Chart(pd.DataFrame(data)).mark_bar().encode(
        x='Godzina:N', y=alt.Y('Ocena:Q', scale=alt.Scale(domain=[0, 4])), 
        color=alt.Color('Status:N', scale=alt.Scale(domain=domain, range=range_colors)),
        tooltip=['Godzina', 'Status']
    ).properties(height=150), use_container_width=True)

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
            
            # Wykresy (zaktualizowane progi)
            plot_chart([{"Godzina": t, "Ocena": (4 if bs>=6 or d>=50 else (3 if b>=5 else (2 if 2<=b<=4 and bs<6 and d<30 else (1 if b==1 else 0)))), "Status": ("⚠️ Niebezpiecznie" if bs>=6 or d>=50 else ("⛵ Wymagający" if b>=5 else ("✅ Idealne" if 2<=b<=4 and bs<6 and d<30 else ("🐢 Zbyt słabo" if b==1 else "😶 Cisza"))))} for t, b, bs, d in zip(fmt_t, w_bft, s_bft, rain)], 
                       ['⚠️ Niebezpiecznie', '⛵ Wymagający', '✅ Idealne', '🐢 Zbyt słabo', '😶 Cisza'], ['#d62728', '#ff7f0e', '#2ca02c', '#87CEEB', '#808080'], "⛵ Żeglarstwo")
            
            plot_chart([{"Godzina": t, "Ocena": (3 if d>=50 else (2 if b>3 else (1 if b==3 else 0))), "Status": ("⚠️ Unikaj" if d>=50 else ("⛵ Trudno" if b>3 else ("🐢 Wymagająco" if b==3 else "✅ Idealnie")))} for t, b, d in zip(fmt_t, w_bft, rain)], 
                       ['⚠️ Unikaj', '⛵ Trudno', '🐢 Wymagająco', '✅ Idealnie'], ['#d62728', '#ff7f0e', '#87CEEB', '#2ca02c'], "🏄 Ocena SUP")
            
            plot_chart([{"Godzina": t, "Ocena": (3 if d>=50 else (2 if tm<20 else (1 if b>3 else 0))), "Status": ("⚠️ Unikaj" if d>=50 else ("❄️ Chłodno" if tm<20 else ("🌬️ Wietrznie" if b>3 else "✅ Idealnie")))} for t, tm, b, d in zip(fmt_t, temp, w_bft, rain)], 
                       ['⚠️ Unikaj', '❄️ Chłodno', '🌬️ Wietrznie', '✅ Idealnie'], ['#d62728', '#1f77b4', '#ff7f0e', '#2ca02c'], "🏖️ Ocena plażowania")

            st.subheader("Szczegóły godzinowe")
            st.dataframe(pd.DataFrame({"Godzina": fmt_t, "Wiatr": [f"{b} Bft" for b in w_bft], "Szkwały": [f"{bs} Bft" for bs in s_bft], "Temp": [f"{round(t, 1)}°C" for t in temp], "Deszcz (%)": rain}), use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("Prognoza na 7 dni")
            daily = data['daily']
            daily_data = []
            for t, w, r in zip(daily['time'], daily['windspeed_10m_max'], daily['precipitation_sum']):
                bft = knots_to_beaufort(w)
                status = "⚠️ Niebezpiecznie" if bft>=6 or r>5 else ("⛵ Wymagający" if bft==5 else ("✅ Idealne" if 2<=bft<=4 and r<2 else ("🐢 Zbyt słabo" if bft==1 else "😶 Cisza")))
                daily_data.append({"Data": t, "Temp": f"{round(daily['temperature_2m_max'][daily['time'].index(t)], 1)}°C", "Wiatr": f"{bft} Bft", "Deszcz": f"{round(r, 1)} mm", "Ocena": status})
            st.dataframe(pd.DataFrame(daily_data), use_container_width=True, hide_index=True)
    else: st.error("Błąd połączenia.")
except Exception as e: st.error(f"Błąd: {e}")
