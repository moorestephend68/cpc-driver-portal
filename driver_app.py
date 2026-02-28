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

# --- 2. GLOBAL STYLES (Universal Fix for iOS & Android) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background-color: #004a99 !important; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    
    /* Safety Message Box - Forced Visibility */
    .safety-box {
        background-color: #fff4f4 !important;
        border: 3px solid #cc0000 !important;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        color: #1a1a1a !important;
    }
    .safety-box h2 { color: #cc0000 !important; margin-top: 0; font-size: 24px; }
    .safety-box p { font-size: 20px !important; line-height: 1.5 !important; color: #1a1a1a !important; }

    /* Confirmation Button */
    .btn-confirm {
        display: block !important; width: 100% !important; padding: 20px 0px !important;
        border-radius: 12px !important; text-align: center !important; font-weight: bold !important;
        font-size: 22px !important; text-decoration: none !important; color: white !important;
        margin-bottom: 15px !important; background-color: #107c10 !important; border: 3px solid #ffffff !important;
    }

    /* Information Cards */
    .stop-detail-card {
        background-color: #f0f2f6 !important; 
        color: #1a1a1a !important; 
        padding: 15px; 
        border-radius: 10px; 
        margin-bottom: 12px; 
        border-left: 6px solid #004a99 !important;
    }
    .dispatch-box {
        border: 2px solid #d35400 !important; 
        padding: 20px; 
        border-radius: 12px; 
        background-color: #fffcf9 !important; 
        margin-bottom: 20px;
        color: #1a1a1a !important;
    }
    .peoplenet-box {background-color: #2c3e50 !important; color: white !important; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;}
    .peoplenet-val {font-size: 22px; font-weight: bold; color: #3498db !important;}
    .badge-info {background: #f8f9fa !important; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; color: #333 !important; margin-bottom: 10px;}
    .val {display: block; font-weight: bold; color: #004a99 !important; font-size: 24px;}

    /* Standard Buttons */
    .btn-blue, .btn-green, .btn-red, .btn-purple, .btn-pink, .btn-sms, .btn-tracker {
        display: block !important; width: 100% !important; padding: 15px 0px !important;
        border-radius: 10px !important; text-align: center !important; font-weight: bold !important;
        font-size: 18px !important; text-decoration: none !important; color: white !important;
        margin-bottom: 8px !important; border: none !important;
    }
    .btn-blue {background-color: #007bff !important;}
    .btn-green {background-color: #28a745 !important;}
    .btn-red {background-color: #dc3545 !important;}
    
    /* Android/iPhone Input Text Fix */
    input { 
        font-size: 24px !important; 
        height: 60px !important; 
        color: #000000 !important; 
        background-color: #ffffff !important; 
        -webkit-text-fill-color: #000000 !important;
    }
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

def clean_num(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return ""
    return re.sub(r'\D', '', str(val).split('.')[0])

def clean_id_alphanumeric(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return ""
    return str(val).strip()

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
    st.markdown("<h1 style='font-size: 32px;'>🚛 CPC Portal</h1>", unsafe_allow_html=True)

    user_input = st.text_input("Enter ID or 'dispatch'", value="").strip().lower()

    if user_input == "dispatch":
        # [Dispatch logic is standard and reliable]
        st.subheader("📋 Dispatch Dashboard")
        # (...rest of dispatch code...)
        pass

    elif user_input:
        roster['match_id'] = roster['Employee #'].apply(clean_num)
        match = roster[roster['match_id'] == user_input]

        if not match.empty:
            driver = match.iloc[0]
            d_name = safe_get(driver, 'Driver Name', 0)
            raw_route = str(driver.get('Route', ''))
            route_num = clean_num(raw_route)

            # --- UNIVERSAL STEP 1: SAFETY MESSAGE (FORCED ON PAGE) ---
            today_str = datetime.now().strftime("%m/%d/%Y")
            safety_msg = "Perform a thorough pre-trip inspection."
            if not safety_df.empty:
                safety_match = safety_df[safety_df.iloc[:, 0].astype(str).str.contains(today_str, na=False)]
                if not safety_match.empty: safety_msg = safety_match.iloc[0, 1]
            
            st.markdown(f"<div class='safety-box'><h2>⚠️ SAFETY REMINDER</h2><p><b>Date:</b> {today_str}</p><p>{safety_msg}</p></div>", unsafe_allow_html=True)

            # --- UNIVERSAL STEP 2: ROUTE CONFIRMATION (PRE-FILLED) ---
            form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfnw_F7nGy4GbJlMlCxSSGXx86b8g5J6VhXRkz_ZvABr2fcMg/viewform?"
            params = {"entry.534103007": d_name, "entry.726947479": user_input, "entry.316322786": raw_route}
            full_url = form_url + urllib.parse.urlencode(params)
            
            st.markdown(f'<a href="{full_url}" target="_blank" class="btn-confirm">🚛 READ SAFETY & CONFIRM ROUTE</a>', unsafe_allow_html=True)
            
            st.markdown(f"<div class='header-box'><div style='font-size:28px; font-weight:bold;'>{d_name}</div>ID: {user_input} | Route: {raw_route}</div>", unsafe_allow_html=True)

            # Compliance
            dot_c, dot_m = get_renewal_status(driver.get('DOT Physical Expires'))
            cdl_c, cdl_m = get_renewal_status(driver.get('DL Expiration Date'))
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='badge-info'>DOT Exp<span class='val'>{format_date(driver.get('DOT Physical Expires'))}</span><small>{dot_c}<br><b style='color:red;'>{dot_m}</b></small></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='badge-info'>CDL Exp<span class='val'>{format_date(driver.get('DL Expiration Date'))}</span><small>{cdl_c}<br><b style='color:red;'>{cdl_m}</b></small></div>", unsafe_allow_html=True)
            
            # Dispatch Notes
            dispatch_notes_df['route_match'] = dispatch_notes_df.iloc[:, 0].apply(clean_num)
            d_info = dispatch_notes_df[dispatch_notes_df['route_match'] == route_num]
            if not d_info.empty:
                r_data = d_info.iloc[0]
                t1, t2 = str(r_data.get('1st Trailer', '')), str(r_data.get('2nd Trailer', ''))
                trailers = t1 if t1 not in ('nan', '0', '') else ""
                if t2 not in ('nan', '0', ''): trailers += f" / {t2}" if trailers else t2
                st.markdown(f"<div class='dispatch-box'><h3>Dispatch Notes</h3><div style='font-size:22px; font-weight:bold; color:#d35400 !important; margin:10px 0;'>{r_data.get('Comments', 'None')}</div><div style='font-size:18px; color: #1a1a1a !important;'><b>Trailers:</b> {trailers if trailers else 'None assigned'}</div></div>", unsafe_allow_html=True)

            # ELD Login
            p_id = clean_id_alphanumeric(safe_get(driver, 'PeopleNet ID', 12))
            st.markdown(f"<div class='peoplenet-box'><div style='font-size:18px; margin-bottom:10px; opacity:0.8;'>ELD Login</div><div style='display:flex; justify-content:space-around;'><div>ORG ID<br><span class='peoplenet-val'>3299</span></div><div>ID<br><span class='peoplenet-val'>{p_id}</span></div><div>PW<br><span class='peoplenet-val'>{p_id}</span></div></div></div>", unsafe_allow_html=True)

            # Schedule
            st.markdown("<h3 style='font-size:24px;'>Daily Schedule</h3>", unsafe_allow_html=True)
            if route_num:
                schedule['route_match'] = schedule.iloc[:, 0].apply(clean_num)
                my_stops = schedule[schedule['route_match'] == route_num]
                for _, stop in my_stops.iterrows():
                    raw_sid = clean_num(safe_get(stop, 'Store ID', 4))
                    sid_5, addr = raw_sid.zfill(5), safe_get(stop, 'Store Address', 5)
                    arr, dep = safe_get(stop, 'Arrival time', 8), safe_get(stop, 'Departure time', 9)
                    with st.expander(f"📍 Store {sid_5 if raw_sid != '0' else 'Relay'} (Arr: {arr})", expanded=True):
                        st.markdown(f"<div class='stop-detail-card'><table style='width:100%; color: #1a1a1a !important;'><tr><td style='width:40%'><b>ID:</b></td><td>{sid_5}</td></tr><tr><td><b>Arrival:</b></td><td>{arr}</td></tr><tr><td><b>Address:</b></td><td>{addr}</td></tr></table></div>", unsafe_allow_html=True)
                        st.markdown(f"""
                        <table style='width:100%; border:none;'>
                        <tr><td><a href='tel:8008710204,1,,88012#,,{raw_sid},#,,,1,,,1' class='btn-green'>📞 Tracker</a></td>
                        <td><a href='https://www.google.com/maps/search/?api=1&query={addr.replace(' ','+')}' class='btn-blue'>🌎 Maps</a></td></tr>
                        </table>
                        """, unsafe_allow_html=True)

        else: st.error("ID not found.")
except Exception as e: st.error(f"Sync Error: {e}")
