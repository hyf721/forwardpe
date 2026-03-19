import streamlit as st
import yfinance as yf
import pandas as pd
import re

# --- 頁面初始設定 ---
st.set_page_config(page_title="全球資產 Forward P/E 監控", layout="wide")

# --- 1. 常用對照表 (含美股重點標的) ---
COMMON_STOCKS = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "6669": "緯穎",
    "NVDA": "NVIDIA (輝達)", "AVGO": "Broadcom (博通)", "TSLA": "Tesla", 
    "AAPL": "Apple", "VT": "Vanguard 全球股票 ETF", "BND": "Vanguard 總體債券 ETF"
}

with st.sidebar:
    st.header("🌎 全球熱門標的參考")
    st.write("**台股 (輸入數字):** 2330, 2317, 2454, 6669")
    st.write("**美股 (輸入代號):** NVDA, AVGO, VT, BND, AAPL")
    st.markdown("---")
    # 歷史區間調整
    st.subheader("📅 歷史數據區間")
    time_range = st.select_slider(
        "選擇顯示範圍",
        options=["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
        value="1y"
    )
    st.info("💡 提示：美股代號不需後綴，台股系統會自動補齊。")

# --- 主標題 ---
st.title("📈 全球資產估值監控儀表板")
st.write("同時支援台股與美股 Forward P/E 實時分析")
st.markdown("---")

# --- 2. 搜尋與自動識別邏輯 ---
user_input = st.text_input("👉 請輸入代號 (例如 2330 或 NVDA):", placeholder="在此輸入...").upper().strip()

def get_global_ticker(symbol):
    """自動識別市場並回傳 Ticker"""
    if not symbol: return None, None, ""
    
    # 判斷是否為台股 (純數字)
    if symbol.isdigit():
        for suffix in [".TW", ".TWO"]:
            target = f"{symbol}{suffix}"
            t = yf.Ticker(target)
            if not t.history(period="1d").empty:
                return t, target, "TWD"
    else:
        # 視為美股
        t = yf.Ticker(symbol)
        if not t.history(period="1d").empty:
            return t, symbol, "USD"
            
    return None, None, ""

if user_input:
    with st.spinner(f'正在獲取 {user_input} 的全球數據...'):
        ticker_obj, formatted_symbol, currency = get_global_ticker(user_input)
        
        if ticker_obj:
            try:
                info = ticker_obj.info
                
                # A. 提取名稱 (優先看自定義表)
                display_name = COMMON_STOCKS.get(user_input)
                if not display_name:
                    raw_name = info.get('shortName') or info.get('longName') or "Unknown"
                    # 台股過濾中文，美股保留原名
                    if currency == "TWD":
                        extracted = "".join(re.findall(r'[\u4e00-\u9fff]+', raw_name))
                        display_name = extracted if extracted else raw_name
                    else:
                        display_name = raw_name
                
                # B. 數值抓取
                forward_pe = info.get('forwardPE')
                trailing_pe = info.get('trailingPE')
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                
                # C. 顯示區
                st.subheader(f"🚀 {display_name} ({formatted_symbol})")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("目前股價", f"{current_price} {currency}")
                
                f_pe_str = f"{forward_pe:.2f}" if forward_pe else "無數據"
                t_pe_str = f"{trailing_pe:.2f}" if trailing_pe else "無數據"
                
                m2.metric("預估 P/E (Forward)", f_pe_str)
                m3.metric("歷史 P/E (Trailing)", t_pe_str)

                # D. 估值分析
                st.markdown("### 📈 估值位階分析")
                pe_to_check = forward_pe if forward_pe else trailing_pe
                
                if pe_to_check:
                    # 美股科技股 (如 NVDA) 容忍度通常較高，但此處採用通用標準
                    if pe_to_check < 15:
                        st.success("🟢 **估值吸引人**：目前 P/E 較低，適合長線價值投資佈局。")
                    elif 15 <= pe_to_check < 30:
                        st.info("🔵 **合理區間**：反映了正常的成長預期，目前溢價尚屬溫和。")
                    elif 30 <= pe_to_check < 50:
                        st.warning("🟡 **估值偏高**：市場情緒樂觀，需注意短線是否有過度反應。")
                    else:
                        st.error("🔴 **極度高估**：估值處於歷史高位區間，請檢視基本面支撐力度。")
                else:
                    st.warning("⚠️ 數據不足（可能為 ETF 或虧損公司），建議參考資產淨值 (NAV)。")

                # E. 歷史走勢圖 (使用側邊欄選擇的區間)
                st.markdown(f"### 🔍 歷史走勢圖 (區間: {time_range})")
                hist = ticker_obj.history(period=time_range)
                if not hist.empty:
                    st.line_chart(hist['Close'])
                else:
                    st.write("查無該區間的歷史數據。")

            except Exception as e:
                st.error(f"解析數據時發生錯誤：{e}")
        else:
            st.error(f"❌ 找不到代碼 {user_input}。請確認美股代號或台股股號是否正確。")
else:
    st.info("👆 請在上方輸入框輸入台美股代號開始分析。例如：2330, NVDA, VT, AVGO")
