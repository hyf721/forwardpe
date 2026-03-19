import streamlit as st
import yfinance as yf
import pandas as pd
import re

# --- 頁面初始設定 ---
st.set_page_config(page_title="全球資產 Forward P/E 監控", layout="wide")

# --- 1. 常用對照表 ---
COMMON_STOCKS = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "6669": "緯穎",
    "NVDA": "NVIDIA (輝達)", "AVGO": "Broadcom (博通)", "TSLA": "Tesla", 
    "AAPL": "Apple", "VT": "Vanguard 全球股票 ETF", "BND": "Vanguard 總體債券 ETF"
}

with st.sidebar:
    st.header("🌎 全球熱門標的參考")
    st.write("**台股:** 2330, 2317, 2454, 6669")
    st.write("**美股:** NVDA, AVGO, VT, BND, AAPL")
    st.markdown("---")
    st.subheader("📅 歷史數據區間")
    time_range = st.select_slider(
        "選擇顯示範圍",
        options=["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
        value="1y"
    )
    st.info("💡 提示：本版本已校準為 Yahoo 網頁顯示之 Forward P/E (今年預估)。")

# --- 主標題 ---
st.title("📈 全球資產估值監控儀表板")
st.write("同步 Yahoo 網頁標竿數據，精準掌握台美股估值位階")
st.markdown("---")

# --- 2. 核心識別邏輯 ---
user_input = st.text_input("👉 請輸入代號 (例如 2330 或 AVGO):", placeholder="在此輸入...").upper().strip()

def get_global_ticker(symbol):
    if not symbol: return None, None, ""
    if symbol.isdigit():
        for suffix in [".TW", ".TWO"]:
            target = f"{symbol}{suffix}"
            t = yf.Ticker(target)
            if not t.history(period="1d").empty:
                return t, target, "TWD"
    else:
        t = yf.Ticker(symbol)
        if not t.history(period="1d").empty:
            return t, symbol, "USD"
    return None, None, ""

if user_input:
    with st.spinner(f'正在分析 {user_input} 的數據...'):
        ticker_obj, formatted_symbol, currency = get_global_ticker(user_input)
        
        if ticker_obj:
            try:
                info = ticker_obj.info
                
                # A. 提取名稱
                display_name = COMMON_STOCKS.get(user_input)
                if not display_name:
                    raw_name = info.get('shortName') or info.get('longName') or "Unknown"
                    if currency == "TWD":
                        extracted = "".join(re.findall(r'[\u4e00-\u9fff]+', raw_name))
                        display_name = extracted if extracted else raw_name
                    else:
                        display_name = raw_name

                # B. 精準 Forward P/E 算法 (對齊網頁 30.x)
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                trailing_pe = info.get('trailingPE')
                
                # 預設值使用 API 原本的 forwardPE
                final_fpe = info.get('forwardPE')
                f_eps = None

                # 嘗試從分析師預估表中抓取 '0y' (今年平均)
                try:
                    df_est = ticker_obj.earnings_estimate
                    if df_est is not None and not df_est.empty and '0y' in df_est.index:
                        f_eps = df_est.loc['0y', 'avg']
                        if f_eps and current_price:
                            final_fpe = current_price / f_eps
                except:
                    # 若抓不到表格，就維持使用 info.get('forwardPE')
                    pass
                
                # C. 顯示區
                st.subheader(f"🚀 {display_name} ({formatted_symbol})")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("目前股價", f"{current_price} {currency}")
                
                f_pe_str = f"{final_fpe:.2f}" if final_fpe else "無數據"
                t_pe_str = f"{trailing_pe:.2f}" if trailing_pe else "無數據"
                
                m2.metric("預估 P/E (Forward)", f_pe_str)
                m3.metric("歷史 P/E (Trailing)", t_pe_str)

                # D. 估值分析
                st.markdown("### 📈 估值位階分析")
                if f_eps:
                    st.caption(f"📌 數據校準：Forward P/E 是基於分析師預估今年 EPS ({f_eps:.2f}) 計算。")
                
                pe_to_check = final_fpe if final_fpe else trailing_pe
                
                if pe_to_check:
                    if pe_to_check < 15:
                        st.success("🟢 **估值吸引人**：目前 P/E 較低，適合長線價值投資佈局。")
                    elif 15 <= pe_to_check < 30:
                        st.info("🔵 **合理區間**：反映了正常的成長預期，目前溢價尚屬溫和。")
                    elif 30 <= pe_to_check < 50:
                        st.warning("🟡 **估值偏高**：市場情緒樂觀，需注意短線是否有過度反應。")
                    else:
                        st.error("🔴 **極度高估**：估值處於歷史高位區間，請檢視基本面支撐力度。")
                else:
                    st.warning("⚠️ 數據不足，建議參考資產淨值 (NAV) 或財報現金流。")

                # E. 歷史走勢圖
                st.markdown(f"### 🔍 歷史走勢圖 (區間: {time_range})")
                hist = ticker_obj.history(period=time_range)
                if not hist.empty:
                    st.line_chart(hist['Close'])

            except Exception as e:
                st.error(f"解析數據時發生錯誤：{e}")
        else:
            st.error(f"❌ 找不到代碼 {user_input}。")
else:
    st.info("👆 請輸入代號開始分析。建議嘗試：AVGO, 2330, NVDA")
