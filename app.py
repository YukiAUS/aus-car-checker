import base64
from collections import deque
from datetime import datetime
import glob
from io import BytesIO
import os
import pandas as pd
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="オーストラリア中古車輸出 適合判定システム",
    layout="wide",
    page_icon="🚘",
)


def remove_outer_bg_only(pil_img):
    """画像の四隅から繋がっている外側背景（空色・白）のみを透明化し、キャラの顔・体の白さは絶対に透けさせない"""
    img = pil_img.convert("RGBA")
    w, h = img.size
    pixels = img.load()
    visited = set()
    queue = deque()

    def is_bg_color(r, g, b):
        is_sky = (b > 205 and g > 185 and r < 190 and (b - r) > 30)
        is_white = (r > 242 and g > 242 and b > 242)
        return is_sky or is_white

    # 外周のピクセルを起点にする
    for x in range(w):
        for y in (0, h - 1):
            r, g, b, _ = pixels[x, y]
            if is_bg_color(r, g, b):
                queue.append((x, y))
                visited.add((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if (x, y) not in visited:
                r, g, b, _ = pixels[x, y]
                if is_bg_color(r, g, b):
                    queue.append((x, y))
                    visited.add((x, y))

    # 外側から連続する背景領域だけを透過
    while queue:
        cx, cy = queue.popleft()
        pixels[cx, cy] = (255, 255, 255, 0)
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                r, g, b, _ = pixels[nx, ny]
                if is_bg_color(r, g, b):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    bb = img.getbbox()
    if bb:
        img = img.crop(bb)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")


def process_single_sprite(img_path):
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size
    if w > h * 1.4:
        boxes = [(0, 0, int(w * 0.34), h), (int(w * 0.33), 0, int(w * 0.67), h), (int(w * 0.66), 0, w, h)]
        return [remove_outer_bg_only(img.crop(box)) for box in boxes]
    return [remove_outer_bg_only(img)]


@st.cache_data(show_spinner=False)
def load_all_four_characters():
    all_imgs = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.JPEG", "*.PNG"):
        for f in glob.glob(ext):
            if not f.startswith("AUS_SEV") and f not in all_imgs:
                all_imgs.append(f)

    if not all_imgs:
        return {}

    assigned = {}
    remaining_sprites = []

    for f in sorted(all_imgs):
        try:
            sp_list = process_single_sprite(f)
            if len(sp_list) == 3:
                assigned.setdefault("hachiware", sp_list[0])
                assigned.setdefault("chiikawa", sp_list[1])
                assigned.setdefault("usagi", sp_list[2])
                continue

            sp = sp_list[0]
            fl = f.lower()
            if ("usagi" in fl or "うさぎ" in fl or "rabbit" in fl) and "usagi" not in assigned:
                assigned["usagi"] = sp
            elif ("hachi" in fl or "ハチ" in fl or "cat" in fl) and "hachiware" not in assigned:
                assigned["hachiware"] = sp
            elif ("chii" in fl or "ちい" in fl) and "chiikawa" not in assigned:
                assigned["chiikawa"] = sp
            elif ("kuri" in fl or "くり" in fl or "2026y" in fl or "4" in fl) and "kurimanju" not in assigned:
                assigned["kurimanju"] = sp
            else:
                remaining_sprites.append(sp)
        except Exception:
            continue

    for slot in ["usagi", "hachiware", "chiikawa", "kurimanju"]:
        if slot not in assigned and remaining_sprites:
            assigned[slot] = remaining_sprites.pop(0)

    return assigned


sprites = load_all_four_characters()

CUSTOM_CSS = (
    "<style>"
    ".stApp { background-color: #F4F6F9; }"
    "section[data-testid='stSidebar'] { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }"
    ".main .block-container { padding-top: 1.6rem !important; max-width: 1180px; }"
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
    ".chara-step-idle { transform-origin: bottom center; animation: footStepIdle 2.2s ease-in-out infinite; display: inline-block; }"
    ".chara-step-active { transform-origin: bottom center; animation: footStepActive 0.65s ease-in-out 5, footStepIdle 2.2s ease-in-out 3.3s infinite; display: inline-block; }"
    ".chara-static { display: inline-block; }"
    ".header-box { display: flex; align-items: center; justify-content: space-between; background: linear-gradient(135deg, #2B4168 0%, #3B5984 100%); padding: 16px 26px; border-radius: 14px; box-shadow: 0 4px 12px rgba(15,23,42,0.08); margin-bottom: 18px; }"
    ".app-title { font-size: 1.45rem; font-weight: 700; color: #FFFFFF; margin: 0 0 8px 0; }"
    ".master-badge { display: inline-flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.95); color: #1E293B; font-size: 0.8rem; font-weight: 600; padding: 4px 12px; border-radius: 999px; }"
    ".dot-green { width: 8px; height: 8px; background-color: #10B981; border-radius: 50%; display: inline-block; }"
    ".result-card { background: #FFFFFF; border-radius: 14px; padding: 20px 24px; margin-bottom: 16px; border: 1px solid #E2E8F0; box-shadow: 0 4px 12px rgba(15,23,42,0.05); }"
    ".card-ok { border-left: 6px solid #10B981; }"
    ".card-warn { border-left: 6px solid #F59E0B; }"
    ".card-ng { border-left: 6px solid #EF4444; }"
    ".sev-header { font-size: 1.1rem; font-weight: 700; color: #0F172A; margin-bottom: 8px; }"
    ".code-pill { display: inline-block; background: #EFF6FF; color: #1D4ED8; font-weight: 600; font-size: 0.82rem; padding: 3px 10px; border-radius: 6px; border: 1px solid #BFDBFE; margin-bottom: 12px; }"
    ".info-list { color: #334155; font-size: 0.92rem; line-height: 1.75; margin: 0; padding-left: 18px; }"
    ".status-box-ok { background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; border-radius: 10px; padding: 10px 14px; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; justify-content: space-between; }"
    ".status-box-warn { background: #FFFBEB; color: #92400E; border: 1px solid #FDE68A; border-radius: 10px; padding: 10px 14px; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; justify-content: space-between; }"
    ".status-box-ng { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; border-radius: 10px; padding: 10px 14px; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; justify-content: space-between; }"
    ".kuri-card { display: flex; align-items: center; justify-content: flex-end; gap: 10px; margin-top: 2px; }"
    ".kuri-img { width: 68px; height: 68px; object-fit: cover; border-radius: 14px; border: 2px solid #CBD5E1; box-shadow: 0 2px 6px rgba(0,0,0,0.08); background: #FFFFFF; }"
    "div.stButton > button[kind='primary'] { background-color: #2B4168; color: #FFFFFF; border: none; border-radius: 8px; font-weight: 600; width: 100%; }"
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
    df.columns = ["SEV番号", "メーカー", "車種名", "カテゴリ", "型式", "製造開始年月", "製造終了年月", "有効期限"]
    return df.dropna(subset=["SEV番号"])


@st.cache_data(ttl=600, show_spinner=False)
def load_latest_sev_master():
    candidates = glob.glob("AUS_SEV_LATEST*.xlsx") + glob.glob("AUS_SEV_LATEST*.xls") + glob.glob("AUS_SEV_LATEST*.csv")
    if candidates:
        candidates.sort(key=lambda x: (x, os.path.getmtime(x)), reverse=True)
        latest_path = candidates[0]
        try:
            df = read_sev_file(latest_path)
            date_str = "最新版"
            if "(" in latest_path and ")" in latest_path:
                date_str = latest_path.split("(")[1].split(")")[0]
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
raws_permission = st.sidebar.checkbox("提携RAWs工場が Model Report の利用ライセンスを保有している", value=True)
run_clicked = st.sidebar.button("🔍 適合判定を実行", type="primary")

with st.sidebar.expander("⚙️ 詳細オプション・手動データ読込", expanded=False):
    if st.button("🔄 最新ファイルに再読み込み"):
        st.cache_data.clear()
        st.rerun()
    uploaded_file = st.file_uploader("手元のExcel / CSVで一時判定する場合", type=["xlsx", "xls", "csv"])

# 右の上から2番目（判定ステータス内）だけが動くアニメーションクラス
moving_anim_class = "chara-step-active" if run_clicked else "chara-step-idle"

# サイドバー下部（静止）
if sprites.get("chiikawa"):
    st.sidebar.markdown(
        f'<div style="text-align:center;margin-top:20px;"><img src="{sprites["chiikawa"]}" class="chara-static" style="width:94px;border-radius:12px;" /></div>',
        unsafe_allow_html=True,
    )

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

# 右上ヘッダー内（静止・色抜けなし）
usagi_html = f'<img src="{sprites["usagi"]}" class="chara-static" style="width:82px;border-radius:12px;margin-left:16px;" />' if sprites.get("usagi") else ""
st.markdown(
    f'<div class="header-box"><div><div class="app-title">🚘 オーストラリア向け中古車輸出 適合判定システム</div><div class="master-badge"><span class="dot-green"></span>{badge_text}</div></div><div>{usagi_html}</div></div>',
    unsafe_allow_html=True,
)

if sev_df is None:
    st.error(f"データファイルを読み込めませんでした（{badge_text}）。")
elif not input_query:
    st.info("左側の検索欄にメーカー・車種名・型式・SEV番号のいずれかを入力してください。")
else:
    target_date = datetime(build_year, build_month, 1)
    today = datetime.now()
    query_clean = "".join(input_query.split())

    def is_match(row):
        sev_id = "".join(str(row["SEV番号"]).upper().split())
        make_str = "".join(str(row["メーカー"]).upper().split())
        model_str = "".join(str(row["車種名"]).upper().split())
        code_str = "".join(str(row["型式"]).upper().split())
        combined = make_str + model_str + code_str + sev_id
        return (query_clean in combined) or (code_str not in ["", "NAN"] and code_str in query_clean)

    matched = sev_df[sev_df.apply(is_match, axis=1)]

    if matched.empty:
        st.error(f"**輸出不可 (SEV未登録):** 「{input_query}」に一致するSEV登録情報が見つかりませんでした。")
    else:
        st.markdown(f"#### 📋 適合判定結果（{len(matched)}件該当）")
        for idx, row in matched.iterrows():
            sev_no = str(row["SEV番号"]).strip()
            make = row["メーカー"]
            model = row["車種名"]
            category = row["カテゴリ"]
            model_code = row["型式"]
            f_str = row["製造開始年月"]
            t_str = row["製造終了年月"]
            exp_str = row["有効期限"]

            d_from = parse_my(f_str)
            d_to = parse_my(t_str)
            expiry = parse_dmy(exp_str)
            in_range = (not d_from or target_date >= d_from) and (not d_to or target_date <= d_to)
            is_expired = expiry and expiry < today

            if not in_range:
                card_cls, box_cls, status_text, sub_note = "card-ng", "status-box-ng", "❌ 輸出不可（製造年月 対象外）", f"{build_year}年{build_month}月は対象期間外です。"
            elif is_expired:
                card_cls, box_cls, status_text, sub_note = "card-warn", "status-box-warn", "⚠️ 要確認（SEV有効期限切れ）", f"有効期限 ({exp_str}) を過ぎています。"
            elif not raws_permission:
                card_cls, box_cls, status_text, sub_note = "card-warn", "status-box-warn", "⚠️ 判定保留（RAWsライセンス未確認）", "提携RAWs工場のMRE利用権限を確認してください。"
            else:
                card_cls, box_cls, status_text, sub_note = "card-ok", "status-box-ok", "✅ SEVs適合（MRE要確認）", ""

            # 右の上から2番目（判定ステータス内）：ここだけが動く！
            hachi_html = f'<img src="{sprites["hachiware"]}" class="{moving_anim_class}" style="width:66px;border-radius:10px;margin-left:10px;" />' if sprites.get("hachiware") else ""
            f_disp = f_str if pd.notna(f_str) and f_str else "指定なし"
            t_disp = t_str if pd.notna(t_str) and t_str else "指定なし"
            exp_disp = exp_str if pd.notna(exp_str) and exp_str else "期限設定なし"
            cat_disp = category if pd.notna(category) and category else "-"

            c1, c2 = st.columns([1.45, 1])
            with c1:
                st.markdown(
                    f'<div class="result-card {card_cls}"><div class="sev-header">🚘 {sev_no} ｜ {make} {model}</div><div class="code-pill">型式: {model_code}</div><ul class="info-list"><li><strong>対象製造期間:</strong> {f_disp} 〜 {t_disp}</li><li><strong>SEV有効期限:</strong> {exp_disp}</li><li><strong>車両カテゴリ:</strong> {cat_disp}</li></ul><div style="margin-top:12px;font-size:0.86rem;">📄 <a href="{ROVER_SEVS_URL}" target="_blank" style="color:#2563EB;text-decoration:none;font-weight:600;">ROVER公式 SEVs登録リストで条件を確認する ↗</a></div></div>',
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f'<div class="result-card"><div class="{box_cls}"><span>{status_text}</span>{hachi_html}</div><div style="font-size:0.8rem;color:#64748B;margin-top:6px;">{sub_note}</div></div>',
                    unsafe_allow_html=True,
                )
                html_button = (
                    f'<div style="width:100%;margin-top:-8px;"><button id="btn_{idx}" onclick="copyAndOpen_{idx}()" style="background-color:#272757;color:#FFFFFF;border:none;padding:11px 16px;font-size:13.5px;font-weight:600;border-radius:9px;cursor:pointer;width:100%;">📋 {sev_no} をコピーしてMRE照会 ↗</button><div style="font-size:11.5px;color:#64748B;text-align:center;margin-top:5px;">※クリックでコピーし、ROVER MRE画面を開きます</div></div>'
                    f'<script>function copyAndOpen_{idx}(){{const b=document.getElementById("btn_{idx}");const o=b.innerText;b.innerText="✅ コピー完了！ROVERを開きます...";b.style.backgroundColor="#059669";setTimeout(()=>{{b.innerText=o;b.style.backgroundColor="#272757";}},2500);if(navigator.clipboard&&window.isSecureContext){{navigator.clipboard.writeText("{sev_no}").then(()=>window.open("{ROVER_MRE_URL}","_blank")).catch(()=>window.open("{ROVER_MRE_URL}","_blank"));}}else{{var t=document.createElement("textarea");t.value="{sev_no}";document.body.appendChild(t);t.select();try{{document.execCommand("copy");}}catch(e){{}}document.body.removeChild(t);window.open("{ROVER_MRE_URL}","_blank");}}}}</script>'
                )
                components.html(html_button, height=68)

        # 右下（静止）
        col_sheet, col_kuri = st.columns([5, 1])
        with col_sheet:
            with st.expander("📊 検索結果一覧（データシート）", expanded=False):
                st.dataframe(matched, use_container_width=True)
        with col_kuri:
            if sprites.get("kurimanju"):
                st.markdown(
                    f'<div class="kuri-card"><img src="{sprites["kurimanju"]}" class="kuri-img chara-static" /></div>',
                    unsafe_allow_html=True,
                )
