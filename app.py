from datetime import datetime
import re
import bs4
import pandas as pd
import requests
import streamlit as st

# ページ全体の基本設定
st.set_page_config(
    page_title="オーストラリア中古車輸出 適合判定システム",
    layout="wide",
    page_icon="🚗",
)

st.title("🚗 オーストラリア向け中古車輸出 適合判定システム")
st.caption("SEVs（特別輸入車両）リスト ＋ ROVER（モデルレポート）自動照合ツール")


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


# 2. ROVERサイトからModel Report情報を自動取得する関数（API/多角検索対応版）
def fetch_rover_mre_info(sev_no):
  """ROVERサイトおよびエンドポイントへアクセスし、対象SEV番号に関連するModel Report（MRE）を自動検索します"""
  rover_url = (
      "https://www.rover.infrastructure.gov.au/PublishedApprovals/MREApprovals/"
  )

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Referer": "https://www.rover.infrastructure.gov.au/",
  }

  session = requests.Session()

  try:
    # 1. 直接HTMLテーブルからのスクレイピング試行
    params = {"RelatedApproval": sev_no}
    res = session.get(rover_url, params=params, headers=headers, timeout=10)

    mre_rows = []
    if res.status_code == 200:
      soup = bs4.BeautifulSoup(res.text, "html.parser")
      tables = soup.find_all("table")

      for table in tables:
        for tr in table.find_all("tr"):
          cols = [
              td.text.strip().replace("\n", " ").replace("\r", "")
              for td in tr.find_all(["td", "th"])
          ]
          if cols and any("MRE-" in c for c in cols):
            mre_rows.append(cols)

    if mre_rows:
      return True, mre_rows

    # 2. クラウド遮断・動的描画用のバックアップリンク生成
    direct_link = (
        f"https://www.rover.infrastructure.gov.au/PublishedApprovals/MREApprovals/?RelatedApproval={sev_no}"
    )
    return (
        False,
        f"ROVERのセキュリティ制御により自動取得が制限されました。[🔗"
        f" こちらをクリックしてROVER公式検索を開く（{sev_no}検索済み）]({direct_link})",
    )

  except Exception as e:
    direct_link = (
        f"https://www.rover.infrastructure.gov.au/PublishedApprovals/MREApprovals/?RelatedApproval={sev_no}"
    )
    return (
        False,
        f"自動接続エラー: [🔗"
        f" こちらからROVER公式結果を開く]({direct_link})（エラー詳細: {str(e)}）",
    )


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


# 日付変換ユーティリティ
def parse_my(date_str):
  if pd.isna(date_str) or str(date_str).strip() == "No end date":
    return None
  try:
    return datetime.strptime(str(date_str).strip(), "%m/%Y")
  except:
    return None


def parse_dmy(date_str):
  if pd.isna(date_str):
    return None
  try:
    return datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
  except:
    return None


# --- メイン判定処理 ---
if st.sidebar.button("🚗 適合判定を実行する", type="primary"):
  if not uploaded_file:
    st.error("最初に左のサイドバーから「AUS SEV早見表.xlsx」をアップロードしてください。")
  elif not input_query:
    st.warning("型式または車種名を入力してください。")
  else:
    sev_df = load_sev_data(uploaded_file)
    target_date = datetime(build_year, build_month, 1)
    today = datetime.now()

    # あいまい部分一致検索（スペースを除外して比較）
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
      valid_sevs = []
      for idx, row in matched.iterrows():
        d_from = parse_my(row["製造開始年月"])
        d_to = parse_my(row["製造終了年月"])
        expiry = parse_dmy(row["有効期限"])

        in_range = True
        if d_from and target_date < d_from:
          in_range = False
        if d_to and target_date > d_to:
          in_range = False

        is_expired = expiry and expiry < today

        if in_range:
          valid_sevs.append((row, is_expired))

      if not valid_sevs:
        st.error(
            f"❌ **輸出不可 (製造年月が対象外):** SEV登録 ({matched.iloc[0]['SEV番号']}) は存在しますが、指定の製造年月 ({build_year}年{build_month}月) は対象期間外です。"
        )
      else:
        first_sev, is_expired = valid_sevs[0]
        sev_no = first_sev["SEV番号"]

        # --- ROVERサイトからの自動情報取得 ---
        st.subheader("🌐 3. ROVER Model Report リアルタイム照合結果")
        with st.spinner(f"ROVERサイトから {sev_no} の最新データを自動取得しています..."):
          has_mre, mre_data = fetch_rover_mre_info(sev_no)

        if is_expired:
          exp_date = first_sev["有効期限"]
          st.warning(
              f"⚠️ **要確認 (SEV有効期限切れ):** SEV番号 `{sev_no}` の有効期限"
              f" ({exp_date}) が切れています。"
          )
        elif not has_mre:
          st.info(f"ℹ️ **SEV適合確認済み (`{sev_no}`)** \n\n {mre_data}")
        elif not raws_permission:
          st.warning(
              f"⚠️ **判定保留 (RAWs利用権未確認):** SEV適合 (`{sev_no}`) および ROVER上に Model Report が確認されましたが、RAWs工場のライセンス所有状況を確認してください。"
          )
        else:
          st.success(
              f"✅ **輸出可能:** SEV適合 (`{sev_no}`)、製造年月適性、ROVER上の"
              " Model Report 承認確認完了！"
          )

        # 取得した Model Report テーブルの日本語表示
        if has_mre and isinstance(mre_data, list):
          st.markdown("**【ROVERから取得完了】関連する Model Report 一覧**")
          mre_df = pd.DataFrame(mre_data)
          st.dataframe(mre_df, use_container_width=True)

        st.subheader("📋 一致したSEV登録データ")
        st.dataframe(matched, use_container_width=True)
