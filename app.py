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

# --- 3体キャラクター画像の自動分割・背景透過処理 ---
@st.cache_data(show_spinner=False)
def prepare_character_sprites():
    # リポジトリ内のキャラクター画像を探す（characters.jpg / .png など）
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

        # 水色の空と真っ白な背景を透明化
        datas = img.getdata()
        new_data = []
        for r, g, b, a in datas:
            # 明るい水色（空）またはほぼ純白の背景部分を透過
            is_sky = (b > 210 and g > 190 and r < 185 and (b - r) > 35)
            is_white_bg = (r > 246 and g > 246 and b > 246)
            if is_sky or is_white_bg:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append((r, g, b, a))
        img.putdata(new_data)

        # 左(ハチワレ)・中央(ちいかわ)・右(うさぎ)の3領域に分割して余白を自動トリミング
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
            sprites.append(f"data:image/png;base64,{b64}")

        return {
            "hachiware": sprites[0],
            "chiikawa": sprites[1],
            "usagi": sprites[2],
        }
    except Exception:
        return None


sprites = prepare_character_sprites()

# --- スタイリッシュUI & 足踏みアニメーションCSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans JP', sans-serif;
    }
    .stApp {
        background-color: #F4F6F9;
    }
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 2rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
    }
    @media (min-width: 769px) {
        .main .block-container {
            padding-top: 1.8rem !important;
            padding-bottom: 3rem !important;
            max-width: 1180px;
        }
    }

    /* 足元を支点にしたトコトコ足踏み＆ピョコピョコ動き */
    @keyframes footStepIdle {
        0%, 100% { transform: translateY(0px) rotate(0deg) scaleY(1); }
        25%      { transform: translateY(-2px) rotate(-2.5deg) scaleY(0.98); }
        50%      { transform: translateY(0px) rotate(0deg) scaleY(1); }
        75%      { transform:
