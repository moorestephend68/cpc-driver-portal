import streamlit as st
import pandas as pd
import re
import time
import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. ANDROID INSTALL LOGIC ---
manifest_json = """
{
  "name": "CPC Driver Portal",
  "short_name": "CPC Portal",
  "start_url": "https://cpc-driver.streamlit.app/",
  "display": "standalone",
  "theme_color": "#004a99",
  "background_color": "#ffffff",
  "icons": [{"src": "https://cdn-icons-png.flaticon.com/512/2554/2554979.png", "sizes": "512x512", "type": "image/png"}]
}
"""
manifest_base64 = base64.b64encode(manifest_json.encode()).decode()

st.set_page_config(page_title="CPC Driver Portal", layout="centered", page_icon="🚛")

st.markdown(f"""
    <head>
        <link rel="manifest" href="data:application/manifest+json;base64,{manifest_base64}">
        <meta name="mobile-web-app-capable" content="yes">
    </head>
    """, unsafe_allow_html=True)

# --- 2. THE "FORCE EVERYTHING" CSS ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background-color: #004a99 !important; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    .badge-info {background: #f8f9fa !important; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; height: 100%; color: #333 !important; margin-bottom: 10px;}
    .val {display: block; font-weight: bold; color: #004a99 !important; font-size: 26px !important;}
    .dispatch-box {border: 3px solid #d35400 !important; padding: 20px; border-radius: 12px; background-color: #fffcf9 !important; margin-bottom: 15px;}
    .peoplenet-box {background-color: #2c3e50 !important; color: white !important; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;}
    
    .btn-blue, .btn-green, .btn-pink, .btn-purple, .btn-red {
        display: block !important; width: 100% !important; padding: 18px 0px !important;
        border-radius: 10px !important; text-align: center !important; font-weight: bold !important;
        font-size: 19px !important; text-decoration: none !important; color: #ffffff !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.2) !important; border: none !important;
    }
    .btn-blue {background-color: #007bff !important;}
    .btn-green {background-color: #28a745 !important;}
    .btn-pink {background-color: #e83e8c !important;}
    .btn-purple {background-color: #6f42c1 !important;}
    .btn-red {background-color: #dc3545 !important; margin-top: 10px !important;}
    
    #store-map-btn { background-color: #007bff !important; color: white !important; }
    input { font-size: 24px !important; height: 60px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA LOADING & HELPERS ---
ISSUE_FORM_URL = "https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAO__Ti7fnBUQzNYTTY1TjY3Uk0xMEwwTE9SUEZIWTRPRC4u"

@st.cache_data(ttl=5) 
def load_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7yF5pvuOjzm0xdRwHrFj8ByzGZ3kh1Iqmyw8pSdegEUUVeb3qSLpd1PDuWD1cUg/pub?output=csv"
    gids = {"roster": "1261782560", "dispatch": "1123038440", "schedule": "1908585361", "links": "489255872"}
    
    def get_sheet(gid):
        # Cache-busting: prevents Google from serving old data
        url = f"{base_url}&gid={gid}&cb={int(time.time())}"
        df = pd.read_csv(url, low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    return get_sheet(gids["roster"]), get_sheet(gids["dispatch"]), get_sheet(gids["schedule"]), get_sheet(gids["links"])

def clean_num(val):
    if pd.isna(val) or str(val).strip() == "" or str(val).lower() == 'nan': return ""
    return re.sub(r'\D', '', str(val).split('.')[0])

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
        now = datetime.now()
        diff = relativedelta(exp_date, now)
        days_left = (exp_date - now).days
        countdown = f"{diff.years}y {diff.months}m {diff.days}d"
        msg = "⚠️ RENEW NOW" if days_left <= 60 else ""
        return countdown, msg
    except: return "N/A", ""

def calculate_tenure(hire_date_val):
    if pd.isna(hire_date_val): return "N/A"
    try:
        hire_date = pd.to_datetime(hire_date_val)
        diff = relativedelta(datetime.now(), hire_date)
        return f"{hire_date.strftime('%B %d, %Y')} ({diff.years} yrs, {diff.months} mos)"
    except: return str(hire_date_val)

# --- 4. MAIN APP ---
try:
    # Small invisible "force refresh" happens on every load via ttl=5
    roster, dispatch, schedule, links = load_all_data()
    
    st.markdown("<h1 style='font-size: 42px;'>🚛 Driver Portal</h1>", unsafe_allow_html=True)
    
    input_val = st.number_input("Enter Employee ID", min_value=0, step=1, value=None)

    if input_val:
        u_id = str(int(input_val))
        roster['match_id'] = roster['Employee #'].apply(clean_num)
        match = roster[roster['match_id'] == u_id]

        if not match.empty:
            driver = match.iloc[0]
            route_num = clean_num(driver.get('Route', ''))
            d_name = driver.get('Driver Name', driver.iloc[0])
            
            # HEADER
            st.markdown(f"<div class='header-box'><div style='font-size:36px; font-weight:bold;'>{d_name}</div><div style='font-size:22px;'>ID: {u_id} | Route: {route_num}</div></div>", unsafe_allow_html=True)

            # COMPLIANCE GRID
            dot_count, dot_msg = get_renewal_status(driver.get('DOT Physical Expires'))
            cdl_count, cdl_msg = get_renewal_status(driver.get('DL Expiration Date'))
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='badge-info'>DOT Exp<span class='val'>{format_date(driver.get('DOT Physical Expires'))}</span><small>{dot_count}<br><b style='color:red;'>{dot_msg}</b></small></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='badge-info'>CDL Exp<span class='val'>{format_date(driver.get('DL Expiration Date'))}</span><small>{cdl_count}<br><b style='color:red;'>{cdl_msg}</b></small></div>", unsafe_allow_html=True)
            st.info(f"**Tenure:** {calculate_tenure(driver.get('Hire Date'))}")

            # DISPATCH NOTES
            dispatch['route_match'] = dispatch.iloc[:, 0].apply(clean_num)
            d_info = dispatch[dispatch['route_match'] == route_num]
            if not d_info.empty:
                r_data = d_info.iloc[0]
                st.markdown(f"<div class='dispatch-box'><h3 style='margin:0; color:#d35400; font-size:18px;'>DISPATCH NOTES</h3><div style='font-size:24px; font-weight:bold; color:#d35400;'>{r_data.get('Comments', 'None')}</div><div style='margin-top:10px;'><b>Trailers:</b> {r_data.get('1st Trailer')} / {r_data.get('2nd Trailer')}</div></div>", unsafe_allow_html=True)

            # PEOPLENET
            p_id, p_pw = clean_num(driver.get('PeopleNet ID')), str(driver.get('PeopleNet Password', ''))
            st.markdown(f"<div class='peoplenet-box'><div style='font-size:20px;'>PeopleNet Login</div><div style='font-size:28px; font-weight:bold;'>ID: {p_id} | PW: {p_pw}</div></div>", unsafe_allow_html=True)

            # DAILY SCHEDULE (BUTTON GRID)
            schedule['route_match'] = schedule.iloc[:, 0].apply(clean_num)
            my_stops = schedule[schedule['route_match'] == route_num]
            if not my_stops.empty:
                st.markdown("<h3 style='font-size:30px;'>Daily Schedule</h3>", unsafe_allow_html=True)
                for _, stop in my_stops.iterrows():
                    raw_sid = clean_num(stop.get('Store ID'))
                    sid_6, sid_5 = raw_sid.zfill(6), raw_sid.zfill(5)
                    addr = str(stop.get('Store Address'))
                    clean_addr = addr.replace(' ','+').replace('\n','')
                    arrival = stop.get('Arrival time')
                    
                    with st.expander(f"📍 Stop: {sid_5 if raw_sid != '0' else 'Relay'} ({arrival})", expanded=True):
                        st.write(f"**Address:** {addr}")
                        st.markdown(f"""
                        <table style="width:100%; border:none; border-collapse:collapse; background:transparent;">
                          <tr>
                            <td style="width:50%; padding:5px; border:none;">
                              <a href="tel:8008710204,1,,88012#,,{sid_6},#,,,1,,,1" class="btn-green">📞 Store Tracker</a>
                            </td>
                            <td style="width:50%; padding:5px; border:none;">
                              <a href="https://www.google.com/maps/search/?api=1&query={clean_addr}" class="btn-blue">🌎 Google</a>
                            </td>
                          </tr>
                          <tr>
                            <td style="width:50%; padding:5px; border:none;">
                              <a href="truckmap://navigate?q={clean_addr}" class="btn-blue">🚛 TruckMap</a>
                            </td>
                            <td style="width:50%; padding:5px; border:none;">
                              <a id="store-map-btn" href="https://wg.cpcfact.com/store-{sid_5}/" class="btn-blue">🗺️ Store Map</a>
                            </td>
                          </tr>
                        </table>
                        <a href="{ISSUE_FORM_URL}" class="btn-red">🚨 Report Issue</a>
                        """, unsafe_allow_html=True)

            # QUICK LINKS
            st.divider()
            for _, link in links.iterrows():
                name, val = str(link.get('Name')), str(link.get('Phone Number or URL'))
                if val != "nan" and val != "":
                    if "elba" in name.lower():
                        st.markdown(f'<a href="mailto:{val}" class="btn-pink">✉️ Email {name}</a>', unsafe_allow_html=True)
                    elif "http" not in val and any(c.isdigit() for c in val):
                        st.markdown(f'<a href="tel:{re.sub(r"[^0-9]", "", val)}" class="btn-purple">📞 Call {name}</a>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<a href="{val}" target="_blank" class="btn-blue">🔗 {name}</a>', unsafe_allow_html=True)
        else:
            st.error("Employee ID not found.")
except Exception as e:
    st.error(f"Error: {e}")
