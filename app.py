import streamlit as st

# ページ設定（サイドバーをスマホでも分かりやすく開閉できるように設定）
st.set_page_config(
    page_title="オーストラリア向け中古車輸出 適合判定システム",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed"  # スマホ初期表示時は結果を広く見せつつ、左上ボタンで即検索
)

# キャラクター画像のURLまたはBase64データ（お手持ちのキャラ画像に差し替え可能）
CHARA_IMG_URL = "https://em-content.zobj.net/source/apple/391/koala_1f428.png"

# スマホ左上「>>」ボタンをキャラクター付き「車種を検索」ボタンに変えるカスタムCSS
custom_search_button_css = f"""
<style>
/* 1. 左上の「>>」ボタン（サイドバー開閉ボタン）を大きく目立つキャラ付きボタンに変更 */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {{
    position: fixed !important;
    top: 10px !important;
    left: 12px !important;
    z-index: 999999 !important;
    width: auto !important;
    height: auto !important;
    background: transparent !important;
}}

[data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button {{
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%) !important;
    color: #ffffff !important;
    border: 2.5px solid #ffffff !important;
    border-radius: 999px !important;
    padding: 6px 16px 6px 8px !important;
    box-shadow: 0 4px 12px rgba(21, 101, 192, 0.35) !important;
    cursor: pointer !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    width: auto !important;
    height: 44px !important;
}}

[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="collapsedControl"] button:hover {{
    transform: scale(1.04) !important;
    box-shadow: 0 6px 16px rgba(21, 101, 192, 0.45) !important;
}}

/* 元々の「>>」矢印アイコンを非表示にする */
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="collapsedControl"] button svg {{
    display: none !important;
}}

/* キャラクターアイコンをボタン左端に配置 */
[data-testid="stSidebarCollapsedControl"] button::before,
[data-testid="collapsedControl"] button::before {{
    content: "" !important;
    display: inline-block !important;
    width: 32px !important;
    height: 32px !important;
    border-radius: 50% !important;
    background-color: #ffffff !important;
    background-image: url("{CHARA_IMG_URL}") !important;
    background-size: cover !important;
    background-position: center !important;
    flex-shrink: 0 !important;
}}

/* 「🔍 車種を検索」のテキストラベルを追加 */
[data-testid="stSidebarCollapsedControl"] button::after,
[data-testid="collapsedControl"] button::after {{
    content: "🔍 車種を検索" !important;
    font-family: "Meiryo", "Hiragino Kaku Gothic ProN", sans-serif !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    white-space: nowrap !important;
    letter-spacing: 0.03em !important;
}}

/* 2. スマホ画面で上のヘッダーバーとメインコンテンツが重ならないよう余白を確保 */
@media (max-width: 768px) {{
    .block-container {{
        padding-top: 3.8rem !important;
    }}
}}
</style>
"""

st.markdown(custom_search_button_css, unsafe_allow_html=True)
