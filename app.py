import os
import streamlit as st
import datetime
import pandas as pd
import google.generativeai as genai
from pypdf import PdfReader

st.set_page_config(page_title="華語 PDF 伴讀助教", page_icon="📖", layout="centered")

# ----------------- 中文文字清理：消除 PDF 抽取時每字強制換行的問題 -----------------
def clean_cjk_text(text):
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = text.split("\n\n")
    cleaned_paras = []
    
    for p in paragraphs:
        lines = p.split("\n")
        cleaned_line = ""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if cleaned_line:
                last_char = cleaned_line[-1]
                first_char = line[0]
                # 若為中文字、注音、常見全形標點符號，則緊密相連不換行、不加空格
                if ('\u4e00' <= last_char <= '\u9fff' or last_char in "「」『』，。！？、：；（）《》…—") or \
                   ('\u4e00' <= first_char <= '\u9fff' or first_char in "「」『』，。！？、：；（）《》…—"):
                    cleaned_line += line
                else:
                    cleaned_line += " " + line
            else:
                cleaned_line = line
        if cleaned_line:
            cleaned_paras.append(cleaned_line)
            
    return "\n\n".join(cleaned_paras)

# ----------------- 自訂 CSS：橫向白色大字與舒適行距 -----------------
st.markdown("""
<style>
    .reading-card {
        background-color: #1e1e2f;
        color: #ffffff !important;
        font-size: 19px !important;
        line-height: 1.8 !important;
        letter-spacing: 0.5px;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #3d3d5c;
        max-height: 250px;
        overflow-y: auto;
        white-space: pre-line; /* 自然橫向換行，保留段落 */
        word-break: break-word;
    }
    .reading-card p, .reading-card div {
        color: #ffffff !important;
        font-size: 19px !important;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

LESSON_FILE = "current_lesson.txt"
LOG_FILE = "student_reading_logs.csv"

# ----------------- 1. 自動讀取 API Key 與儲存的課文 -----------------
default_api_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""

saved_text = ""
if os.path.exists(LESSON_FILE):
    with open(LESSON_FILE, "r", encoding="utf-8") as f:
        saved_text = f.read()

# ----------------- 2. 側邊欄設定 -----------------
with st.sidebar:
    st.header("⚙️ 教師管理專區")
    
    if default_api_key:
        st.success("✅ 後台已永久綁定 API Key (免輸入)")
        api_key = default_api_key
    else:
        api_key = st.text_input("Gemini API Key", type="password", help="可在 Streamlit 後台 Secrets 設定永久保存")
    
    st.subheader("📄 課文管理")
    uploaded_pdf = st.file_uploader("上傳新課文 PDF (上傳一次永久保存)", type=["pdf"])
    
    if uploaded_pdf:
        reader = PdfReader(uploaded_pdf)
        extracted = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                extracted += t + "\n"
        
        # 進行中文文字平整化修復
        cleaned = clean_cjk_text(extracted)
        if cleaned.strip():
            with open(LESSON_FILE, "w", encoding="utf-8") as f:
                f.write(cleaned)
            saved_text = cleaned
            st.success("🎉 課文已成功保存並排版完成！")

    st.divider()
    st.header("👨‍🎓 學生登入")
    student_id = st.text_input("學生代號 (例如 S01):", placeholder="S01")
    
    st.divider()
    if st.button("📥 下載全班對話紀錄 (CSV)"):
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "rb") as f:
                st.download_button("點此儲存檔案", f, file_name="reading_logs.csv", mime="text/csv")
        else:
            st.info("目前尚無紀錄")

if not student_id:
    st.warning("👈 歡迎！請先點擊左上角「>」展開側邊欄，輸入您的「學生代號」！")
    st.stop()

reading_text = saved_text if saved_text.strip() else "（教師尚未上傳課文，請先在側邊欄上傳 PDF 一次即可永久使用）"

# ----------------- 3. 手機上半部：高對比橫向白色大字閱讀區 -----------------
st.caption("📖 本次閱讀教材內容 (可滑動閱讀)")
st.markdown(f'<div class="reading-card">{reading_text}</div>', unsafe_allow_html=True)
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
        st.error("請在側邊欄填入 Gemini API Key，或在 Streamlit 後台設定 Secrets！")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-3.8-flash", system_instruction=SYSTEM_PROMPT)
            
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
