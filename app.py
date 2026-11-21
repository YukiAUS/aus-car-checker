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


st.sidebar.header("🔍 1. 車両情報の入力 🐨")
input_query = st.sidebar.text_input("メーカー・車種名・型式・SEV番号", value="ZVW40").strip().upper()

col_y, col_m = st.sidebar.columns(2)
build_year = col_y.number_input("製造年 (年)", min_value=1980, max_value=2026, value=2015)
build_month = col_m.number_input("製造月 (月)", min_value=1, max_value=12, value=6)

raws_permission = st.sidebar.checkbox("提携RAWs工場が Model Report の利用ライセンスを保有している", value=True)
auto_check_rover = st.sidebar.checkbox("🌐 ROVER公式APIへリアルタイム自動照会を行う", value=True)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 最新データに強制同期する ✨"):
    st.cache_data.clear()
    st.rerun()

uploaded_file = st.sidebar.file_uploader("（任意）手元のExcelで手動判定する場合 🐥", type=["xlsx", "xls"])

if st.sidebar.button("🚙 適合判定を実行する 💨 🦘", type="primary"):
    err_detail = ""
    if uploaded_file:
        try:
            sev_df = pd.read_excel(uploaded_file, skiprows=1).iloc[:, :8]
            sev_df.columns = ["SEV番号", "メーカー", "車種名", "カテゴリ", "型式", "製造開始年月", "製造終了年月", "有効期限"]
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

        def is_match(row):
            sev_id = re.sub(r"\s+", "", str(row["SEV番号"]).upper())
            make_str = re.sub(r"\s+", "", str(row["メーカー"]).upper())
            model_str = re.sub(r"\s+", "", str(row["車種名"]).upper())
            code_str = re.sub(r"\s+", "", str(row["型式"]).upper())
            combined = f"{make_str}{model_str}{code_str}{sev_id}"
            return (query_clean in combined) or (code_str not in ["", "NAN"] and code_str in query_clean)

        matched = sev_df[sev_df.apply(is_match, axis=1)]

        if matched.empty:
            st.error(f"❌ **輸出不可 (SEV未登録):** 「{input_query}」に一致するSEV登録情報が見つかりませんでした。 😿")
        else:
            st.subheader(f"📋 該当するSEVエントリー ({len(matched)}件) & 総合判定結果 🦘✨")

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

                mre_ok, mre_result = (False, "未照会")
                if auto_check_rover:
                    mre_ok, mre_result = fetch_mre_for_sev(sev_no)

                has_active_mre = False
                if mre_ok and isinstance(mre_result, list):
                    if len(mre_result) > 0:
                        has_active_mre = any("In Force" in str(m.get("ステータス", "")) for m in mre_result)

                with st.expander(f"🚜 **SEV Code: {sev_no}** | {make} {model} ({model_code}) 🐨🐾", expanded=True):
                    c1, c2 = st.columns([2, 1])

                    with c1:
                        st.markdown("**① SEVs登録情報（公式レジスター）**")
                        st.markdown(f"- **メーカー / 車種:** {make} {model} （型式: `{model_code}`）")
                        st.markdown(
                            f"- **対象製造期間:** {f_str if pd.notna(f_str) and f_str else '指定なし'} 〜 "
                            f"{t_str if pd.notna(t_str) and t_str else '指定なし'}"
                        )
                        st.markdown(f"- **SEV有効期限:** {exp_str if pd.notna(exp_str) and exp_str else '期限設定なし'}")
                        if under_review.upper() == "YES":
                            st.warning("⚠️ **Under review（見直し中）:** 現在オーストラリア政府により登録内容の見直しが行われています。")

                        sev_page_url = f"{ROVER_SEV_DETAIL_BASE}{detail_id}" if detail_id and detail_id != "nan" else ROVER_SEVS_URL
                        st.markdown(f"📄 [ROVER公式【SEV詳細ページ】で適用基準・グレードを確認する ↗️]({sev_page_url})")

                    with c2:
                        st.markdown("**② 総合輸出判定**")
                        if not in_range:
                            st.error("❌ 輸出不可（製造年月 対象外） 😿")
                            st.caption(f"{build_year}年{build_month}月は対象期間外です。")
                        elif is_expired:
                            st.warning("⚠️ 要確認（SEV有効期限切れ） 🙀")
                            st.caption(f"有効期限 ({exp_str}) が過ぎています。")
                        elif mre_ok and has_active_mre and raws_permission:
                            st.success("✅ 輸出可能（SEVs・MRE共に有効） 🎊 🦘")
                        elif mre_ok and not has_active_mre:
                            st.error("❌ 輸出不可（有効なMREなし） 😿")
                            st.caption("SEV適合ですが、有効(In Force)なModel Reportがありません。")
                        elif not raws_permission:
                            st.warning("⚠️ 判定保留（RAWsライセンス未確認） 🐱")
                        else:
                            st.success("✅ SEVs適合（MRE要確認） 🐨")

                        html_button = f"""
                        <div style="width: 100%; text-align: center; margin-top: 6px;">
                            <button onclick="copyAndOpen()" style="
                                background-color: #FF4B4B;
                                color: white;
                                border: none;
                                padding: 10px 14px;
                                font-size: 13px;
                                font-weight: bold;
                                border-radius: 8px;
                                cursor: pointer;
                                width: 100%;
                                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                            ">
                                🔗 {sev_no} をコピーしてMREを開く ↗️ 🐨
                            </button>
                        </div>
                        <script>
                        function copyAndOpen() {{
                            if (navigator.clipboard && window.isSecureContext) {{
                                navigator.clipboard.writeText("{sev_no}").then(function() {{
                                    window.open("{ROVER_MRE_URL}", "_blank");
                                }}).catch(function(err) {{
                                    window.open("{ROVER_MRE_URL}", "_blank");
                                }});
                            }} else {{
                                var textArea = document.createElement("textarea");
                                textArea.value = "{sev_no}";
                                document.body.appendChild(textArea);
                                textArea.select();
                                try {{ document.execCommand('copy'); }} catch (err) {{}}
                                document.body.removeChild(textArea);
                                window.open("{ROVER_MRE_URL}", "_blank");
                            }}
                        }}
                        </script>
                        """
                        components.html(html_button, height=55)
                        st.caption("※開いたら検索窓で貼り付け (Ctrl+V / 長押し)")

                    if auto_check_rover:
                        if mre_ok and isinstance(mre_result, list):
                            st.markdown(f"**③ ROVER公式【Model Report】照合結果（{len(mre_result)}件ヒット）**")
                            st.dataframe(pd.DataFrame(mre_result), use_container_width=True)
                        else:
                            st.caption(f"ℹ️ Model Report 自動照会メモ: {mre_result}")

            st.markdown("---")
            st.subheader("📊 検索結果一覧（データシート） 🐨🦘🐰")
            display_cols = [c for c in matched.columns if c != "詳細ID"]
            st.dataframe(matched[display_cols], use_container_width=True)
