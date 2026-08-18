import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

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

@st.cache_data(ttl=900, show_spinner=False)
def fetch_weather_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,apparent_temperature,windspeed_10m,windgusts_10m,winddirection_10m,precipitation_probability,precipitation,cloudcover,cape,uv_index&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,sunrise,sunset&windspeed_unit=kn&timezone=Europe%2FWarsaw&forecast_days=7"
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
    if not hours: return "Brak odpowiednich okienek"
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
        'Kierunek_Str': [f"{degrees_to_cardinal(d)[0]} {degrees_to_cardinal(d)[1]}" for d in hourly['winddirection_10m'][start_idx : start_idx+12]],
        'Kierunek': [degrees_to_cardinal(d)[0] for d in hourly['winddirection_10m'][start_idx : start_idx+12]],
        'Temp': hourly['temperature_2m'][start_idx : start_idx+12],
        'Odczuwalna': hourly['apparent_temperature'][start_idx : start_idx+12],
        'Deszcz_Prob': hourly['precipitation_probability'][start_idx : start_idx+12],
        'Deszcz_mm': hourly['precipitation'][start_idx : start_idx+12],
        'Chmury': hourly['cloudcover'][start_idx : start_idx+12],
        'CAPE': hourly['cape'][start_idx : start_idx+12] if 'cape' in hourly else [0]*12,
        'UV': hourly['uv_index'][start_idx : start_idx+12] if 'uv_index' in hourly else [0]*12
    })

    def eval_sail(row):
        w, s, rain, rain_prob = row['Wiatr_Bft'], row['Szkwały_Bft'], row['Deszcz_mm'], row['Deszcz_Prob']
        
        if s >= 6: score = 0.5
        elif w >= 5: score = 3.0
        elif 2 <= w <= 4: score = 4.0
        elif w == 1: score = 2.0
        else: score = 1.0

        if s >= 6: return score, "⚠️ Niebezpiecznie", f"Szkwały {s} Bft"
        if rain > 1.0: return max(0.5, score - 1.5), "🌧️ Ulewa", f"Wiatr {w} Bft, ale ulewa ({rain} mm/h)"
        if rain > 0: return max(0.5, score - 1.0), "🌦️ Pada deszcz", f"Wiatr {w} Bft, mokro ({rain} mm/h)"
        if w >= 5: return score, "⛵ Wymagający", f"Silny wiatr {w} Bft"
        if 2 <= w <= 4: return score, "✅ Idealne", f"Optymalny wiatr {w} Bft"
        if w == 1: return score, "🐢 Zbyt słabo", f"Słaby wiatr ({w} Bft)"
        return score, "😶 Cisza", "Flauta"
        
    def eval_sup(row):
        h = row['Czas'].hour
        w, rain, rain_prob = row['Wiatr_Bft'], row['Deszcz_mm'], row['Deszcz_Prob']
        
        if h > 20 or h < 7: return 0.5, "🌙 Noc / Zmierzch", "Poza godzinami"
        
        if w > 4: score = 0.5
        elif w == 4: score = 2.0
        elif w == 3: score = 3.0
        else: score = 4.0

        if w > 4: return score, "⚠️ Unikaj", f"Zbyt silny wiatr ({w} Bft)"
        if rain > 1.0: return max(0.5, score - 1.5), "🌧️ Ulewa", f"Silny deszcz ({rain} mm/h)"
        if rain > 0: return max(0.5, score - 1.0), "🌦️ Pada deszcz", f"Wiatr ok, ale mokro ({rain} mm/h)"
        if w == 4: return score, "⛵ Trudno", f"Wiatr {w} Bft"
        if w == 3: return score, "🐢 Wymagająco", "Wiatr ok. 3 Bft"
        return score, "✅ Idealne", f"Spokojna woda ({w} Bft)"
        
    def eval_beach(row):
        if row['Czas'] > max_beach_dt or row['Czas'].hour < 9: return 0.5, "🌙 Po zachodzie słońca", "Niewłaściwa pora"
        
        temp, w, s, rain, rain_prob, clouds = row['Temp'], row['Wiatr_Bft'], row['Szkwały_Bft'], row['Deszcz_mm'], row['Deszcz_Prob'], row['Chmury']

        if temp < 16 or s >= 5: return 1.0, "⚠️ Unikaj / Chłodno", f"Chłodno ({temp}°C) lub uciążliwy wiatr"
        if rain > 1.0: return 0.5, "🌧️ Ulewa", f"Ulewa ({rain} mm/h)"
        if rain > 0: return 1.5, "🌦️ Pada deszcz", f"Deszcz ({rain} mm/h)"
        if w > 3 or (30 <= clouds < 70): return 3.0, "⛅ Umiarkowanie", "Umiarkowane warunki"
        if clouds >= 70: return 2.0, "☁️ Duże zachmurzenie", f"Chmury ({clouds}%)"
        return 4.0, "☀️ Idealne słońce", f"Ciepło, słońce (UV: {row['UV']})"

    df_12h[['Sail_Score', 'Sail_Status', 'Sail_Desc']] = df_12h.apply(eval_sail, axis=1, result_type="expand")
    df_12h[['SUP_Score', 'SUP_Status', 'SUP_Desc']] = df_12h.apply(eval_sup, axis=1, result_type="expand")
    df_12h[['Beach_Score', 'Beach_Status', 'Beach_Desc']] = df_12h.apply(eval_beach, axis=1, result_type="expand")

    curr = df_12h.iloc[0]

    st.markdown("---")
    st.subheader("📌 Aktualnie nad wodą i ostrzeżenia na dziś")
    
    warnings_critical = []
    warnings_standard = []

    storm_df = df_12h[(df_12h['CAPE'] >= 300) & (df_12h['Deszcz_Prob'] > 40)]
    if not storm_df.empty: warnings_critical.append(f"⚡ **OSTRZEŻENIE BURZOWE:** Ryzyko wyładowań od godz. {storm_df['Godzina'].iloc[0]}. Zejdź z wody!")

    gust_df = df_12h[df_12h['Szkwały_Bft'] >= 6]
    if not gust_df.empty: warnings_critical.append(f"⛵ **OSTRZEŻENIE ŻEGLARSKIE:** Szkwały ≥ 6 Bft od godz. {gust_df['Godzina'].iloc[0]}.")

    rain_df = df_12h[df_12h['Deszcz_mm'] > 1.0]
    if not rain_df.empty: warnings_standard.append(f"🌧️ **OSTRZEŻENIE O OPADACH:** Zapowiadany uciążliwy deszcz od godz. {rain_df['Godzina'].iloc[0]}.")

    sup_wind = df_12h[df_12h['Wiatr_Bft'] >= 4]
    if not sup_wind.empty: warnings_standard.append(f"🏄 **OSTRZEŻENIE SUP (SILNY WIATR):** Wiatr ≥ 4 Bft od godz. {sup_wind['Godzina'].iloc[0]}.")

    offshore = df_12h[(df_12h['Wiatr_Bft'] >= 3) & (df_12h['Kierunek'].isin(["E", "ENE", "ESE", "SE"]))]
    if not offshore.empty: warnings_standard.append(f"🏄 **UWAGA SUP (WIATR ODBRZEGOWY):** Wiatr wschodni od godz. {offshore['Godzina'].iloc[0]}.")

    high_uv = df_12h[df_12h['UV'] >= 7]
    if not high_uv.empty: warnings_standard.append(f"☀️ **EKSTREMALNE UV:** Indeks UV ≥ 7 od godz. {high_uv['Godzina'].iloc[0]}.")

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
    m_col4.metric("Deszcz (Teraz)", f"{curr['Deszcz_mm']} mm/h")
    
    st.markdown("---")

    tab1, tab2 = st.tabs(["Dziś (godzinowo)", "Prognoza na 7 dni"])
    
    with tab1:
        st.caption(f"🌅 Wschód słońca: **{sunrise_dt.strftime('%H:%M')}** | Zachód słońca: **{sunset_dt.strftime('%H:%M')}**")
        st.info("👆 **Wskazówka:** Kliknij (tapnij) dowolny słupek wykresu, aby zobaczyć szczegóły poniżej.")

        # --- CAŁKOWICIE NOWY SPOSÓB RYSOWANIA WYKRESÓW (Słupki + Emotki) ---
        def draw_chart(df, score_col, status_col, desc_col, title, sel_name):
            chart_df = df[['Godzina', score_col, status_col, desc_col]].copy()
            chart_df.columns = ['Godzina', 'Ocena', 'Status', 'Opis']
            
            # Ekstrakcja emotki ze statusu (wyciąga pierwszy znak, czyli np. "☀️" z "☀️ Idealne słońce")
            chart_df['Emoji'] = chart_df['Status'].apply(lambda x: x.split(' ')[0])
            
            st.subheader(title)
            click_sel = alt.selection_point(name=sel_name, fields=['Godzina'], on='click', empty='none')
            
            # Wspólna podstawa wykresu
            base = alt.Chart(chart_df).encode(
                x=alt.X('Godzina:N', title='Godzina'),
                y=alt.Y('Ocena:Q', scale=alt.Scale(domain=[0, 4.5]), title='Ocena (4=Najlepiej)'), # Domenę dajemy do 4.5, aby zmieściła się emotka
                tooltip=['Godzina', 'Status', 'Opis']
            )
            
            # Jednolite słupki
            bars = base.mark_bar(
                color='#3b82f6', # Elegancki błękitny kolor
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
                size=22 # Odpowiednia szerokość
            ).encode(
                opacity=alt.condition(click_sel, alt.value(1.0), alt.value(0.4))
            ).add_params(click_sel)
            
            # Emotki jako etykiety nad słupkami
            emojis = base.mark_text(
                align='center',
                baseline='bottom',
                dy=-3, # Lekko podnosimy ikonę nad słupek
                fontSize=20 # Duża, czytelna wielkość
            ).encode(
                text='Emoji:N',
                opacity=alt.condition(click_sel, alt.value(1.0), alt.value(0.4))
            )
            
            # Łączymy warstwy (słupki + emotki)
            chart = alt.layer(bars, emojis).properties(
                height=180, background='transparent'
            ).configure_view(stroke=None)
            
            event = st.altair_chart(chart, use_container_width=True, theme="streamlit", on_select="rerun")
            
            sel_data = getattr(event.selection, sel_name, [])
            if len(sel_data) > 0:
                w_godzina = sel_data[0]["Godzina"]
                opis = chart_df[chart_df["Godzina"] == w_godzina]["Opis"].values[0]
                status = chart_df[chart_df["Godzina"] == w_godzina]["Status"].values[0]
                st.info(f"👉 **Godzina {w_godzina}** | {status} - {opis}")

        # Rysowanie wykresów z nową funkcją (bez definiowania tablic kolorów!)
        draw_chart(df_12h, 'Sail_Score', 'Sail_Status', 'Sail_Desc', "⛵ Ocena żeglarska", "sel_sail")
        draw_chart(df_12h, 'SUP_Score', 'SUP_Status', 'SUP_Desc', "🏄 Ocena SUP", "sel_sup")
        draw_chart(df_12h, 'Beach_Score', 'Beach_Status', 'Beach_Desc', "🏖️ Ocena plażowania", "sel_beach")

        with st.expander("📊 Tabela: Szczegółowe dane godzinowe (kliknij, aby rozwinąć)"):
            display_df = df_12h[['Godzina', 'Wiatr_Bft', 'Kierunek_Str', 'Szkwały_Bft', 'Temp', 'UV', 'Chmury', 'Deszcz_mm', 'Deszcz_Prob']].copy()
            display_df.columns = ["Godzina", "Wiatr (Bft)", "Kierunek", "Szkwały (Bft)", "Temp (°C)", "UV", "Chmury (%)", "Deszcz (mm)", "Szansa (%)"]
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
                h_rain_prob = hourly['precipitation_probability'][idx]
                h_rain_mm = hourly['precipitation'][idx] 
                h_val = int(hourly['time'][idx][11:13])
                
                if 8 <= h_val <= 20 and h_rain_mm <= 1.0:
                    if h_bft <= 2 and h_rain_prob < 50: sup_hours.append(h_val)
                    if 2 <= h_bft <= 4 and h_gust < 6 and h_rain_prob < 50: sail_hours.append(h_val)
                        
            sup_okienka = get_windows(sup_hours)
            zagiel_okienka = get_windows(sail_hours)

            if bft >= 6:
                status, box_color = "⚠️ Niebezpiecznie", "red"
                uzasadnienie = f"Wiatr w porywach osiągnie ryzykowny poziom **{bft} Bft**."
            elif r > 5:
                status, box_color = "🌧️ Deszczowo", "blue"
                uzasadnienie = f"Mokry dzień (suma opadów: **{r} mm**). Dłuższe pływanie będzie niekomfortowe."
            elif len(sail_hours) >= 4 and len(sup_hours) >= 4:
                status, box_color = "🌟 Rewelacyjny dzień", "green"
                uzasadnienie = "Brak ulew, świetny wiatr i długie okienka pogodowe dla wszystkich."
            elif len(sail_hours) >= 4:
                status, box_color = "⛵ Świetny na żagle", "green"
                uzasadnienie = "Stabilny wiatr bez ulew. Wymarzona pogoda dla żeglarzy."
            elif len(sup_hours) >= 4:
                status, box_color = "🏄 Świetny na SUP", "green"
                uzasadnienie = "Spokojna woda bez ulew i silnego wiatru."
            elif len(sail_hours) > 0 or len(sup_hours) > 0:
                status, box_color = "⛅ Krótkie okienka", "orange"
                uzasadnienie = "Zmienny wiatr lub opady. Zejście na wodę możliwe tylko przez krótki czas."
            else:
                status, box_color = "😶 Brak warunków", "gray"
                uzasadnienie = "Brak bezpiecznych okienek (zbyt silny wiatr, ulewy lub całkowita flauta)."

            with st.container(border=True):
                c1, c2, c3 = st.columns([1.5, 3, 1.5])
                with c1: st.markdown(f"### {t_date}")
                with c2:
                    st.write(f"🌡️ Max: **{temp_max}°C** | 💨 Wiatr: **{bft} Bft** | 🌧️ Deszcz: **{r} mm**")
                    st.caption(f"🌅 {sunrise} | 🌇 {sunset}")
                with c3:
                    if box_color == "green": st.success(status)
                    elif box_color == "red": st.error(status)
                    elif box_color == "orange": st.warning(status)
                    elif box_color == "blue": st.info(status)
                    else: st.info(status)
                
                with st.expander("🔎 Kliknij, by zobaczyć uzasadnienie i możliwe okienka"):
                    st.markdown(f"**Ocena:** {uzasadnienie}")
                    st.markdown(f"🏄 **Godziny na SUP:** {sup_okienka}")
                    st.markdown(f"⛵ **Godziny na Żagle:** {zagiel_okienka}")

except Exception as e:
    st.error(f"Wystąpił problem z połączeniem z serwerem pogodowym. Spróbuj odświeżyć stronę za chwilę. (Szczegóły: {e})")
