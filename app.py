"""Prognoza rekreacyjna dla Jeziora Tarnobrzeskiego. Uruchom: streamlit run jezioro_tarnobrzeskie.py"""
from html import escape
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
st.markdown("""<style>
:root {color-scheme: dark;}
.stApp {background:#08151e;color:#eaf3f5;}
[data-testid="stHeader"] {background:transparent;}
.block-container {max-width:1200px;padding-top:2.2rem;padding-bottom:2rem;}
h1,h2,h3,p,label {color:inherit;}
[data-testid="stCaptionContainer"] {color:#93abb7;}
.brand {display:flex;align-items:center;justify-content:space-between;margin:0 0 26px;gap:20px;}
.brand-name {font-size:18px;font-weight:700;letter-spacing:-.5px;}
.brand-name span {color:#69dfc3;margin-right:10px;}
.eyebrow {font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#9bb8c5;font-weight:600;}
.small {color:#9bb0bb;font-size:13px;line-height:1.6;}
.hero {position:relative;overflow:hidden;border:1px solid #2b4957;border-radius:26px;background:linear-gradient(115deg,#163440,#102b3b 64%,#154c57);padding:34px 36px;margin-bottom:22px;}
.hero h1 {font-size:clamp(28px,4vw,45px);letter-spacing:-1.7px;line-height:1.1;margin:10px 0 22px;color:#f2f8f9;}
.hero-top {position:relative;z-index:1;display:flex;justify-content:space-between;align-items:center;gap:24px;}
.temp {font-size:84px;letter-spacing:-6px;font-weight:550;line-height:1;}
.temp small {font-size:30px;letter-spacing:-1px;color:#a9c2ca;}
.weather-copy {margin-top:14px;font-size:16px;color:#bcd2dc;}
.orb {width:108px;height:108px;border-radius:50%;background:#f5d887;box-shadow:0 0 70px #f5d88730;flex-shrink:0;margin:12px 40px 32px;}
.hero-stats {position:relative;z-index:1;display:grid;grid-template-columns:repeat(4,1fr);gap:18px;border-top:1px solid #ffffff20;margin-top:32px;padding-top:22px;}
.hero-stats b {display:block;font-size:24px;font-weight:550;margin-top:5px;}
.hero-stats small {font-size:12px;color:#a5bdc7;}
.waves {position:absolute;width:65%;height:210px;right:-10%;bottom:20px;opacity:.16;transform:rotate(-10deg);border:1px solid #8fe8de;border-radius:50%;box-shadow:0 18px 0 -1px #3f9a9b,0 38px 0 -1px #3f9a9b,0 58px 0 -1px #3f9a9b;}
.section-title {font-size:20px;font-weight:650;letter-spacing:-.5px;margin:28px 0 14px;}
.activities {display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:12px;}
.activity {background:#10222d;border:1px solid #233944;border-radius:18px;padding:22px;}
.activity-head {display:flex;justify-content:space-between;align-items:center;font-size:16px;font-weight:600;}
.activity-number {color:#77909d;font-size:12px;font-weight:400;}
.pill {display:inline-block;border-radius:7px;padding:5px 9px;font-size:12px;background:#193e37;color:#87e3be;margin:16px 0 8px;}
.pill.amber {color:#f1cb83;background:#3d3325;}.pill.red {color:#f0a7a0;background:#422c30;}.pill.muted {color:#a6bbc6;background:#263943;}
.hour-strip {display:flex;overflow-x:auto;gap:10px;padding:3px 0 14px;scrollbar-color:#375966 #10222d;}
.hour {min-width:95px;background:#10222d;border:1px solid #223944;border-radius:14px;padding:16px 12px;text-align:center;}
.hour:first-child {border-color:#64d7bd;background:#16332f;}
.hour b {display:block;font-size:23px;margin:12px 0;}
.hour .symbol {font-size:24px;display:block;margin-top:10px;}
.day-row {display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr;gap:12px;align-items:center;border-bottom:1px solid #263944;padding:16px 4px;}
.day-row b {font-weight:550;}.day-row small {display:block;color:#90a9b6;margin-top:4px;}
.notice {border:1px solid #65513a;background:#302b23;color:#ebd5ac;border-radius:12px;padding:13px 18px;font-size:13px;margin-bottom:18px;}
.footer {display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap;border-top:1px solid #233944;margin-top:28px;padding-top:20px;color:#8ea7b5;font-size:12px;}
.footer a {color:#88d8c7;text-decoration:none;margin-left:18px;}
[data-baseweb="tab-list"] {gap:24px;border-bottom:1px solid #263944;}
[data-baseweb="tab"] {color:#a8bdc8;}
[data-baseweb="tab"][aria-selected="true"] {color:#78dfc4;}
[data-baseweb="tab-highlight"] {background-color:#78dfc4;}
[data-testid="stExpander"] {border-color:#263944;background:#10222d;color:#eaf3f5;}
[data-baseweb="select"]>div {background:#10222d;color:#eaf3f5;border-color:#37515f;}
@media(max-width:640px){.block-container{padding-top:1.3rem;}.brand{margin-bottom:18px;}.brand .small{display:none;}.hero{padding:23px 21px;border-radius:20px;}.hero-top{gap:10px;}.temp{font-size:66px;}.orb{width:58px;height:58px;margin:0 4px 22px;}.hero-stats{grid-template-columns:repeat(2,1fr);gap:18px;margin-top:23px;}.hero-stats b{font-size:23px;}.activities{grid-template-columns:1fr;gap:9px;}.activity{padding:15px 18px;}.pill{margin-top:9px;}.day-row{grid-template-columns:1.3fr 1fr 1fr;font-size:13px;}.day-row .daily-rain{display:none;}.footer a{margin:0 16px 0 0;}}
</style>""", unsafe_allow_html=True)


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
    """Beaufort według zaokrąglonych przedziałów w węzłach; porywy prezentowane jako równoważna prędkość."""
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
            return level('Niekorzystne', [f'wiatr {bft(wind)} Bft, porywy odpowiadają {bft(gust)} Bft'])
        if wind < 4:
            return level('Słaby wiatr', [f'wiatr {bft(wind)} Bft'])
        reasons = []
        if gust >= 17:
            reasons.append(f'porywy odpowiadają {bft(gust)} Bft')
    elif activity == 'SUP':
        if wind >= 11 or gust >= 17:
            return level('Niekorzystne', [f'wiatr {bft(wind)} Bft, porywy odpowiadają {bft(gust)} Bft'])
        reasons = []
        if wind >= 7 or gust >= 11:
            reasons.append(f'wiatr {bft(wind)} Bft, porywy odpowiadają {bft(gust)} Bft')
    else:
        if pd.isna(row.temperature_2m):
            return level('Brak danych', ['brak temperatury'])
        if row.temperature_2m < 16 or gust >= 28:
            return level('Niekorzystne', [f'{row.temperature_2m:.0f}°C, porywy odpowiadają {bft(gust)} Bft'])
        reasons = []
        if row.temperature_2m < 21 or wind >= 11:
            reasons.append(f'{row.temperature_2m:.0f}°C, wiatr {bft(wind)} Bft')
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

def fmt(value, suffix='', digits=0):
    return '—' if pd.isna(value) else f'{value:.{digits}f}{suffix}'


def wind_fmt(value):
    result = bft(value)
    return '—' if result is None else f'{result} Bft'


def weather(code, night=False):
    if pd.isna(code):
        return '◌', 'Brak opisu pogody'
    if code == 0:
        return ('☾', 'Bezchmurnie') if night else ('☀', 'Słonecznie')
    if code in (1, 2):
        return '☁', 'Częściowe zachmurzenie'
    if code == 3:
        return '☁', 'Pochmurno'
    if code in (45, 48):
        return '≋', 'Mgła'
    if code in (95, 96, 99):
        return 'ϟ', 'Burza w prognozie'
    if code in (71, 73, 75, 77, 85, 86):
        return '❄', 'Opady śniegu'
    return '☂', 'Opady'


def tone(label):
    return {'Sprzyjające': '', 'Umiarkowane': 'amber', 'Niekorzystne': 'red'}.get(label, 'muted')


def html(markup):
    st.markdown(markup, unsafe_allow_html=True)


current = future.iloc[0]
night = current.time < current.sunrise or current.time >= current.sunset
symbol, description = weather(current.weather_code, night)
html('<div class="brand"><div class="brand-name"><span>≈</span> NAD WODĄ</div><div class="small">Jezioro Tarnobrzeskie · 50.555° N / 21.652° E</div></div>')
orb_style = 'background:#bad5e1;box-shadow:0 0 55px #bad5e120' if night else ('background:#a8bec9;box-shadow:none' if current.weather_code != 0 else '')
html(f'''<section class="hero"><div class="waves"></div><div class="eyebrow">Prognoza na {current.time:%d.%m · %H:%M}</div><h1>Dzień nad jeziorem.</h1><div class="hero-top"><div><div class="temp">{fmt(current.temperature_2m)}<small>°C</small></div><div class="weather-copy">{description} <span class="small"> · odczuwalna {fmt(current.apparent_temperature, '°C')}</span></div></div><div class="orb" style="{orb_style}" aria-hidden="true"></div></div><div class="hero-stats"><div><small>WIATR · {compass(current.wind_direction_10m)}</small><b>{wind_fmt(current.wind_speed_10m)}</b><small>skala Beauforta</small></div><div><small>PORYWY</small><b>{wind_fmt(current.wind_gusts_10m)}</b><small>przeliczona prędkość</small></div><div><small>SZANSA OPADU</small><b>{fmt(current.precipitation_probability, '%')}</b><small>{fmt(current.precipitation, ' mm', 1)} w godzinie</small></div><div><small>ZACHÓD SŁOŃCA</small><b>{current.sunset:%H:%M}</b><small>wschód {current.sunrise:%H:%M}</small></div></div></section>''')

alerts = []
for title, mask in (
    ('Burza w prognozie', future.head(12).weather_code.isin([95, 96, 99])),
    ('Porywy odpowiadają ≥6 Bft', future.head(12).wind_gusts_10m >= 22),
    ('Opad >1 mm/h', future.head(12).precipitation > 1),
):
    rows = future.head(12).loc[mask]
    if not rows.empty:
        alerts.append(f'{title} · od {rows.iloc[0].time:%d.%m %H:%M}')
if alerts:
    html('<div class="notice">' + ' &nbsp; / &nbsp; '.join(alerts) + '</div>')

html('<div class="section-title">Jakie warunki na teraz?</div>')
cards = []
for number, name in enumerate(('Żagle', 'SUP', 'Plaża'), 1):
    result = assess(current, name, current.sunrise, current.sunset)
    cards.append(f'<article class="activity"><div class="activity-head">{name}<span class="activity-number">0{number}</span></div><div class="pill {tone(result["ocena"])}">{result["ocena"]}</div><div class="small">{escape(result["powody"])}</div></article>')
html('<div class="activities">' + ''.join(cards) + '</div>')
st.caption('Orientacyjna ocena prognozy. Warunki na miejscu i komunikaty lokalne mogą się różnić.')

hour_tab, week_tab = st.tabs(['Najbliższe godziny', 'Prognoza na 7 dni'])
with hour_tab:
    html('<div class="section-title">Pogoda godzina po godzinie</div>')
    hours = []
    for index, row in enumerate(future.itertuples()):
        icon, desc = weather(row.weather_code, row.time < row.sunrise or row.time >= row.sunset)
        label = 'Teraz' if index == 0 else row.time.strftime('%H:%M')
        hours.append(f'<div class="hour"><div class="small">{label}</div><div class="small">{row.time:%d.%m}</div><span class="symbol" title="{desc}">{icon}</span><b>{fmt(row.temperature_2m, "°")}</b><div class="small">{wind_fmt(row.wind_speed_10m)}</div><div class="small">{fmt(row.precipitation_probability, "%")} opadu</div></div>')
    html('<div class="hour-strip">' + ''.join(hours) + '</div>')
    left, right = st.columns([2, 1], gap='large')
    with left:
        html('<div class="section-title">Wiatr i porywy</div>')
        plot = future[['time', 'wind_speed_10m', 'wind_gusts_10m']].copy()
        for field in ('wind_speed_10m', 'wind_gusts_10m'):
            plot[field] = plot[field].map(bft)
        plot = plot.melt('time', var_name='Rodzaj', value_name='Bft')
        plot['Rodzaj'] = plot['Rodzaj'].map({'wind_speed_10m': 'Wiatr', 'wind_gusts_10m': 'Porywy'})
        chart = alt.Chart(plot).mark_line(strokeWidth=2.5, interpolate='step-after').encode(
            x=alt.X('time:T', title=None, axis=alt.Axis(format='%H:%M', tickCount=6)),
            y=alt.Y('Bft:Q', title='Beaufort (Bft)', scale=alt.Scale(zero=True), axis=alt.Axis(tickMinStep=1, format='d')),
            color=alt.Color('Rodzaj:N', title=None, scale=alt.Scale(domain=['Wiatr', 'Porywy'], range=['#70dfbf', '#e7bb78'])),
            tooltip=[alt.Tooltip('time:T', title='Godzina', format='%d.%m %H:%M'), 'Rodzaj:N', alt.Tooltip('Bft:Q', format='.0f')],
        ).properties(height=250, background='#08151e').configure_view(stroke=None).configure_axis(
            gridColor='#233743', domain=False, labelColor='#9eb4c0', titleColor='#9eb4c0', tickColor='#233743'
        ).configure_legend(labelColor='#c4d5dd', orient='top')
        st.altair_chart(chart, use_container_width=True, theme=None)
        st.caption('Wiatr w skali Beauforta. Dla porywów podajemy odpowiadający im stopień skali.')
    with right:
        html('<div class="section-title">Zaplanuj swój czas</div>')
        activity = st.selectbox('Aktywność', ['Żagle', 'SUP', 'Plaża'])
        evaluated = [(row, assess(row, activity, row.sunrise, row.sunset)) for row in future.itertuples()]
        good = [row.time for row, result in evaluated if result['ocena'] == 'Sprzyjające']
        html(f'<div class="activity"><div class="eyebrow">Sprzyjające godziny</div><div style="font-size:20px;line-height:1.55;margin:14px 0">{windows(good)}</div><div class="small">{activity} · kolejne 24 godziny</div></div>')
        st.caption('Godziny wynikają z prognozy. Koniec przedziału oznacza koniec ostatniej wskazanej godziny.')
    with st.expander('Wszystkie parametry godzinowe'):
        details = future[['time', 'temperature_2m', 'wind_speed_10m', 'wind_gusts_10m', 'precipitation_probability', 'uv_index']].copy()
        for field in ('wind_speed_10m', 'wind_gusts_10m'):
            details[field] = details[field].map(bft).astype('Int64')
        details.columns = ['Godzina', 'Temperatura °C', 'Wiatr Bft', 'Porywy Bft (przeliczenie)', 'Opad %', 'UV']
        details['Godzina'] = details['Godzina'].dt.strftime('%d.%m %H:%M')
        st.dataframe(details, hide_index=True, use_container_width=True)
with week_tab:
    html('<div class="section-title">Spójrz kilka dni dalej</div>')
    weekdays = ['Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota', 'Niedziela']
    for day in daily.itertuples():
        label = 'Dzisiaj' if day.date == now.date() else weekdays[day.date.weekday()]
        day_df = df.loc[df.time.dt.date == day.date]
        max_wind = day_df.wind_speed_10m.max()
        html(f'<div class="day-row"><div><b>{label}</b><small>{day.date:%d.%m}</small></div><div><b>{fmt(day.temperature_2m_max, "°")} <span class="small">/ {fmt(day.temperature_2m_min, "°")}</span></b><small>maks. / min.</small></div><div><b>{wind_fmt(max_wind)}</b><small>maks. wiatr</small></div><div class="daily-rain"><b>{fmt(day.precipitation_sum, " mm", 1)}</b><small>suma opadów</small></div></div>')
        with st.expander(f'Godziny dla aktywności · {day.date:%d.%m}'):
            remaining = day_df.loc[day_df.time >= now.floor('h')]
            for name in ('Żagle', 'SUP', 'Plaża'):
                good = [row.time for row in remaining.itertuples() if assess(row, name, row.sunrise, row.sunset)['ocena'] == 'Sprzyjające']
                st.write(f'**{name}:** {windows(good)}')
            st.caption(f'Wschód {day.sunrise:%H:%M} · zachód {day.sunset:%H:%M}')
html('<div class="footer"><span>Prognoza: Open-Meteo · czas polski</span><div><a href="https://www.google.com/maps/dir/?api=1&destination=Jezioro+Tarnobrzeskie" target="_blank" rel="noopener noreferrer">Dojazd ↗</a><a href="https://mosir.tarnobrzeg.pl/jezioro-tarnobrzeskie/kamery-on-line/" target="_blank" rel="noopener noreferrer">Kamery ↗</a></div></div>')
