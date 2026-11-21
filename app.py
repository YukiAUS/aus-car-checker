import streamlit as st
import streamlit.components.v1 as components

# キャラクター画像（お手持ちのBase64またはURLに変更してください）
CHARA_IMG_URL = "https://em-content.zobj.net/source/apple/391/koala_1f428.png"

# 1. 安全なCSS（元のクリック領域を壊さず見た目だけ変更）
safe_search_button_css = f"""
<style>
/* Streamlit新旧バージョン両対応のサイドバー開閉ボタン */
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button,
[data-testid="stExpandSidebarButton"] {{
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%) !important;
    color: #ffffff !important;
    border: 2px solid #ffffff !important;
    border-radius: 999px !important;
    padding: 4px 14px 4px 6px !important;
    box-shadow: 0 3px 10px rgba(21, 101, 192, 0.35) !important;
    width: auto !important;
    min-width: 145px !important;
    height: 40px !important;
    pointer-events: auto !important;
}}

/* 元々の矢印アイコンを消す */
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="collapsedControl"] button svg,
[data-testid="stExpandSidebarButton"] svg {{
    display: none !important;
}}

/* キャラクター画像を左側に表示 */
[data-testid="stSidebarCollapsedControl"] button::before,
[data-testid="collapsedControl"] button::before,
[data-testid="stExpandSidebarButton"]::before {{
    content: "" !important;
    display: inline-block !important;
    width: 28px !important;
    height: 28px !important;
    border-radius: 50% !important;
    background-color: #ffffff !important;
    background-image: url("{CHARA_IMG_URL}") !important;
    background-size: cover !important;
    background-position: center !important;
    flex-shrink: 0 !important;
}}

/* 「🔍 車種を検索」の文字を表示 */
[data-testid="stSidebarCollapsedControl"] button::after,
[data-testid="collapsedControl"] button::after,
[data-testid="stExpandSidebarButton"]::after {{
    content: "🔍 車種を検索" !important;
    font-family: "Meiryo", sans-serif !important;
    font-size: 13px !important;
    font-weight: bold !important;
    color: #ffffff !important;
    white-space: nowrap !important;
}}
</style>
"""
st.markdown(safe_search_button_css, unsafe_allow_html=True)
