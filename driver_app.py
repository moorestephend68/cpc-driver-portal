import streamlit as st
import pandas as pd
import re
import time
import base64
import urllib.parse
from datetime import datetime
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh 

# --- 1. CONFIG & REFRESH ---
st_autorefresh(interval=60000, key="datarefresh")
st.set_page_config(page_title="CPC Portal", layout="centered", page_icon="🚛")

# --- 2. DISPATCH CONSTANTS ---
MT_CITIES = {
    'PHOENIX', 'TUCSON', 'MESA', 'SCOTTSDALE', 'GILBERT', 'CHANDLER', 'GLENDALE', 
    'PEORIA', 'SURPRISE', 'BUCKEYE', 'GOODYEAR', 'APACHE JUNCTION', 'GOLD CANYON', 
    'CASA GRANDE', 'MARANA', 'ORO VALLEY', 'GREEN VALLEY', 'PRESCOTT', 'ANTHEM', 
    'KINGMAN', 'ALBUQUERQUE', 'SANTA FE', 'RIO RANCHO', 'GRANTS', 'GALLUP', 
    'SILVER CITY', 'DEMING', 'ESPANOLA', 'LOS RANCHOS', 'SALT LAKE CITY', 'OREM', 
    'TAYLORSVILLE', 'KAYSVILLE', 'WOODS CROSS', 'TOOELE', 'HERRIMAN', 'WEST JORDAN', 
    'HURRICANE', 'CEDAR CITY', 'PLEASANT GROVE', 'ROY', 'SYRACUSE', 'CLINTON', 
    'OGDEN', 'LOGAN'
}
DAYS_MAP = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
DAYS_LIST = list(DAYS_MAP.keys())

# --- 3. STYLES ---
st.markdown("""
    <style>
    .header-box {background-color: #004a99; color: white; padding: 20px; border-radius: 12px; margin-bottom: 15px;}
    .badge-info {background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; margin-bottom: 10px;}
    .val {display: block; font-weight: bold; color: #004a99; font-size: 24px;}
    .dispatch-box {border: 3px solid #d35400; padding: 20px; border-radius: 12px; background-color: #fffcf9; margin-bottom: 15px;}
    .peoplenet-box {background-color: #2c3e50; color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;}
    .peoplenet-val {font-size: 22px; font-weight: bold; color: #3498db;}
    .special-stop {background-color: #e3f2fd; border-left: 8px solid #2196f3; padding: 20px; border-radius: 10px; font-size: 22px; font-weight: bold; color: #0d47a1;}
    .dispatch-card {background: white; padding: 15px; border-radius: 12px; border-left: 8px solid #0f6cbd; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
    .btn-sms {display: inline-block; background: #0f6cbd; color: white !important; padding: 10px 14px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-right: 5px;}
    .btn-blue, .btn-green, .btn-red, .btn-purple, .btn-pink {
        display: block; width: 100%; padding: 15px 0; border-radius: 10px; text-align: center; font-weight: bold; text-decoration: none; color: white !important; margin-bottom: 5px;
    }
    .btn-blue {background-color: #007bff;}
    .btn-green {background-color: #28a745;}
    .btn-red {background-color: #dc3545;}
    .btn-purple {background-color: #6f42c1;}
    .btn-pink {background-color: #e83e8c;}
    input { font-size: 22px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. HELPERS ---
def convert_mt_to_pt(time_str, address):
    if not time_str or ',' not in str(time_str): return time_str
    city = str(address).split(',')[-1].strip().upper()
    if not any(mt_city in city for mt_city in MT_CITIES): return time_str
    try:
        time_part, day_part = str(time_str).split(',')
        hour, minute = map(int, time_part.split(':'))
        day_idx = DAYS_MAP[day_part.strip()]
        hour -= 1
        if hour < 0:
            hour = 23
            day_idx = (day_idx - 1) % 7
        return f"{hour:02d}:{minute:02d},{DAYS_LIST[day_idx]}"
    except: return time_str

def get_sort_val(time_str):
    try:
        time_part, day_part = str(time_str).split(',')
        hour, minute = map(int, time_part.split(':'))
        return (DAYS_MAP[day_part.strip()], hour, minute)
    except: return (9, 0, 0)

def clean_num(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return ""
    return re.sub(r'\D', '', str(val).split('.')[0])

def clean_phone(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return None
    digits = "".join(filter(str.isdigit, str(val)))
    return "+1" + digits if len(digits) == 10 else ("+" + digits if digits else None)

@st.cache_data(ttl=0)
def load_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7yF5pvuOjzm0xdRwHrFj8ByzGZ3kh1Iqmyw8pSdegEUUVeb3qSLpd1PDuWD1cUg/pub?output=csv"
    gids = {"roster": "1261782560", "dispatch": "1123038440", "schedule": "1908585361", "links": "489255872"}
    def get_sheet(gid):
        url = f"{base_url}&gid={gid}&cb={int(time.time())}"
        df = pd.read_csv(url, low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    return get_sheet(gids["roster"]), get_sheet(gids["dispatch"]), get_sheet(gids["schedule"]), get_sheet(gids["links"])

# --- 5. MAIN APP ---
try:
    roster, dispatch_notes, schedule, quick_links = load_all_data()
    st.markdown("<h1 style='font-size: 38px;'>🚛 CPC Portal</h1>", unsafe_allow_html=True)
    st.caption(f"Last sync: {datetime.now().strftime('%H:%M:%S')}")

    user_input = st.text_input("Enter ID or 'dispatch'", value="").strip().lower()

    if user_input == "dispatch":
        st.subheader("📋 Dispatch Dashboard (PT)")
        phones = {}
        for _, row in roster.iterrows():
            name = str(row.iloc[0]).strip().upper()
            phone = clean_phone(row.iloc[11])
            if name and phone:
                for n in name.split('/'): phones[n.strip().upper()] = phone

        stops_list = []
        for _, row in schedule.iterrows():
            driver_name = str(row.iloc[0]).strip()
            addr = str(row.iloc[5])
            raw_arr = str(row.iloc[8]).strip()
            if not driver_name or raw_arr in ('0', '-', '', 'nan'): continue
            
            pt_arr = convert_mt_to_pt(raw_arr, addr)
            tracker = str(row.iloc[25]).replace('DIALPAD:', '').strip() if len(row) > 25 else ""
            
            stops_list.append({
                'driver': driver_name, 'arrival': pt_arr, 'store': str(row.iloc[4]).zfill(5), 
                'address': addr, 'sort': get_sort_val(pt_arr), 'tracker': tracker
            })
        
        stops_list.sort(key=lambda x: x['sort'])

        for s in stops_list:
            sms_links = ""
            for name_part in s['driver'].split('/'):
                p = phones.get(name_part.strip().upper())
                if p:
                    msg = f"Reminder: Arrival {s['arrival']} - Store {s['store']} ({s['address']}). Don't forget to arrive and depart in cheetah"
                    sms_links += f"<a class='btn-sms' href='sms:{p}?body={urllib.parse.quote(msg)}'>Text {name_part.strip()}</a>"
            
            st.markdown(f"""
                <div class='dispatch-card'>
                    <div style='font-weight:bold;'>{s['driver']} — {s['arrival']}</div>
                    <div style='font-size:14px;'>Store {s['store']} • {s['address']}</div>
                    <div style='margin-top:10px;'>{sms_links} <a class='btn-tracker' href='tel:{s['tracker']}' style='color:#107c10; font-weight:bold;'>📞 Tracker</a></div>
                </div>
            """, unsafe_allow_html=True)

    elif user_input:
        roster['match_id'] = roster['Employee #'].apply(clean_num)
        match = roster[roster['match_id'] == user_input]

        if not match.empty:
            driver = match.iloc[0]
            raw_route = str(driver.get('Route', '')).strip()
            d_name = driver.get('Driver Name', 'Driver')
            
            st.markdown(f"<div class='header-box'><div style='font-size:32px; font-weight:bold;'>{d_name}</div>ID: {user_input} | Route: {raw_route}</div>", unsafe_allow_html=True)

            # Compliance & ELD
            p_id = str(driver.get('PeopleNet ID', '')).strip()
            st.markdown(f"<div class='peoplenet-box'>ELD Login<br><span class='peoplenet-val'>ORG: 3299 | ID: {p_id} | PW: {p_id}</span></div>", unsafe_allow_html=True)

            # Route Logic
            st.markdown("<h3 style='font-size:28px;'>Daily Schedule</h3>", unsafe_allow_html=True)
            route_num = clean_num(raw_route)
            
            if not raw_route or raw_route.lower() == 'nan':
                st.warning("⚠️ Refer to Dispatch Email")
            elif not route_num:
                st.markdown(f"<div class='special-stop'>📍 Assignment: {raw_route}</div>", unsafe_allow_html=True)
            else:
                schedule['route_match'] = schedule.iloc[:, 0].apply(clean_num)
                my_stops = schedule[schedule['route_match'] == route_num]
                if my_stops.empty:
                    st.warning("⚠️ Refer to Dispatch Email")
                else:
                    for _, stop in my_stops.iterrows():
                        sid = clean_num(stop.iloc[4])
                        arr, dep = str(stop.iloc[8]), str(stop.iloc[9])
                        with st.expander(f"📍 Store {sid.zfill(5)} (Arr: {arr})", expanded=True):
                            st.write(f"**Address:** {stop.iloc[5]}")
                            st.markdown(f"<a href='tel:8008710204,1,,88012#,,{sid},#,,,1,,,1' class='btn-green'>📞 Store Tracker</a>", unsafe_allow_html=True)
                            st.markdown(f"<a href='https://www.google.com/maps/search/?api=1&query={str(stop.iloc[5]).replace(' ','+')}' class='btn-blue'>🌎 Google Maps</a>", unsafe_allow_html=True)

            # Quick Links
            st.divider()
            for _, link in quick_links.iterrows():
                n, v = str(link.get('Name')), str(link.get('Phone Number or URL'))
                if "elba" in n.lower(): st.markdown(f"<a href='mailto:{v}' class='btn-pink'>✉️ Email {n}</a>", unsafe_allow_html=True)
                elif "http" in v: st.markdown(f"<a href='{v}' class='btn-blue'>🔗 {n}</a>", unsafe_allow_html=True)
                else: st.markdown(f"<a href='tel:{re.sub(r'[^0-9]', '', v)}' class='btn-purple'>📞 Call {n}</a>", unsafe_allow_html=True)
        else:
            st.error("ID not found.")

except Exception as e:
    st.error(f"Sync Error: {e}")
