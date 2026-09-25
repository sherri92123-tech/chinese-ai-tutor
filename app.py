import os
import streamlit as st
import datetime
import pandas as pd
import google.generativeai as genai
from pypdf import PdfReader

st.set_page_config(page_title="華語 PDF 伴讀助教", page_icon="📖", layout="centered")

# ----------------- 1. 側邊欄：設定與 PDF 上傳 -----------------
with st.sidebar:
    st.header("⚙️ 教師管理專區")
    api_key = st.text_input("Gemini API Key", type="password", help="在 Google AI Studio 申請的免費金鑰")
    uploaded_pdf = st.file_uploader("📄 上傳本次課文 PDF", type=["pdf"])
    
    st.divider()
    st.header("👨‍🎓 學生登入")
    student_id = st.text_input("學生代號 (例如 S01):", placeholder="S01")
    
    st.divider()
    if st.button("📥 下載全班對話紀錄 (CSV)"):
        if os.path.exists("student_reading_logs.csv"):
            with open("student_reading_logs.csv", "rb") as f:
                st.download_button("點此儲存檔案", f, file_name="reading_logs.csv", mime="text/csv")
        else:
            st.info("目前尚無紀錄")

if not student_id:
    st.warning("👈 歡迎！請先點擊左上角「>」展開側邊欄，輸入您的「學生代號」！")
    st.stop()

# ----------------- 2. 讀取與解析 PDF 內容 -----------------
reading_text = ""
if uploaded_pdf:
    reader = PdfReader(uploaded_pdf)
    for page in reader.pages:
        text = page.extract_text()
        if text:
            reading_text += text + "\n"
else:
    reading_text = "（教師尚未上傳 PDF，目前使用預設課文）\n在台灣，夜市不僅是品嚐小吃的地方，更是體驗文化的重要窗口。"

# ----------------- 3. 手機上半部：固定閱讀區 -----------------
st.caption("📖 本次閱讀教材內容")
with st.container(height=260):
    st.text_area("文章內容（可滾動閱讀）", value=reading_text, height=200, disabled=True)

st.divider()

# ----------------- 4. 手機下半部：AI 伴讀聊天室 -----------------
SYSTEM_PROMPT = f"""
你是一位專業的二語華語閱讀教學助教。
學生正在閱讀以下教材內容：
\"\"\"{reading_text}\"\"\"

【引導規則】：
1. 學生剛進入時，向學生問好，請他閱讀上方教材的前半段，讀完告訴你。
2. 逐段向學生提問以檢核理解，每次只問 1 個問題。
3. 嚴禁直接給答案。若學生答錯，給予線索提示；若詢問生詞，依文章情境簡短解釋並造句。
4. 全程使用繁體中文，親切且耐心地引導。
"""

LOG_FILE = "student_reading_logs.csv"
def save_log(sid, role, msg):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = pd.DataFrame([{"時間": now, "學號": sid, "發言者": role, "內容": msg}])
    if not os.path.exists(LOG_FILE):
        df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(LOG_FILE, mode="a", header=False, index=False, encoding="utf-8-sig")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "model", "content": f"你好，{student_id}！今天我們要一起讀這篇課文。請先看上方框框裡的文章，讀完前幾句後請告訴我「我讀完了」！"}
    ]
    save_log(student_id, "AI助教", st.session_state.messages[-1]["content"])

for m in st.session_state.messages:
    role_name = "assistant" if m["role"] == "model" else "user"
    with st.chat_message(role_name):
        st.markdown(m["content"])

if prompt := st.chat_input("輸入訊息回覆 AI 助教..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    save_log(student_id, "學生", prompt)

    if not api_key:
        st.error("請在側邊欄填入 Gemini API Key！")
    else:
        try:
            genai.configure(api_key=api_key)
            
            # 【自動挑選可用的最新模型】避免版本更迭導致 404
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            selected_model = "gemini-2.0-flash"
            for m in available_models:
                if "flash" in m:
                    selected_model = m
                    break
            
            model = genai.GenerativeModel(selected_model, system_instruction=SYSTEM_PROMPT)
            
            gemini_history = []
            for msg in st.session_state.messages[:-1]:
                if not gemini_history and msg["role"] == "model":
                    continue
                gemini_history.append({"role": msg["role"], "parts": [msg["content"]]})
            
            chat = model.start_chat(history=gemini_history)
            res = chat.send_message(prompt)
            reply = res.text
            
            st.session_state.messages.append({"role": "model", "content": reply})
            with st.chat_message("assistant"):
                st.markdown(reply)
            save_log(student_id, "AI助教", reply)
        except Exception as e:
            st.error(f"連線失敗：{e}")
