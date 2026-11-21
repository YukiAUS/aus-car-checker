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
    """画像の四隅から繋がっている外側背景（空色・白）のみを透明化する"""
    img = pil_img.convert("RGBA")
    w, h = img.size
    pixels = img.load()
    visited = set()
    queue = deque()

    def is_bg_color(r, g, b):
        is_sky = (b > 205 and g > 185 and r < 190 and (b - r) > 30)
        is_white = (r > 242 and g > 242 and b > 242)
        return is_sky or is_white

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

kuri_bg_rule = f"background-image: url('{sprites['kurimanju']}');" if sprites.get("kurimanju") else ""

CUSTOM_CSS = f"""
<style>
.stApp {{ background-color: #F4F6F9; }}
section[data-testid='stSidebar'] {{ background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }}
.main .block-container {{ padding-top: 1.6rem !important; max-width: 1180px; }}
@keyframes footStepIdle {{
  0%, 100% {{ transform: translateY(0px) rotate(0deg) scaleY(1); }}
  25%      {{ transform: translateY(-2px) rotate(-2.5deg) scaleY(0.98); }}
  50%      {{ transform: translateY(0px) rotate(0deg) scaleY(1); }}
  75%      {{ transform: translateY(-2px) rotate(2.5deg) scaleY(0.98); }}
}}
@keyframes footStepActive {{
  0%, 100% {{ transform: translateY(0px) rotate(0deg) scaleY(1); }}
  20%      {{ transform: translateY(-5px) rotate(-4.5deg) scaleY(0.96); }}
  40%      {{ transform: translateY(0px) rotate(0deg) scaleY(1.02); }}
  60%      {{ transform: translateY(-5px) rotate(4.5deg) scaleY(0.96); }}
  80%      {{ transform: translateY(0px) rotate(0deg) scaleY(1.02); }}
}}
.chara-step-idle {{ transform-origin: bottom center; animation: footStepIdle 2.2s ease-in-out infinite; display: inline-block; }}
.chara-step-active {{ transform-origin: bottom center; animation: footStepActive 0.65s ease-in-out 5, footStepIdle 2.2s ease-in-out 3.3s infinite; display: inline-block; }}
.chara-static {{ display: inline-block; }}
.header-box {{ display: flex; align-items: center; justify-content: space-between; background: linear-gradient(135deg, #2B4168 0%, #3B5984 100%); padding: 16px 26px; border-radius: 14px; box-shadow: 0 4px 12px rgba(15,23,42,0.08); margin-bottom: 18px; }}
.app-title {{ font-size: 1.45rem; font-weight: 700; color: #FFFFFF; margin: 0 0 8px 0; }}
.master-badge {{ display: inline-flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.95); color: #1E293B; font-size: 0.8rem; font-weight: 600; padding: 4px 12px; border-radius: 999px; }}
.dot-green {{ width: 8px; height: 8px; background-color: #10B981; border-radius: 50%; display: inline-block; }}
.result-card {{ background: #FFFFFF; border-radius: 14px; padding: 20px 24px; margin-bottom: 16px; border: 1px solid #E2E8F0; box-shadow: 0 4px 12px rgba(15,23,42,0.05); }}
.card-ok {{ border-left: 6px solid #10B981; }}
.card-warn {{ border-left: 6px solid #F59E0B; }}
.card-ng {{ border-left: 6px solid #EF4444; }}
.sev-header {{ font-size: 1.1rem; font-weight: 700; color: #0F172A; margin-bottom: 8px; }}
.code-pill {{ display: inline-block; background: #EFF6FF; color: #1D4ED8; font-weight: 600; font-size: 0.82rem; padding: 3px 10px; border-radius: 6px; border: 1px solid #BFDBFE; margin-bottom: 12px; }}
.info-list {{ color: #334155; font-size: 0.92rem; line-height: 1.75; margin: 0; padding-left: 18px; }}
.status-box-ok {{ background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; border-radius: 10px; padding: 10px 14px; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; justify-content: space-between; }}
.status-box-warn {{ background: #FFFBEB; color: #92400E; border: 1px solid #FDE68A; border-radius: 10px; padding: 10px 14px; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; justify-content: space-between; }}
.status-box-ng {{ background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; border-radius: 10px; padding: 10px 14px; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; justify-content: space-between; }}
.kuri-box {{ display: flex; flex-direction: column; align-items: center; justify-content: center; background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 14px; padding: 10px 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); }}
.predict-panel {{ background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 5px solid #3B82F6; border-radius: 12px; padding: 16px 20px; margin-top: 14px; box-shadow: 0 3px 10px rgba(15,23,42,0.04); }}
div.stButton > button[kind='primary'] {{ background-color: #2B4168; color: #FFFFFF; border: none; border-radius: 8px; font-weight: 600; width: 100%; }}
@media (max-width: 768px) {{
  [data-testid="stSidebarCollapsedControl"] button,
  [data-testid="collapsedControl"] button,
  [data-testid="stExpandSidebarButton"] {{
    width: auto !important;
    height: 40px !important;
    padding: 4px 12px 4px 6px !important;
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
  }}
  [data-testid="stSidebarCollapsedControl"] button *,
  [data-testid="collapsedControl"] button *,
  [data-testid="stExpandSidebarButton"] * {{
    display: none !important;
  }}
  [data-testid="stSidebarCollapsedControl"] button::before,
  [data-testid="collapsedControl"] button::before,
  [data-testid="stExpandSidebarButton"]::before {{
    content: "" !important;
    display: inline-block !important;
    width: 30px !important;
    height: 30px !important;
    {kuri_bg_rule}
    background-size: contain !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
  }}
  [data-testid="stSidebarCollapsedControl"] button::after,
  [data-testid="collapsedControl"] button::after,
  [data-testid="stExpandSidebarButton"]::after {{
    content: "🔍 車種を検索" !important;
    color: #31333F !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
  }}
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

ROVER_SEVS_URL = "https://www.rover.infrastructure.gov.au/PublishedApprovals/SEVApprovals/"
ROVER_MRE_URL = "https://www.rover.infrastructure.gov.au/PublishedApprovals/MREApprovals/"
LEGACY_EXCEL_PATH = "AUS SEV早見表.xlsx"

if "show_predictions" not in st.session_state:
    st.session_state.show_predictions = False
if "override_query" not in st.session_state:
    st.session_state.override_query = None


def read_sev_file(file_obj_or_path):
    name = file_obj_or_path if isinstance(file_obj_or_path, str) else file_obj_or_path.name
    if str(name).lower().endswith(".csv"):
        df = pd.read_csv(file_obj_or_path, skiprows=1).iloc[:, :8]
    else:
        df = pd.read_excel(file_obj_or_path, skiprows=1).iloc[:, :8]
    df.columns = ["SEV番号", "メーカー", "車種名", "カテゴリ", "型式
