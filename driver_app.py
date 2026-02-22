import streamlit as st
import pd
import re
import time
import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh 

# --- 1. AUTO-REFRESH TIMER (1 Minute) ---
st_autorefresh(interval=60000, key="datarefresh")

# --- 2. CONFIG & PWA LOGIC ---
st.set_page_config(page_title="CPC Driver Portal", layout="centered", page_icon="🚛")

# --- 3. CSS STYLING ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background-color: #004a99 !important; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    .badge-info {background: #f8f9fa !important; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; height: 100%; color: #333 !important; margin-bottom: 10px;}
    .val {display: block; font-weight: bold; color: #004a99 !important; font-size: 26px !important;}
    .dispatch-box {border: 3px solid #d35400 !important; padding: 20px; border-radius: 12px; background-color: #fffcf9 !important; margin-bottom: 15px;}
    .peoplenet-box {background-color: #2c3e50 !important; color: white !important; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;}
    .peoplenet-val {font-size: 22px; font-weight: bold; color: #3498db;}
    
    .btn-blue, .btn-green, .btn-pink, .btn-purple, .btn-red {
        display: block !important; width: 100% !important; padding: 18px 0px !important;
        border-radius: 10px !important; text-align: center !important; font-weight: bold !important;
        font-size: 19px !important; text-decoration: none !important; color: #ffffff !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.2) !important; border: none !important;
    }
    .btn-blue {background-color: #007bff !important;}
    .btn-green {background-color: #28a745 !important;}
    .btn-red {background-color: #dc3545 !important; margin-top: 10px !important;}
    
    #store-map-btn { background-color: #007bff !important; color: white !important; }
    input { font-size: 24px !important; height: 60px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. DATA HELPERS ---
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

def clean_num(val):
    if pd.isna(val) or str(val).strip() == "" or str(val).lower() == 'nan': return ""
    return re.sub(r'\D', '', str(val).split('.')[0])

def clean_id(val):
    if pd.isna(val) or str(val).strip() == "" or str(val).lower() == 'nan': return ""
    return str(val).strip()

# --- 5. MAIN APP ---
try:
    roster, dispatch, schedule, links = load_all_data()
    st.markdown("<h1 style='font-size: 42px; margin-bottom: 0;'>🚛 Driver Portal</h1>", unsafe_allow_html=True)
    st.caption(f"🕒 Last sync: {datetime.now().strftime('%H:%M:%S')}")
    
    input_val = st.number_input("Enter Employee ID", min_value=0, step=1, value=None)

    if input_val:
        u_id = str(int(input_val))
        roster['match_id'] = roster['Employee #'].apply(clean_num)
        match = roster[roster['match_id'] == u_id]

        if not match.empty:
            driver = match.iloc[0]
            route_num = clean_num(driver.get('Route', ''))
            d_name = driver.get('Driver Name', driver.iloc[0])
            
            # Header & Compliance
            st.markdown(f"<div class='header-box'><div style='font-size:36px; font-weight:bold;'>{d_name}</div><div style='font-size:22px;'>ID: {u_id} | Route: {route_num}</div></div>", unsafe_allow_html=True)
            
            # Dispatch & PeopleNet (ELD)
            p_id = clean_id(driver.get('PeopleNet ID'))
            st.markdown(f"""
                <div class='peoplenet-box'>
                    <div style='font-size:20px; padding-bottom:10px;'>PeopleNet / ELD Login</div>
                    <div style='display: flex; justify-content: space-around; font-size: 16px;'>
                        <div>ORG ID<br><span class='peoplenet-val'>3299</span></div>
                        <div>DRIVER ID<br><span class='peoplenet-val'>{p_id}</span></div>
                        <div>PASSWORD<br><span class='peoplenet-val'>{p_id}</span></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Daily Schedule
            schedule['route_match'] = schedule.iloc[:, 0].apply(clean_num)
            my_stops = schedule[schedule['route_match'] == route_num]
            
            if not my_stops.empty:
                st.markdown("<h3 style='font-size:30px;'>Daily Schedule</h3>", unsafe_allow_html=True)
                for _, stop in my_stops.iterrows():
                    raw_sid = clean_num(stop.get('Store ID'))
                    sid_raw = raw_sid 
                    sid_5 = raw_sid.zfill(5) 
                    addr = str(stop.get('Store Address'))
                    clean_addr = addr.replace(' ','+').replace('\n','')
                    
                    # Mapping Times: Column I (Index 8) and Column J (Index 9)
                    arr_time = str(stop.iloc[8]) if len(stop) > 8 else "N/A"
                    dep_time = str(stop.iloc[9]) if len(stop) > 9 else "N/A"
                    
                    with st.expander(f"📍 Stop: {sid_5 if raw_sid != '0' else 'Relay'} (Arr: {arr_time})", expanded=True):
                        st.markdown(f"""
                        <div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 12px; border-left: 6px solid #004a99;'>
                            <div style='font-size: 14px; color: #666; text-transform: uppercase; font-weight: bold; margin-bottom: 5px;'>Stop Details</div>
                            <table style='width:100%; border:none; font-size: 18px;'>
                                <tr>
                                    <td style='width:40%'><b>Arrival:</b></td><td>{arr_time}</td>
                                </tr>
                                <tr>
                                    <td><b>Departure:</b></td><td>{dep_time}</td>
                                </tr>
                                <tr>
                                    <td valign='top'><b>Address:</b></td><td>{addr}</td>
                                </tr>
                            </table>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Action Buttons Grid
                        st.markdown(f"""
                        <table style="width:100%; border:none; border-collapse:collapse; background:transparent;">
                          <tr>
                            <td style="width:50%; padding:5px; border:none;">
                              <a href="tel:8008710204,1,,88012#,,{sid_raw},#,,,1,,,1" class="btn-green">📞 Store Tracker</a>
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
                        <a href="https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAO__Ti7fnBUQzNYTTY1TjY3Uk0xMEwwTE9SUEZIWTRPRC4u" class="btn-red">🚨 Report Issue</a>
                        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error: {e}")
