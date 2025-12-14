import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
import os

# --- 🔐 密码设置 ---
SESSION_PASSCODES = {
    "13th Dec - Morning Session": "146865",    
    "13th Dec - Afternoon Session": "978654",  
    "14th Dec - Morning Session": "015563",    
    "14th Dec - Afternoon Session": "215478"   
}
ADMIN_PASSWORD = "happy4640"
BACKUP_FILE = "local_backup_logs.csv"
OFFLINE_MODE = False

st.set_page_config(page_title="Check-in", page_icon="✅", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 🚀 缓存读取名单 (适配 2 Column) ---
@st.cache_data(ttl=600) 
def get_participants_data():
    try:
        # 只读取前两列: Name, Category
        df = conn.read(worksheet="Participants", usecols=[0, 1])
        
        # 强制命名列名，防止出错
        if len(df.columns) >= 2:
            df.columns = ['Name', 'Category']
        else:
            df.columns = ['Name']
            df['Category'] = 'Pre-registered' # 默认值
            
        # 变成字符串并去空
        return df.dropna(subset=['Name']).astype(str)
    except:
        return pd.DataFrame(columns=['Name', 'Category'])

# --- 📊 实时读取 Log ---
@st.cache_data(ttl=30)
def get_live_logs():
    try:
        return conn.read(worksheet="Logs", ttl=0)
    except:
        if os.path.exists(BACKUP_FILE):
            return pd.read_csv(BACKUP_FILE)
        return pd.DataFrame()

# --- 写入数据函数 ---
def write_log(session, name, user_type, email="-", phone="-"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_data = pd.DataFrame([{
        "Timestamp": timestamp, "Session": session, "Name": name, 
        "Type": user_type, "Email": email, "Phone": phone
    }])
    
    # 本地备份
    if not os.path.exists(BACKUP_FILE):
        new_data.to_csv(BACKUP_FILE, index=False)
    else:
        new_data.to_csv(BACKUP_FILE, mode='a', header=False, index=False)

    if OFFLINE_MODE:
        st.success(f"✅ {name} 签到成功! (Offline)")
        time.sleep(1.5)
        st.rerun()
        return

    try:
        existing_data = conn.read(worksheet="Logs", ttl=0)
        updated_df = pd.concat([existing_data, new_data], ignore_index=True)
        conn.update(worksheet="Logs", data=updated_df)
        st.success(f"✅ {name} 签到成功!")
        st.balloons()
    except Exception:
        st.warning(f"⚠️ 已存入本地备份 (Google忙碌)，数据安全。")
    
    time.sleep(2)
    st.rerun()

# ================= ADMIN 后台 =================
with st.sidebar:
    st.header("🔐 Admin")
    if st.text_input("Pwd", type="password") == ADMIN_PASSWORD:
        st.success("Unlocked")
        if os.path.exists(BACKUP_FILE):
            df_local = pd.read_csv(BACKUP_FILE)
            st.write(f"📊 本地记录: {len(df_local)} 条")
            st.download_button("📥 下载 CSV 备份", df_local.to_csv(index=False), "backup.csv")
            if st.button("☁️ 同步到 Google"):
                try:
                    existing = conn.read(worksheet="Logs", ttl=0)
                    combined = pd.concat([existing, df_local]).drop_duplicates(subset=['Timestamp', 'Name'])
                    conn.update(worksheet="Logs", data=combined)
                    st.success("同步成功！")
                except: st.error("同步失败")

# ================= 主界面 =================
st.title("🎓 Diploma in Financial Market Analysis")

sessions = list(SESSION_PASSCODES.keys())
selected_session = st.selectbox("📅 Session", sessions)
entered_code = st.text_input("🔑 Code", type="password")

st.divider()
tab1, tab2 = st.tabs(["🔍 Search Name", "📝 Walk-in Form"])

# === TAB 1: 搜索名单 (CFT / RSVP) ===
with tab1:
    st.info("已在名单内的 (包含 CFT / RSVP) 请在此搜索 / Search your name here")
    
    df_participants = get_participants_data()
    
    # 自动去重逻辑
    if not df_participants.empty:
        unique_names = sorted(df_participants['Name'].unique().tolist())
    else:
        unique_names = []
    
    selected_name = st.selectbox("Name", [""] + unique_names)
    
    if selected_name:
        # 抓取用户对应的类别 (CFT 或 RSVP)
        user_row = df_participants[df_participants['Name'] == selected_name]
        
        if not user_row.empty:
            # 直接读取 B 列的内容
            cat = user_row.iloc[0]['Category']
            st.write(f"**Category:** `{cat}`")
            final_type_label = cat 
        else:
            final_type_label = "Pre-registered"

        if st.button("Confirm Check-in", key="btn_pre"):
            if entered_code == SESSION_PASSCODES.get(selected_session):
                write_log(selected_session, selected_name, final_type_label)
            else:
                st.error("❌ Code Error")

# === TAB 2: Walk-in ===
with tab2:
    st.warning("名单里没有名字的请填此表 / Fill this if your name is NOT in the list")
    with st.form("wi"):
        wn = st.text_input("Name")
        we = st.text_input("Email")
        c1, c2 = st.columns([1,3])
        wc = c1.selectbox("Code", ["+60","+65","+86","+1","+44","Other"])
        wp = c2.text_input("Phone")
        if st.form_submit_button("Submit"):
            if entered_code != SESSION_PASSCODES.get(selected_session):
                st.error("❌ Code Error")
            elif not (wn and we and wp):
                st.error("⚠️ Fill all fields")
            else:
                write_log(selected_session, wn, "Walk-in Guest", we, f"{wc} {wp}")

# ================= 底部实时列表 =================
st.divider()
st.subheader("📋 Live Check-in Status (Latest 10)")
st.caption(f"Showing records for: {selected_session}")

df_logs = get_live_logs()
if not df_logs.empty:
    if 'Session' in df_logs.columns and 'Timestamp' in df_logs.columns:
        current_session_logs = df_logs[df_logs['Session'] == selected_session].copy()
        if not current_session_logs.empty:
            current_session_logs = current_session_logs.sort_values(by="Timestamp", ascending=False)
            display_df = current_session_logs[['Timestamp', 'Name', 'Type']].head(10)
            st.dataframe(display_df, hide_index=True, use_container_width=True)
            st.caption("Auto-refreshes every 30 seconds.")
        else:
            st.info("No check-ins yet for this session.")
    else:
        st.info("Logs data structure updating...")
else:
    st.info("Loading logs...")
