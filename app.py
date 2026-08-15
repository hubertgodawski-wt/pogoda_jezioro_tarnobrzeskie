import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

# Konfiguracja strony
st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

# CSS: Ukrycie natywnych pasków Streamlita, by przypominało aplikację mobilną
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Czas
current_time_warsaw = pd.Timestamp.now(tz='Europe/Warsaw')
formatted_date = current_time_warsaw.strftime('%d.%m.%Y')
formatted_clock = current_time_warsaw.strftime('%H:%M')
current_dt = current_time_warsaw.tz_localize(None) # Do obliczeń zachodu słońca

st.title("🌊 Jezioro Tarnobrzeskie")
st.caption(f"📅 **{formatted_date}** | ⏰ **{formatted_clock}**")

btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 1])
with btn_col1:
    st.link_button("🚗 Dojazd", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie", use_container_width=True)
with btn_col2:
    st.link_button("📹 Kamery", "https://mosir.tarnobrzeg.pl/jezioro-tarnobrzeskie/kamery-on-line/", use_container_width=True)
with btn_col3:
    if st.button("🔄", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

LAT, LON = "50.555", "21.652"

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

def get_clothing_advice(app_temp):
    if app_temp < 15:
        return "Konieczna długa gruba pianka (np. 4/3mm), buty neoprenowe i wiatrówka."
    elif app_temp < 20:
        return "Sprawdzi się krótka pianka (shorty) lub grubsza lycra i szorty."
    elif app_temp < 25:
        return "Lycra UV, szorty kąpielowe. Woda może jeszcze chłodzić przy upadku."
    else:
        return "Tylko strój kąpielowy, ale KONIECZNIE Lycra z filtrem UV i czapka!"

@st.cache_data(ttl=900)
def fetch_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,apparent_temperature,windspeed_10m,windgusts_10m,winddirection_10m,precipitation_probability,cloudcover,cape,uv_index,surface_pressure,visibility&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,sunrise,sunset&windspeed_unit=kn&timezone=Europe%2FWarsaw&forecast_days=8"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    return None

# Spinner ładowania w trakcie pobierania danych
with st.spinner('📡 Pobieranie pomiarów...'):
    data = fetch_weather()

if data:
    hourly = data['hourly']
    daily = data['daily']
    
    curr = current_time_warsaw.strftime('%Y-%m-%dT%H:00')
    try:
        start = hourly['time'].index(curr)
    except ValueError:
        start = 0 
    
    current_temp = hourly['temperature_2m'][start]
    current_app_temp = hourly['apparent_temperature'][start]
    current_wind_kt = hourly['windspeed_10m'][start]
    current_wind_bft = knots_to_beaufort(current_wind_kt)
    current_gust_bft = knots_to_beaufort(hourly['windgusts_10m'][start])
    curr_dir_text, curr_dir_arrow = degrees_to_cardinal(hourly['winddirection_10m'][start])
    current_rain = hourly['precipitation_probability'][start]
    current_cloud = hourly['cloudcover'][start]
    current_uv = hourly['uv_index'][start]
    current_vis = hourly['visibility'][start]
    
    day_winds = hourly['windspeed_10m'][start:start+12]
    day_gusts = hourly['windgusts_10m'][start:start+12]
    day_rains = hourly['precipitation_probability'][start:start+12]
    day_capes = hourly['cape'][start:start+12]
    
    max_wind_trend = max(day_winds)
    max_gust_trend = max(day_gusts)
    max_cape_trend = max(day_capes) if day_capes else 0
    max_temp_today = max(hourly['temperature_2m'][start:start+12])
    
    sunset_dt = datetime.fromisoformat(daily['sunset'][0])
    
    # Toasty z przypomnieniami
    if current_temp > 25:
        st.toast("Pamiętaj o butelce wody! Dziś jest gorąco. 💧", icon="🔥")
    if current_app_temp < 15:
        st.toast("Woda i wiatr mocno chłodzą. Załóż piankę! 🏄‍♂️", icon="👕")
    if current_uv >= 6:
        st.toast("Silne promieniowanie słońca. Użyj kremu z filtrem! ☀️", icon="🧴")

    st.markdown("---")
    
    # WERDYKT NA TERAZ (Hero Section)
    st.markdown("### 🚦 Werdykt na teraz:")
    warnings = []
    
    if max_gust_trend >= 22 or knots_to_beaufort(max_gust_trend) >= 6:
        warnings.append("🚨 **ŻEGLARSTWO:** Szkwały powyżej 6 Bft! Zostań na brzegu.")
    if max_cape_trend >= 300:
        warnings.append("⚡ **BURZE:** Wysokie CAPE. Zwiększone ryzyko wyładowań.")
    if start >= 3 and (hourly['surface_pressure'][start] - hourly['surface_pressure'][start-3]) <= -3:
        warnings.append("📉 **CIŚNIENIE:** Szybki spadek. Zbliża się załamanie pogody.")
    if curr_dir_text in ["W", "WNW", "WSW"] and current_wind_bft >= 2:
        warnings.append("🚩 **SUP:** Wiatr ODBRZEGOWY z głównej plaży! Uważaj na zniesienie.")
    if current_vis < 2000:
        warnings.append("🌫️ **WIDZIALNOŚĆ:** Mgła lub zamglenie na wodzie.")
    if current_uv >= 7:
        warnings.append("🔥 **UV:** Bardzo silne promieniowanie (Indeks 7+).")

    if warnings:
        st.error("🔴 **UWAGA! WYSTĘPUJĄ TRUDNE WARUNKI:**")
        for warn in warnings:
            st.markdown(f"- {warn}")
    elif current_wind_bft <= 2 and current_rain < 30:
        st.success("🟢 **IDEALNIE!** Świetne warunki na SUP i plażowanie.")
    elif 2 < current_wind_bft <= 4 and current_rain < 30:
        st.info("🟡 **ŻAGLOWA POGODA!** Świetnie na jacht, na SUP-ie będzie wymagać siły.")
    else:
        st.warning("🟠 **UMIARKOWANIE.** Zmienne warunki pogodowe. Sprawdź wykresy.")

    st.markdown("---")
    
    # Siatka 2x2 z metrykami zoptymalizowana pod Mobile
    m_col1, m_col2 = st.columns(2)
    m_col1.metric("Temperatura", f"{round(current_temp, 1)}°C", f"Odczuwalna: {round(current_app_temp, 1)}°C")
    m_col2.metric("Wiatr", f"{current_wind_bft} Bft ({curr_dir_text} {curr_dir_arrow})", f"Szkwały: {current_gust_bft} Bft")
    
    m_col3, m_col4 = st.columns(2)
    m_col3.metric("Indeks UV", f"{round(current_uv, 1)}", f"Chmury: {current_cloud}%")
    m_col4.metric("Deszcz", f"{current_rain}%")
    
    # Odliczanie do zachodu słońca
    if current_dt < sunset_dt:
        diff = sunset_dt - current_dt
        hrs = diff.seconds // 3600
        mins = (diff.seconds % 3600) // 60
        st.info(f"⏳ Do zachodu słońca pozostało: **{hrs} godz. {mins} min.**")
    else:
        st.info("🌙 Słońce już zaszło.")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["Dziś (godzinowo)", "Prognoza 7 dni", "👕 Sprzęt i Złota Godzina"])
    
    with tab1:
        raw_times = hourly['time'][start:start+12]
        times = [t[-5:] for t in raw_times]
        hours = [int(t[11:13]) for t in raw_times]
        
        w_bft = [knots_to_beaufort(w) for w in day_winds]
        s_bft = [knots_to_beaufort(s) for s in hourly['windgusts_10m'][start:start+12]]
        dirs_raw = [degrees_to_cardinal(d) for d in hourly['winddirection_10m'][start:start+12]]
        w_dir = [f"{d[0]} {d[1]}" for d in dirs_raw]
        temp = hourly['temperature_2m'][start:start+12]
        app_temp = hourly['apparent_temperature'][start:start+12]
        rain = day_rains
        clouds = hourly['cloudcover'][start:start+12]
        
        def draw_chart(chart_data, domain, colors, title):
            st.subheader(title)
            st.altair_chart(alt.Chart(pd.DataFrame(chart_data)).mark_bar().encode(
                x=alt.X('Godzina:N', sort=None), 
                y=alt.Y('Ocena:Q', scale=alt.Scale(domain=[0, 4])), 
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
        
        draw_chart(sail_data, ['⚠️ Niebezpiecznie', '⛵ Wymagający', '✅ Idealne', '🐢 Zbyt słabo', '😶 Cisza'], ['#d62728', '#ff7f0e', '#2ca02c', '#87CEEB', '#808080'], "⛵ Ocena dla żeglarzy")

        sup_data = []
        for t, b, d, h, dir_txt in zip(times, w_bft, rain, hours, [d[0] for d in dirs_raw]):
            if h < 7 or h > 20: sup_data.append({"Godzina": t, "Ocena": 0, "Status": "🌙 Noc / Zmierzch"})
            elif d >= 50: sup_data.append({"Godzina": t, "Ocena": 4, "Status": "⚠️ Unikaj (Deszcz)"})
            elif b > 3 or (dir_txt in ["W", "WNW", "WSW"] and b >= 2): sup_data.append({"Godzina": t, "Ocena": 3, "Status": "🚩 Trudno (Odbrzegowy)"})
            elif b == 3: sup_data.append({"Godzina": t, "Ocena": 2, "Status": "🐢 Wymagająco"})
            else: sup_data.append({"Godzina": t, "Ocena": 1, "Status": "✅ Idealne"})
            
        draw_chart(sup_data, ['🌙 Noc / Zmierzch', '⚠️ Unikaj (Deszcz)', '🚩 Trudno (Odbrzegowy)', '🐢 Wymagająco', '✅ Idealne'], ['#333333', '#d62728', '#ff7f0e', '#87CEEB', '#2ca02c'], "🏄 Ocena dla SUP")

        with st.expander("📊 Zobacz pełne dane tabelaryczne"):
            df = pd.DataFrame({
                "Godzina": times, 
                "Wiatr": [f"{b} Bft" for b in w_bft], 
                "Kierunek": w_dir, 
                "Szkwały": [f"{s} Bft" for s in s_bft], 
                "Temp": [f"{round(t, 1)}°C" for t in temp], 
                "Odczuwalna": [f"{round(at, 1)}°C" for at in app_temp],
                "Chmury": [f"{c}%" for c in clouds], 
                "Deszcz": [f"{r}%" for r in rain]
            })
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Prognoza na najbliższe dni")
        daily_data = []
        for i in range(7):
            w = daily['windspeed_10m_max'][i]
            r = daily['precipitation_sum'][i]
            bft = knots_to_beaufort(w)
            status = "⚠️ Niebezpiecznie" if bft>=6 or r>5 else ("⛵ Wymagający" if bft==5 else ("✅ Idealne" if 2<=bft<=4 and r<2 else ("🐢 Zbyt słabo" if bft==1 else "😶 Cisza")))
            
            day_str = datetime.fromisoformat(daily['time'][i]).strftime('%d.%m')
            
            daily_data.append({
                "Data": f"{day_str}", 
                "Temp Max": f"{round(daily['temperature_2m_max'][i], 1)}°C", 
                "Wiatr Max": f"{bft} Bft", 
                "Ocena": status,
                "Wschód": daily['sunrise'][i][-5:], 
                "Zachód": daily['sunset'][i][-5:]
            })
        st.dataframe(pd.DataFrame(daily_data), use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("👕 Asystent Ubioru na Wodę")
        st.info(f"Aktualna temperatura odczuwalna: **{round(current_app_temp, 1)}°C**. \n\n**Rekomendacja:** {get_clothing_advice(current_app_temp)}")
        
        st.markdown("---")
        st.subheader("📸 Złota Godzina (Najlepsze światło)")
        
        sunrise_dt = datetime.fromisoformat(daily['sunrise'][0])
        gh_morning_start = sunrise_dt
        gh_morning_end = sunrise_dt + timedelta(hours=1)
        gh_evening_start = sunset_dt - timedelta(hours=1)
        gh_evening_end = sunset_dt
        
        c1, c2 = st.columns(2)
        c1.success(f"🌅 Poranna: \n**{gh_morning_start.strftime('%H:%M')} - {gh_morning_end.strftime('%H:%M')}**")
        c2.success(f"🌇 Wieczorna: \n**{gh_evening_start.strftime('%H:%M')} - {gh_evening_end.strftime('%H:%M')}**")

else:
    st.error("Błąd pobierania danych. Sprawdź połączenie z internetem i odśwież stronę.")
