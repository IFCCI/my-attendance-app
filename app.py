import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# --- 页面配置 ---
st.set_page_config(page_title="Event Check-in", page_icon="✅")

# --- 标题 ---
st.title("🎓 Diploma in Financial Market Analysis")
st.subheader("Third In-Person Class | Attendance Check-in")

# --- 连接 Google Sheets ---
# 我们使用 st.connection 来连接，稍后会在 Secrets 里配置
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 读取数据函数 (缓存以提高速度) ---
def get_participants():
    # 读取 Participants 表 (假设在第一个 worksheet)
    df = conn.read(worksheet="Participants", usecols=[0], ttl=5)
    return df['Name'].dropna().tolist()

# --- 写入数据函数 ---
def write_log(session, name, user_type, email="-", phone="-"):
    # 获取当前时间
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 创建新的一行数据
    new_data = pd.DataFrame([{
        "Timestamp": timestamp,
        "Session": session,
        "Name": name,
        "Type": user_type,
        "Email": email,
        "Phone": phone
    }])
    
    # 读取现有的 Logs (假设在第二个 worksheet，即 worksheet="Logs")
    # 注意：初次读取如果为空可能会报错，这里做简单处理
    try:
        existing_data = conn.read(worksheet="Logs", ttl=0)
        updated_df = pd.concat([existing_data, new_data], ignore_index=True)
    except:
        updated_df = new_data

    # 将更新后的数据写回 Google Sheets 的 Logs 分页
    conn.update(worksheet="Logs", data=updated_df)
    
    st.success(f"✅ {name} 签到成功! ({timestamp})")
    st.balloons()
    time.sleep(2) # 稍微暂停让用户看到成功信息
    st.rerun() # 刷新页面

# --- 侧边栏：选择 Session ---
# 这里由工作人员或用户选择当前是哪一场
sessions = [
    "13th Dec - Morning Session",
    "13th Dec - Afternoon Session",
    "14th Dec - Morning Session",
    "14th Dec - Afternoon Session"
]
selected_session = st.selectbox("📅 Select Current Session (请选择当前场次)", sessions)

st.divider()

# --- 主要逻辑：Tab 分页 ---
tab1, tab2 = st.tabs(["🔍 已报名 (Pre-registered)", "📝 现场报名 (Walk-in)"])

# === TAB 1: 已报名用户 ===
with tab1:
    st.info("如果您已经报名，请在下方搜索您的名字。")
    
    try:
        name_list = get_participants()
        # 搜索框
        selected_name = st.selectbox("🔍 Search your name (搜索姓名)", [""] + name_list)
        
        if selected_name:
            st.write(f"**Selected:** {selected_name}")
            # 确认按钮
            if st.button("Confirm Check-in (确认签到)", key="btn_pre"):
                write_log(selected_session, selected_name, "Pre-registered")
                
    except Exception as e:
        st.error("无法加载名单，请检查网络或联系管理员。")
        st.error(e)

# === TAB 2: 未报名用户 ===
with tab2:
    st.warning("如果您未在名单中，请填写以下信息。")
    
    with st.form("walk_in_form"):
        wi_name = st.text_input("Full Name as per IC (姓名)*")
        wi_email = st.text_input("Email (邮箱)*")
        wi_phone = st.text_input("Contact Number (联络号码)*")
        
        submitted = st.form_submit_button("Submit & Check-in")
        
        if submitted:
            if wi_name and wi_email and wi_phone:
                write_log(selected_session, wi_name, "Walk-in", wi_email, wi_phone)
            else:
                st.error("请填写所有必填项 (Please fill in all fields).")