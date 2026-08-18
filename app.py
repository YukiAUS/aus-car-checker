from datetime import datetime
import os
import re
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ページ全体の基本設定（スマホ表示時のレスポンシブ最適化）
st.set_page_config(
    page_title="オーストラリア中古車輸出 適合判定システム",
    layout="wide",
    page_icon="🦘",
    initial_sidebar_state="collapsed",  # スマホ開いた時にサイドバーを自動で閉じて見やすくする
)

# スマホ画面向けCSSの適用（文字サイズとボタン余白の微調整）
st.markdown(
    """
    <style>
    /* スマホ画面での余白調整 */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    /* 見出しサイズのスマホ最適化 */
    h3 {
        font-size: 1.25rem !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# タイトル（控えめサイズ ＋ キャラクター）
st.markdown(
    "### 🚘 🚜 オーストラリア輸出適合判定 🦘🐨 🐥🐶"
)
st.caption(
    "SEVs早見表照合 ＋ ワンクリック即時コピー＆ROVER起動ツール"
)

# 固定ファイルパスの設定
DATA_FILE_PATH = "AUS SEV早見表.xlsx"


# 1. SEVデータ（Excel）の自動読み込み＆キャッシュ
@st.cache_data
def load_sev_data_default():
  if not os.path.exists(DATA_FILE_PATH):
    return None
  df = pd.read_excel(DATA_FILE_PATH, skiprows=1)
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
  return df


# 日付変換ユーティリティ
def parse_my(date_str):
  if pd.isna(date_str) or str(date_str).strip() in ["No end date", ""]:
    return None
  try:
    return datetime.strptime(str(date_str).strip(), "%m/%Y")
  except:
    return None


def parse_dmy(date_str):
  if pd.isna(date_str) or str(date_str).strip() in [""]:
    return None
  try:
    return datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
  except:
    return None


# --- サイドバー設定パネル ---
st.sidebar.header("🔍 1. 車両情報の入力 🐨")
input_query = (
    st.sidebar.text_input("型式 または 車種名", value="CKV36")
    .strip()
    .upper()
)

col_y, col_m = st.sidebar.columns(2)
build_year = col_y.number_input(
    "製造年 (年)", min_value=1980, max_value=2026, value=2008
)
build_month = col_m.number_input(
    "製造月 (月)", min_value=1, max_value=12, value=1
)

raws_permission = st.sidebar.checkbox(
    "提携RAWs工場が Model Report の利用ライセンスを保有している", value=True
)

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader(
    "（任意）別のSEV早見表を使用する場合 🐥", type=["xlsx", "xls"]
)


# --- メイン判定処理 ---
if st.sidebar.button("🚙 適合判定を実行する 💨 🦘", type="primary"):
  if uploaded_file:
    sev_df = pd.read_excel(uploaded_file, skiprows=1)
    sev_df.columns = [
        "SEV番号",
        "メーカー",
        "車種名",
        "カテゴリ",
        "型式",
        "製造開始年月",
        "製造終了年月",
        "有効期限",
    ]
  else:
    sev_df = load_sev_data_default()

  if sev_df is None:
    st.error(
        f"❌ リポジトリ内に `{DATA_FILE_PATH}`"
        " が見つかりません。GitHubにファイルをアップロードするか、サイドバーから選択してください。"
    )
  elif not input_query:
    st.warning("型式または車種名を入力してください。")
  else:
    target_date = datetime(build_year, build_month, 1)
    today = datetime.now()

    query_clean = re.sub(r"\s+", "", input_query)

    def is_match(row):
      code = re.sub(r"\s+", "", str(row["型式"]).upper())
      model = re.sub(r"\s+", "", str(row["車種名"]).upper())
      return (
          (query_clean in code or code in query_clean) if code else False
      ) or ((query_clean in model or model in query_clean) if model else False)

    matched = sev_df[sev_df.apply(is_match, axis=1)]

    if matched.empty:
      st.error(
          f"❌ **輸出不可 (SEV未登録):** 入力された「{input_query}」に関連するSEV登録情報が見つかりませんでした。 😿"
      )
    else:
      st.subheader(
          f"📋 該当SEV ({len(matched)}件) 🦘✨"
      )

      rover_url = (
          "https://www.rover.infrastructure.gov.au/PublishedApprovals/MREApprovals/"
      )

      for idx, row in matched.iterrows():
        sev_no = row["SEV番号"]
        make = row["メーカー"]
        model = row["車種名"]
        model_code = row["型式"]
        f_str = row["製造開始年月"]
        t_str = row["製造終了年月"]
        exp_str = row["有効期限"]

        d_from = parse_my(f_str)
        d_to = parse_my(t_str)
        expiry = parse_dmy(exp_str)

        # 1. 製造年月チェック
        in_range = True
        if d_from and target_date < d_from:
          in_range = False
        if d_to and target_date > d_to:
          in_range = False

        # 2. 有効期限チェック
        is_expired = expiry and expiry < today

        with st.expander(
            f"🚜 **{sev_no}** | {make} {model} 🐨",
            expanded=True,
        ):
          # スマホでも見やすいようにカラム比率を自動調整
          c1, c2 = st.columns([1, 1])

          with c1:
            st.markdown(f"**メーカー/車種:** {make} {model}")
            st.markdown(f"**対象型式:** `{model_code}`")
            st.markdown(
                f"**製造期間:** {f_str if pd.notna(f_str) else '指定なし'} 〜"
                f" {t_str if pd.notna(f_str) else '指定なし'}"
            )
            st.markdown(
                f"**SEV期限:**"
                f" {exp_str if pd.notna(exp_str) else '設定なし'}"
            )

          with c2:
            if not in_range:
              st.error("❌ 製造年月 対象外 😿")
            elif is_expired:
              st.warning("⚠️ SEV有効期限切れ 🙀")
            elif not raws_permission:
              st.warning("⚠️ RAWs利用権 未確認 🐱")
            else:
              st.success("✅ SEV適合 & 期間内 🎊 🦘")

            # スマホ対応：タップしやすい大きなアクションボタン
            html_button = f"""
            <button onclick="copyAndOpen()" style="
                background-color: #FF4B4B;
                color: white;
                border: none;
                padding: 12px 14px;
                font-size: 15px;
                font-weight: bold;
                border-radius: 10px;
                cursor: pointer;
                width: 100%;
                margin-top: 5px;
                box-shadow: 0 3px 6px rgba(0,0,0,0.2);
                -webkit-tap-highlight-color: transparent;
            ">
                📲 コピーしてROVERを開く 🐨
            </button>
            <script>
            function copyAndOpen() {{
                navigator.clipboard.writeText("{sev_no}").then(function() {{
                    window.open("{rover_url}", "_blank");
                }}).catch(function(err) {{
                    window.open("{rover_url}", "_blank");
                }});
            }}
            </script>
            """
            components.html(html_button, height=60)
            st.caption("※開いたら検索窓を長押し ➔ 貼り付け")

      st.markdown("---")
      st.subheader("📊 検索結果一覧（データシート） 🐨🦘")
      st.dataframe(matched, use_container_width=True)
