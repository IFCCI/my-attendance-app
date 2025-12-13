import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
import os

# --- 🔐 设置每个场次的 6 位密码 ---
SESSION_PASSCODES = {
    "13th Dec - Morning Session": "146865",    
    "13th Dec - Afternoon Session": "978654",  
    "14th Dec - Morning Session": "015563",    
    "14th Dec - Afternoon Session": "215478"   
}

# --- 🔐 管理员密码 ---
ADMIN_PASSWORD = "happy4640"
BACKUP_FILE = "local_backup_logs.csv"

# --- 页面配置 ---
st.set_page_config(page_title="Event Check-in", page_icon="✅", layout="wide")

# --- 连接 Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 🚀 缓存读取功能 ---
@st.cache_data(ttl=600) 
def get_participants():
    try:
        df = conn.read(worksheet="Participants", usecols=[0])
        return df['Name'].dropna().tolist()
    except Exception:
        return []

# --- 💾 写入数据函数 (双重备份) ---
def write_log(session, name, user_type, email="-", phone="-"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 准备数据
    new_data = {
        "Timestamp": timestamp,
        "Session": session,
        "Name": name,
        "Type": user_type,
        "Email": email,
        "Phone": phone
    }
    df_new = pd.DataFrame([new_data])
    
    # === 1. 本地 CSV 备份 (秒级写入，不受 API 限制) ===
    try:
        if not os.path.exists(BACKUP_FILE):
            df_new.to_csv(BACKUP_FILE, index=False)
        else:
            df_new.to_csv(BACKUP_FILE, mode='a', header=False, index=False)
    except Exception as e:
        st.error(f"Local Backup Failed: {e}")

    # === 2. Google Sheets 写入 (带重试机制) ===
    # 即使 Google 失败了，本地 CSV 已经存下来了，所以不用太担心
    max_retries = 3
    google_success = False
    
    for attempt in range(max_retries):
        try:
            try:
                existing_data = conn.read(worksheet="Logs", ttl=0)
                updated_df = pd.concat([existing_data, df_new], ignore_index=True)
            except:
                updated_df = df_new
            
            conn.update(worksheet="Logs", data=updated_df)
            google_success = True
            break # 成功则跳出循环
        except Exception:
            time.sleep(1) # 失败重试
    
    # === 3. 反馈结果 ===
    if google_success:
        st.success(f"✅ {name} 签到成功! (Saved to Cloud)")
        st.balloons()
    else:
        # 如果 Google 失败但本地成功
        st.warning(f"⚠️ {name} 签到已保存到本地备份，但同步 Google 失败。数据是安全的！")
        st.info("Saved to Local Backup only due to network congestion.")
    
    time.sleep(2)
    st.cache_data.clear()
    st.rerun()

# ==========================================
# 🔧 Sidebar: Admin Dashboard (管理员后台)
# ==========================================
with st.sidebar:
    st.header("🔐 Admin Access")
    pwd = st.text_input("Enter Admin Password", type="password")
    
    if pwd == ADMIN_PASSWORD:
        st.success("Access Granted")
        st.divider()
        
        st.subheader("📂 Local Backup (Emergency)")
        st.info("如果 Google Sheet 挂了，请下载这个文件。")
        
        if os.path.exists(BACKUP_FILE):
            df_local = pd.read_csv(BACKUP_FILE)
            st.write(f"Total Records: {len(df_local)}")
            # 下载按钮
            st.download_button(
                label="📥 Download CSV Backup",
                data=df_local.to_csv(index=False).encode('utf-8'),
                file_name=f"attendance_backup_{datetime.now().strftime('%H%M')}.csv",
                mime="text/csv"
            )
            with st.expander("View Local Data"):
                st.dataframe(df_local)
        else:
            st.write("No local records yet.")
            
        st.divider()
        st.subheader("☁️ Google Sheets Data")
        if st.button("🔄 Refresh Cloud Data"):
            try:
                df_cloud = conn.read(worksheet="Logs", ttl=0)
                st.dataframe(df_cloud)
            except:
                st.error("Cannot connect to Google Sheets.")

# ==========================================
# 🏠 Main Page (用户界面)
# ==========================================

st.title("🎓 Diploma in Financial Market Analysis")
st.subheader("Third In-Person Class | Attendance Check-in")

# --- 选择场次 & 输入密码 ---
sessions = list(SESSION_PASSCODES.keys())
selected_session = st.selectbox("📅 Select Current Session (请选择当前场次)", sessions)
entered_code = st.text_input("🔑 Enter Session Code (请输入6位场次代码)", type="password")

st.divider()

# --- 主要逻辑 ---
tab1, tab2 = st.tabs(["🔍 已报名 (Pre-registered)", "📝 现场报名 (Walk-in)"])

# === TAB 1: 已报名用户 ===
with tab1:
    st.info("如果您已经报名，请在下方搜索您的名字。")
    name_list = get_participants()
    
    if not name_list:
        st.warning("⚠️ 暂时无法加载名单，请尝试直接使用'现场报名' (Walk-in)。")
    
    selected_name = st.selectbox("🔍 Search your name (搜索姓名)", [""] + name_list)
    
    if selected_name:
        st.write(f"**Selected:** {selected_name}")
        if st.button("Confirm Check-in (确认签到)", key="btn_pre"):
            correct_code = SESSION_PASSCODES.get(selected_session)
            if entered_code == correct_code:
                write_log(selected_session, selected_name, "Pre-registered")
            else:
                st.error("❌ 场次代码错误 (Invalid Session Code)！")

# === TAB 2: 未报名用户 ===
with tab2:
    st.warning("如果您未在名单中，请填写以下信息。")
    with st.form("walk_in_form"):
        wi_name = st.text_input("Full Name as per IC (姓名)*")
        wi_email = st.text_input("Email (邮箱)*")
        
        st.write("Contact Number (联络号码)*")
        c1, c2 = st.columns([1, 3])
        with c1:
            country_code = st.selectbox("Code", ["+60", "+65", "+86", "+1", "+44", "+61", "Other"])
        with c2:
            phone_num = st.text_input("Number (e.g. 123456789)")
            
        submitted = st.form_submit_button("Submit & Check-in")
        
        if submitted:
            correct_code = SESSION_PASSCODES.get(selected_session)
            if entered_code != correct_code:
                st.error("❌ 场次代码错误 (Invalid Session Code)！")
            elif not (wi_name and wi_email and phone_num):
                st.error("⚠️ 请填写所有必填项 (Please fill in all fields).")
            elif "@" not in wi_email or "." not in wi_email:
                st.error("⚠️ Email 格式不正确 (Invalid Email format).")
            elif not phone_num.replace(" ", "").isnumeric():
                st.error("⚠️ 电话号码只能包含数字 (Phone number should only contain digits).")
            else:
                full_phone = f"{country_code} {phone_num}"
                write_log(selected_session, wi_name, "Walk-in", wi_email, full_phone)
