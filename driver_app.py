import streamlit as st
import pandas as pd
import re
import time
import urllib.parse
from datetime import datetime
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh 

# --- 1. CONFIG & REFRESH ---
st_autorefresh(interval=60000, key="datarefresh")
st.set_page_config(page_title="CPC Portal", layout="centered", page_icon="🚛")

# --- 2. GLOBAL STYLES (High Contrast & Android Fixes) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background-color: #004a99 !important; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    .safety-box {background-color: #fff4f4 !important; border: 3px solid #cc0000 !important; padding: 25px; border-radius: 12px; margin-bottom: 20px; color: #1a1a1a !important;}
    .safety-box h2 { color: #cc0000 !important; margin-top: 0; }
    .safety-box p { font-size: 20px !important; line-height: 1.5 !important; color: #1a1a1a !important; }
    .btn-confirm {display: block !important; width: 100% !important; padding: 20px 0px !important; border-radius: 12px !important; text-align: center !important; font-weight: bold !important; font-size: 22px !important; text-decoration: none !important; color: white !important; margin-bottom: 15px !important; background-color: #107c10 !important; border: 3px solid #ffffff !important;}
    .stop-detail-card {background-color: #f0f2f6 !important; color: #1a1a1a !important; padding: 15px; border-radius: 10px; margin-bottom: 12px; border-left: 6px solid #004a99 !important;}
    .dispatch-box {border: 2px solid #d35400 !important; padding: 20px; border-radius: 12px; background-color: #fffcf9 !important; margin-bottom: 20px; color: #1a1a1a !important;}
    .peoplenet-box {background-color: #2c3e50 !important; color: white !important; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;}
    .peoplenet-val {font-size: 22px; font-weight: bold; color: #3498db !important;}
    .badge-info {background: #f8f9fa !important; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; color: #333 !important; margin-bottom: 10px;}
    .val {display: block; font-weight: bold; color: #004a99 !important; font-size: 24px;}
    .btn-blue, .btn-green, .btn-red, .btn-sms, .btn-tracker {display: block !important; width: 100% !important; padding: 15px 0px !important; border-radius: 10px !important; text-align: center !important; font-weight: bold !important; font-size: 18px !important; text-decoration: none !important; color: white !important; margin-bottom: 8px !important; border: none !important;}
    .btn-blue {background-color: #007bff !important;}
    .btn-green {background-color: #28a745 !important;}
    .btn-red {background-color: #dc3545 !important;}
    input { font-size: 24px !important; height: 60px !important; color: #000000 !important; background-color: #ffffff !important; -webkit-text-fill-color: #000000 !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. HELPERS ---
def convert_mt_to_pt(time_str, address):
    if not time_str or ',' not in str(time_str): return time_str
    MT_CITIES = {'PHOENIX', 'TUCSON', 'MESA', 'SCOTTSDALE', 'GILBERT', 'CHANDLER', 'GLENDALE', 'PEORIA', 'SURPRISE', 'BUCKEYE', 'GOODYEAR', 'APACHE JUNCTION', 'GOLD CANYON', 'CASA GRANDE', 'MARANA', 'ORO VALLEY', 'GREEN VALLEY', 'PRESCOTT', 'ANTHEM', 'KINGMAN', 'ALBUQUERQUE', 'SANTA FE', 'RIO RANCHO', 'GRANTS', 'GALLUP', 'SILVER CITY', 'DEMING', 'ESPANOLA', 'LOS RANCHOS', 'SALT LAKE CITY', 'OREM', 'TAYLORSVILLE', 'KAYSVILLE', 'WOODS CROSS', 'TOOELE', 'HERRIMAN', 'WEST JORDAN', 'HURRICANE', 'CEDAR CITY', 'PLEASANT GROVE', 'ROY', 'SYRACUSE', 'CLINTON', 'OGDEN', 'LOGAN'}
    DAYS_MAP = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
    DAYS_LIST = list(DAYS_MAP.keys())
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
    DAYS_MAP = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
    try:
        t, d = str(time_str).split(',')
        h, m = map(int, t.split(':'))
        return (DAYS_MAP[d.strip()], h, m)
    except: return (9, 0, 0)

def clean_num(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return ""
    return re.sub(r'\D', '', str(val).split('.')[0])

def clean_id_alphanumeric(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return ""
    return str(val).strip()

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

def calculate_tenure(hire_date_val):
    if pd.isna(hire_date_val): return "N/A"
    try:
        hire_date = pd.to_datetime(hire_date_val)
        diff = relativedelta(datetime.now(), hire_date)
        return f"{hire_date.strftime('%B %d, %Y')} ({diff.years} yrs, {diff.months} mos)"
    except: return str(hire_date_val)

def safe_get(row, col_name, index, default=""):
    if col_name in row: return str(row[col_name]).strip()
    if len(row) > index: return str(row.iloc[index]).strip()
    return default

@st.cache_data(ttl=0)
def load_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7yF5pvuOjzm0xdRwHrFj8ByzGZ3kh1Iqmyw8pSdegEUUVeb3qSLpd1PDuWD1cUg/pub?output=csv"
    gids = {"roster": "1261782560", "dispatch": "1123038440", "schedule": "1908585361", "links": "489255872", "safety": "1978744657"}
    def get_s(gid):
        try:
            df = pd.read_csv(f"{base_url}&gid={gid}&cb={int(time.time())}", low_memory=False)
            df.columns = df.columns.str.strip()
            return df
        except: return pd.DataFrame()
    return get_s(gids["roster"]), get_s(gids["dispatch"]), get_s(gids["schedule"]), get_s(gids["links"]), get_s(gids["safety"])

# --- 4. MAIN APP ---
try:
    roster, dispatch_notes_df, schedule, quick_links, safety_df = load_all_data()
    st.markdown("<h1 style='font-size: 38px;'>🚛 CPC Portal</h1>", unsafe_allow_html=True)
    st.caption(f"Last sync: {datetime.now().strftime('%H:%M:%S')}")

    user_input = st.text_input("Enter ID or 'dispatch'", value="").strip().lower()

    if user_input == "dispatch":
        st.subheader("📋 Dispatch Dashboard (PT)")
        phones = {}
        for _, row in roster.iterrows():
            name = safe_get(row, 'Driver Name', 0).upper()
            phone = clean_phone(safe_get(row, 'Cell Phone', 11))
            if name and phone:
                for n in name.split('/'): phones[n.strip()] = phone

        stops_list = []
        for _, row in schedule.iterrows():
            driver_name = safe_get(row, 'Driver Name', 0)
            arrival = safe_get(row, 'Arrival time', 8)
            if not driver_name or arrival in ('0', '-', '', 'nan'): continue
            addr = safe_get(row, 'Store Address', 5)
            pt_arr = convert_mt_to_pt(arrival, addr)
            pt_dep = convert_mt_to_pt(safe_get(row, 'Departure time', 9), addr)
            raw_sid = clean_num(safe_get(row, 'Store ID', 4))
            route = safe_get(row, 'Route', 1)
            tracker_raw = safe_get(row, 'Dialpad', 25)
            tracker = tracker_raw.replace('DIALPAD:', '').strip()
            stops_list.append({'driver': driver_name, 'arrival': pt_arr, 'departure': pt_dep, 'store': raw_sid.zfill(5), 'address': addr, 'sort': get_sort_val(pt_arr), 'tracker': tracker, 'route': route})
        
        stops_list.sort(key=lambda x: x['sort'])
        for s in stops_list:
            sms_links = ""
            for d in [name.strip() for name in s['driver'].split('/')]:
                p = phones.get(d.upper())
                if p:
                    body = f"Reminder: Arrival {s['arrival']} - Store {s['store']} ({s['address']}). Don't forget to arrive and depart in cheetah"
                    sms_links += f"<a class='btn-sms' href='sms:{p}?body={urllib.parse.quote(body)}'>Text {d}</a>"
            st.markdown(f"<div style='background: white !important; color: #1a1a1a !important; padding: 15px; border-radius: 12px; border-left: 8px solid #0f6cbd !important; margin-bottom: 12px;'><b>{s['driver']} — {s['arrival']} • {s['departure']}</b><br>Route {s['route']} • Store {s['store']}<br>{s['address']}<br>{sms_links} <a class='btn-tracker' href='tel:{s['tracker']}'>Dial Tracker</a></div>", unsafe_allow_html=True)

    elif user_input:
        roster['match_id'] = roster['Employee #'].apply(clean_num)
        match = roster[roster['match_id'] == user_input]

        if not match.empty:
            # --- STEP 1: MANDATORY SAFETY BRIEFING ---
            if f"safety_read_{user_input}" not in st.session_state: 
                st.session_state[f"safety_read_{user_input}"] = False

            if not st.session_state[f"safety_read_{user_input}"]:
                today_str = datetime.now().strftime("%m/%d/%Y")
                safety_msg = "Perform a thorough pre-trip inspection."
                if not safety_df.empty:
                    safety_match = safety_df[safety_df.iloc[:, 0].astype(str).str.contains(today_str, na=False)]
                    if not safety_match.empty: safety_msg = safety_match.iloc[0, 1]
                st.markdown(f"<div class='safety-box'><h2>⚠️ DAILY SAFETY REMINDER</h2><p><b>Date:</b> {today_str}</p><p>{safety_msg}</p></div>", unsafe_allow_html=True)
                if st.button("✅ I HAVE READ AND UNDERSTAND", use_container_width=True):
                    st.session_state[f"safety_read_{user_input}"] = True
                    st.rerun()
            else:
                # --- STEP 2: SHOW PORTAL DATA & ROUTE CONFIRMATION ---
                driver = match.iloc[0]
                d_name = safe_get(driver, 'Driver Name', 0)
                raw_route = safe_get(driver, 'Route', 1)
                route_num = clean_num(raw_route)
                
                st.markdown(f"<div class='header-box'><div style='font-size:32px; font-weight:bold;'>{d_name}</div>ID: {user_input} | Route: {raw_route}</div>", unsafe_allow_html=True)

                if f"route_confirmed_{user_input}" not in st.session_state:
                    st.session_state[f"route_confirmed_{user_input}"] = False

                if not st.session_state[f"route_confirmed_{user_input}"]:
                    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfnw_F7nGy4GbJlMlCxSSGXx86b8g5J6VhXRkz_ZvABr2fcMg/viewform?"
                    params = {"entry.534103007": d_name, "entry.726947479": user_input, "entry.316322786": raw_route}
                    full_url = form_url + urllib.parse.urlencode(params)
                    st.markdown(f'<a href="{full_url}" target="_blank" class="btn-confirm">🚛 CONFIRM ROUTE & START SHIFT</a>', unsafe_allow_html=True)
                    if st.button("Internal Confirmation (Bypass Form)"): 
                        st.session_state[f"route_confirmed_{user_input}"] = True
                        st.rerun()
                else:
                    st.success("✅ Shift Started and Route Confirmed.")

                # Compliance Cards
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
                    t1, t2 = str(r_data.get('1st Trailer', '')), str(r_data.get('2nd Trailer', ''))
                    trailers = t1 if t1 not in ('nan', '0', '') else ""
                    if t2 not in ('nan', '0', ''): trailers += f" / {t2}" if trailers else t2
                    st.markdown(f"<div class='dispatch-box'><h3>Dispatch Notes</h3><div style='font-size:24px; font-weight:bold; color:#d35400 !important; margin:10px 0;'>{r_data.get('Comments', 'None')}</div><div style='font-size:18px; color: #1a1a1a !important;'><b>Trailers:</b> {trailers if trailers else 'None assigned'}</div></div>", unsafe_allow_html=True)

                # ELD Login
                p_id = clean_id_alphanumeric(safe_get(driver, 'PeopleNet ID', 12))
                st.markdown(f"<div class='peoplenet-box'><div style='font-size:18px; margin-bottom:10px; opacity:0.8;'>PeopleNet / ELD Login</div><div style='display:flex; justify-content:space-around;'><div>ORG ID<br><span class='peoplenet-val'>3299</span></div><div>DRIVER ID<br><span class='peoplenet-val'>{p_id}</span></div><div>PASSWORD<br><span class='peoplenet-val'>{p_id}</span></div></div></div>", unsafe_allow_html=True)

                # Schedule
                st.markdown("<h3 style='font-size:28px;'>Daily Schedule</h3>", unsafe_allow_html=True)
                if not route_num and not safe_get(driver, 'Route', 1): st.warning("⚠️ Refer to Dispatch Email")
                elif not route_num: st.markdown(f"<div style='background-color:#e3f2fd !important; color: #0d47a1 !important; padding:20px; border-radius:10px; font-size:22px; font-weight:bold;'>📍 Assignment: {safe_get(driver, 'Route', 1)}</div>", unsafe_allow_html=True)
                else:
                    schedule['route_match'] = schedule.iloc[:, 0].apply(clean_num)
                    my_stops = schedule[schedule['route_match'] == route_num]
                    if my_stops.empty: st.warning("⚠️ Refer to Dispatch Email")
                    else:
                        for _, stop in my_stops.iterrows():
                            raw_sid = clean_num(safe_get(stop, 'Store ID', 4))
                            sid_5, addr = raw_sid.zfill(5), safe_get(stop, 'Store Address', 5)
                            arr, dep = safe_get(stop, 'Arrival time', 8), safe_get(stop, 'Departure time', 9)
                            with st.expander(f"📍 Store {sid_5 if raw_sid != '0' else 'Relay'} (Arr: {arr})", expanded=True):
                                st.markdown(f"<div class='stop-detail-card'><table style='width:100%; color: #1a1a1a !important;'><tr><td style='width:40%'><b>Store ID:</b></td><td>{sid_5}</td></tr><tr><td><b>Arrival:</b></td><td>{arr}</td></tr><tr><td><b>Departure:</b></td><td>{dep}</td></tr><tr><td><b>Address:</b></td><td>{addr}</td></tr></table></div>", unsafe_allow_html=True)
                                
                                tracker_url = f"tel:8008710204,1,,88012#,,{raw_sid},#,,,1,,,1"
                                maps_url = f"https://www.google.com/maps/search/?api=1&query={addr.replace(' ','+')}"
                                truck_url = f"truckmap://navigate?q={addr.replace(' ','+')}"
                                s_map_url = f"https://wg.cpcfact.com/store-{sid_5}/"
                                issue_url = "https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAO__Ti7fnBUQzNYTTY1TjY3Uk0xMEwwTE9SUEZIWTRPRC4u"
                                
                                st.markdown(f"""
                                <table style='width:100%; border:none;'>
                                <tr><td><a href='{tracker_url}' class='btn-green'>📞 Store Tracker</a></td>
                                <td><a href='{maps_url}' class='btn-blue'>🌎 Google</a></td></tr>
                                <tr><td><a href='{truck_url}' class='btn-blue'>🚛 TruckMap</a></td>
                                <td><a href='{s_map_url}' class='btn-blue'>🗺️ Store Map</a></td></tr>
                                </table><a href='{issue_url}' class='btn-red'>🚨 Report Issue</a>
                                """, unsafe_allow_html=True)
                
                # QUICK LINKS
                st.divider()
                for _, link in quick_links.iterrows():
                    n, v = str(link.get('Name')), str(link.get('Phone Number or URL'))
                    if "elba" in n.lower(): st.markdown(f"<a href='mailto:{v}' class='btn-pink'>✉️ Email {n}</a>", unsafe_allow_html=True)
                    elif "http" in v: st.markdown(f"<a href='{v}' class='btn-blue'>🔗 {n}</a>", unsafe_allow_html=True)
                    else: st.markdown(f"<a href='tel:{re.sub(r'[^0-9]', '', v)}' class='btn-purple'>📞 Call {n}</a>", unsafe_allow_html=True)
        else: st.error("ID not found.")
except Exception as e: st.error(f"Sync Error: {e}")
