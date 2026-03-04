import streamlit as st
import pandas as pd
import re
import time
import urllib.parse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh 

# --- 1. CONFIG & REFRESH ---
st_autorefresh(interval=60000, key="datarefresh")
st.set_page_config(page_title="CPC Portal", layout="centered", page_icon="🚛")

# --- 2. GLOBAL STYLES ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 18px !important; }
    .header-box {background-color: #004a99 !important; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 15px;}
    .safety-box {background-color: #fff4f4 !important; border: 3px solid #cc0000 !important; padding: 20px; border-radius: 12px; margin-bottom: 15px; color: #1a1a1a !important;}
    .safety-box h2 { color: #cc0000 !important; margin-top: 0; font-size: 22px; }
    .btn-confirm {display: block !important; width: 100% !important; padding: 20px 0px !important; border-radius: 12px !important; text-align: center !important; font-weight: bold !important; font-size: 20px !important; text-decoration: none !important; color: white !important; margin-bottom: 15px !important; background-color: #107c10 !important; border: 2px solid #ffffff !important; text-decoration: none !important;}
    .btn-done {display: block !important; width: 100% !important; padding: 20px 0px !important; border-radius: 12px !important; text-align: center !important; font-weight: bold !important; font-size: 20px !important; text-decoration: none !important; color: white !important; margin-bottom: 15px !important; background-color: #007bff !important; border: 2px solid #ffffff !important; text-decoration: none !important;}
    .stop-detail-card {background-color: #f0f2f6 !important; color: #1a1a1a !important; padding: 15px; border-radius: 10px; margin-bottom: 12px; border-left: 6px solid #004a99 !important;}
    .eld-card {background-color: #2c3e50 !important; color: #ffffff !important; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; border: 1px solid #34495e;}
    .eld-val {color: #3498db !important; font-size: 26px; font-weight: bold; font-family: monospace;}
    .btn-blue, .btn-green, .btn-red {display: block !important; width: 100% !important; padding: 15px 0px !important; border-radius: 10px !important; text-align: center !important; font-weight: bold !important; font-size: 18px !important; text-decoration: none !important; color: white !important; margin-bottom: 10px !important; border: none !important; text-decoration: none !important;}
    .btn-blue {background-color: #007bff !important;}
    .btn-green {background-color: #28a745 !important;}
    .btn-red {background-color: #dc3545 !important;}
    .tom-dispatch-box {border: 3px solid #004a99 !important; padding: 15px; border-radius: 12px; background-color: #f0f7ff !important; margin-bottom: 15px; color: #1a1a1a !important;}
    input { font-size: 22px !important; height: 55px !important; color: #000 !important; background-color: #fff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. HELPERS ---
def clean_num(val):
    if pd.isna(val) or str(val).strip() in ('0', '', 'nan'): return ""
    return re.sub(r'\D', '', str(val).split('.')[0])

def make_tel_link(phone_str):
    digits = re.sub(r'\D', '', str(phone_str))
    return f"tel:{digits}"

def safe_get(row, col_name, index, default=""):
    if col_name in row: return str(row[col_name]).strip()
    if len(row) > index: return str(row.iloc[index]).strip()
    return default

@st.cache_data(ttl=0)
def load_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7yF5pvuOjzm0xdRwHrFj8ByzGZ3kh1Iqmyw8pSdegEUUVeb3qSLpd1PDuWD1cUg/pub?output=csv"
    gids = {
        "roster": "1261782560", 
        "dispatch": "1123038440", 
        "schedule": "1908585361", 
        "links": "489255872", 
        "safety": "1978744657",
        "next_schedule": "1032676579",
        "next_dispatch": "313559236"
    }
    def get_s(gid):
        try:
            df = pd.read_csv(f"{base_url}&gid={gid}&cb={int(time.time())}", low_memory=False)
            df.columns = df.columns.str.strip()
            return df
        except: return pd.DataFrame()
    return get_s(gids["roster"]), get_s(gids["dispatch"]), get_s(gids["schedule"]), get_s(gids["links"]), get_s(gids["safety"]), get_s(gids["next_schedule"]), get_s(gids["next_dispatch"])

# --- 4. MAIN APP ---
try:
    roster, dispatch, schedule, quick_links, safety, next_schedule, next_dispatch = load_all_data()
    st.markdown("<h1 style='font-size: 28px;'>🚛 CPC Portal</h1>", unsafe_allow_html=True)
    user_input = st.text_input("Enter ID", value="").strip().lower()

    if user_input == "dispatch":
        st.subheader("📋 Dispatch Dashboard")
        sheet_url = "https://docs.google.com/spreadsheets/d/1yGwaBQaciW6F0MTlHSTgx1ozp00nULTNApctZYtBOAU/edit?usp=sharing"
        st.markdown(f'<a href="{sheet_url}" target="_blank" class="btn-confirm" style="background-color: #004a99 !important;">📊 VIEW LIVE ROUTE CONFIRMATIONS</a>', unsafe_allow_html=True)

    elif user_input:
        roster['match_id'] = roster['Employee #'].apply(clean_num)
        match = roster[roster['match_id'] == user_input]

        if not match.empty:
            driver = match.iloc[0]
            d_name = safe_get(driver, 'Driver Name', 0)
            raw_route = str(driver.get('Route', ''))
            route_num = clean_num(raw_route)
            today_str = datetime.now().strftime("%m/%d/%Y")
            tom_str = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")

            # 1. SAFETY & CONFIRMATION
            safety_msg = "Perform a thorough pre-trip inspection."
            if not safety.empty:
                s_match = safety[safety.iloc[:, 0].astype(str).str.contains(today_str, na=False)]
                if not s_match.empty: safety_msg = s_match.iloc[0, 1]
            st.markdown(f"<div class='safety-box'><h2>⚠️ DAILY SAFETY REMINDER</h2><p>{safety_msg}</p></div>", unsafe_allow_html=True)

            is_confirmed = st.toggle("I have submitted the Confirmation Form", key=f"conf_{user_input}")
            form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfnw_F7nGy4GbJlMlCxSSGXx86b8g5J6VhXRkz_ZvABr2fcMg/viewform?"
            params = {"entry.534103007": d_name, "entry.726947479": user_input, "entry.316322786": raw_route}
            full_url = form_url + urllib.parse.urlencode(params)
            btn_class = "btn-done" if is_confirmed else "btn-confirm"
            btn_text = "✅ ROUTE CONFIRMED" if is_confirmed else "🚛 READ SAFETY & CONFIRM ROUTE"
            st.markdown(f'<a href="{full_url}" target="_blank" class="{btn_class}">{btn_text}</a>', unsafe_allow_html=True)

            # 2. HEADER & ELD
            st.markdown(f"<div class='header-box'><h3>{d_name}</h3>ID: <b>{user_input}</b> | Route: <b>{raw_route}</b></div>", unsafe_allow_html=True)
            p_id = clean_num(safe_get(driver, 'PeopleNet ID', 12))
            st.markdown(f"""<div class='eld-card'><div style='font-size:14px; opacity:0.8;'>ELD LOGIN</div>
                        <span class='eld-val'>3299 | {p_id} | {p_id}</span></div>""", unsafe_allow_html=True)

            # 3. SCHEDULE TABS
            st.markdown("### Route Schedule")
            tab_today, tab_tom = st.tabs([f"📅 Today ({today_str})", f"⏭️ Tomorrow ({tom_str})"])

            with tab_today:
                dispatch['route_match'] = dispatch.iloc[:, 0].apply(clean_num)
                today_notes = dispatch[dispatch['route_match'] == route_num]
                if not today_notes.empty:
                    st.markdown(f"<div style='border: 2px solid #d35400; padding: 15px; border-radius: 12px; background-color: #fffcf9; margin-bottom: 15px;'><b>Today's Notes:</b><br>{today_notes.iloc[0].get('Comments', 'None')}</div>", unsafe_allow_html=True)
                
                schedule['route_match'] = schedule.iloc[:, 0].apply(clean_num)
                stops = schedule[schedule['route_match'] == route_num]
                if stops.empty: st.info("No stops found for today.")
                for _, stop in stops.iterrows():
                    sid = clean_num(safe_get(stop, 'Store ID', 4))
                    addr = safe_get(stop, 'Store Address', 5)
                    with st.expander(f"📍 Store {sid.zfill(5)}", expanded=True):
                        st.markdown(f"<div class='stop-detail-card'>{addr}</div>", unsafe_allow_html=True)
                        t_url = f"tel:8008710204,1,,88012#,,{sid},#,,,1,,,1"
                        g_url = f"http://maps.apple.com/?q={addr.replace(' ','+')}"
                        s_map = f"https://wg.cpcfact.com/store-{sid.zfill(5)}/"
                        iss_url = f"https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAO__Ti7fnBUQzNYTTY1TjY3Uk0xMEwwTE9SUEZIWTRPRC4u&r6db86d06117646df9723ec7f53f3e1f3={sid.zfill(5)}"
                        st.markdown(f"<a href='{t_url}' class='btn-green'>📞 Store Tracker</a>", unsafe_allow_html=True)
                        st.markdown(f"<a href='{g_url}' class='btn-blue'>🌎 Navigation</a>", unsafe_allow_html=True)
                        st.markdown(f"<a href='{s_map}' class='btn-blue'>🗺️ Store Map</a>", unsafe_allow_html=True)
                        st.markdown(f"<a href='{iss_url}' class='btn-red'>🚨 Report Issue</a>", unsafe_allow_html=True)

            with tab_tom:
                next_dispatch['route_match'] = next_dispatch.iloc[:, 0].apply(clean_num)
                tom_notes = next_dispatch[next_dispatch['route_match'] == route_num]
                if not tom_notes.empty:
                    st.markdown(f"<div class='tom-dispatch-box'><b>Tomorrow's Notes:</b><br>{tom_notes.iloc[0].get('Comments', 'None')}</div>", unsafe_allow_html=True)
                
                next_schedule['route_match'] = next_schedule.iloc[:, 0].apply(clean_num)
                t_stops = next_schedule[next_schedule['route_match'] == route_num]
                if t_stops.empty: st.info("Tomorrow's schedule is not yet posted.")
                for _, stop in t_stops.iterrows():
                    sid_t = clean_num(safe_get(stop, 'Store ID', 4))
                    addr_t = safe_get(stop, 'Store Address', 5)
                    with st.expander(f"📍 Store {sid_t.zfill(5)}"):
                        st.markdown(f"<div class='stop-detail-card'>{addr_t}</div>", unsafe_allow_html=True)
                        # Restored interactive buttons for Tomorrow
                        t_url_t = f"tel:8008710204,1,,88012#,,{sid_t},#,,,1,,,1"
                        g_url_t = f"http://maps.apple.com/?q={addr_t.replace(' ','+')}"
                        s_map_t = f"https://wg.cpcfact.com/store-{sid_t.zfill(5)}/"
                        iss_url_t = f"https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAO__Ti7fnBUQzNYTTY1TjY3Uk0xMEwwTE9SUEZIWTRPRC4u&r6db86d06117646df9723ec7f53f3e1f3={sid_t.zfill(5)}"
                        st.markdown(f"<a href='{t_url_t}' class='btn-green'>📞 Store Tracker</a>", unsafe_allow_html=True)
                        st.markdown(f"<a href='{g_url_t}' class='btn-blue'>🌎 Navigation</a>", unsafe_allow_html=True)
                        st.markdown(f"<a href='{s_map_t}' class='btn-blue'>🗺️ Store Map</a>", unsafe_allow_html=True)
                        st.markdown(f"<a href='{iss_url_t}' class='btn-red'>🚨 Report Issue</a>", unsafe_allow_html=True)

            # 4. QUICK LINKS
            st.divider()
            for _, link in quick_links.iterrows():
                n, v = str(link.get('Name')), str(link.get('Phone Number or URL'))
                if "http" in v.lower():
                    st.markdown(f"<a href='{v}' class='btn-blue'>{n}</a>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<a href='{make_tel_link(v)}' class='btn-green'>📞 Call {n}</a>", unsafe_allow_html=True)

        else: st.error("ID not found.")
except Exception as e: st.error(f"Error: {e}")
