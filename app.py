import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

# --- WŁASNY CSS POWIĘKSZAJĄCY KAFELKI I WYKRESY ---
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
st.caption("🌤️ Dane pogodowe dostarczane bezpłatnie przez API [Open-Meteo](https://open-meteo.com/)")

btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    st.link_button("🚗 Dojazd", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie", use_container_width=True)
with btn_col2:
    st.link_button("📹 Kamery online (MOSiR)", "https://mosir.tarnobrzeg.pl/jezioro-tarnobrzeskie/kamery-on-line/", use_container_width=True)

LAT, LON = "50.555", "21.652"
# DODANO: uv_index do zapytania API
url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,apparent_temperature,windspeed_10m,windgusts_10m,winddirection_10m,precipitation_probability,cloudcover,cape,uv_index&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,sunrise,sunset&windspeed_unit=kn&timezone=Europe%2FWarsaw&forecast_days=7"

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
        current_uv = hourly['uv_index'][start] if 'uv_index' in hourly else 0
        
        raw_times = hourly['time'][start:start+12]
        times = [t[-5:] for t in raw_times]
        hours = [int(t[11:13]) for t in raw_times]
        
        day_winds = hourly['windspeed_10m'][start:start+12]
        day_gusts = hourly['windgusts_10m'][start:start+12]
        day_rains = hourly['precipitation_probability'][start:start+12]
        day_capes = hourly['cape'][start:start+12] if 'cape' in hourly else [0]*12
        day_temps = hourly['temperature_2m'][start:start+12]
        day_uvs = hourly['uv_index'][start:start+12] if 'uv_index' in hourly else [0]*12
        
        w_bft = [knots_to_beaufort(w) for w in day_winds]
        s_bft = [knots_to_beaufort(s) for s in day_gusts]
        dirs_raw = [degrees_to_cardinal(d) for d in hourly['winddirection_10m'][start:start+12]]
        w_dir_text_list = [d[0] for d in dirs_raw]
        w_dir = [f"{d[0]} {d[1]}" for d in dirs_raw]
        
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
        st.subheader("📌 Aktualnie nad wodą i ostrzeżenia na dziś")
        
        warnings_critical = []
        warnings_standard = []

        # --- LOGIKA OSTRZEŻEŃ ---

        # 1. Burza i wyładowania (Wspólne, priorytetowe)
        danger_storm_times = [t for t, c, r in zip(times, day_capes, day_rains) if c >= 300 and r > 40]
        if danger_storm_times:
            warnings_critical.append(f"⚡ **OSTRZEŻENIE BURZOWE:** Ryzyko wyładowań w godz: **{danger_storm_times[0]} - {danger_storm_times[-1]}**. Deski SUP i żaglówki powinny bezwzględnie opuścić wodę!")

        # 2. Żeglarskie (Szkwały)
        danger_gust_times = [t for t, bs in zip(times, s_bft) if bs >= 6]
        if danger_gust_times:
            warnings_critical.append(f"⛵ **OSTRZEŻENIE ŻEGLARSKIE:** Prognozowane szkwały ≥ 6 Bft w godz: **{danger_gust_times[0]} - {danger_gust_times[-1]}**.")

        # 3. SUP: Silny wiatr
        sup_wind_times = [t for t, b in zip(times, w_bft) if b >= 4]
        if sup_wind_times:
            warnings_standard.append(f"🏄 **OSTRZEŻENIE SUP (SILNY WIATR):** Wiatr ≥ 4 Bft w godz: **{sup_wind_times[0]} - {sup_wind_times[-1]}**. Utrudniony powrót na brzeg pod wiatr.")

        # 4. SUP: Wiatr odbrzegowy (Zdradliwe warunki)
        sup_offshore_times = [t for t, b, dt in zip(times, w_bft, w_dir_text_list) if b >= 3 and dt in ["E", "ENE", "ESE", "SE"]]
        if sup_offshore_times:
            warnings_standard.append(f"🏄 **UWAGA SUP (WIATR ODBRZEGOWY):** Wiatr wschodni od plaży (≥ 3 Bft) w godz: **{sup_offshore_times[0]} - {sup_offshore_times[-1]}**. Wysokie ryzyko zniesienia na środek jeziora!")

        # 5. Plaża: Latające parasole
        beach_gust_times = [t for t, bs in zip(times, s_bft) if bs >= 5]
        if beach_gust_times:
            warnings_standard.append(f"🏖️ **UWAGA PLAŻA (WIATR):** Szkwały ≥ 5 Bft w godz: **{beach_gust_times[0]} - {beach_gust_times[-1]}**. Ryzyko unoszenia parasoli i uciążliwego piasku.")

        # 6. Plaża: UV
        beach_uv_times = [t for t, uv in zip(times, day_uvs) if uv >= 7]
        if beach_uv_times:
            warnings_standard.append(f"☀️ **EKSTREMALNE UV:** Indeks UV ≥ 7 w godz: **{beach_uv_times[0]} - {beach_uv_times[-1]}**. Konieczny krem z filtrem i cień!")

        # 7. Plaża/Ogólne: Nagłe załamanie pogody
        sudden_change = False
        for i in range(len(w_bft) - 3):
            if max(w_bft[i+1:i+4]) - w_bft[i] >= 3 or max(s_bft[i+1:i+4]) - s_bft[i] >= 3:
                sudden_change = True
                break
        if sudden_change:
            warnings_critical.append("⚠️ **NAGŁE ZAŁAMANIE POGODY:** W ciągu najbliższych godzin prognozowany jest gwałtowny skok siły wiatru!")

        # --- WYŚWIETLANIE OSTRZEŻEŃ ---
        if warnings_critical or warnings_standard:
            for warn in warnings_critical:
                st.error(warn)
            for warn in warnings_standard:
                st.warning(warn)
        else:
            st.success("✅ **Werdykt na teraz:** Brak ostrzeżeń. Warunki bezpieczne i stabilne dla wszystkich aktywności.")

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Temperatura", f"{round(current_temp, 1)}°C", f"Odczuwalna: {round(current_app_temp, 1)}°C")
        m_col2.metric("Wiatr", f"{current_wind_bft} Bft ({curr_dir_text} {curr_dir_arrow})", f"Szkwały: {current_gust_bft} Bft")
        m_col3.metric("UV / Chmury", f"UV: {round(current_uv, 1)}", f"Chmury: {current_cloud}%")
        m_col4.metric("Deszcz", f"{current_rain}%")
        
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
            
            select_hour = alt.selection_point(fields=['Godzina'], nearest=True, on='click', empty='none')

            def draw_interactive_chart(chart_data, domain, colors, title):
                st.subheader(title)
                df_chart = pd.DataFrame(chart_data)
                
                base = alt.Chart(df_chart).mark_bar().encode(
                    x=alt.X('Godzina:N', title='Godzina', axis=alt.Axis(labelColor='white', titleColor='white')),
                    y=alt.Y('Ocena:Q', scale=alt.Scale(domain=[0, 4]), title='Ocena', axis=alt.Axis(labelColor='white', titleColor='white')),
                    color=alt.Color('Status:N', scale=alt.Scale(domain=domain, range=colors), title='Status', legend=alt.Legend(labelColor='white', titleColor='white')),
                    tooltip=['Godzina', 'Status', 'Opis']
                ).properties(
                    height=160,
                    background='transparent'
                ).configure_view(
                    stroke=None
                )

                chart = base.add_params(select_hour).encode(
                    opacity=alt.condition(select_hour, alt.value(1), alt.value(0.7))
                )
                
                st.altair_chart(chart, use_container_width=True, theme=None)

            # 1. Żeglarstwo
            sail_data = []
            for t, b, bs, d in zip(times, w_bft, s_bft, rain):
                if bs >= 6 or d >= 50: desc, score, stat = f"Szkwały {bs} Bft lub deszcz {d}%", 4, "⚠️ Niebezpiecznie"
                elif b >= 5: desc, score, stat = f"Wiatr wiodący {b} Bft (wymagający)", 3, "⛵ Wymagający"
                elif 2 <= b <= 4 and bs < 6 and d < 30: desc, score, stat = f"Wiatr {b} Bft, szkwały {bs} Bft, deszcz {d}%", 2, "✅ Idealne"
                elif b == 1: desc, score, stat = f"Słaby wiatr ({b} Bft)", 1, "🐢 Zbyt słabo"
                else: desc, score, stat = f"Cisza na wodzie", 0.4, "😶 Cisza"
                sail_data.append({"Godzina": t, "Ocena": score, "Status": stat, "Opis": desc})
            draw_interactive_chart(
                sail_data, 
                ['⚠️ Niebezpiecznie', '⛵ Wymagający', '✅ Idealne', '🐢 Zbyt słabo', '😶 Cisza'], 
                ['#ff3333', '#ff9900', '#00ffcc', '#00bfff', '#ab82ff'], 
                "⛵ Ocena żeglarska (kliknij słupek, aby zobaczyć szczegóły)"
            )

            # 2. SUP
            sup_data = []
            for t, b, d, h in zip(times, w_bft, rain, hours):
                h_now_eval = int(t[:2])
                if h_now_eval > 20 or h_now_eval < 7: desc, score, stat = "Poza godzinami dozwolonymi (noc/zmierzch)", 0.4, "🌙 Noc / Zmierzch"
                elif d >= 50: desc, score, stat = f"Wysokie prawdopodobieństwo deszczu ({d}%)", 4, "⚠️ Unikaj"
                elif b > 3: desc, score, stat = f"Za duży wiatr dla SUP ({b} Bft)", 3, "⛵ Trudno"
                elif b == 3: desc, score, stat = f"Wiatr w granicach 3 Bft (wymagająco)", 2, "🐢 Wymagająco"
                else: desc, score, stat = f"Spokojna woda, wiatr {b} Bft, deszcz {d}%", 1, "✅ Idealne"
                sup_data.append({"Godzina": t, "Ocena": score, "Status": stat, "Opis": desc})
            draw_interactive_chart(
                sup_data, 
                ['🌙 Noc / Zmierzch', '⚠️ Unikaj', '⛵ Trudno', '🐢 Wymagająco', '✅ Idealne'], 
                ['#ab82ff', '#ff3333', '#ff9900', '#00bfff', '#00ffcc'], 
                "🏄 Ocena SUP"
            )

            # 3. Plażowanie
            beach_data = []
            for t, tm, b, d, c, h, uv in zip(times, temp, w_bft, rain, clouds, hours, day_uvs):
                h_now_eval = int(t[:2])
                if h_now_eval > max_beach_hour or h_now_eval < 9:
                    desc, score, stat = "Po zachodzie słońca lub wcześnie rano", 0.4, "🌙 Po zachodzie słońca"
                elif d >= 50 or tm < 16 or b >= 5:
                    desc, score, stat = f"Chłodno ({tm}°C), uciążliwy wiatr ({b} Bft) lub deszcz", 1, "⚠️ Unikaj / Chłodno"
                elif c >= 70:
                    desc, score, stat = f"Duże zachmurzenie ({c}%)", 2, "☁️ Duże zachmurzenie"
                elif b > 3 or (30 <= c < 70):
                    desc, score, stat = f"Umiarkowanie (chmury {c}%, wiatr {b} Bft)", 3, "⛅ Umiarkowanie"
                else:
                    desc, score, stat = f"Ciepło ({tm}°C), słońce (UV: {uv}), słaby wiatr", 4, "☀️ Idealne słońce"
                beach_data.append({"Godzina": t, "Ocena": score, "Status": stat, "Opis": desc})
            draw_interactive_chart(
                beach_data, 
                ['🌙 Po zachodzie słońca', '⚠️ Unikaj / Chłodno', '☁️ Duże zachmurzenie', '⛅ Umiarkowanie', '☀️ Idealne słońce'], 
                ['#ab82ff', '#ff3333', '#a9a9a9', '#ff9900', '#00ffcc'], 
                "🏖️ Ocena plażowania"
            )

            st.subheader("Szczegóły godzinowe")
            df = pd.DataFrame({
                "Godzina": times, 
                "Wiatr": [f"{b} Bft" for b in w_bft], 
                "Kierunek": w_dir, 
                "Szkwały": [f"{s} Bft" for s in s_bft], 
                "Temp": [f"{round(t, 1)}°C" for t in temp], 
                "UV": [round(uv, 1) for uv in day_uvs],
                "Chmury": [f"{c}%" for c in clouds], 
                "Deszcz (%)": rain
            })
            st.dataframe(df, use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("📅 Kafelkowa prognoza na 7 dni")
            daily = data['daily']
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
