import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

# --- WŁASNY CSS POWIĘKSZAJĄCY KAFELKI (METRYKI) ---
st.markdown("""
    <style>
    [data-testid="stMetricLabel"] {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 2.3rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 1rem !important;
    }
    </style>
""", unsafe_allow_html=True)

current_time_warsaw = pd.Timestamp.now(tz='Europe/Warsaw')
formatted_date = current_time_warsaw.strftime('%d.%m.%Y')
formatted_clock = current_time_warsaw.strftime('%H:%M')

st.title("🌊 Jezioro Tarnobrzeskie - warunki na wodzie")
st.caption(f"📅 Dzisiaj jest **{formatted_date}** | ⏰ Aktualny czas: **{formatted_clock}**")

btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    st.link_button("🚗 Dojazd", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie", use_container_width=True)
with btn_col2:
    st.link_button("📹 Kamery online (MOSiR)", "https://mosir.tarnobrzeg.pl/jezioro-tarnobrzeskie/kamery-on-line/", use_container_width=True)

LAT, LON = "50.555", "21.652"
url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,apparent_temperature,windspeed_10m,windgusts_10m,winddirection_10m,precipitation_probability,cloudcover,cape&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,sunrise,sunset&windspeed_unit=kn&timezone=Europe%2FWarsaw&forecast_days=7"

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
    if deg is None: return ("-", "⬆️")
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    arrows = ["⬇️", "↙️", "↙️", "⬅️", "⬅️", "↖️", "↖️", "⬆️", "⬆️", "↗️", "↗️", "➡️", "➡️", "↘️", "↘️", "⬇️"]
    ix = int((deg + 11.25) / 22.5) % 16
    return dirs[ix], arrows[ix]

try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        hourly = data['hourly']
        daily = data['daily']
        
        curr = current_time_warsaw.strftime('%Y-%m-%dT%H:00')
        start = hourly['time'].index(curr) if curr in hourly['time'] else 0
        
        current_temp = hourly['temperature_2m'][start]
        current_app_temp = hourly['apparent_temperature'][start]
        current_wind_kt = hourly['windspeed_10m'][start]
        current_wind_bft = knots_to_beaufort(current_wind_kt)
        current_gust_kt = hourly['windgusts_10m'][start]
        current_gust_bft = knots_to_beaufort(current_gust_kt)
        curr_dir_text, curr_dir_arrow = degrees_to_cardinal(hourly['winddirection_10m'][start])
        current_rain = hourly['precipitation_probability'][start]
        current_cloud = hourly['cloudcover'][start]
        current_cape = hourly['cape'][start] if 'cape' in hourly else 0
        
        raw_times = hourly['time'][start:start+12]
        times = [t[-5:] for t in raw_times]
        hours = [int(t[11:13]) for t in raw_times]
        
        day_winds = hourly['windspeed_10m'][start:start+12]
        day_gusts = hourly['windgusts_10m'][start:start+12]
        day_rains = hourly['precipitation_probability'][start:start+12]
        day_capes = hourly['cape'][start:start+12] if 'cape' in hourly else [0]*12
        day_temps = hourly['temperature_2m'][start:start+12]
        
        max_wind_trend = max(day_winds)
        max_rain_trend = max(day_rains)
        max_gust_trend = max(day_gusts)
        max_cape_trend = max(day_capes) if day_capes else 0
        
        trend_desc = "stabilne warunki przez cały dzień."
        if max_wind_trend > current_wind_kt + 5:
            trend_desc = "⚠️ W ciągu dnia wiatr będzie narastał."
        elif max_rain_trend > 40:
            trend_desc = "☔ Wzrost ryzyka opadów w ciągu dnia."
        elif max_wind_trend < current_wind_kt - 3:
            trend_desc = "🍃 Wiatr powoli będzie słabł."

        st.markdown("---")
        st.subheader("📌 Aktualnie nad wodą i ostrzeżenia na dziś")
        
        warnings = []
        danger_gust_times = [t for t, g in zip(times, day_gusts) if knots_to_beaufort(g) >= 6]
        if danger_gust_times:
            warnings.append(f"🚨 **OSTRZEŻENIE ŻEGLARSKIE:** Prognozowane szkwały ≥ 6 Bft w godzinach: **{danger_gust_times[0]} - {danger_gust_times[-1]}**. Zaplanuj powrót z wody wcześniej!")

        danger_storm_times = [t for t, c in zip(times, day_capes) if c >= 300]
        if danger_storm_times:
            warnings.append(f"⚡ **OSTRZEŻENIE BURZOWE:** Wysoka niestabilność atmosferyczna w godzinach: **{danger_storm_times[0]} - {danger_storm_times[-1]}**.")

        danger_heat_times = [t for t, tp in zip(times, day_temps) if tp >= 30]
        if danger_heat_times:
            warnings.append(f"🔥 **OSTRZEŻENIE UPAŁOWE:** Temperatura ≥ 30°C w godzinach: **{danger_heat_times[0]} - {danger_heat_times[-1]}**.")

        if warnings:
            for warn in warnings:
                st.error(warn)
        else:
            st.success("✅ **Werdykt na teraz:** Brak poważnych ostrzeżeń meteorologicznych na najbliższe godziny.")

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Temperatura", f"{round(current_temp, 1)}°C", f"Odczuwalna: {round(current_app_temp, 1)}°C")
        m_col2.metric("Wiatr", f"{current_wind_bft} Bft ({curr_dir_text} {curr_dir_arrow})", f"Szkwały: {current_gust_bft} Bft")
        m_col3.metric("Deszcz", f"{current_rain}%")
        m_col4.metric("Zachmurzenie", f"{current_cloud}%")
        
        st.info(f"📈 **Trend na dziś:** {trend_desc}")
        st.markdown("---")

        tab1, tab2 = st.tabs(["Dziś (godzinowo)", "Prognoza na 7 dni"])
        
        with tab1:
            sunrise_str = daily['sunrise'][0]
            sunset_str = daily['sunset'][0]
            sunrise_dt = datetime.fromisoformat(sunrise_str)
            sunset_dt = datetime.fromisoformat(sunset_str)
            max_beach_dt = sunset_dt + timedelta(minutes=30)
            max_beach_hour = max_beach_dt.hour
            max_beach_minute = max_beach_dt.minute
            
            w_bft = [knots_to_beaufort(w) for w in day_winds]
            s_bft = [knots_to_beaufort(s) for s in day_gusts]
            
            dirs_raw = [degrees_to_cardinal(d) for d in hourly['winddirection_10m'][start:start+12]]
            w_dir = [f"{d[0]} {d[1]}" for d in dirs_raw]
            
            temp = day_temps
            app_temp = hourly['apparent_temperature'][start:start+12]
            rain = day_rains
            clouds = hourly['cloudcover'][start:start+12]
            
            st.caption(f"🌅 Wschód słońca: **{sunrise_dt.strftime('%H:%M')}** | Zachód słońca: **{sunset_dt.strftime('%H:%M')}** (okno plażowe do {max_beach_dt.strftime('%H:%M')})")

            best_sup, best_sail = [], []
            for t, b, bs, d, h in zip(times, w_bft, s_bft, rain, hours):
                if b <= 2 and d < 40 and 8 <= h <= 20: best_sup.append(t)
                if 2 <= b <= 4 and bs < 6 and d < 30: best_sail.append(t)
            
            sup_window = f"{best_sup[0]} - {best_sup[-1]}" if len(best_sup) > 0 else "brak"
            sail_window = f"{best_sail[0]} - {best_sail[-1]}" if len(best_sail) > 0 else "brak"
            
            st.info(f"🎯 **Rekomendowane okna dzisiaj:** 🏄 SUP: **{sup_window}** | ⛵ Żagle: **{sail_window}**")
            
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
                h_now_eval = int(t[:2])
                if (h_now_eval > max_beach_hour or (h_now_eval == max_beach_hour and max_beach_minute > 0)) or h < 9:
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
            df = pd.DataFrame({
                "Godzina": times, 
                "Wiatr": [f"{b} Bft" for b in w_bft], 
                "Kierunek": w_dir, 
                "Szkwały": [f"{s} Bft" for s in s_bft], 
                "Temp": [f"{round(t, 1)}°C" for t in temp], 
                "Odczuwalna": [f"{round(at, 1)}°C" for at in app_temp],
                "Chmury": [f"{c}%" for c in clouds], 
                "Deszcz (%)": rain
            })
            st.dataframe(df, use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("📅 Kafelkowa prognoza na 7 dni")
            daily = data['daily']
            
            # Tworzymy rząd kolumn dla kolejnych dni (np. po 7 dni)
            days_count = len(daily['time'])
            cols = st.columns(days_count)
            
            for i, col in enumerate(cols):
                t = daily['time'][i]
                w = daily['windspeed_10m_max'][i]
                r = daily['precipitation_sum'][i]
                bft = knots_to_beaufort(w)
                temp_max = round(daily['temperature_2m_max'][i], 1)
                sunrise = daily['sunrise'][i][-5:]
                sunset = daily['sunset'][i][-5:]
                
                # Ocena dnia
                if bft >= 6 or r > 5:
                    status = "⚠️ Niebezpiecznie"
                    box_color = "red"
                elif bft == 5:
                    status = "⛵ Wymagający"
                    box_color = "orange"
                elif 2 <= bft <= 4 and r < 2:
                    status = "✅ Idealne"
                    box_color = "green"
                elif bft == 1:
                    status = "🐢 Zbyt słabo"
                    box_color = "blue"
                else:
                    status = "😶 Cisza"
                    box_color = "gray"

                with col:
                    st.markdown(f"### **{t}**")
                    st.metric("Temp Max", f"{temp_max}°C")
                    st.write(f"💨 **Wiatr Max:** {bft} Bft")
                    st.write(f"🌧️ **Deszcz:** {r} mm")
                    st.write(f"🌅 {sunrise} | 🌇 {sunset}")
                    
                    # Kolorowe podsumowanie statusu w kafelku
                    if box_color == "green":
                        st.success(status)
                    elif box_color == "red":
                        st.error(status)
                    elif box_color == "orange":
                        st.warning(status)
                    else:
                        st.info(status)

    else: st.error("Błąd pobierania danych.")
except Exception as e: st.error(f"Błąd: {e}")
