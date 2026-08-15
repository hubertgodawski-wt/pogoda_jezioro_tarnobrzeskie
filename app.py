import streamlit as st
import requests
import pandas as pd
import altair as alt

st.set_page_config(page_title="Woda Tarnobrzeg", page_icon="🌊", layout="wide")

st.title("🌊 Warunki na wodzie")
st.link_button("🚗 Sprawdź korki dojazdowe", "https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie")

LAT = "50.555"
LON = "21.652"
url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,windspeed_10m,windgusts_10m,precipitation_probability&windspeed_unit=kn&timezone=Europe%2FWarsaw&forecast_days=2"

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
    elif kt <= 47: return 9
    elif kt <= 55: return 10
    elif kt <= 63: return 11
    else: return 12

def beaufort_opis(bft):
    opisy = {
        0: "Cisza", 1: "Zefirek", 2: "Słaby", 3: "Łagodny",
        4: "Umiarkowany", 5: "Dość silny", 6: "Silny", 7: "Wicher",
        8: "Sztorm", 9: "Silny sztorm", 10: "Gwałtowny sztorm", 11: "Huragan", 12: "Huragan"
    }
    return opisy.get(bft, "")

def ocena_aktywnosci(bft, bft_szkwal, temp, deszcz):
    oceny = {}
    if 2 <= bft <= 4 and bft_szkwal < 6: oceny["⛵ Żeglarstwo"] = "Idealnie"
    elif bft > 4 or bft_szkwal >= 6: oceny["⛵ Żeglarstwo"] = "Trudno (refowanie)"
    else: oceny["⛵ Żeglarstwo"] = "Słaby wiatr"
    
    if bft <= 1: oceny["🏄 SUP"] = "Idealnie"
    elif bft == 2: oceny["🏄 SUP"] = "Wymagająco"
    else: oceny["🏄 SUP"] = "Niebezpiecznie"
    
    if temp >= 20 and bft <= 2 and deszcz < 30: oceny["🏖️ Plażowanie"] = "Idealnie"
    elif temp < 18 or deszcz >= 50: oceny["🏖️ Plażowanie"] = "Unikaj (deszcz/chłód)"
    else: oceny["🏖️ Plażowanie"] = "Wietrznie"
    
    return oceny

def ocena_zeglarska_punktowa(bft, bft_szkwal, deszcz):
    """Przelicza warunki żeglarskie na punkty od 0 do 3 do wykresu"""
    if bft_szkwal >= 6 or deszcz >= 60:
        return 1, "Trudno / Szkwały"
    elif 2 <= bft <= 4 and bft_szkwal < 6 and deszcz < 40:
        return 3, "Idealnie"
    elif bft == 1 or bft == 5:
        return 2, "Można pływać"
    else:
        return 0, "Słaby wiatr"

try:
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        hourly = data['hourly']
        
        current_time_str = pd.Timestamp.now(tz='Europe/Warsaw').strftime('%Y-%m-%dT%H:00')
        
        if current_time_str in hourly['time']:
            start_idx = hourly['time'].index(current_time_str)
        else:
            start_idx = 0
            
        times = hourly['time'][start_idx:start_idx+12]
        wiatr_kt = hourly['windspeed_10m'][start_idx:start_idx+12]
        szkwal_kt = hourly['windgusts_10m'][start_idx:start_idx+12]
        temp = hourly['temperature_2m'][start_idx:start_idx+12]
        deszcz = hourly['precipitation_probability'][start_idx:start_idx+12]
        
        formatted_times = [t[-5:] for t in times]
        
        wiatr_bft = [knots_to_beaufort(w) for w in wiatr_kt]
        szkwal_bft = [knots_to_beaufort(s) for s in szkwal_kt]
        
        st.subheader("Ocena warunków (na teraz)")
        oceny = ocena_aktywnosci(wiatr_bft[0], szkwal_bft[0], temp[0], deszcz[0])
        
        cols = st.columns(3)
        for i, (aktywnosc, ocena) in enumerate(oceny.items()):
            cols[i].metric(aktywnosc, ocena)
            
        najlepszy_sup = None
        najlepszy_zeglarz = None
        min_bft_sup = 99
        najlepszy_wynik_zeglarz = -1
        
        for t, b, bs, d in zip(formatted_times, wiatr_bft, szkwal_bft, deszcz):
            if b < min_bft_sup and d < 40:
                min_bft_sup = b
                najlepszy_sup = t
            if 2 <= b <= 4 and bs < 6 and d < 30:
                score = 10 - abs(3 - b)
                if score > najlepszy_wynik_zeglarz:
                    najlepszy_wynik_zeglarz = score
                    najlepszy_zeglarz = t

        st.info(f"💡 **Sugerowane okno czasowe na dziś:**\n\n"
                f"🏄 **Najlepszy moment na SUP:** ok. **{najlepszy_sup if najlepszy_sup else formatted_times[0]}**\n\n"
                f"⛵ **Najlepszy moment na żagle:** ok. **{najlepszy_zeglarz if najlepszy_zeglarz else 'brak idealnych warunków'}**")
        
        st.divider()
        
        # --- NOWOŚĆ: DEDYKOWANY WYKRES WARUNKÓW ŻEGLARSKICH ---
        st.subheader("⛵ Ocena warunków żeglarskich godzinowo")
        
        sailing_data = []
        for t, b, bs, d in zip(formatted_times, wiatr_bft, szkwal_bft, deszcz):
            punkty, status = ocena_zeglarska_punktowa(b, bs, d)
            sailing_data.append({"Godzina": t, "Ocena": punkty, "Status": status})
            
        sail_df = pd.DataFrame(sailing_data)
        
        chart_sailing = alt.Chart(sail_df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X('Godzina:N', title='Godzina', sort=None),
            y=alt.Y('Ocena:Q', title='Ocena', scale=alt.Scale(domain=[0, 3])),
            color=alt.Color('Status:N', title='Warunki', scale=alt.Scale(
                domain=['Idealnie', 'Można pływać', 'Trudno / Szkwały', 'Słaby wiatr'],
                range=['#2ca02c', '#1f77b4', '#ff7f0e', '#7f7f7f']
            )),
            tooltip=['Godzina', 'Status']
        ).properties(height=180)
        
        st.altair_chart(chart_sailing, use_container_width=True)
        # -----------------------------------------------------
        
        st.subheader("Wiatr i Szkwały (Skala Beauforta)")
        wind_df = pd.DataFrame({
            "Godzina": formatted_times * 2,
            "Beaufort (Bft)": wiatr_bft + szkwal_bft,
            "Typ": ["Wiatr (Bft)"] * len(wiatr_bft) + ["Szkwały (Bft)"] * len(szkwal_bft)
        })
        
        chart_wind = alt.Chart(wind_df).mark_area(opacity=0.4).encode(
            x=alt.X('Godzina:N', title='Godzina', sort=None),
            y=alt.Y('Beaufort (Bft):Q', title='Skala Beauforta', scale=alt.Scale(domain=[0, 12])),
            color=alt.Color('Typ:N', title='', scale=alt.Scale(range=['#1f77b4', '#ff7f0e']))
        ).properties(height=200)
        
        st.altair_chart(chart_wind, use_container_width=True)
        
        st.subheader("Temperatura i Szansa Deszczu")
        env_df = pd.DataFrame({
            "Godzina": formatted_times * 2,
            "Wartość": [round(t, 1) for t in temp] + deszcz,
            "Parametr": ["Temperatura (°C)"] * len(temp) + ["Szansa deszczu (%)"] * len(deszcz)
        })
        
        chart_env = alt.Chart(env_df).mark_line(strokeWidth=3).encode(
            x=alt.X('Godzina:N', title='Godzina', sort=None),
            y=alt.Y('Wartość:Q', title='°C / %'),
            color=alt.Color('Parametr:N', title='', scale=alt.Scale(range=['#2ca02c', '#d62728']))
        ).properties(height=180)
        
        st.altair_chart(chart_env, use_container_width=True)
        
        st.subheader("Szczegóły godzinowe")
        df = pd.DataFrame({
            "Godzina": formatted_times, 
            "Wiatr": [f"{b} Bft ({beaufort_opis(b)})" for b in wiatr_bft], 
            "Szkwały": [f"{bs} Bft" for bs in szkwal_bft], 
            "Temp (°C)": [round(t, 1) for t in temp],
            "Deszcz (%)": deszcz
        })
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.error("Błąd pobierania danych pogodowych z serwerów Open-Meteo.")
except Exception as e:
    st.error(f"Wystąpił nieoczekiwany problem: {e}")
