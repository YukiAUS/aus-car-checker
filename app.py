from datetime import datetime
import html
import os
import re
import bs4
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

# ページ全体の基本設定（PC・スマホ両対応）
st.set_page_config(
    page_title="オーストラリア中古車輸出 適合判定システム",
    layout="wide",
    page_icon="🦘",
)

# レスポンシブCSS
st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
    }
    @media (min-width: 769px) {
        .main .block-container {
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
        }
    }
    button {
        -webkit-tap-highlight-color: transparent;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown("### 🚘 🚜 オーストラリア向け中古車輸出 適合判定システム 🦘🐨 🐥🐶")
st.caption("ROVER公式【SEVs登録全車種】×【Model Report承認リスト】リアルタイム自動統合判定ツール")

# 公式URLおよびバックアップファイル設定
ROVER_SEVS_URL = "https://www.rover.infrastructure.gov.au/PublishedApprovals/SEVApprovals/"
ROVER_SEV_DETAIL_BASE = "https://www.rover.infrastructure.gov.au/PublishedApprovals/SEVDetails/?id="
ROVER_MRE_URL = "https://www.rover.infrastructure.gov.au/PublishedApprovals/MREApprovals/"
BACKUP_EXCEL_PATH = "AUS SEV早見表.xlsx"


# 共通：Power Apps Portal の HTMLからセキュリティキーを抽出し、APIで最新データを取得する関数
def fetch_all_rover_records(page_url, search_text="", page_size=100, fetch_all_pages=True):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-AU,en;q=0.9,ja;q=0.8",
    }
    try:
        resp = session.get(page_url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return False, f"ROVER接続エラー (HTTP {resp.status_code})"

        # HTMLエンティティ(&quot;など)をデコードして内部設定JSONを抽出可能にする
        raw_html = resp.text
        decoded_html = html.unescape(raw_html)
        soup = bs4.BeautifulSoup(raw_html, "html.parser")

        # 1. CSRFトークンの抽出
        token_input = soup.find("input", {"name": "__RequestVerificationToken"})
        token = token_input["value"] if token_input else ""

        # 2. APIエンドポイントの抽出
        api_match = re.search(r'/_services/entity-grid-data\.json/[0-9a-fA-F\-]{36}', decoded_html)
        if not api_match:
            return False, "ROVERのAPIエンドポイントが見つかりませんでした"
        api_url = "https://www.rover.infrastructure.gov.au" + api_match.group(0)

        # 3. 必須の Base64SecureConfiguration と ViewId を抽出
        secure_cfg_match = re.search(r'"Base64SecureConfiguration"\s*:\s*"([^"]+)"', decoded_html)
        secure_cfg = secure_cfg_match.group(1) if secure_cfg_match else ""

        view_id_match = re.search(r'"Id"\s*:\s*"([0-9a-fA-F\-]{36})"', decoded_html)
        view_id = view_id_match.group(1) if view_id_match else ""

        api_headers = {
            "User-Agent": headers["User-Agent"],
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.rover.infrastructure.gov.au",
            "Referer": page_url,
        }
        if token:
            api_headers["__RequestVerificationToken"] = token

        all_records = []
        current_page = 1
        max_pages = 25

        while current_page <= max_pages:
            payload = {
                "base64SecureConfiguration": secure_cfg,
                "search": search_text,
                "page": current_page,
                "pageSize": page_size,
                "filter": "",
                "metaFilter": "",
                "timezoneOffset": -540,
                "customParameters": [],
            }
            if view_id:
                payload["viewId"] = view_id

            api_resp = session.post(api_url, headers=api_headers, json=payload, timeout=20)
            if api_resp.status_code != 200:
                if all_records:
                    break
                return False, f"ROVER API応答エラー (HTTP {api_resp.status_code})"

            # JSONとして解析できるか検証
            try:
                data = api_resp.json()
            except Exception:
                return False, "ROVERからJSON以外の応答が返されました（アクセス制限の可能性）"

            records = data.get("Records", [])
            total_count = data.get("TotalRecordCount", 0)

            if not records:
                break

            all_records.extend(records)

            if not fetch_all_pages or len(all_records) >= total_count:
                break

            current_page += 1

        return True, all_records
    except Exception as e:
        return False, f"通信エラー: {str(e)}"


# 1. SEVs全車種データの自動取得（常にROVER公式 SEVApprovals から最新を取得）
@st.cache_data(ttl=1800, show_spinner=False)
def load_sevs_master():
    ok, result = fetch_all_rover_records(ROVER_SEVS_URL, search_text="", page_size=100, fetch_all_pages=True)
    if ok and isinstance(result, list) and len(result) > 0:
        rows = []
        for rec in result:
            rec_id = rec.get("Id", "")
            attrs = {}
            for a in rec.get("Attributes", []):
                val = a.get("DisplayValue") if a.get("DisplayValue") not in [None, ""] else a.get("Value", "")
                attrs[a["Name"]] = val

            rows.append({
                "SEV番号": attrs.get("gov_sevnumber", attrs.get("gov_approvalnumber", "")),
                "メーカー": attrs.get("gov_make", ""),
                "車種名": attrs.get("gov_model", ""),
                "カテゴリ": attrs.get("gov_vehiclecategory", attrs.get("gov_category", "")),
                "型式": attrs.get("gov_modelcode", ""),
                "製造開始年月": attrs.get("gov_builddatefrom", ""),
                "製造終了年月": attrs.get("gov_builddateto", ""),
                "有効期限": attrs.get("gov_expirydate", ""),
                "見直し中": attrs.get("gov_underreview", ""),
                "詳細ID": rec_id,
            })
        df = pd.DataFrame(rows)
        if not df.empty and df["SEV番号"].astype(str).str.contains("SEV-").any():
            return df, f"🌐 ROVER公式SEVApprovals（最新・全{len(df)}車種を直接取得）", datetime.now().strftime("%Y/%m/%d %H:%M"), ""

    # 取得できなかった場合のエラー詳細を保持しつつ、緊急バックアップExcelを読み込む
    err_reason = result if not ok else "レコードが0件でした"
    if os.path.exists(BACKUP_EXCEL_PATH):
        try:
            df = pd.read_excel(BACKUP_EXCEL_PATH, skiprows=1).iloc[:, :8]
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
            df["見直し中"] = ""
            df["詳細ID"] = ""
            return df.dropna(subset=["SEV番号"]), f"📁 バックアップExcel（全{len(df)}件）", "ローカル保存版", err_reason
        except Exception:
            pass

    return None, "データ取得エラー", "", err_reason


# 2. Model Report (MRE) の自動照会
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_mre_for_sev(sev_no):
    ok, result = fetch_all_rover_records(ROVER_MRE_URL, search_text=sev_no, page_size=50, fetch_all_pages=False)
    if ok and isinstance(result, list):
        parsed_list = []
        for rec in result:
            attrs = {}
            for a in rec.get("Attributes", []):
                val = a.get("DisplayValue") if a.get("DisplayValue") not in [None, ""] else a.get("Value", "")
                attrs[a["Name"]] = val

            parsed_list.append({
                "MRE番号": attrs.get("gov_approvalnumber", ""),
                "メーカー": attrs.get("gov_make", ""),
                "車種名": attrs.get("gov_model", ""),
                "ステータス": attrs.get("statuscode", ""),
                "製造期間": attrs.get("gov_builddaterange", ""),
                "適合レベル": attrs.get("gov_compliancelevel", ""),
            })
        return True, parsed_list
    return False, result


# 日付変換ユーティリティ
def parse_my(date_str):
    if pd.isna(date_str) or str(date_str).strip() in ["No end date", "", "nan", "None"]:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), "%m/%Y")
    except:
        return None


def parse_dmy(date_str):
    if pd.isna(date_str) or str(date_str).strip() in ["", "nan", "None"]:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
    except:
        return None


# --- サイドバー設定パネル ---
st.sidebar.header("🔍 1. 車両情報の入力 🐨")
input_query = (
    st.sidebar.text_input("メーカー・車種名・型式・SEV番号", value="ZVW40")
    .strip()
    .upper()
)

col_y, col_m = st.sidebar.columns(2)
build_year = col_y.number_input(
    "製造年 (年)", min_value=1980, max_value=2026, value=2015
)
build_month = col_m.number_input(
    "製造月 (月)", min_value=1, max_value=12, value=6
)

raws_permission = st.sidebar.checkbox(
    "提携RAWs工場が Model Report の利用ライセンスを保有している", value=True
)

auto_check_rover = st.sidebar.checkbox(
    "🌐 ROVER公式APIへリアルタイム自動照会を行う", value=True
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 最新データに強制同期する ✨"):
    st.cache_data.clear()
    st.rerun()

uploaded_file = st.sidebar.file_uploader(
    "（任意）手元のExcelで手動判定する場合 🐥", type=["xlsx", "xls"]
)


# --- メイン判定処理 ---
if st.sidebar.button("🚙 適合判定を実行する 💨 🦘", type="primary"):
    err_detail = ""
    if uploaded_file:
        try:
            sev_df = pd.read_excel(uploaded_file, skiprows=1).iloc[:, :8]
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
            sev_df["見直し中"] = ""
            sev_df["詳細ID"] = ""
            source_label = "📤 手動アップロードExcel"
            sync_time = "一時読み込み"
        except Exception as e:
            st.error(f"ファイルの読み込みに失敗しました: {e}")
            sev_df = None
    else:
        with st.spinner("📡 ROVER公式サイトから最新の全登録車種データを取得中..."):
            sev_df, source_label, sync_time, err_detail = load_sevs_master()

    if sev_df is None:
        st.error(f"❌ SEVsデータの取得に失敗しました。（詳細: {err_detail}）")
    elif not input_query:
        st.warning("メーカー・車種名・型式・SEV番号のいずれかを入力してください。")
    else:
        st.caption(f"📡 情報源: **{source_label}** （取得時刻: {sync_time}）")
        if err_detail:
            st.warning(f"⚠️ ROVER公式からの直接取得が一時的に制限されたためバックアップを使用中です（理由: {err_detail}）")

        target_date = datetime(build_year, build_month, 1)
        today = datetime.now()
        query_clean = re.sub(r"\s+", "", input_query)

        # メーカー名・車種名・型式・SEV番号のすべてを横断検索
        def is_match(row):
            sev_id = re.sub(r"\s+", "", str(row["SEV番号"]).upper())
            make_str = re.sub(r"\s+", "", str(row["メーカー"]).upper())
            model_str = re.sub(r"\s+", "", str(row["車種名"]).upper())
            code_str = re.sub(r"\s+", "", str(row["型式"]).upper())
            combined = f"{make_str}{model_str}{code_str}{sev_id}"
            return (
                (query_clean in combined)
                or (code_str != "" and code_str != "NAN" and code_str in query_clean)
            )

        matched = sev_df[sev_df.apply(is_match, axis=1)]

        if matched.empty:
            st.error(
                f"❌ **輸出不可 (SEV未登録):** 「{input_query}」に一致するSEV登録情報が見つかりませんでした。 😿"
            )
        else:
            st.subheader(
                f"📋 該当するSEVエントリー ({len(matched)}件) & 総合判定結果 🦘✨"
            )

            for idx, row in matched.iterrows():
                sev_no = str(row["SEV番号"]).strip()
                make = row["メーカー"]
                model = row["車種名"]
                model_code = row["型式"]
                f_str = row["製造開始年月"]
                t_str = row["製造終了年月"]
                exp_str = row["有効期限"]
                under_review = str(row.get("見直し中", "")).strip()
                detail_id = str(row.get("詳細ID", "")).strip()

                d_from = parse_my(f_str)
                d_to = parse_my(t_str)
                expiry = parse_dmy(exp_str)

                in_range = True
                if d_from and target_date < d_from:
                    in_range = False
                if d_to and target_date > d_to:
                    in_range = False

                is_expired = expiry and expiry < today

                # Model Report (MRE) の自動照会
                mre_ok, mre_result = (False, "未照会")
                if auto_check_rover:
                    mre_ok, mre_result = fetch_mre_for_sev(sev_no)

                has_active_mre = False
                if mre_ok and isinstance(mre_result, list) and len(mre_result) >
