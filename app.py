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
st.caption("SEVs（特別輸入車両）リスト ＋ ROVER（モデルレポート）照合ツール")


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


# 2. 現行環境の標準通信（requests）でROVERデータを試行取得する関数
def fetch_rover_mre_standard(sev_no):
  rover_url = (
      "https://www.rover.infrastructure.gov.au/PublishedApprovals/MREApprovals/"
  )
  target_url = f"{rover_url}?RelatedApproval={sev_no}"

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      ),
      "Accept": (
          "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
      ),
  }

  try:
    res = requests.get(target_url, headers=headers, timeout=10)

    if res.status_code == 200:
      soup = bs4.BeautifulSoup(res.text, "html.parser")
      mre_rows = []

      for tr in soup.find_all("tr"):
        text = tr.text
        if "MRE-" in text:
          cols = [
              td.text.strip().replace("\n", " ").replace("\r", "")
              for td in tr.find_all(["td", "th"])
          ]
          if cols:
            mre_rows.append(cols)

      if mre_rows:
        return True, mre_rows

    # ROVERのJS動的描画により自動取得できない場合
    return (
        False,
        f"ROVERのセキュリティ制御により自動取得が制限されました。[🔗"
        f" こちらをクリックしてROVER公式検索を開く（{sev_no}検索済み）]({target_url})",
    )

  except Exception as e:
    return (
        False,
        f"通信制限: [🔗 こちらをクリックしてROVER公式検索を開く（{sev_no}検索済み）]({target_url})",
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

      # 該当した各SEVコードごとに個別カードを生成
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

        rover_link = f"https://www.rover.infrastructure.gov.au/PublishedApprovals/MREApprovals/?RelatedApproval={sev_no}"

        # 各SEVコードごとのカード表示
        with st.expander(
            f"🔹 **SEV Code: {sev_no}** | {make} {model} ({model_code})",
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
              st.success("✅ SEV適合 & 期間内")

            st.markdown(
                f"👉 [**ROVERで {sev_no} の MRE を開く**]({rover_link})"
            )

          # ROVERデータ照合結果または直接リンク案内
          has_mre, mre_res = fetch_rover_mre_standard(sev_no)
          if has_mre and isinstance(mre_res, list):
            st.markdown(f"**【自動取得データ】{sev_no} の Model Report**")
            st.dataframe(pd.DataFrame(mre_res), use_container_width=True)
          else:
            st.info(f"ℹ️ {mre_res}")

      st.markdown("---")
      st.subheader("📊 検索結果一覧（データシート）")
      st.dataframe(matched, use_container_width=True)
