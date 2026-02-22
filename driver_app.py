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

# --- 2. ANDROID PWA LOGIC ---
manifest_json = """
{
  "name": "CPC Portal",
  "short_name": "CPC Portal",
  "start_url": "https://cpc-driver.streamlit.app/",
  "display": "standalone",
  "theme_color": "#004a99",
  "background_color": "#ffffff",
  "icons": [{"src": "https://cdn-icons-png.flaticon.com/512/2554/2554979.png", "sizes": "512x512", "type": "image/png"}]
}
"""
manifest_base64 = base64.b64encode(manifest_json.encode()).decode()
st.markdown(f'<head><link rel="manifest" href="data:application/manifest+json;base64,{manifest_base64}"><meta name="mobile-web-app-capable" content="yes"></head>', unsafe_allow_html=True)

# --- 3. DISPATCH CONSTANTS ---
MT_CITIES = {'PHOENIX', 'TUCSON', 'MESA', 'SCOTTSDALE', 'GILBERT', 'CHANDLER', 'GLENDALE', 'PEORIA', 'SURPRISE', 'BUCKEYE', 'GOODYEAR', 'APACHE JUNCTION', 'GOLD CANYON', 'CASA GRANDE', 'MARANA', 'ORO VALLEY', 'GREEN VALLEY', 'PRESCOTT', 'ANTHEM', 'KINGMAN', 'ALBUQUERQUE', 'SANTA FE', 'RIO RANCHO', 'GRANTS', 'GALLUP', 'SILVER CITY', 'DEMING', 'ESPANOLA', 'LOS RANCHOS', 'SALT LAKE CITY', 'OREM', 'TAYLORSVILLE', 'KAYSVILLE', 'WOODS CROSS', 'TOOELE', 'HERRIMAN', 'WEST JORDAN', 'HURRICANE', 'CEDAR CITY', 'PLEASANT GROVE', 'ROY', 'SYRACUSE', 'CLINTON', 'OGDEN', 'LOGAN'}
DAYS_MAP = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
DAYS_LIST = list(DAYS_MAP.keys())

# --- 4. GLOBAL STYLES ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background-color: #004a99; color: white; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    .badge-info {background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; height: 100%; color: #333 !important; margin-bottom: 10px;}
    .val {display: block; font-weight: bold; color: #004a99; font-size: 24px;}
    .dispatch-box {border: 3px solid #d35400; padding: 20px; border-radius: 12px; background-color: #fffcf9; margin-bottom: 15px;}
    .peoplenet-box {background-color: #2c3e50; color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;}
    .peoplenet-val {font-size: 22px; font-weight: bold; color: #3498db;}
    .special-stop {background-color: #e3f2fd; border-left: 8px solid #2196f3; padding: 20px; border-radius: 10px; font-size: 22px; font-weight: bold; color: #0d47a1;}
    .dispatch-card {background: white; padding: 15px; border-radius: 12px; border-left: 8px solid #0f6cbd; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
    
    .btn-blue, .btn-green, .btn-red, .btn-purple, .btn-pink, .btn-sms {
        display: block !important; width: 100% !important; padding: 15px 0px !important;
        border-radius: 10px !important; text-align: center !important; font-weight: bold !important;
        font-size: 18px !important; text-decoration: none !important; color: white !important;
        margin-bottom: 8px !important; border: none !important;
    }
    .btn-blue {background-color: #007bff !important;}
    .btn-green {background-color: #28a745 !important;}
    .btn-red {background-color: #dc3545 !important;}
    .btn-purple {background-color: #6f42c1 !important;}
    .btn-pink {background-color: #e83e8c !important;}
    .btn-sms {background-color: #0f6cbd !important; padding: 10px 0 !important;}
    
    input { font-size: 24px !important; height: 60px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. DATA HELPERS ---
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

def get_renewal_status(exp_date_val):
    if pd.isna(exp_date_val): return "N/A", ""
    try:
        exp_date = pd.to_datetime(exp_date_val)
        diff = relativedelta(exp_date, datetime.now())
        days_left = (exp_date - datetime.now()).days
        return f"{diff.years}y {diff.months}m {diff.days}d", ("⚠️ RENEW NOW" if days_left <= 60 else "")
    except: return "N/A", ""

@st.cache_data(ttl=0)
def load_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7yF5pvuOjzm0xdRwHrFj8ByzGZ3kh1Iqmyw8pSdegEUUVeb3qSLpd1PDuWD1cUg/pub?output=csv"
    gids = {"roster": "1261782560", "dispatch": "1123038440", "schedule": "1908585361", "links": "489255872"}
    def get_s(gid):
        df = pd.read_csv(f"{base_url}&gid={gid}&cb={int(time.time())}", low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    return get_s(gids["roster"]), get_s(gids["dispatch"]), get_s(gids["schedule"]), get_s(gids["links"])

# --- 6. MAIN APP ---
try:
    roster, dispatch_notes_df, schedule, quick_links = load_all_data()
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
            
            stops_list.append({'driver': driver_name, 'arrival': pt_arr, 'store': str(row.iloc[4]).zfill(5), 'address': addr, 'sort': get_sort_val(pt_arr), 'tracker': tracker})
        
        stops_list.sort(key=lambda x: x['sort'])
        for s in stops_list:
            sms_links = ""
            for name_part in s['driver'].split('/'):
                p = phones.get(name_part.strip().upper())
                if p:
                    msg = f"Reminder: Arrival {s['arrival']} - Store {s['store']} ({s['address']}). Don't forget to arrive and depart in cheetah"
                    sms_links += f"<a class='btn-sms' href='sms:{p}?body={urllib.parse.quote(msg)}'>Text {name_part.strip()}</a>"
            
            st.markdown(f"<div class='dispatch-card'><div style='font-weight:bold;'>{s['driver']} — {s['arrival']}</div><div style='font-size:14px;'>Store {s['store']} • {s['address']}</div><div style='margin-top:10px;'>{sms_links} <a href='tel:{s['tracker']}' style='color:#107c10; font-weight:bold;'>📞 Tracker</a></div></div>", unsafe_allow_html=True)

    elif user_input:
        roster['match_id'] = roster['Employee #'].apply(clean_num)
        match = roster[roster['match_id'] == user_input]

        if not match.empty:
            driver = match.iloc[0]
            raw_route = str(driver.get('Route', '')).strip()
            route_num = clean_num(raw_route)
            # Fetch name from "Driver Name" column or fallback to first column (Index 0)
            d_name = driver.get('Driver Name', driver.iloc[0])
            
            # Header & Compliance
            st.markdown(f"<div class='header-box'><div style='font-size:32px; font-weight:bold;'>{d_name}</div>ID: {user_input} | Route: {raw_route}</div>", unsafe_allow_html=True)
            
            dot_count, dot_msg = get_renewal_status(driver.get('DOT Physical Expires'))
            cdl_count, cdl_msg = get_renewal_status(driver.get('DL Expiration Date'))
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='badge-info'>DOT Exp<span class='val'>{format_date(driver.get('DOT Physical Expires'))}</span><small>{dot_count}<br><b style='color:red;'>{dot_msg}</b></small></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='badge-info'>CDL Exp<span class='val'>{format_date(driver.get('DL Expiration Date'))}</span><small>{cdl_count}<br><b style='color:red;'>{cdl_msg}</b></small></div>", unsafe_allow_html=True)
            st.info(f"**Tenure:** {calculate_tenure(driver.get('Hire Date'))}")

            # Dispatch Notes
            dispatch_notes_df['route_match'] = dispatch_notes_df.iloc[:, 0].apply(clean_num)
            d_info = dispatch_notes_df[dispatch_notes_df['route_match'] == route_num]
            if not d_info.empty:
                r_data = d_info.iloc[0]
                st.markdown(f"<div class='dispatch-box'><h3 style='margin:0; color:#d35400; font-size:18px;'>DISPATCH NOTES</h3><div style='font-size:24px; font-weight:bold; color:#d35400;'>{r_data.get('Comments', 'None')}</div><div style='margin-top:10px;'><b>Trailers:</b> {r_data.get('1st Trailer')} / {r_data.get('2nd Trailer')}</div></div>", unsafe_allow_html=True)

            # ELD Login
            p_id = str(driver.get('PeopleNet ID', '')).strip()
            st.markdown(f"<div class='peoplenet-box'>ELD Login<br><span class='peoplenet-val'>ORG: 3299 | ID: {p_id} | PW: {p_id}</span></div>", unsafe_allow_html=True)

            # Schedule Logic
            st.markdown("<h3 style='font-size:28px;'>Daily Schedule</h3>", unsafe_allow_html=True)
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
                        raw_sid = clean_num(stop.iloc[4])
                        sid_5 = raw_sid.zfill(5)
                        addr = str(stop.iloc[5])
                        clean_addr = addr.replace(' ','+').replace('\n','')
                        arr, dep = str(stop.iloc[8]), str(stop.iloc[9])
                        
                        with st.expander(f"📍 Stop: {sid_5 if raw_sid != '0' else 'Relay'} (Arr: {arr})", expanded=True):
                            st.markdown(f"<div style='background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:12px; border-left:6px solid #004a99;'><table style='width:100%; border:none; font-size:18px;'><tr><td style='width:40%'><b>Arrival:</b></td><td>{arr}</td></tr><tr><td><b>Departure:</b></td><td>{dep}</td></tr><tr><td valign='top'><b>Address:</b></td><td>{addr}</td></tr></table></div>", unsafe_allow_html=True)
                            
                            # Restore All Stop Buttons
                            st.markdown(f"""
                            <table style="width:100%; border:none; border-collapse:collapse; background:transparent;">
                              <tr>
                                <td style="width:50%; padding:5px;"><a href="tel:8008710204,1,,88012#,,{raw_sid},#,,,1,,,1" class="btn-green">📞 Store Tracker</a></td>
                                <td style="width:50%; padding:5px;"><a href="https://www.google.com/maps/search/?api=1&query={clean_addr}" class="btn-blue">🌎 Google</a></td>
                              </tr>
                              <tr>
                                <td style="width:50%; padding:5px;"><a href="truckmap://navigate?q={clean_addr}" class="btn-blue">🚛 TruckMap</a></td>
                                <td style="width:50%; padding:5px;"><a href="https://wg.cpcfact.com/store-{sid_5}/" class="btn-blue">🗺️ Store Map</a></td>
                              </tr>
                            </table>
                            <a href="https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAO__Ti7fnBUQzNYTTY1TjY3Uk0xMEwwTE9SUEZIWTRPRC4u" class="btn-red">🚨 Report Issue</a>
                            """, unsafe_allow_html=True)

            # Quick Links
            st.divider()
            for _, link in quick_links.iterrows():
                n, v = str(link.get('Name')), str(link.get('Phone Number or URL'))
                if "elba" in n.lower(): st.markdown(f"<a href='mailto:{v}' class='btn-pink'>✉️ Email {n}</a>", unsafe_allow_html=True)
                elif "http" in v: st.markdown(f"<a href='{v}' class='btn-blue'>🔗 {n}</a>", unsafe_allow_html=True)
                else: st.markdown(f"<a href='tel:{re.sub(r'[^0-9]', '', v)}' class='btn-purple'>📞 Call {n}</a>", unsafe_allow_html=True)
        else: st.error("ID not found.")
except Exception as e: st.error(f"Sync Error: {e}")
