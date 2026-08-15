import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

st.title("🌊 Jezioro Tarnobrzeskie - warunki na wodzie")

# Panel przycisków
btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    st.link_button("🚗 Dojazd", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie", use_container_width=True)
with btn_col2:
    st.link_button("📹 Kamery online (MOSiR)", "https://mosir.tarnobrzeg.pl/jezioro-tarnobrzeskie/kamery-on-line/", use_container_width=True)

LAT, LON = "50.555", "21.652"
# Dodano sunrise (wschód słońca) do zapytania API
url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,windspeed_10m,windgusts_10m,winddirection_10m,precipitation_probability,cloudcover&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,sunrise,sunset&windspeed_unit=kn&timezone=Europe%2FWarsaw&forecast_days=7"

def knots_to_beaufort(kt):
    if kt < 1: return 0
    elif kt <= 3: return 1
    elif kt <= 6: return 2
    elif kt <= 10: return 3
    elif kt <= 16: return 4
    elif kt <= 21: return 5
    elif kt <= 27: return 6
    else: return 7

def degrees_to_cardinal(deg):
    if deg is None: return "-"
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    ix = int((deg + 11.25) / 22.5) % 16
    return dirs[ix]

# --- GŁÓWNA LOGIKA ---
try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        hourly = data['hourly']
        daily = data['daily']
        
        curr = pd.Timestamp.now(tz='Europe/Warsaw').strftime('%Y-%m-%dT%H:00')
        start = hourly['time'].index(curr) if curr in hourly['time'] else 0
        
        # --- BIEŻĄCA POGODA I TREND ---
        current_temp = hourly['temperature_2m'][start]
        current_wind_kt = hourly['windspeed_10m'][start]
        current_wind_bft = knots_to_beaufort(current_wind_kt)
        current_gust_bft = knots_to_beaufort(hourly['windgusts_10m'][start])
        current_dir = degrees_to_cardinal(hourly['winddirection_10m'][start])
        current_rain = hourly['precipitation_probability'][start]
        current_cloud = hourly['cloudcover'][start]
        
        day_winds = hourly['windspeed_10m'][start:start+12]
        day_rains = hourly['precipitation_probability'][start:start+12]
        max_wind_trend = max(day_winds)
        max_rain_trend = max(day_rains)
        
        trend_desc = "stabilne warunki przez cały dzień."
        if max_wind_trend > current_wind_kt + 5:
            trend_desc = "⚠️ W ciągu dnia wiatr będzie narastał."
        elif max_rain_trend > 40:
            trend_desc = "☔ Wzrost ryzyka opadów w ciągu dnia."
        elif max_wind_trend < current_wind_kt - 3:
            trend_desc = "🍃 Wiatr powoli będzie słabł."

        st.markdown("---")
        st.subheader("📌 Aktualnie nad wodą")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Temperatura", f"{round(current_temp, 1)}°C")
        m_col2.metric("Wiatr", f"{current_wind_bft} Bft ({current_dir})", f"Szkwały: {current_gust_bft} Bft")
        m_col3.metric("Deszcz", f"{current_rain}%")
        m_col4.metric("Zachmurzenie", f"{current_cloud}%")
        
        st.info(f"📈 **Trend na dziś:** {trend_desc}")
        st.markdown("---")

        tab1, tab2 = st.tabs(["Dziś (godzinowo)", "Prognoza na 7 dni"])
        
        with tab1:
            # Wschód i zachód słońca dla dzisiejszego dnia
            sunrise_str = daily['sunrise'][0]
            sunset_str = daily['sunset'][0]
            sunrise_dt = datetime.fromisoformat(sunrise_str)
            sunset_dt = datetime.fromisoformat(sunset_str)
            max_beach_dt = sunset_dt + timedelta(minutes=30)
            max_beach_hour = max_beach_dt.hour
            max_beach_minute = max_beach_dt.minute
            
            raw_times = hourly['time'][start:start+12]
            times = [t[-5:] for t in raw_times]
            hours = [int(t[11:13]) for t in raw_times]
            
            w_bft = [knots_to_beaufort(w) for w in day_winds]
            s_bft = [knots_to_beaufort(s) for s in hourly['windgusts_10m'][start:start+12]]
            w_dir = [degrees_to_cardinal(d) for d in hourly['winddirection_10m'][start:start+12]]
            temp = hourly['temperature_2m'][start:start+12]
            rain = day_rains
            clouds = hourly['cloudcover'][start:start+12]
            
            st.caption(f"🌅 Wschód słońca: **{sunrise_dt.strftime('%H:%M')}** | Zachód słońca: **{sunset_dt.strftime('%H:%M')}** (okno plażowe do {max_beach_dt.strftime('%H:%M')})")

            h_now = hours[0]
            is_after_sunset = (h_now > max_beach_hour) or (h_now == max_beach_hour and 0 >= max_beach_minute)
            
            oceny = {}
            if 2 <= w_bft[0] <= 4 and s_bft[0] < 6: oceny["⛵ Żeglarstwo"] = "Idealnie"
            elif w_bft[0] > 4 or s_bft[0] >= 6: oceny["⛵ Żeglarstwo"] = "Trudno"
            else: oceny["⛵ Żeglarstwo"] = "Słaby"
            
            if w_bft[0] <= 2: oceny["🏄 SUP"] = "Idealnie"
            elif w_bft[0] == 3: oceny["🏄 SUP"] = "Wymagająco"
            else: oceny["🏄 SUP"] = "Niebezpiecznie"

            if is_after_sunset or h_now < 9:
                oceny["🏖️ Plażowanie"] = "Po zmroku / Noc"
            elif temp[0] >= 20 and w_bft[0] <= 2 and rain[0] < 30 and clouds[0] < 40:
                oceny["🏖️ Plażowanie"] = "Idealnie"
            elif temp[0] < 18 or rain[0] >= 50:
                oceny["🏖️ Plażowanie"] = "Unikaj"
            else:
                oceny["🏖️ Plażowanie"] = "Wietrznie/Pochmurno"

            cols = st.columns(3)
            for i, (a, o) in enumerate(oceny.items()): cols[i].metric(a, o)
            
            sup, sail = None, None
            for t, b, bs, d, h in zip(times, w_bft, s_bft, rain, hours):
                if b <= 2 and d < 40 and 8 <= h <= 20 and not sup: sup = t
                if 2 <= b <= 4 and bs < 6 and d < 30 and not sail: sail = t
            st.info(f"🏄 SUP: **{sup or 'brak'}** | ⛵ Żagle: **{sail or 'brak'}**")
            
            def draw_chart(chart_data, domain, colors, title):
                st.subheader(title)
                st.altair_chart(alt.Chart(pd.DataFrame(chart_data)).mark_bar().encode(
                    x='Godzina:N', y=alt.Y('Ocena:Q', scale=alt.Scale(domain=[0, 4])), 
                    color=alt.Color('Status:N', scale=alt.Scale(domain=domain, range=colors)),
                    tooltip=['Godzina', 'Status']
                ).properties(height=150), use_container_width=True)

            sail_data = []
            for t, b, bs, d in zip(times, w_bft, s_bft, rain):
                if bs >= 6 or d >= 50: sail_data.append({"Godzina": t, "Ocena": 4, "Status": "⚠️ Niebezpiecznie"})
                elif b >= 5: sail_data.append({"Godzina": t, "Ocena": 3, "Status": "⛵ Wymagający"})
                elif 2 <= b <= 4 and bs < 6 and d < 30: sail_data.append({"Godzina": t, "Ocena": 2, "Status": "✅ Idealne"})
                elif b == 1: sail_data.append({"Godzina": t, "Ocena": 1, "Status": "🐢 Zbyt słabo"})
                else: sail_data.append({"Godzina": t, "Ocena": 0, "Status": "😶 Cisza"})
            draw_chart(sail_data, ['⚠️ Niebezpiecznie', '⛵ Wymagający', '✅ Idealne', '🐢 Zbyt słabo', '😶 Cisza'], ['#d62728', '#ff7f0e', '#2ca02c', '#87CEEB', '#808080'], "⛵ Ocena żeglarska")

            sup_data = []
            for t, b, d, h in zip(times, w_bft, rain, hours):
                if h < 7 or h > 20: sup_data.append({"Godzina": t, "Ocena": 0, "Status": "🌙 Noc / Zmierzch"})
                elif d >= 50: sup_data.append({"Godzina": t, "Ocena": 4, "Status": "⚠️ Unikaj"})
                elif b > 3: sup_data.append({"Godzina": t, "Ocena": 3, "Status": "⛵ Trudno"})
                elif b == 3: sup_data.append({"Godzina": t, "Ocena": 2, "Status": "🐢 Wymagająco"})
                else: sup_data.append({"Godzina": t, "Ocena": 1, "Status": "✅ Idealne"})
            draw_chart(sup_data, ['🌙 Noc / Zmierzch', '⚠️ Unikaj', '⛵ Trudno', '🐢 Wymagająco', '✅ Idealne'], ['#333333', '#d62728', '#ff7f0e', '#87CEEB', '#2ca02c'], "🏄 Ocena SUP")

            beach_data = []
            for t, tm, b, d, c, h in zip(times, temp, w_bft, rain, clouds, hours):
                if (h > max_beach_hour or (h == max_beach_hour and max_beach_minute > 0)) or h < 9:
                    beach_data.append({"Godzina": t, "Ocena": 0, "Status": "🌙 Po zachodzie słońca"})
                elif d >= 50 or tm < 16:
                    beach_data.append({"Godzina": t, "Ocena": 1, "Status": "⚠️ Unikaj / Chłodno"})
                elif c >= 70:
                    beach_data.append({"Godzina": t, "Ocena": 2, "Status": "☁️ Duże zachmurzenie"})
                elif b > 3 or (30 <= c < 70):
                    beach_data.append({"Godzina": t, "Ocena": 3, "Status": "⛅ Umiarkowanie"})
                else:
                    beach_data.append({"Godzina": t, "Ocena": 4, "Status": "☀️ Idealne słońce"})
            draw_chart(beach_data, ['🌙 Po zachodzie słońca', '⚠️ Unikaj / Chłodno', '☁️ Duże zachmurzenie', '⛅ Umiarkowanie', '☀️ Idealne słońce'], ['#333333', '#d62728', '#7f7f7f', '#ff7f0e', '#2ca02c'], "🏖️ Ocena plażowania")

            st.subheader("Szczegóły godzinowe")
            df = pd.DataFrame({"Godzina": times, "Wiatr": [f"{b} Bft" for b in w_bft], "Kierunek": w_dir, "Szkwały": [f"{s} Bft" for s in s_bft], "Temp": [f"{round(t, 1)}°C" for t in temp], "Chmury": [f"{c}%" for c in clouds], "Deszcz (%)": rain})
            st.dataframe(df, use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("Prognoza na 7 dni")
            daily = data['daily']
            daily_data = []
            for i, t in enumerate(daily['time']):
                w = daily['windspeed_10m_max'][i]
                r = daily['precipitation_sum'][i]
                bft = knots_to_beaufort(w)
                status = "⚠️ Niebezpiecznie" if bft>=6 or r>5 else ("⛵ Wymagający" if bft==5 else ("✅ Idealne" if 2<=bft<=4 and r<2 else ("🐢 Zbyt słabo" if bft==1 else "😶 Cisza")))
                daily_data.append({
                    "Data": t, 
                    "Temp Max": f"{round(daily['temperature_2m_max'][i], 1)}°C", 
                    "Wschód": daily['sunrise'][i][-5:], 
                    "Zachód": daily['sunset'][i][-5:], 
                    "Wiatr Max": f"{bft} Bft", 
                    "Ocena": status
                })
            st.dataframe(pd.DataFrame(daily_data), use_container_width=True, hide_index=True)

    else: st.error("Błąd pobierania danych.")
except Exception as e: st.error(f"Błąd: {e}")
