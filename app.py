import base64
from datetime import datetime
import glob
from io import BytesIO
import os
import re
import pandas as pd
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="オーストラリア中古車輸出 適合判定システム",
    layout="wide",
    page_icon="🚘",
)


@st.cache_data(show_spinner=False)
def prepare_character_sprites():
    img_candidates = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        for f in glob.glob(ext):
            if "char" in f.lower() or "image_bb" in f.lower():
                img_candidates.append(f)
    if not img_candidates:
        all_imgs = glob.glob("*.jpg") + glob.glob("*.jpeg") + glob.glob("*.png")
        img_candidates = [f for f in all_imgs if not f.startswith("AUS_SEV")]

    if not img_candidates:
        return None

    try:
        img = Image.open(img_candidates[0]).convert("RGBA")
        w, h = img.size

        datas = img.getdata()
        new_data = []
        for r, g, b, a in datas:
            is_sky = (b > 210 and g > 190 and r < 185 and (b - r) > 35)
            is_white_bg = (r > 246 and g > 246 and b > 246)
            if is_sky or is_white_bg:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append((r, g, b, a))
        img.putdata(new_data)

        boxes = [
            (0, 0, int(w * 0.34), h),
            (int(w * 0.33), 0, int(w * 0.67), h),
            (int(w * 0.66), 0, w, h),
        ]
        sprites = []
        for box in boxes:
            cropped = img.crop(box)
            bbox = cropped.getbbox()
            if bbox:
                cropped = cropped.crop(bbox)
            buf = BytesIO()
            cropped.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            sprites.append("data:image/png;base64," + b64)

        return {
            "hachiware": sprites[0],
            "chiikawa": sprites[1],
            "usagi": sprites[2],
        }
    except Exception:
        return None


sprites = prepare_character_sprites()

CUSTOM_CSS = (
    "<style>"
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');"
    "html, body, [class*='css'] { font-family: 'Inter', 'Noto Sans JP', sans-serif; }"
    ".stApp { background-color: #F4F6F9; }"
    "section[data-testid='stSidebar'] { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }"
    "@media (max-width: 768px) { .main .block-container { padding: 1.2rem 0.8rem 2rem 0.8rem !important; } }"
    "@media (min-width: 769px) { .main .block-container { padding: 1.8rem 1rem 3rem 1rem !important; max-width: 1180px; } }"
    "@keyframes footStepIdle {"
    "  0%, 100% { transform: translateY(0px) rotate(0deg) scaleY(1); }"
    "  25%      { transform: translateY(-2px) rotate(-2.5deg) scaleY(0.98); }"
    "  50%      { transform: translateY(0px) rotate(0deg) scaleY(1); }"
    "  75%      { transform: translateY(-2px) rotate(2.5deg) scaleY(0.98); }"
    "}"
    "@keyframes footStepActive {"
    "  0%, 100% { transform: translateY(0px) rotate(0deg) scaleY(1); }"
    "  20%      { transform: translateY(-5px) rotate(-4.5deg) scaleY(0.96); }"
    "  40%      { transform: translateY(0px) rotate(0deg) scaleY(1.02); }"
    "  60%      { transform: translateY(-5px) rotate(4.5deg) scaleY(0.96); }"
    "  80%      { transform: translateY(0px) rotate(0deg) scaleY(1.02); }"
    "}"
    ".chara-step-idle { transform-origin: bottom center; animation: footStepIdle 2.2s ease-in-out infinite; display: inline-block; user-select: none; }"
    ".chara-step-active { transform-origin: bottom center; animation: footStepActive 0.65s ease-in-out 5, footStepIdle 2.2s ease-in-out 3.3s infinite; display: inline-block; user-select: none; }"
    ".header-box { display: flex; align-items: center; justify-content: space-between; background: #FFFFFF; padding: 18px 24px; border-radius: 14px; border: 1px solid #E2E8F0; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04); margin-bottom: 18px; }"
    ".app-title { font-size: 1.45rem; font-weight: 700; color: #0F172A; margin: 0 0 6px 0; }"
    ".master-badge { display: inline-flex; align-items: center; gap: 6px; background: #F1F5F9; color: #334155; font-size: 0.8rem; font-weight: 600; padding: 4px 12px; border-radius: 999px; border: 1px solid #CBD5E1; }"
    ".dot-green { width: 8px; height: 8px; background-color: #10B981; border-radius: 50%; display: inline-block; }"
    ".result-card { background: #FFFFFF; border-radius: 14px; padding: 20px 24px; margin-bottom: 16px; border: 1px solid #E2E8F0; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05); }"
    ".card-ok { border-left: 6px solid #10B981; }"
    ".card-warn { border-left: 6px solid #F59E0B; }"
    ".card-ng { border-left: 6px solid #EF4444; }"
    ".sev-header { font-size: 1.12rem; font-weight: 700; color: #0F172A; margin-bottom: 8px; }"
    ".code-pill { display: inline-block; background: #EFF6FF; color: #1D4ED8; font-weight: 600; font-size: 0.82rem; padding: 3px 10px; border-radius: 6px; border: 1px solid #BFDBFE; margin-bottom: 12px; }"
    ".info-list { color: #334155; font-size: 0.92rem; line-height: 1.75; margin: 0; padding-left: 18px; }"
    ".status-box-ok { background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; border-radius: 10px; padding: 12px 14px; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; justify-content: space-between; }"
    ".status-box-warn { background: #FFFBEB; color: #92400E; border: 1px solid #FDE68A; border-radius: 10px; padding: 12px 14px; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; justify-content: space-between; }"
    ".status-box-ng { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; border-radius: 10px; padding: 12px 14px; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; justify-content: space-between; }"
    "div.stButton > button[kind='primary'] { background-color: #1E293B; color: #FFFFFF; border: none; border-radius: 8px; font-weight: 600; padding: 0.55rem 1rem; width: 100%; }"
    "div.stButton > button[kind='primary']:hover { background-color: #0F172A; }"
    "</style>"
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

ROVER_SEVS_URL = "https://www.rover.infrastructure.gov.au/PublishedApprovals/SEVApprovals/"
ROVER_MRE_URL = "https://www.rover.infrastructure.gov.au/PublishedApprovals/MREApprovals/"
LEGACY_EXCEL_PATH = "AUS SEV早見表.xlsx"


def read_sev_file(file_obj_or_path):
    name = file_obj_or_path if isinstance(file_obj_or_path, str) else file_obj_or_path.name
    if str(name).lower().endswith(".csv"):
        df = pd.read_csv(file_obj_or_path, skiprows=1).iloc[:, :8]
    else:
        df = pd.read_excel(file_obj_or_path, skiprows=1).iloc[:, :8]
    df.columns = [
        "SEV番号",
        "メーカー",
        "車種名",
        "カテゴリ",
        "型式",
        "製造開始年月",
        "製造終了年月",
        "有効期限",
    ]
    return df.dropna(subset=["SEV番号"])


@st.cache_data(ttl=600, show_spinner=False)
def load_latest_sev_master():
    candidates = glob.glob("AUS_SEV_LATEST*.xlsx") + glob.glob("AUS_SEV_LATEST*.xls") + glob.glob("AUS_SEV_LATEST*.csv")
    if candidates:
        candidates.sort(key=lambda x: (x, os.path.getmtime(x)), reverse=True)
        latest_path = candidates[0]
        try:
            df = read_sev_file(latest_path)
            date_match = re.search(r"\((\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})\)", latest_path)
            date_str = date_match.group(1) if date_match else "最新版"
            return df, f"ROVER SEVs Master | {date_str} 更新（全{len(df)}車種）"
        except Exception as e:
            return None, f"読み込みエラー: {e}"

    if os.path.exists(LEGACY_EXCEL_PATH):
        try:
            df = read_sev_file(LEGACY_EXCEL_PATH)
            return df, f"ROVER SEVs Master | 標準データ（全{len(df)}車種）"
        except Exception as e:
            return None, f"読み込みエラー: {e}"

    return None, "SEVデータファイル未検出"


def parse_my(date_str):
    if pd.isna(date_str) or str(date_str).strip() in ["No end date", "", "nan", "None"]:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), "%m/%Y")
    except Exception:
        return None


def parse_dmy(date_str):
    if pd.isna(date_str) or str(date_str).strip() in ["", "nan", "None"]:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
    except Exception:
        return None


st.sidebar.markdown("### 🔍 車両・型式検索")
input_query = st.sidebar.text_input("メーカー・車種名・型式・SEV番号", value="ZVW40").strip().upper()

col_y, col_m = st.sidebar.columns(2)
build_year = col_y.number_input("製造年 (年)", min_value=1980, max_value=2026, value=2015)
build_month = col_m.number_input("製造月 (月)", min_value=1, max_value=12, value=6)

raws_permission = st.sidebar.checkbox(
    "提携RAWs工場が Model Report の利用ライセンスを保有している", value=True
)

run_clicked = st.sidebar.button("🔍 適合判定を実行", type="primary")

with st.sidebar.expander("⚙️ 詳細オプション・手動データ読込", expanded=False):
    reload_clicked = st.button("🔄 最新ファイルに再読み込み")
    if reload_clicked:
        st.cache_data.clear()
        st.rerun()
    uploaded_file = st.file_uploader(
        "手元のExcel / CSVで一時判定する場合", type=["xlsx", "xls", "csv"]
    )

anim_class = "chara-step-active" if run_clicked else "chara-step-idle"

if sprites and sprites.get("chiikawa"):
    chiikawa_div = (
        f'<div style="text-align: center; margin-top: 24px; padding-top: 12px;">'
        f'<img src="{sprites["chiikawa"]}" class="{anim_class}" style="width: 96px; height: auto;" />'
        f'</div>'
    )
    st.sidebar.markdown(chiikawa_div, unsafe_allow_html=True)

if uploaded_file:
    try:
        sev_df = read_sev_file(uploaded_file)
        badge_text = f"手動読込: {uploaded_file.name}（全{len(sev_df)}車種）"
    except Exception as e:
        st.error(f"ファイルの読み込みに失敗しました: {e}")
        sev_df = None
        badge_text = "読み込みエラー"
else:
    sev_df, badge_text = load_latest_sev_master()

usagi_html = ""
if sprites and sprites.get("usagi"):
    usagi_html = f'<img src="{sprites["usagi"]}" class="{anim_class}" style="width: 78px; height: auto; margin-left: 16px;" />'

header_html = (
    f'<div class="header-box">'
    f'<div>'
    f'<div class="app-title">🚘 オーストラリア向け中古車輸出 適合判定システム</div>'
    f'<div class="master-badge"><span class="dot-green"></span>{badge_text}</div>'
    f'</div>'
    f'<div>{usagi_html}</div>'
    f'</div>'
)
st.markdown(header_html, unsafe_allow_html=True)

if sev_df is None:
    st.error(f"データファイルを読み込めませんでした（{badge_text}）。")
elif not input_query:
    st.info("左側の検索欄にメーカー・車種名・型式・SEV番号のいずれかを入力してください。")
else:
    target_date = datetime(build_year, build_month, 1)
    today = datetime.now()
    query_clean = re.
