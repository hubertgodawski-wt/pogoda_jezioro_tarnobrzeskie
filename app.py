"""Prognoza rekreacyjna dla Jeziora Tarnobrzeskiego. Uruchom: streamlit run jezioro_tarnobrzeskie.py"""
from datetime import datetime
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import requests
import streamlit as st

LAT, LON = 50.555, 21.652
TZ = ZoneInfo('Europe/Warsaw')
API = 'https://api.open-meteo.com/v1/forecast'
HOURLY = ('temperature_2m', 'apparent_temperature', 'wind_speed_10m',
          'wind_gusts_10m', 'wind_direction_10m', 'precipitation_probability',
          'precipitation', 'cloud_cover', 'uv_index', 'weather_code')
DAILY = ('sunrise', 'sunset', 'temperature_2m_max', 'temperature_2m_min',
         'precipitation_sum')

st.set_page_config(page_title='Jezioro Tarnobrzeskie | Pogoda', page_icon='🌊', layout='wide')
st.markdown('''<style>
.block-container {max-width: 1120px; padding-top: 1.3rem;}
[data-testid="stMetricValue"] {font-size: 1.75rem;}
@media(max-width: 640px) {[data-testid="stMetricValue"] {font-size: 1.45rem;}}
</style>''', unsafe_allow_html=True)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_weather():
    response = requests.get(API, params={
        'latitude': LAT, 'longitude': LON, 'timezone': 'Europe/Warsaw',
        'forecast_days': 7, 'wind_speed_unit': 'kn',
        'hourly': ','.join(HOURLY), 'daily': ','.join(DAILY),
    }, timeout=12)
    response.raise_for_status()
    return response.json()


def bft(knots):
    """Beaufort według zaokrąglonych przedziałów w węzłach; tylko wiatr średni."""
    if pd.isna(knots):
        return None
    thresholds = (1, 4, 7, 11, 17, 22, 28, 34, 41, 48, 56, 64)
    return next((i for i, limit in enumerate(thresholds) if knots < limit), 12)


def compass(degrees):
    if pd.isna(degrees):
        return '—'
    directions = ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW')
    return directions[int((degrees + 22.5) // 45) % 8]


def level(label, reasons):
    return {'ocena': label, 'powody': '; '.join(reasons) if reasons else 'Warunki pogodowe sprzyjające'}


def assess(row, activity, sunrise, sunset):
    """Proste filtry prognozy, a nie ocena bezpieczeństwa akwenu."""
    wind, gust = row.wind_speed_10m, row.wind_gusts_10m
    rain, chance = row.precipitation, row.precipitation_probability
    code = row.weather_code
    if any(pd.isna(v) for v in (wind, gust, rain, chance, code)):
        return level('Brak danych', ['niepełna prognoza'])
    if row.time < sunrise or row.time >= sunset:
        return level('Poza porą dzienną', ['przed wschodem lub po zachodzie słońca'])
    if code in (95, 96, 99):
        return level('Niekorzystne', ['prognozowana burza'])
    if activity == 'Żagle':
        if gust >= 22 or wind >= 17:
            return level('Niekorzystne', [f'wiatr {wind:.0f} kn, porywy {gust:.0f} kn'])
        if wind < 4:
            return level('Słaby wiatr', [f'wiatr {wind:.0f} kn'])
        reasons = []
        if gust >= 17:
            reasons.append(f'porywy do {gust:.0f} kn')
    elif activity == 'SUP':
        if wind >= 11 or gust >= 17:
            return level('Niekorzystne', [f'wiatr {wind:.0f} kn, porywy {gust:.0f} kn'])
        reasons = []
        if wind >= 7 or gust >= 11:
            reasons.append(f'wiatr {wind:.0f} kn, porywy {gust:.0f} kn')
    else:
        if pd.isna(row.temperature_2m):
            return level('Brak danych', ['brak temperatury'])
        if row.temperature_2m < 16 or gust >= 28:
            return level('Niekorzystne', [f'{row.temperature_2m:.0f}°C, porywy {gust:.0f} kn'])
        reasons = []
        if row.temperature_2m < 21 or wind >= 11:
            reasons.append(f'{row.temperature_2m:.0f}°C, wiatr {wind:.0f} kn')
    if rain > 1 or chance >= 70:
        return level('Niekorzystne', reasons + [f'opad {rain:.1f} mm, prawdopodobieństwo {chance:.0f}%'])
    if rain > 0 or chance >= 40:
        reasons.append(f'możliwy opad ({chance:.0f}%)')
    return level('Umiarkowane' if reasons else 'Sprzyjające', reasons)


def windows(times):
    if not times:
        return 'Brak w pokazanym zakresie'
    spans = []
    start = previous = times[0]
    for moment in times[1:]:
        if moment - previous != pd.Timedelta(hours=1):
            spans.append(f'{start:%d.%m %H:%M}–{previous + pd.Timedelta(hours=1):%H:%M}')
            start = moment
        previous = moment
    spans.append(f'{start:%d.%m %H:%M}–{previous + pd.Timedelta(hours=1):%H:%M}')
    return ', '.join(spans)


st.title('🌊 Jezioro Tarnobrzeskie')
st.caption('Prognoza pogody na jeziorze • strefa czasowa: Polska')
try:
    payload = fetch_weather()
    df = pd.DataFrame(payload['hourly'])
    required = {'time', *HOURLY}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError('Brakuje pól prognozy: ' + ', '.join(sorted(missing)))
    df['time'] = pd.to_datetime(df['time'])
    for field in HOURLY:
        df[field] = pd.to_numeric(df[field], errors='coerce')
    now = pd.Timestamp.now(tz=TZ).tz_localize(None)
    future = df.loc[df.time >= now.floor('h')].head(24).copy()
    if future.empty:
        raise ValueError('Brak aktualnej prognozy godzinowej')
    daily = pd.DataFrame(payload['daily'])
    daily['date'] = pd.to_datetime(daily['time']).dt.date
    daily['sunrise'] = pd.to_datetime(daily['sunrise'])
    daily['sunset'] = pd.to_datetime(daily['sunset'])
    df['date'] = df.time.dt.date
    future['date'] = future.time.dt.date
    df = df.merge(daily[['date', 'sunrise', 'sunset']], on='date', how='left')
    future = future.merge(daily[['date', 'sunrise', 'sunset']], on='date', how='left')
    if future[['sunrise', 'sunset']].isna().any().any():
        raise ValueError('Brak godzin wschodu lub zachodu słońca')
except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
    st.error(f'Nie udało się pobrać kompletnej prognozy. Spróbuj ponownie za chwilę. ({exc})')
    st.stop()

current = future.iloc[0]
st.caption(f'Pokazywana godzina prognozy: {current.time:%d.%m %H:%M} • aktualny czas: {now:%H:%M} • aktualizacja danych: co najwyżej co 15 min')
cols = st.columns(4)
cols[0].metric('Temperatura', f'{current.temperature_2m:.0f}°C' if pd.notna(current.temperature_2m) else '—')
cols[1].metric('Wiatr', f'{current.wind_speed_10m:.0f} kn' if pd.notna(current.wind_speed_10m) else '—',
               f'{compass(current.wind_direction_10m)} • {bft(current.wind_speed_10m)} Bft' if pd.notna(current.wind_speed_10m) else None)
cols[2].metric('Porywy', f'{current.wind_gusts_10m:.0f} kn' if pd.notna(current.wind_gusts_10m) else '—')
cols[3].metric('Opad', f'{current.precipitation:.1f} mm/h' if pd.notna(current.precipitation) else '—',
               f'szansa {current.precipitation_probability:.0f}%' if pd.notna(current.precipitation_probability) else None)

st.subheader('Na teraz')
activity_cols = st.columns(3)
for col, name, icon in zip(activity_cols, ('Żagle', 'SUP', 'Plaża'), ('⛵', '🏄', '🏖️')):
    result = assess(current, name, current.sunrise, current.sunset)
    with col:
        with st.container(border=True):
            st.markdown(f'**{icon} {name}: {result["ocena"]}**')
            st.caption(result['powody'])
st.caption('Oceny są orientacyjne i dotyczą prognozy, nie warunków obserwowanych na miejscu. Sprawdź lokalne komunikaty, szczególnie przed wejściem na wodę.')

next_12 = future.head(12)
alerts = []
for title, mask in (
    ('Burza w prognozie', next_12.weather_code.isin([95, 96, 99])),
    ('Silniejsze porywy', next_12.wind_gusts_10m >= 22),
    ('Intensywniejszy opad', next_12.precipitation > 1),
):
    rows = next_12.loc[mask]
    if not rows.empty:
        alerts.append(f'{title}: od {rows.iloc[0].time:%d.%m %H:%M}')
if alerts:
    st.warning('W prognozie na kolejne 12 godzin: ' + ' • '.join(alerts))
else:
    st.info('W prognozie na kolejne 12 godzin nie wykryto burzy, porywów ≥22 kn ani opadu >1 mm/h. To nie jest potwierdzenie bezpieczeństwa.')

hour_tab, week_tab = st.tabs(['Najbliższe 24 godziny', 'Kolejne dni'])
with hour_tab:
    activity = st.segmented_control('Pokaż warunki dla', ['Żagle', 'SUP', 'Plaża'], default='Żagle')
    activity = activity or 'Żagle'
    view = future.copy()
    evaluations = [assess(row, activity, row.sunrise, row.sunset) for row in view.itertuples()]
    view['Ocena'] = [item['ocena'] for item in evaluations]
    view['Uzasadnienie'] = [item['powody'] for item in evaluations]
    candidates = view.loc[view.Ocena.isin(['Sprzyjające', 'Umiarkowane']), 'time'].tolist()
    st.markdown(f'**Okna pogodowe: {windows(candidates)}**')
    st.caption('Okno jest zestawieniem godzin prognozy; warunki mogą się zmienić.')
    plot = view[['time', 'wind_speed_10m', 'wind_gusts_10m']].melt('time', var_name='Rodzaj', value_name='Węzły')
    plot['Rodzaj'] = plot['Rodzaj'].map({'wind_speed_10m': 'Wiatr', 'wind_gusts_10m': 'Porywy'})
    chart = alt.Chart(plot).mark_line(point=True).encode(
        x=alt.X('time:T', title='Godzina', axis=alt.Axis(format='%d.%m %H:%M')),
        y=alt.Y('Węzły:Q', title='Prędkość (kn)', scale=alt.Scale(zero=True)),
        color=alt.Color('Rodzaj:N', scale=alt.Scale(domain=['Wiatr', 'Porywy'], range=['#2288bd', '#e08e35'])),
        tooltip=[alt.Tooltip('time:T', title='Czas', format='%d.%m %H:%M'), 'Rodzaj:N', 'Węzły:Q'],
    ).properties(height=240)
    st.altair_chart(chart, use_container_width=True)
    details = view[['time', 'Ocena', 'Uzasadnienie', 'wind_speed_10m', 'wind_gusts_10m',
                    'wind_direction_10m', 'temperature_2m', 'precipitation_probability', 'precipitation']].copy()
    details['wind_direction_10m'] = details['wind_direction_10m'].map(compass)
    details.columns = ['Godzina', 'Ocena', 'Powód', 'Wiatr (kn)', 'Porywy (kn)', 'Kierunek',
                       'Temp. (°C)', 'Szansa opadu (%)', 'Opad (mm)']
    details['Godzina'] = details['Godzina'].dt.strftime('%d.%m %H:%M')
    with st.expander('Szczegóły godzinowe'):
        st.dataframe(details, hide_index=True, use_container_width=True)

with week_tab:
    st.caption('Każdy dzień liczony jest tylko z pozostałych godzin dziennych; dzisiaj pomijamy minione godziny.')
    for day in daily.itertuples():
        remaining = df.loc[(df.time.dt.date == day.date) & (df.time >= now.floor('h')) &
                           (df.time >= day.sunrise) & (df.time < day.sunset)]
        with st.container(border=True):
            st.markdown(f'**{day.date:%d.%m.%Y}**  ·  {day.temperature_2m_min:.0f}–{day.temperature_2m_max:.0f}°C  ·  opad dobowy {day.precipitation_sum:.1f} mm')
            st.caption(f'Wschód {day.sunrise:%H:%M} • zachód {day.sunset:%H:%M}')
            if remaining.empty:
                st.caption('Brak pozostałych godzin dziennych')
            else:
                for name, icon in (('Żagle', '⛵'), ('SUP', '🏄'), ('Plaża', '🏖️')):
                    good = [row.time for row in remaining.itertuples()
                            if assess(row, name, row.sunrise, row.sunset)['ocena'] in ('Sprzyjające', 'Umiarkowane')]
                    st.caption(f'{icon} {name}: {windows(good)}')

link_a, link_b = st.columns(2)
link_a.link_button('🚗 Dojazd', 'https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie', use_container_width=True)
link_b.link_button('📹 Kamery nad jeziorem', 'https://mosir.tarnobrzeg.pl/jezioro-tarnobrzeskie/kamery-on-line/', use_container_width=True)
st.caption('Dane: Open-Meteo. Kierunek oznacza stronę, z której wieje wiatr. Porywy pokazujemy w węzłach; skala Beauforta dotyczy średniego wiatru.')
