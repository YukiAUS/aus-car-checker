from datetime import datetime
import re
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ページ全体の基本設定
st.set_page_config(
    page_title="オーストラリア中古車輸出 適合判定システム",
    layout="wide",
    page_icon="🚘",
)

# タイトルを小文字（控えめなサイズ）＋ 親しみやすい絵文字
st.markdown(
    "### 🚘 🚜 オーストラリア向け中古車輸出 適合判定システム 🐻🐱"
)
st.caption(
    "SEVs（特別輸入車両）早見表照合 ＋ ワンクリック即時コピー＆ROVER起動ツール"
)


# 1. SEVデータ（Excel）の読み込み
@st.cache_data
def load_sev_data(file):
  df = pd.read_excel(file, skiprows=1)
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
st.sidebar.header("📁 1. データファイルの選択")
uploaded_file = st.sidebar.file_uploader(
    "「AUS SEV早見表.xlsx」を選択", type=["xlsx", "xls"]
)

st.sidebar.header("🔍 2. 車両情報の入力")
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


# --- メイン判定処理 ---
if st.sidebar.button("🚙 適合判定を実行する 💨", type="primary"):
  if not uploaded_file:
    st.error("最初に左のサイドバーから「AUS SEV早見表.xlsx」をアップロードしてください。")
  elif not input_query:
    st.warning("型式または車種名を入力してください。")
  else:
    sev_df = load_sev_data(uploaded_file)
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
          f"❌ **輸出不可 (SEV未登録):** 入力された「{input_query}」に関連するSEV登録情報が見つかりませんでした。"
      )
    else:
      st.subheader(
          f"📋 該当するSEVエントリー ({len(matched)}件) & 各SEVコード別の判定結果"
      )

      rover_url = (
          "https://www.rover.infrastructure.gov.au/PublishedApprovals/MREApprovals/"
      )

      # 該当した各SEVコードごとに個別のカードを生成
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

        # 各SEVコードごとのカード表示
        with st.expander(
            f"🚜 **SEV Code: {sev_no}** | {make} {model} ({model_code}) 🐾",
            expanded=True,
        ):
          c1, c2 = st.columns([2, 1])

          with c1:
            st.markdown(f"**メーカー / 車種名:** {make} {model}")
            st.markdown(f"**対象型式:** `{model_code}`")
            st.markdown(
                f"**対象製造期間:** {f_str if pd.notna(f_str) else '指定なし'} 〜"
                f" {t_str if pd.notna(t_str) else '指定なし'}"
            )
            st.markdown(
                f"**SEV有効期限:**"
                f" {exp_str if pd.notna(exp_str) else '期限設定なし'}"
            )

          with c2:
            # 適合バッジの表示
            if not in_range:
              st.error("❌ 製造年月 対象外")
              st.caption(
                  f"入力された {build_year}年{build_month}月"
                  " は対象期間に含まれません。"
              )
            elif is_expired:
              st.warning("⚠️ SEV有効期限切れ")
              st.caption(f"SEVの有効期限 ({exp_str}) が過ぎています。")
            elif not raws_permission:
              st.warning("⚠️ RAWs利用権 未確認")
              st.caption("RAWs工場のModel Reportライセンス確認が必要です。")
            else:
              st.success("✅ SEV適合 & 期間内 🎊")

            # JavaScript連携ボタン（クリックでクリップボード書き込み ＋ ROVERを開く）
            html_button = f"""
            <button onclick="copyAndOpen()" style="
                background-color: #FF4B4B;
                color: white;
                border: none;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                cursor: pointer;
                width: 100%;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            ">
                🔗 コピーしてROVERを開く ↗️
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
            components.html(html_button, height=50)
            st.caption("※開いたら検索窓で Ctrl + V (貼り付け)")

      st.markdown("---")
      st.subheader("📊 検索結果一覧（データシート） 🐻🐱")
      st.dataframe(matched, use_container_width=True)
