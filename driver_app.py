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
MT_CITIES = {'PHOENIX', 'TUCSON', 'MESA', 'SCOTTSDALE', 'GILBERT', 'CHANDLER', 'GLENDALE', 'PEORIA', 'SURPRISE', 'BUCKEYE', 'GOODYEAR', 'APACHE JUNCTION', 'GOLD CANYON', 'CASA GRANDE', 'MARANA', 'ORO VALLEY', 'GREEN VALLEY', 'PRESCOTT', 'ANTHEM', 'KINGMAN', 'ALBUQUERQUE', 'SANTA FE', 'RIO RANCHO', 'GRANTS', 'GALLUP', 'SILVER CITY', 'DEMING', 'ESPANOLA', 'LOS RANCHOS', 'SALT LAKE CITY', 'OREM', 'TAYLORSVILLE', 'KAYSVILLE', 'WOODS CROSS', 'TOOELE', 'HERRIMAN', 'WEST JORDAN', 'HURRICANE', 'CEDAR CITY', 'PLEASANT GROVE', 'ROY', 'SYRACUSE', 'CLINTON', 'OGDEN', 'LOGAN'}
DAYS_MAP = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
DAYS_LIST = list(DAYS_MAP.keys())

# --- 3. STYLES ---
st.markdown("""
    <style>
    .header-box {background-color: #004a99; color: white; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    .dispatch-card {background: white; padding: 15px; border-radius: 12px; border-left: 8px solid #0f6cbd; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
    .btn-sms {display: inline-block; background: #0f6cbd; color: white !important; padding: 10px 14px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-right: 5px; margin-bottom: 5px;}
    .btn-tracker {display: inline-block; background: #107c10; color: white !important; padding: 10px 14px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-bottom: 5px;}
    .btn-disabled {display: inline-block; background: #888; color: white !important; padding: 10px 14px; border-radius: 10px; opacity: 0.6; pointer-events: none;}
    .badge-info {background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; margin-bottom: 10px;}
    .val {display: block; font-weight: bold; color: #004a99; font-size: 24px;}
    input { font-size: 22px !important; height: 50px !important; }
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
        if hour < 0: hour = 23; day_idx = (day_idx - 1) % 7
        return f"{hour:02d}:{minute:02d},{DAYS_LIST[day_idx]}"
    except: return time_str

def get_sort_val(time_str):
    try:
        t, d = str(time_str).split(',')
        h, m = map(int, t.split(':'))
        return (DAYS_MAP[d.strip()], h, m)
    except: return (9, 0, 0)

def clean_num(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return ""
    return re.sub(r'\D', '', str(val).split('.')[0])

def clean_phone(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return None
    d = "".join(filter(str.isdigit, str(val)))
    return "+1" + d if len(d) == 10 else ("+" + d if d else None)

def format_date(date_str):
    if pd.isna(date_str) or not str(date_str).strip(): return "N/A"
    try:
        dt = pd.to_datetime(date_str, errors='coerce')
        return dt.strftime("%B %d, %Y") if not pd.isna(dt) else str(date_str)
    except: return str(date_str)

@st.cache_data(ttl=0)
def load_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7yF5pvuOjzm0xdRwHrFj8ByzGZ3kh1Iqmyw8pSdegEUUVeb3qSLpd1PDuWD1cUg/pub?output=csv"
    gids = {"roster": "1261782560", "dispatch": "1123038440", "schedule": "1908585361", "links": "489255872"}
    def get_s(gid):
        df = pd.read_csv(f"{base_url}&gid={gid}&cb={int(time.time())}", low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    return get_s(gids["roster"]), get_s(gids["dispatch"]), get_s(gids["schedule"]), get_s(gids["links"])

# --- 5. MAIN APP ---
try:
    roster, dispatch_notes_df, schedule, quick_links = load_all_data()
    st.markdown("<h1 style='font-size: 38px;'>🚛 CPC Portal</h1>", unsafe_allow_html=True)
    st.caption(f"Last sync: {datetime.now().strftime('%H:%M:%S')}")

    user_input = st.text_input("Enter ID or 'dispatch'", value="").strip().lower()

    if user_input == "dispatch":
        st.subheader("📋 Dispatch Dashboard (PT)")
        
        # Build Phone Directory
        phones = {}
        for _, row in roster.iterrows():
            name = str(row.iloc[0]).strip().upper()
            phone = clean_phone(row.iloc[11])
            if name and phone:
                for n in name.split('/'): phones[n.strip().upper()] = phone

        stops_list = []
        for _, row in schedule.iterrows():
            driver_name = str(row.iloc[0]).strip()
            # 5-digit Store ID
            try: store_raw = str(row.iloc[4]).strip()
            except: store_raw = ""
            
            arrival = str(row.iloc[8]).strip()
            
            # Skip invalid
            if not driver_name or store_raw in ('0', '', 'nan') or arrival in ('0', '-', '', 'nan'):
                continue
            
            try: sid_5 = str(int(float(store_raw))).zfill(5)
            except: sid_5 = store_raw.zfill(5)

            address = str(row.iloc[5]).strip()
            arr_pt = convert_mt_to_pt(arrival, address)
            dep_pt = convert_mt_to_pt(str(row.iloc[9]), address)
            
            # Tracker Column Z (Index 25)
            tracker = str(row.iloc[25]).replace('DIALPAD:', '').strip() if len(row) > 25 else ""
            
            stops_list.append({
                'driver': driver_name, 'arrival': arr_pt, 'departure': dep_pt,
                'store': sid_5, 'address': address, 'sort': get_sort_val(arr_pt), 
                'tracker': tracker, 'route': str(row.iloc[1])
            })
        
        stops_list.sort(key=lambda x: x['sort'])

        for s in stops_list:
            sms_links = ""
            for name_part in s['driver'].split('/'):
                p = phones.get(name_part.strip().upper())
                if p:
                    # Message Body
                    body = f"Reminder: Arrival {s['arrival']} - Store {s['store']} ({s['address']}). Don't forget to arrive and depart in cheetah"
                    sms_links += f"<a class='btn-sms' href='sms:{p}?body={urllib.parse.quote(body)}'>Text {name_part.strip()}</a>"
                else:
                    sms_links += f"<span class='btn-disabled'>No phone for {name_part.strip()}</span>"
            
            st.markdown(f"""
                <div class='dispatch-card'>
                    <div style='font-weight:bold; font-size:18px;'>{s['driver']} — {s['arrival']} • {s['departure']}</div>
                    <div style='font-size:14px; color:#444;'>Route {s['route']} • Store {s['store']}</div>
                    <div style='font-size:14px; color:#444; margin-bottom:10px;'>{s['address']}</div>
                    <div>
                        {sms_links}
                        <a class='btn-tracker' href='tel:{s['tracker']}'>Dial Store Tracker</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    elif user_input:
        # [Existing Driver Portal Logic]
        roster['match_id'] = roster['Employee #'].apply(clean_num)
        match = roster[roster['match_id'] == user_input]
        if not match.empty:
            driver = match.iloc[0]
            d_name = driver.get('Driver Name', driver.iloc[0])
            st.markdown(f"<div class='header-box'><div style='font-size:32px; font-weight:bold;'>{d_name}</div>ID: {user_input}</div>", unsafe_allow_html=True)
            # ... (Schedule and Compliance as before)
        else: st.error("ID not found.")

except Exception as e: st.error(f"Sync Error: {e}")
