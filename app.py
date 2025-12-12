import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- 🔐 设置每个场次的 6 位密码 (请在这里修改) ---
SESSION_PASSCODES = {
    "13th Dec - Morning Session": "146865",    # <-- 修改这里的密码
    "13th Dec - Afternoon Session": "978654",  # <-- 修改这里的密码
    "14th Dec - Morning Session": "102556",    # <-- 修改这里的密码
    "14th Dec - Afternoon Session": "125478"   # <-- 修改这里的密码
}

# --- 页面配置 ---
st.set_page_config(page_title="Event Check-in", page_icon="✅")

# --- 标题 ---
st.title("🎓 Diploma in Financial Market Analysis")
st.subheader("Third In-Person Class | Attendance Check-in")

# --- 连接 Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 读取数据函数 ---
def get_participants():
    try:
        # 读取 Participants 表
        df = conn.read(worksheet="Participants", usecols=[0], ttl=5)
        return df['Name'].dropna().tolist()
    except:
        return []

# --- 写入数据函数 ---
def write_log(session, name, user_type, email="-", phone="-"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_data = pd.DataFrame([{
        "Timestamp": timestamp,
        "Session": session,
        "Name": name,
        "Type": user_type,
        "Email": email,
        "Phone": phone
    }])
    
    try:
        existing_data = conn.read(worksheet="Logs", ttl=0)
        updated_df = pd.concat([existing_data, new_data], ignore_index=True)
    except:
        updated_df = new_data

    conn.update(worksheet="Logs", data=updated_df)
    
    st.success(f"✅ {name} 签到成功! (Checked in successfully!)")
    st.balloons()
    time.sleep(2)
    st.rerun()

# --- 📅 1. 选择场次 & 输入密码 ---
sessions = list(SESSION_PASSCODES.keys())
selected_session = st.selectbox("📅 Select Current Session (请选择当前场次)", sessions)

# 密码输入框 (密码形式显示)
entered_code = st.text_input("🔑 Enter Session Code (请输入6位场次代码)", type="password")

st.divider()

# --- 主要逻辑：Tab 分页 ---
tab1, tab2 = st.tabs(["🔍 已报名 (Pre-registered)", "📝 现场报名 (Walk-in)"])

# === TAB 1: 已报名用户 ===
with tab1:
    st.info("如果您已经报名，请在下方搜索您的名字。")
    
    try:
        name_list = get_participants()
        selected_name = st.selectbox("🔍 Search your name (搜索姓名)", [""] + name_list)
        
        if selected_name:
            st.write(f"**Selected:** {selected_name}")
            
            # 确认按钮
            if st.button("Confirm Check-in (确认签到)", key="btn_pre"):
                # --- 验证密码 ---
                correct_code = SESSION_PASSCODES.get(selected_session)
                if entered_code == correct_code:
                    write_log(selected_session, selected_name, "Pre-registered")
                else:
                    st.error("❌ 场次代码错误 (Invalid Session Code)！请向工作人员询问。")
                
    except Exception as e:
        st.error("无法加载名单，请检查网络或联系管理员。")

# === TAB 2: 未报名用户 ===
with tab2:
    st.warning("如果您未在名单中，请填写以下信息。")
    
    with st.form("walk_in_form"):
        wi_name = st.text_input("Full Name as per IC (姓名)*")
        
        # 邮箱验证逻辑会在提交时进行
        wi_email = st.text_input("Email (邮箱)*")
        
        # 电话号码：国家代码 + 号码
        st.write("Contact Number (联络号码)*")
        c1, c2 = st.columns([1, 3])
        with c1:
            country_code = st.selectbox("Code", ["+60", "+65", "+86", "+1", "+44", "+61", "Other"])
        with c2:
            phone_num = st.text_input("Number (e.g. 123456789)")
            
        submitted = st.form_submit_button("Submit & Check-in")
        
        if submitted:
            # --- 1. 验证密码 ---
            correct_code = SESSION_PASSCODES.get(selected_session)
            
            if entered_code != correct_code:
                st.error("❌ 场次代码错误 (Invalid Session Code)！请向工作人员询问。")
            
            # --- 2. 验证必填项 ---
            elif not (wi_name and wi_email and phone_num):
                st.error("⚠️ 请填写所有必填项 (Please fill in all fields).")
                
            # --- 3. 验证 Email 格式 ---
            elif "@" not in wi_email or "." not in wi_email:
                st.error("⚠️ Email 格式不正确 (Invalid Email format).")
                
            # --- 4. 验证电话号码 (是否为数字) ---
            elif not phone_num.replace(" ", "").isnumeric():
                st.error("⚠️ 电话号码只能包含数字 (Phone number should only contain digits).")
                
            # --- 全部通过 -> 写入 ---
            else:
                full_phone = f"{country_code} {phone_num}"
                write_log(selected_session, wi_name, "Walk-in", wi_email, full_phone)

