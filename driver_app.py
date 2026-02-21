import streamlit as st
import pandas as pd
import re
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURATION ---
ISSUE_FORM_URL = "https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAO__Ti7fnBUQzNYTTY1TjY3Uk0xMEwwTE9SUEZIWTRPRC4u"

st.set_page_config(page_title="Driver Portal", layout="centered", page_icon="🚛")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .header-box {background: #004a99; color: white; padding: 20px; border-radius: 12px; margin-bottom: 15px;}
    .badge-info {background: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #eee; text-align: center; height: 100%;}
    .val {display: block; font-weight: bold; color: #004a99; font-size: 16px;}
    .dispatch-box {border: 2px solid #d35400; padding: 15px; border-radius: 12px; background: #fffcf9; margin-bottom: 15px;}
    .peoplenet-box {background: #2c3e50; color: white; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 20px;}
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=5) 
def load_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7yF5pvuOjzm0xdRwHrFj8ByzGZ3kh1Iqmyw8pSdegEUUVeb3qSLpd1PDuWD1cUg/pub?output=csv"
    
    roster_gid = "1261782560" 
    schedule_gid = "1908585361" 
    dispatch_gid = "1123038440" 
    quicklinks_gid = "489255872" 
    
    def get_sheet(gid):
        url = f"{base_url}&gid={gid}&cache_bust={int(time.time())}"
        df = pd.read_csv(url, low_memory=False)
        df.columns = df.columns.str.strip()
        return df
    
    return get_sheet(roster_gid), get_sheet(dispatch_gid), get_sheet(schedule_gid), get_sheet(quicklinks_gid)

# --- FORMATTING HELPERS ---
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
    st.title("🚛 CPC Driver Portal")
    
    target_id = st.text_input("Enter Employee ID", type="password")

    if target_id:
        u_id = clean_num(target_id)
        roster_df['match_id'] = roster_df['Employee #'].apply(clean_num)
        driver_match = roster_df[roster_df['match_id'] == u_id]

        if not driver_match.empty:
            driver = driver_match.iloc[0]
            route_num = clean_num(driver.get('Route', ''))
            
            # 1. HEADER
            st.markdown(f"<div class='header-box'><div style='font-size:24px; font-weight:bold;'>{driver.get('Driver Name', driver.get('Driver  Name', 'Driver'))}</div><div style='font-size:14px;'>ID: {u_id} | Route: {route_num}</div></div>", unsafe_allow_html=True)

            # 2. EXPIRATIONS
            dot_count, dot_msg = get_renewal_status(driver.get('DOT Physical Expires'))
            cdl_count, cdl_msg = get_renewal_status(driver.get('DL Expiration Date'))
            
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='badge-info'>DOT Exp<span class='val'>{format_date(driver.get('DOT Physical Expires'))}</span><small>{dot_count}<br><b style='color:red;'>{dot_msg}</b></small></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='badge-info'>CDL Exp<span class='val'>{format_date(driver.get('DL Expiration Date'))}</span><small>{cdl_count}<br><b style='color:red;'>{cdl_msg}</b></small></div>", unsafe_allow_html=True)
            
            c3, c4 = st.columns(2)
            c3.markdown(f"<div class='badge-info'>SmartDrive Score<span class='val'>{driver.get('SmartDrive Score', 'N/A')}</span></div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='badge-info'>PTO/Leave<span class='val'>{driver.get('Next Leave Type', 'None')}</span></div>", unsafe_allow_html=True)

            st.info(f"**Tenure:** {calculate_tenure(driver.get('Hire Date'))}")

            # 3. DISPATCH
            dispatch_df['route_match'] = dispatch_df.iloc[:, 0].apply(clean_num)
            d_info = dispatch_df[dispatch_df['route_match'] == route_num]
            if not d_info.empty:
                r_data = d_info.iloc[0]
                dispatch_html = f"<div class='dispatch-box'><h3 style='margin:0; color:#d35400; font-size:12px;'>DISPATCH COMMENTS</h3><div style='font-size:18px; font-weight:bold; color:#d35400;'>{r_data.get('Comments', 'No Comments')}</div><div style='margin-top:8px;'><b>Trailers:</b> {r_data.get('1st Trailer', 'N/A')} / {r_data.get('2nd Trailer', 'N/A')}</div></div>"
                st.markdown(dispatch_html, unsafe_allow_html=True)

            # 4. PEOPLENET
            p_id, p_pw = clean_num(driver.get('PeopleNet ID')), str(driver.get('PeopleNet Password', ''))
            st.markdown(f"<div class='peoplenet-box'><div style='font-size:12px;'>PeopleNet Login</div><div style='font-size:16px; font-weight:bold;'>ID: {p_id} | PW: {p_pw}</div></div>", unsafe_allow_html=True)

            # 5. SCHEDULE STOPS
            schedule_df['route_match'] = schedule_df.iloc[:, 0].apply(clean_num)
            my_stops = schedule_df[schedule_df['route_match'] == route_num]
            
            if not my_stops.empty:
                st.write("### Today's Stops")
                for _, stop in my_stops.iterrows():
                    addr = str(stop.get('Store Address', 'No Address'))
                    raw_sid = clean_num(stop.get('Store ID'))
                    sid = raw_sid.zfill(5) if raw_sid else ""
                    arrival = stop.get('Arrival time', 'TBD')
                    
                    if addr != "nan" and len(addr) > 5:
                        with st.expander(f"📍 Stop: {sid if sid else 'Relay'} ({arrival})", expanded=True):
                            st.write(f"**Arrival:** {arrival} | **Departure:** {stop.get('Departure Time', 'TBD')}")
                            st.write(f"**Address:** {addr}")
                            
                            # ACTION BUTTONS GRID
                            col_a, col_b = st.columns(2)
                            clean_addr = addr.replace(' ','+').replace('\n','')
                            
                            with col_a:
                                # STORE TRACKER (Pulls SID dynamically for each stop)
                                if sid:
                                    tracker_url = f"tel:8008710204,1,,88012#,,{sid},#,,,1,,,1"
                                    st.link_button("📞 Store Tracker", tracker_url, use_container_width=True)
                                
                                st.link_button("🌎 Google Maps", f"https://www.google.com/maps/search/?api=1&query={clean_addr}", use_container_width=True)
                            
                            with col_b:
                                st.link_button("🚛 Truck Map", f"truckmap://navigate?q={clean_addr}", use_container_width=True)
                                
                                if sid:
                                    st.link_button(f"🗺️ View Store Map ({sid})", f"https://wg.cpcfact.com/store-{sid}/", use_container_width=True)
                            
                            # REPORT ISSUE (Full width below navigation)
                            st.link_button("🚨 Report Issue", ISSUE_FORM_URL, use_container_width=True)

            # 6. QUICK LINKS
            st.divider()
            st.subheader("🔗 Quick Links")
            for _, link in ql_df.iterrows():
                name = str(link.get('Name', ''))
                url = str(link.get('Phone Number or URL', ''))
                if url != "nan" and url != "":
                    st.link_button(name, url, use_container_width=True)

        else:
            st.error("Employee ID not found.")

except Exception as e:
    st.error(f"Sync Error: {e}")