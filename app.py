from datetime import datetime
import html
import os
import re
import bs4
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="オーストラリア中古車輸出 適合判定システム",
    layout="wide",
    page_icon="🦘",
)

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
    button { -webkit-tap-highlight-color: transparent; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("### 🚘 🚜 オーストラリア向け中古車輸出 適合判定システム 🦘🐨 🐥🐶")
st.caption("ROVER公式【SEVs登録全車種】×【Model Report承認リスト】リアルタイム自動統合判定ツール")

ROVER_SEVS_URL = "https://www.rover.infrastructure.gov.au/PublishedApprovals/SEVApprovals/"
ROVER_SEV_DETAIL_BASE = "https://www.rover.infrastructure.gov.au/PublishedApprovals/SEVDetails/?id="
ROVER_MRE_URL = "https://www.rover.infrastructure.gov.au/PublishedApprovals/MREApprovals/"
BACKUP_EXCEL_PATH = "AUS SEV早見表.xlsx"


def fetch_all_rover_records(page_url, search_text="", page_size=100, fetch_all_pages=True):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-AU,en;q=0.9,ja;q=0.8",
    }
    try:
        resp = session.get(page_url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return False, f"ROVER接続エラー (HTTP {resp.status_code})"

        decoded_html = html.unescape(resp.text)
        soup = bs4.BeautifulSoup(resp.text, "html.parser")

        token_input = soup.find("input", {"name": "__RequestVerificationToken"})
        token = token_input["value"] if token_input else ""

        api_match = re.search(r'/_services/entity-grid-data\.json/[0-9a-fA-F\-]{36}', decoded_html)
        if not api_match:
            return False, "APIエンドポイント未検出"
        api_url = "https://www.rover.infrastructure.gov.au" + api_match.group(0)

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
        while current_page <= 25:
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
                return False, f"API応答エラー (HTTP {api_resp.status_code})"

            try:
                data = api_resp.json()
            except Exception:
                return False, "JSON解析不可（アクセス制限の可能性）"

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


@st.cache_data(ttl=1800, show_spinner=False)
def load_sevs_master():
    ok, result = fetch_all_rover_records(ROVER_SEVS_URL, search_text="", page_size=100, fetch_all_pages=True)
    if ok and isinstance(result, list) and len(result) > 0:
        rows = []
        for rec in result:
            rec_id = rec.get("Id", "")
            attrs = {
                a["Name"]: (a.get("DisplayValue") if a.get("DisplayValue") not in [None, ""] else a.get("Value", ""))
                for a in rec.get("Attributes", [])
            }
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

    err_reason = result if not ok else "レコード0件"
    if os.path.exists(BACKUP_EXCEL_PATH):
        try:
            df = pd.read_excel(BACKUP_EXCEL_PATH, skiprows=1).iloc[:, :8]
            df.columns = ["SEV番号", "メーカー", "車種名", "カテゴリ", "型式", "製造開始年月", "製造終了年月", "有効期限"]
            df["見直し中"] = ""
            df["詳細ID"] = ""
            return df.dropna(subset=["SEV番号"]), f"📁 バックアップExcel（全{len(df)}件）", "ローカル保存版", err_reason
        except Exception:
            pass

    return None, "データ取得エラー", "", err_reason


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_mre_for_sev(sev_no):
    ok, result = fetch_all_rover_records(ROVER_MRE_URL, search_text=sev_no, page_size=50, fetch_all_pages=False)
    if ok and isinstance(result, list):
        parsed_list = []
        for rec in result:
            attrs = {
                a["Name"]: (a.get("DisplayValue") if a.get("DisplayValue") not in [None, ""] else a.get("Value", ""))
                for a in rec.get("Attributes", [])
            }
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


def parse_my(date_str):
    if pd.isna(date_str) or str(date_str).strip() in ["No end date", "", "nan", "None"]:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), "%m/%Y")
    except Exception:
        return None


def parse_dmy
