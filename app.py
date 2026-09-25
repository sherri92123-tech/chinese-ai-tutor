import os
import streamlit as st
import datetime
import pandas as pd
from openai import OpenAI

# 頁面標題與手機排版設定
st.set_page_config(page_title="華語閱讀伴讀助教", page_icon="📖", layout="centered")

# ----------------- 1. 本次閱讀文章與生詞資料 -----------------
READING_DATA = {
    "title": "台灣的夜市與智慧生活",
    "p1": "在台灣，夜市不僅是品嚐傳統小吃的地方，更是體驗在地生活文化的重要窗口。每到傍晚，街道兩旁擺滿了各式各樣的攤位，從珍珠奶茶、鹽酥雞到臭豆腐，吸引了成千上萬的市民與外國觀光客。",
    "p2": "近年來，許多傳統夜市開始引進數位科技。以前外國學習者到夜市點餐時，常常因為看不懂菜單或擔心發音不標準而感到緊張；現在，不少攤位設置了多語言行動支付與掃碼點餐系統，讓點餐變得更加方便。",
    "p3": "然而，科技的介入也引發了一些討論。有人認為，掃碼點餐減少了人與人之間面對面的寒暄與交流，讓夜市少了一點傳統的人情味；但也有人覺得，科技讓傳統文化更容易被世界看見，是一種雙贏的進步。",
    "vocab": {
        "品嚐 (pǐncháng)": "細細地吃或喝，仔細體會滋味。",
        "窗口 (chuāngkǒu)": "比喻觀察或接觸某種文化、事物的途徑。",
        "引進 (yǐnjìn)": "將外面的技術、觀念或設備帶進來使用。",
        "寒暄 (hánxuān)": "見面時談論天氣、問候起居等社交客套話。",
        "人情味 (rénqíngwèi)": "人與人之間溫暖、熱情、互相體貼的情感。"
    }
}

# ----------------- 2. AI 系統提示詞 -----------------
SYSTEM_PROMPT = f"""
你是一位專業的二語華語閱讀教學助教，引導外籍學生進行閱讀理解。
本次閱讀文章為《{READING_DATA['title']}》。
【第一段】：{READING_DATA['p1']}
【第二段】：{READING_DATA['p2']}
【第三段】：{READING_DATA['p3']}

【引導規則】：
1. 學生一進來，請親切打招呼，請他點選上方「第一段」分頁閱讀，讀完後回傳「讀完了」。
2. 逐段提問（每次只問 1 題，絕不直接給答案）：
   - 第一段讀完：問 1 個事實題（如：夜市對台灣人的意義是什麼？）。
   - 第二段讀完：問 1 個推論題（如：科技如何解決外籍學生在夜市點餐的困難？）。
   - 第三段讀完：問 1 個開放思辨題（如：你認為科技讓夜市更方便，還是少了人情味？為什麼？）。
3. 若學生答錯，給予線索提示重試；若問生詞，依上下文簡短解釋並造 1 句。
4. 全程使用繁體中文，難度控制在 TOCFL 3 級左右。
"""

# ----------------- 3. 儲存學生對話紀錄 -----------------
LOG_FILE = "student_reading_logs.csv"

def save_log(student_id, role, msg):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = pd.DataFrame([{"時間": now, "學號": student_id, "發言者": role, "內容": msg}])
    if not os.path.exists(LOG_FILE):
        df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(LOG_FILE, mode="a", header=False, index=False, encoding="utf-8-sig")

# ----------------- 4. 側邊欄（設定與研究資料下載） -----------------
with st.sidebar:
    st.header("⚙️ 設定與研究專區")
    api_key = st.text_input("OpenAI API Key (教師填寫)", type="password")
    student_id = st.text_input("請輸入學生代號 (例如 S01):", placeholder="S01")
    
    st.divider()
    if st.button("📥 下載全班對話紀錄 (CSV)"):
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "rb") as f:
                st.download_button("點此儲存對話檔案", f, file_name="reading_logs.csv", mime="text/csv")
        else:
            st.info("尚無紀錄")

if not student_id:
    st.warning("👈 請先點擊左上角「>」展開側邊欄，輸入您的「學生代號」再開始！")
    st.stop()

# ----------------- 5. 手機上半部：固定閱讀區 -----------------
st.caption(f"📖 閱讀文章：《{READING_DATA['title']}》")

# 使用固定高度的滾動容器，確保在手機上只佔上半部
with st.container(height=260):
    tab1, tab2, tab3, tab_v = st.tabs(["【第一段】", "【第二段】", "【第三段】", "💡 重點生詞"])
    with tab1:
        st.write(READING_DATA["p1"])
    with tab2:
        st.write(READING_DATA["p2"])
    with tab3:
        st.write(READING_DATA["p3"])
    with tab_v:
        for word, meaning in READING_DATA["vocab"].items():
            st.markdown(f"**{word}**：{meaning}")

st.divider()

# ----------------- 6. 手機下半部：AI 伴讀聊天室 -----------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": f"你好，{student_id}！今天我們要一起讀《{READING_DATA['title']}》。請先點上方【第一段】分頁閱讀，讀完後請留言告訴我「我讀完了」！"}
    ]
    save_log(student_id, "AI助教", st.session_state.messages[-1]["content"])

# 顯示所有聊天紀錄
for m in st.session_state.messages:
    if m["role"] != "system":
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

# 學生手機底部輸入框
if prompt := st.chat_input("在此輸入訊息回覆 AI 助教..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    save_log(student_id, "學生", prompt)

    # 呼叫 AI
    if not api_key:
        st.error("請教師先在側邊欄填入 API Key！")
    else:
        try:
            client = OpenAI(api_key=api_key)
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
                temperature=0.7
            )
            reply = res.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": reply})
            with st.chat_message("assistant"):
                st.markdown(reply)
            save_log(student_id, "AI助教", reply)
        except Exception as e:
            st.error(f"連線失敗：{e}")
