import streamlit as st
import pandas as pd
import re
import time
import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. ANDROID INSTALL LOGIC (PWA) ---
# This forces Chrome to see the 'Install App' option for https://cpc-driver.streamlit.app/
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

# Injecting the manifest into the browser header
st.markdown(f"""
    <head>
        <link rel="manifest" href="data:application/manifest+json;base64,{manifest_base64}">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
    </head>
    """, unsafe_allow_html=True)

# --- 2. CUSTOM CSS (FIXED COLORS & LARGER FONTS) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background: #004a99; color: white; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    .badge-info {background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; height: 100%; font-size: 20px !important;}
    .val {display: block; font-weight: bold; color: #004a99; font-size: 26px !important;}
    .dispatch-box {border: 3px solid #d35400; padding: 20px; border-radius: 12px; background: #fffcf9; margin-bottom: 15px; font-size: 22px !important;}
    .peoplenet-box {background: #2c3e50; color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; font-size: 24px !important;}
    
    /* Button Styles - FORCED WHITE TEXT FOR ANDROID VISIBILITY */
    .btn-blue, .btn-pink, .btn-purple, .btn-green {
        padding: 18px !important; 
        font-size: 22px !important; 
        border-radius: 10px; 
        text-align: center; 
        font-weight: bold; 
        margin-bottom: 10px; 
        text-decoration: none; 
        display: block;
        color: white !important; /* Forces white letters on all backgrounds */
    }
    .btn-blue {background-color: #007bff !important;}
    .btn-pink {background-color: #e83e8c !important;}
    .btn-purple {background-color: #6f42c1 !important;}
    .btn-green {background-color: #28a745 !important;}
    
    /* Larger Input for Android visibility */
    input { font-size: 24px !important; height: 60px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURATION ---
ISSUE_FORM_URL = "https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAO__Ti7fnBUQzNYTTY1TjY3Uk0xMEwwTE9SUEZIWTRPRC4u"

@st.cache_data(ttl=5) 
def load_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7yF5pvuOjzm0xdRwHrFj8ByzGZ3kh1Iqmyw8pSdegEUUVeb3qSLpd1PDuWD1cUg/pub?output=csv"
    roster_gid, schedule_gid, dispatch_gid, ql_gid = "1261782560", "1908585361", "1123038440", "489255872"
    
    def get_sheet(gid):
        url = f"{base_url}&gid={gid}&cache_bust={int(time.time())}"
        df = pd.read_csv(url, low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    return get_sheet(roster_gid), get_sheet(dispatch_gid), get_sheet(schedule_gid), get_sheet(ql_gid)

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

# --- MAIN APP ---
try:
    roster_df, dispatch_df, schedule_df, ql_df = load_all_data()
    st.markdown("<h1 style='font-size: 42px;'>🚛 Driver Portal</h1>", unsafe_allow_html=True)
    
    # Label restored to "Employee ID" but using number_input for Android keypad
    input_val = st.number_input("Enter Employee ID", min_value=0, step=1, value=None, placeholder="Type Numbers Only")

    if input_val:
        u_id = str(int(input_val))
        roster_df['match_id'] = roster_df['Employee #'].apply(clean_num)
        driver_match = roster_df[roster_df['match_id'] == u_id]

        if not driver_match.empty:
            driver = driver_match.iloc[0]
            route_num = clean_num(driver.get('Route', ''))
            
            # 1. PROFILE HEADER
            st.markdown(f"<div class='header-box'><div style='font-size:32px; font-weight:bold;'>{driver.get('Driver Name', driver.get('Driver  Name', 'Driver'))}</div><div style='font-size:22px;'>ID: {u_id} | Route: {route_num}</div></div>", unsafe_allow_html=True)

            # 2. COMPLIANCE GRID
            dot_count, dot_msg = get_renewal_status(driver.get('DOT Physical Expires'))
            cdl_count, cdl_msg = get_renewal_status(driver.get('DL Expiration Date'))
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='badge-info'>DOT Exp<span class='val'>{format_date(driver.get('DOT Physical Expires'))}</span><small>{dot_count}<br><b style='color:red;'>{dot_msg}</b></small></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='badge-info'>CDL Exp<span class='val'>{format_date(driver.get('DL Expiration Date'))}</span><small>{cdl_count}<br><b style='
