import os
import re
import streamlit as st
import datetime
import pandas as pd
import google.generativeai as genai
from pypdf import PdfReader

st.set_page_config(page_title="華語閱讀伴讀助教", page_icon="📖", layout="centered")

# ----------------- 內建精選優質教材庫（100% 正確排版、0 亂碼、段落清晰） -----------------
BUILTIN_LESSONS = {
    "📱 單元一：《「低頭族」小心！》": {
        "title": "「低頭族」小心！",
        "text": """【第一段】
你用智慧型手機（smartphone）嗎？你一天花多少時間盯著手機呢？最近有一個新的名詞——「低頭族」（Smartphone Addicts），指的是那些隨時低著頭使用3C產品的人。因為社會越來越進步，出現了很多新的3C產品，所以成為「低頭族」的人也越來越多了。

【第二段】
使用智慧型手機的好處有很多，你可以隨時隨地和朋友聊天、寫電子郵件、玩遊戲，也可以隨時隨地聽音樂、看影片。這麼多的功能，只要一根手指頭就可以辦到！因為智慧型手機這麼方便，所以很多人不管什麼時候，像是走路、吃飯或搭車，常常手機不離身，永遠專心地看著手機。

【第三段】
智慧型手機有這麼多的好處，但也有很多讓人困擾的地方。很多人和朋友吃飯的時候都專心在手機上，大家就算真的見面，也很少抬頭聊天。這樣讓人與人的關係日漸疏遠，溝通不再是面對面的，而是手機裡一個個的文字訊息。此外，低頭太久也可能對健康不好，脖子和手指很容易受傷。這些人走在路上也容易因為不夠專心，過馬路的時候容易發生危險。

【第四段】
你也是「低頭族」嗎？使用智慧型手機雖然很方便，但我們也要小心它帶來的問題。有時候也抬頭看看身邊可愛的朋友，看看這個美麗的世界吧！"""
    },
    "🧋 單元二：《買手搖飲料（對話篇）》": {
        "title": "買東西（二）：買手搖飲料",
        "text": """【對話情境：世天與泰熙走進一家飲料店】

店員：嗨，帥哥，老樣子，珍奶半糖去冰嗎？
世天：沒錯，麻煩妳了！
泰熙：（對世天說）店員好厲害，怎麼知道你要點什麼？
世天：因為我常常來這家店啊！小美，這是我的韓國朋友泰熙，我帶她來喝喝看妳們家的飲料。

店員：（對泰熙說）帥哥是我們店的老客人了，所以我會記得他喜歡喝什麼。美女妳呢？今天想喝什麼呢？
泰熙：我不知道耶，每個看起來都很棒，妳推薦什麼呢？
店員：帥哥點的珍珠奶茶是我們店裡的招牌；如果妳喜歡喝茶的話，我們的烏龍綠茶也很好喝唷！我們是用茶葉現泡的，沒有加香精，很清涼解渴呢！

泰熙：那我要試試看烏龍綠茶！我要一杯大杯的，謝謝！
店員：好的，甜度冰塊正常嗎？
泰熙：（轉頭問世天）甜度冰塊是什麼意思啊？
世天：她在問妳，綠茶的糖跟冰塊要不要多加一點，或是少加一點，還是不要改變。

泰熙：我在減肥，我不想加糖；天氣那麼熱，冰塊就不要改變好了。
店員：那就是一杯烏龍綠無糖正常冰。跟您收20元，帥哥的是25元，你們要一起算嗎？
世天：一起算！這杯我請妳吧！
泰熙：這怎麼好意思呢？
世天：沒關係啊！下次再換妳請我就好了。
泰熙：好吧！那就先謝謝你的烏龍綠了！"""
    },
    "🥟 單元三：《水餃的故事》": {
        "title": "水餃的故事",
        "text": """【第一段】
去餐廳吃飯的時候，我們常常可以在菜單上看到「水餃」這個食物。很多外國人來到臺灣，也一定會嚐嚐這個中國傳統的食物。你知道嗎？關於「水餃」，還有一個有趣的小故事。

【第二段】
張仲景是中國古代一位很厲害的醫生。據說，水餃就是他發明的。他不但是位醫術高明的醫生，也很有愛心，不管是富人還是貧窮的人，他都很認真地幫大家看病，因此救了許多人的生命。

【第三段】
有一次，他回到家鄉，發現很多人不但沒東西吃，天氣寒冷也沒有足夠的衣服保暖，耳朵都被凍爛了。張仲景看到這個現象，決定要想個方法救救大家。他回到家之後，叫他的學生在空地上準備一個大鍋子煮藥湯，準備在冬至那天分給生病的人喝。

【第四段】
這個藥湯的名字叫「祛寒嬌耳湯」。做法是把一些羊肉、藥材用麵皮包起來下鍋煮熟，外形就像耳朵一樣。人們喝完熱湯、吃了「嬌耳」之後全身發熱，血液循環變好，耳朵的凍傷也都全好了。人們為了感謝並紀念張仲景的愛心，在每年冬至和大年初一的時候，都會模仿「嬌耳」的樣子做成食物來吃，這就是今天我們所吃的「水餃」！"""
    },
    "🍢 單元四：《臺灣的小吃》": {
        "title": "臺灣的小吃",
        "text": """【第一段】
到哪裡玩必須帶著護照、現金以及夠大的胃呢？答案就是臺灣。

【第二段】
美國有線電視新聞網CNN的CNN GO網站，在2012年6月13日刊出了一篇文章，篇名是「40種不能沒有的臺灣食物」。文章介紹了40種臺灣熱門的小吃，例如像山一樣高的刨冰、像臉一樣大的雞排、鳳梨酥、蚵仔煎、珍珠奶茶等。文章還說明了臺灣小吃，因為融合了閩南、潮州、福建以及日本等各個地方食物的特色，所以才能有各式各樣風味獨特的小吃。

【第三段】
文章更提醒想要來臺灣旅遊的人：如果來臺灣旅遊，就不應該遵守「一天吃三餐」的習慣，而是隨時隨地，只要你的胃有空間，就該品嚐臺灣的美食，因為臺灣的美食真的太多了。舉例來說，臺北就有大約20條專門賣小吃的街道。每當你以為你已經找到最棒的路邊攤，例如味道令你難忘的臭豆腐，或者是令你垂涎三尺的牛肉麵，結果過些時候，你又會在另一條街道找到比之前更好吃的路邊攤。

【第四段】
文章的最後還打趣地說，如果你問幾個臺灣朋友：「在臺灣，什麼是最好吃的食物？」那幾個臺灣人可能會因此而吵架呢！如果你想知道40種臺灣熱門的小吃是什麼，請自行到網站上一探究竟吧！"""
    },
    "🍉 單元五：《老王賣瓜，自賣自誇》": {
        "title": "老王賣瓜，自賣自誇",
        "text": """【第一段】
「老王賣瓜，自賣自誇」是一句常見的歇後語。意思是形容人喜歡誇耀自己的能力或本領。這句話的背後有個小故事。以前有一個人叫王坡，因為他很嘮叨，做起事來婆婆媽媽的，既擔心這個，又擔心那個，所以大家都叫他「王婆」。

【第二段】
王婆的工作是種瓜，這種瓜是外地來的，樣子不太好看，但是吃起來非常甜。王婆把種好的瓜拿到市場上賣，但是因為大家都沒看過這種奇怪樣子的瓜，所以賣了好幾天，一顆都沒賣出去。王婆很著急，於是就開始大聲介紹自己的瓜有多麼好吃，而且把瓜切開讓大家吃看看。剛開始大家都不太敢吃，後來有個大膽的人吃了一口之後說：「這個瓜好甜啊！跟蜂蜜一樣甜！」後來這件事一傳十，十傳百，大家都知道王婆的瓜很好吃，王婆的生意也越來越好了。

【第三段】
有一天，皇帝經過這個地方，看見王婆正在介紹自己的瓜。而且王婆看見了皇帝也不害怕，也跟皇帝介紹起自己的瓜。皇帝一吃之後非常開心，問王婆：「你的瓜這麼甜！為什麼還要努力向大家介紹呢？」王婆說：「我這個瓜是外地來的，大家都不認識，不介紹的話大家就不會買了。」皇帝聽了之後說：「這麼好吃的瓜，真是誇得有道理啊！」"""
    }
}

# ----------------- 自訂優雅清晰的 CSS 排版 -----------------
st.markdown("""
<style>
    .reading-card {
        background-color: #1e1e2f;
        color: #ffffff !important;
        font-size: 19px !important;
        line-height: 1.9 !important;
        letter-spacing: 0.6px;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #3d3d5c;
        max-height: 270px;
        overflow-y: auto;
        white-space: pre-wrap; /* 完美保留段落空行 */
        word-break: break-word;
    }
</style>
""", unsafe_allow_html=True)

LOG_FILE = "student_reading_logs.csv"

# 1. 讀取 API Key
default_api_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""

# 2. 側邊欄設計
with st.sidebar:
    st.header("⚙️ 教師管理專區")
    
    if default_api_key:
        st.success("✅ 後台已永久綁定 API Key")
        api_key = default_api_key
    else:
        api_key = st.text_input("Gemini API Key", type="password")
        
    st.subheader("📚 選擇課文教材")
    lesson_choice = st.selectbox(
        "請選擇本次上課教材：",
        list(BUILTIN_LESSONS.keys()) + ["📄 自訂上傳 PDF 檔案"]
    )
    
    reading_title = ""
    reading_text = ""
    
    if lesson_choice == "📄 自訂上傳 PDF 檔案":
        uploaded_pdf = st.file_uploader("上傳課文 PDF", type=["pdf"])
        if uploaded_pdf:
            reader = PdfReader(uploaded_pdf)
            raw_text = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    raw_text += t + "\n"
            raw_text = re.sub(r'[\U00010000-\U0010ffff]', '', raw_text)
            reading_title = "自訂上傳課文"
            reading_text = raw_text.strip()
        else:
            reading_title = "未選擇"
            reading_text = "請在左側上傳您的課文 PDF。"
    else:
        reading_title = BUILTIN_LESSONS[lesson_choice]["title"]
        reading_text = BUILTIN_LESSONS[lesson_choice]["text"]

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

# 3. 手機上半部：段落分明、高對比白色大字閱讀區
st.caption(f"📖 本次閱讀課文：《{reading_title}》 (可滑動閱讀)")
st.markdown(f'<div class="reading-card">{reading_text}</div>', unsafe_allow_html=True)
st.divider()

# 4. 手機下半部：AI 伴讀聊天室
SYSTEM_PROMPT = f"""
你是一位專業的二語華語閱讀教學助教。
學生正在閱讀課文《{reading_title}》：
\"\"\"{reading_text}\"\"\"

【引導規則】：
1. 向學生親切問好，請他閱讀上方教材的前半段，讀完告訴你。
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
        {"role": "model", "content": f"你好，{student_id}！今天我們要一起讀《{reading_title}》。請先看上方框框裡的文章，讀完前幾句後請告訴我「我讀完了」！"}
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
