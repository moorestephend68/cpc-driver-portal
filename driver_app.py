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
st.set_page_config(page_title="CPC Driver Portal", layout="centered", page_icon="🚛")

# --- 2. DISPATCH LOGIC CONSTANTS ---
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

# --- 3. HELPERS ---
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

def clean_phone(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return None
    digits = "".join(filter(str.isdigit, str(val)))
    return "+" + digits if digits.startswith('1') else "+1" + digits

# --- 4. CSS ---
st.markdown("""
    <style>
    .dispatch-card {background: white; padding: 15px; border-radius: 12px; border-left: 8px solid #0f6cbd; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
    .btn-sms {display: inline-block; background: #0f6cbd; color: white !important; padding: 8px 12px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-right: 5px;}
    .btn-tracker {display: inline-block; background: #107c10; color: white !important; padding: 8px 12px; border-radius: 8px; text-decoration: none; font-weight: bold;}
    /* Existing Styles */
    .header-box {background-color: #004a99; color: white; padding: 20px; border-radius: 12px; margin-bottom: 15px;}
    .peoplenet-box {background-color: #2c3e50; color: white; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 15px;}
    .peoplenet-val {font-size: 20px; font-weight: bold; color: #3498db;}
    </style>
    """, unsafe_allow_html=True)

# --- 5. DATA LOADING ---
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

# --- 6. MAIN APP ---
try:
    roster, dispatch_notes, schedule, quick_links = load_all_data()
    st.markdown("<h1 style='font-size: 38px;'>🚛 CPC Portal</h1>", unsafe_allow_html=True)
    st.caption(f"Last sync: {datetime.now().strftime('%H:%M:%S')}")

    # Changed number_input to text_input to allow "dispatch"
    user_input = st.text_input("Enter Employee ID or 'dispatch'", value="").strip().lower()

    if user_input == "dispatch":
        st.subheader("📋 Dispatch Dashboard (PT)")
        
        # Build Phone Directory
        phones = {}
        for _, row in roster.iterrows():
            name = str(row.iloc[0]).strip().upper()
            p = clean_phone(row.get('Cell Phone')) # Assuming 'Cell Phone' is the header
            if name and p: phones[name] = p

        stops_list = []
        for _, row in schedule.iterrows():
            driver_name = str(row.get('Driver Name', '')).strip()
            if not driver_name or driver_name.lower() == 'nan': continue
            
            addr = str(row.get('Store Address', ''))
            raw_arr = str(row.iloc[8]) # Column I
            raw_dep = str(row.iloc[9]) # Column J
            
            pt_arr = convert_mt_to_pt(raw_arr, addr)
            pt_dep = convert_mt_to_pt(raw_dep, addr)
            
            stops_list.append({
                'driver': driver_name,
                'arrival': pt_arr,
                'departure': pt_dep,
                'store': str(row.get('Store ID', '')).zfill(5),
                'address': addr,
                'sort': get_sort_val(pt_arr),
                'tracker': str(row.iloc[25]).replace('DIALPAD:', '').strip() if len(row) > 25 else ""
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
                    <div style='font-weight:bold; font-size:18px;'>{s['driver']} — {s['arrival']}</div>
                    <div style='font-size:14px; color:#555;'>Store {s['store']} • {s['address']}</div>
                    <div style='margin-top:10px;'>
                        {sms_links}
                        <a class='btn-tracker' href='tel:{s['tracker']}'>📞 Tracker</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    elif user_input:
        # EXISTING DRIVER PORTAL LOGIC
        # (Search Roster for Employee ID and display Compliance/Schedule)
        # Note: u_id = user_input for the search
        pass # [Existing driver logic here]

except Exception as e:
    st.error(f"Error: {e}")
