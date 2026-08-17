import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

# --- WŁASNY CSS ---
st.markdown("""
    <style>
    [data-testid="stMetricLabel"] { font-size: 1.1rem !important; font-weight: 600 !important; }
    [data-testid="stMetricValue"] { font-size: 2.3rem !important; font-weight: 700 !important; }
    [data-testid="stMetricDelta"] { font-size: 1rem !important; }
    .streamlit-expanderHeader { font-weight: bold; color: #33ccff; }
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
    st.link_button("📹 Kamery online", "https://mosir.tarnobrzeg.pl/jezioro-tarnobrzeskie/kamery-on-line/", use_container_width=True)

LAT, LON = "50.555", "21.652"

# --- BEZPIECZNY CACHE ---
@st.cache_data(ttl=900, show_spinner=False)
def fetch_weather_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,apparent_temperature,windspeed_10m,windgusts_10m,winddirection_10m,precipitation_probability,cloudcover,cape,uv_index&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,sunrise,sunset&windspeed_unit=kn&timezone=Europe%2FWarsaw&forecast_days=7"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

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

def get_windows(hours):
    if not hours: return "Brak odpowiednich warunków"
    windows = []
    start, prev = hours[0], hours[0]
    for h in hours[1:]:
        if h == prev + 1: prev = h
        else:
            windows.append(f"{start:02d}:00-{prev+1:02d}:00")
            start, prev = h, h
    windows.append(f"{start:02d}:00-{prev+1:02d}:00")
    return " | ".join(windows)

try:
    data = fetch_weather_data(LAT, LON)
    hourly, daily = data['hourly'], data['daily']
    
    now_naive = current_time_warsaw.tz_localize(None).replace(minute=0, second=0, microsecond=0)
    dt_times = pd.to_datetime(hourly['time'])
    start_idx = abs(dt_times - now_naive).argmin()
    
    sunrise_dt = datetime.fromisoformat(daily['sunrise'][0])
    sunset_dt = datetime.fromisoformat(daily['sunset'][0])
    max_beach_dt = sunset_dt + timedelta(minutes=30)
    
    df_12h = pd.DataFrame({
        'Czas': dt_times[start_idx : start_idx+12],
        'Godzina': [t[11:16] for t in hourly['time'][start_idx : start_idx+12]],
        'Wiatr_Bft': [knots_to_beaufort(w) for w in hourly['windspeed_10m'][start_idx : start_idx+12]],
        'Szkwały_Bft': [knots_to_beaufort(w) for w in hourly['windgusts_10m'][start_idx : start_idx+12]],
        'Kierunek': [degrees_to_cardinal(d)[0] for d in hourly['winddirection_10m'][start_idx : start_idx+12]],
        'Kierunek_Str': [f"{degrees_to_cardinal(d)[0]} {degrees_to_cardinal(d)[1]}" for d in hourly['winddirection_10m'][start_idx : start_idx+12]],
        'Temp': hourly['temperature_2m'][start_idx : start_idx+12],
        'Odczuwalna': hourly['apparent_temperature'][start_idx : start_idx+12],
        'Deszcz': hourly['precipitation_probability'][start_idx : start_idx+12],
        'Chmury': hourly['cloudcover'][start_idx : start_idx+12],
        'CAPE': hourly['cape'][start_idx : start_idx+12] if 'cape' in hourly else [0]*12,
        'UV': hourly['uv_index'][start_idx : start_idx+12] if 'uv_index' in hourly else [0]*12
    })

    def eval_sail(row):
        if row['Szkwały_Bft'] >= 6 or row['Deszcz'] >= 50: return 4, "⚠️ Niebezpiecznie", f"Szkwały {row['Szkwały_Bft']} Bft lub deszcz {row['Deszcz']}%"
        if row['Wiatr_Bft'] >= 5: return 3, "⛵ Wymagający", f"Wiatr wiodący {row['Wiatr_Bft']} Bft"
        if 2 <= row['Wiatr_Bft'] <= 4 and row['Szkwały_Bft'] < 6 and row['Deszcz'] < 30: return 2, "✅ Idealne", f"Wiatr {row['Wiatr_Bft']} Bft, szkwały {row['Szkwały_Bft']} Bft"
        if row['Wiatr_Bft'] == 1: return 1, "🐢 Zbyt słabo", f"Słaby wiatr ({row['Wiatr_Bft']} Bft)"
        return 0.4, "😶 Cisza", "Cisza na wodzie"
        
    def eval_sup(row):
        h = row['Czas'].hour
        if h > 20 or h < 7: return 0.4, "🌙 Noc / Zmierzch", "Poza godzinami dozwolonymi"
        if row['Deszcz'] >= 50: return 4, "⚠️ Unikaj", f"Ryzyko deszczu ({row['Deszcz']}%)"
        if row['Wiatr_Bft'] > 3: return 3, "⛵ Trudno", f"Silny wiatr ({row['Wiatr_Bft']} Bft)"
        if row['Wiatr_Bft'] == 3: return 2, "🐢 Wymagająco", "Wiatr w granicach 3 Bft"
        return 1, "✅ Idealne", f"Spokojna woda ({row['Wiatr_Bft']} Bft)"
        
    def eval_beach(row):
        if row['Czas'] > max_beach_dt or row['Czas'].hour < 9: return 0.4, "🌙 Po zachodzie słońca", "Niewłaściwa pora"
        if row['Deszcz'] >= 50 or row['Temp'] < 16 or row['Szkwały_Bft'] >= 5: return 1, "⚠️ Unikaj / Chłodno", f"Chłodno ({row['Temp']}°C), wiatr lub deszcz"
        if row['Chmury'] >= 70: return 2, "☁️ Duże zachmurzenie", f"Chmury ({row['Chmury']}%)"
        if row['Wiatr_Bft'] > 3 or (30 <= row['Chmury'] < 70): return 3, "⛅ Umiarkowanie", "Umiarkowane warunki"
        return 4, "☀️ Idealne słońce", f"Ciepło, słońce (UV: {row['UV']})"

    df_12h[['Sail_Score', 'Sail_Status', 'Sail_Desc']] = df_12h.apply(eval_sail, axis=1, result_type="expand")
    df_12h[['SUP_Score', 'SUP_Status', 'SUP_Desc']] = df_12h.apply(eval_sup, axis=1, result_type="expand")
    df_12h[['Beach_Score', 'Beach_Status', 'Beach_Desc']] = df_12h.apply(eval_beach, axis=1, result_type="expand")

    curr = df_12h.iloc[0]

    st.markdown("---")
    st.subheader("📌 Aktualnie nad wodą i ostrzeżenia na dziś")
    
    warnings_critical = []
    warnings_standard = []

    storm_df = df_12h[(df_12h['CAPE'] >= 300) & (df_12h['Deszcz'] > 40)]
    if not storm_df.empty: warnings_critical.append(f"⚡ **OSTRZEŻENIE BURZOWE:** Ryzyko wyładowań od godz. {storm_df['Godzina'].iloc[0]}. Zejdź z wody!")

    gust_df = df_12h[df_12h['Szkwały_Bft'] >= 6]
    if not gust_df.empty: warnings_critical.append(f"⛵ **OSTRZEŻENIE ŻEGLARSKIE:** Szkwały ≥ 6 Bft od godz. {gust_df['Godzina'].iloc[0]}.")

    sup_wind = df_12h[df_12h['Wiatr_Bft'] >= 4]
    if not sup_wind.empty: warnings_standard.append(f"🏄 **OSTRZEŻENIE SUP (SILNY WIATR):** Wiatr ≥ 4 Bft od godz. {sup_wind['Godzina'].iloc[0]}.")

    offshore = df_12h[(df_12h['Wiatr_Bft'] >= 3) & (df_12h['Kierunek'].isin(["E", "ENE", "ESE", "SE"]))]
    if not offshore.empty: warnings_standard.append(f"🏄 **UWAGA SUP (WIATR ODBRZEGOWY):** Wiatr wschodni (≥ 3 Bft) od godz. {offshore['Godzina'].iloc[0]}.")

    beach_gust = df_12h[df_12h['Szkwały_Bft'] >= 5]
    if not beach_gust.empty: warnings_standard.append(f"🏖️ **UWAGA PLAŻA (WIATR):** Szkwały ≥ 5 Bft od godz. {beach_gust['Godzina'].iloc[0]}.")

    high_uv = df_12h[df_12h['UV'] >= 7]
    if not high_uv.empty: warnings_standard.append(f"☀️ **EKSTREMALNE UV:** Indeks UV ≥ 7 od godz. {high_uv['Godzina'].iloc[0]}.")

    sudden_change = False
    for i in range(len(df_12h) - 3):
        if df_12h['Wiatr_Bft'].iloc[i+1:i+4].max() - df_12h['Wiatr_Bft'].iloc[i] >= 3 or df_12h['Szkwały_Bft'].iloc[i+1:i+4].max() - df_12h['Szkwały_Bft'].iloc[i] >= 3:
            sudden_change = True
            break
    if sudden_change: warnings_critical.append("⚠️ **NAGŁE ZAŁAMANIE POGODY:** Spodziewany gwałtowny wzrost wiatru w najbliższym czasie!")

    if warnings_critical or warnings_standard:
        for w in warnings_critical: st.error(w)
        for w in warnings_standard: st.warning(w)
    else:
        st.success("✅ **Werdykt na teraz:** Brak ostrzeżeń. Warunki bezpieczne i stabilne.")

    m_col1, m_col2 = st.columns(2)
    m_col1.metric("Temperatura", f"{round(curr['Temp'], 1)}°C", f"Odczuwalna: {round(curr['Odczuwalna'], 1)}°C")
    m_col2.metric("Wiatr", f"{curr['Wiatr_Bft']} Bft ({curr['Kierunek_Str']})", f"Szkwały: {curr['Szkwały_Bft']} Bft")
    
    m_col3, m_col4 = st.columns(2)
    m_col3.metric("UV / Chmury", f"UV: {round(curr['UV'], 1)}", f"Chmury: {curr['Chmury']}%")
    m_col4.metric("Deszcz", f"{curr['Deszcz']}%")
    
    st.markdown("---")

    tab1, tab2 = st.tabs(["Dziś (godzinowo)", "Prognoza na 7 dni"])
    
    with tab1:
        st.caption(f"🌅 Wschód słońca: **{sunrise_dt.strftime('%H:%M')}** | Zachód słońca: **{sunset_dt.strftime('%H:%M')}**")
        st.info("👆 **Wskazówka:** Kliknij (tapnij) dowolny słupek wykresu, aby zobaczyć szczegóły poniżej.")

        # --- NAPRAWA 1: Przywrócony mechanizm tapnięcia na słupki dla telefonów ---
        def draw_chart(df, score_col, status_col, desc_col, domain, colors, title, sel_name):
            chart_df = df[['Godzina', score_col, status_col, desc_col]].copy()
            chart_df.columns = ['Godzina', 'Ocena', 'Status', 'Opis']
            
            st.subheader(title)
            click_sel = alt.selection_point(name=sel_name, fields=['Godzina'], on='click', empty='none')
            
            base = alt.Chart(chart_df).mark_bar().encode(
                x=alt.X('Godzina:N', title='Godzina'),
                y=alt.Y('Ocena:Q', scale=alt.Scale(domain=[0, 4]), title='Ocena'),
                color=alt.Color('Status:N', scale=alt.Scale(domain=domain, range=colors), title='Status'),
                tooltip=['Godzina', 'Status', 'Opis']
            ).properties(
                height=160, background='transparent'
            ).configure_view(stroke=None)
            
            chart = base.add_params(click_sel).encode(
                opacity=alt.condition(click_sel, alt.value(1), alt.value(0.7))
            )
            
            # on_select="rerun" gwarantuje wyłapanie kliknięcia na smartfonie
            event = st.altair_chart(chart, use_container_width=True, theme="streamlit", on_select="rerun")
            
            sel_data = getattr(event.selection, sel_name, [])
            if len(sel_data) > 0:
                w_godzina = sel_data[0]["Godzina"]
                opis = chart_df[chart_df["Godzina"] == w_godzina]["Opis"].values[0]
                status = chart_df[chart_df["Godzina"] == w_godzina]["Status"].values[0]
                st.info(f"👉 **Godzina {w_godzina}** | {status} - {opis}")

        draw_chart(df_12h, 'Sail_Score', 'Sail_Status', 'Sail_Desc',
                   ['⚠️ Niebezpiecznie', '⛵ Wymagający', '✅ Idealne', '🐢 Zbyt słabo', '😶 Cisza'], 
                   ['#ff3333', '#ff9900', '#00ffcc', '#00bfff', '#ab82ff'], "⛵ Ocena żeglarska", "sel_sail")

        draw_chart(df_12h, 'SUP_Score', 'SUP_Status', 'SUP_Desc',
                   ['🌙 Noc / Zmierzch', '⚠️ Unikaj', '⛵ Trudno', '🐢 Wymagająco', '✅ Idealne'], 
                   ['#ab82ff', '#ff3333', '#ff9900', '#00bfff', '#00ffcc'], "🏄 Ocena SUP", "sel_sup")

        draw_chart(df_12h, 'Beach_Score', 'Beach_Status', 'Beach_Desc',
                   ['🌙 Po zachodzie słońca', '⚠️ Unikaj / Chłodno', '☁️ Duże zachmurzenie', '⛅ Umiarkowanie', '☀️ Idealne słońce'], 
                   ['#ab82ff', '#ff3333', '#a9a9a9', '#ff9900', '#00ffcc'], "🏖️ Ocena plażowania", "sel_beach")

        with st.expander("📊 Tabela: Szczegółowe dane godzinowe (kliknij, aby rozwinąć)"):
            display_df = df_12h[['Godzina', 'Wiatr_Bft', 'Kierunek_Str', 'Szkwały_Bft', 'Temp', 'UV', 'Chmury', 'Deszcz']].copy()
            display_df.columns = ["Godzina", "Wiatr (Bft)", "Kierunek", "Szkwały (Bft)", "Temp (°C)", "UV", "Chmury (%)", "Deszcz (%)"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("📅 Kafelkowa prognoza na 7 dni")
        
        for i in range(len(daily['time'])):
            t_date = daily['time'][i]
            w = daily['windspeed_10m_max'][i]
            r = daily['precipitation_sum'][i]
            bft = knots_to_beaufort(w)
            temp_max = round(daily['temperature_2m_max'][i], 1)
            sunrise = daily['sunrise'][i][-5:]
            sunset = daily['sunset'][i][-5:]
            
            day_indices = [idx for idx, time_str in enumerate(hourly['time']) if time_str.startswith(t_date)]
            sup_hours, sail_hours = [], []
            
            for idx in day_indices:
                h_bft = knots_to_beaufort(hourly['windspeed_10m'][idx])
                h_gust = knots_to_beaufort(hourly['windgusts_10m'][idx])
                h_rain = hourly['precipitation_probability'][idx]
                h_val = int(hourly['time'][idx][11:13])
                
                if 8 <= h_val <= 20:
                    if h_bft <= 2 and h_rain < 40: sup_hours.append(h_val)
                    if 2 <= h_bft <= 4 and h_gust < 6 and h_rain < 30: sail_hours.append(h_val)
                        
            sup_okienka = get_windows(sup_hours)
            zagiel_okienka = get_windows(sail_hours)

            # --- NAPRAWA 2: Ocena dnia bazuje NA DŁUGOŚCI OKIENEK, a nie na skrajnych wartościach ---
            if bft >= 6 or r > 10:
                status, box_color = "⚠️ Niebezpiecznie", "red"
                uzasadnienie = f"Wiatr w porywach osiągnie ryzykowny poziom **{bft} Bft** lub wystąpią silne opady deszczu."
            elif len(sail_hours) >= 4 and len(sup_hours) >= 4:
                status, box_color = "🌟 Rewelacyjny dzień", "green"
                uzasadnienie = "Długie okienka pogodowe dla wszystkich sportów. Bardzo stabilne warunki."
            elif len(sail_hours) >= 4:
                status, box_color = "⛵ Świetny na żagle", "green"
                uzasadnienie = "Większość dnia z dobrym i stabilnym wiatrem, wymarzona dla żeglarzy."
            elif len(sup_hours) >= 4:
                status, box_color = "🏄 Świetny na SUP", "green"
                uzasadnienie = "Spokojna woda i sprzyjający wiatr przez większość dnia."
            elif len(sail_hours) > 0 or len(sup_hours) > 0:
                status, box_color = "⛅ Krótkie okienka", "orange"
                uzasadnienie = "Pogoda w kratkę. Warunki pozwolą na bezpieczne zejście na wodę tylko przez krótki czas."
            else:
                status, box_color = "😶 Brak warunków", "gray"
                uzasadnienie = "Brak odpowiednich okienek pogodowych w ciągu dnia (zbyt silny wiatr, deszcz lub całkowita flauta)."

            with st.container(border=True):
                c1, c2, c3 = st.columns([1.5, 3, 1.5])
                with c1: st.markdown(f"### {t_date}")
                with c2:
                    st.write(f"🌡️ Max: **{temp_max}°C** | 💨 Wiatr (Max): **{bft} Bft** | 🌧️ Deszcz: **{r} mm**")
                    st.caption(f"🌅 {sunrise} | 🌇 {sunset}")
                with c3:
                    if box_color == "green": st.success(status)
                    elif box_color == "red": st.error(status)
                    elif box_color == "orange": st.warning(status)
                    else: st.info(status)
                
                with st.expander("🔎 Kliknij, by zobaczyć uzasadnienie i dostępne okienka"):
                    st.markdown(f"**Ocena:** {uzasadnienie}")
                    st.markdown(f"🏄 **Godziny na SUP:** {sup_okienka}")
                    st.markdown(f"⛵ **Godziny na Żagle:** {zagiel_okienka}")

except Exception as e:
    st.error(f"Wystąpił problem z połączeniem z serwerem pogodowym. Spróbuj odświeżyć stronę za chwilę. (Szczegóły: {e})")
