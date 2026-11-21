from datetime import datetime
import glob
import os
import re
import pandas as pd
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
st.caption("ROVER公式【SEVs登録全車種】×【Model Report承認リスト】適合判定・即時照会ツール")

ROVER_SEVS_URL = "https://www.rover.infrastructure.gov.au/PublishedApprovals/SEVApprovals/"
ROVER_MRE_URL = "https://www.rover.infrastructure.gov.au/PublishedApprovals/MREApprovals/"
LEGACY_EXCEL_PATH = "AUS SEV早見表.xlsx"


def read_sev_file(file_obj_or_path):
    name = file_obj_or_path if isinstance(file_obj_or_path, str) else file_obj_or_path.name
    if str(name).lower().endswith(".csv"):
        df = pd.read_csv(file_obj_or_path, skiprows=1).iloc[:, :8]
    else:
        df = pd.read_excel(file_obj_or_path, skiprows=1).iloc[:, :8]
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
    return df.dropna(subset=["SEV番号"])


@st.cache_data(ttl=600, show_spinner=False)
def load_latest_sev_master():
    # AUS_SEV_LATEST で始まる最新ファイル（xlsx / csv）を自動検出
    candidates = glob.glob("AUS_SEV_LATEST*.xlsx") + glob.glob("AUS_SEV_LATEST*.xls") + glob.glob("AUS_SEV_LATEST*.csv")
    if candidates:
        # ファイル名（日付順）と更新日時の両方を考慮して最新を選択
        candidates.sort(key=lambda x: (x, os.path.getmtime(x)), reverse=True)
        latest_path = candidates[0]
        try:
            df = read_sev_file(latest_path)
            date_match = re.search(r"\((\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})\)", latest_path)
            ver_label = f"データ基準日: {date_match.group(1)}" if date_match else f"ファイル: {latest_path}"
            return df, f"📂 {latest_path}（全{len(df)}件）", ver_label
        except Exception as e:
            return None, f"読み込みエラー ({latest_path}): {e}", ""

    # 見つからない場合は従来の AUS SEV早見表.xlsx を使用
    if os.path.exists(LEGACY_EXCEL_PATH):
        try:
            df = read_sev_file(LEGACY_EXCEL_PATH)
            return df, f"📁 {LEGACY_EXCEL_PATH}（全{len(df)}件）", "標準マスター"
        except Exception as e:
            return None, f"読み込みエラー: {e}", ""

    return None, "SEVデータファイルが見つかりません", ""


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


# --- サイドバー ---
st.sidebar.header("🔍 1. 車両情報の入力 🐨")
input_query = st.sidebar.text_input("メーカー・車種名・型式・SEV番号", value="ZVW40").strip().upper()

col_y, col_m = st.sidebar.columns(2)
build_year = col_y.number_input("製造年 (年)", min_value=1980, max_value=2026, value=2015)
build_month = col_m.number_input("製造月 (月)", min_value=1, max_value=12, value=6)

raws_permission = st.sidebar.checkbox(
    "提携RAWs工場が Model Report の利用ライセンスを保有している", value=True
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 最新ファイルに再読み込みする ✨"):
    st.cache_data.clear()
    st.rerun()

uploaded_file = st.sidebar.file_uploader(
    "（任意）手元のExcel / CSVで一時判定する場合 🐥", type=["xlsx", "xls", "csv"]
)

# --- メイン判定処理 ---
if st.sidebar.button("🚙 適合判定を実行する 💨 🦘", type="primary"):
    if uploaded_file:
        try:
            sev_df = read_sev_file(uploaded_file)
            source_label = f"📤 手動アップロード: {uploaded_file.name}（全{len(sev_df)}件）"
            sync_time = "一時読み込み"
        except Exception as e:
            st.error(f"ファイルの読み込みに失敗しました: {e}")
            sev_df = None
    else:
        sev_df, source_label, sync_time = load_latest_sev_master()

    if sev_df is None:
        st.error(f"❌ {source_label}")
    elif not input_query:
        st.warning("メーカー・車種名・型式・SEV番号のいずれかを入力してください。")
    else:
        st.caption(f"📡 情報源: **{source_label}** （{sync_time}）")

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

                d_from = parse_my(f_str)
                d_to = parse_my(t_str)
                expiry = parse_dmy(exp_str)

                in_range = True
                if d_from and target_date < d_from:
                    in_range = False
                if d_to and target_date > d_to:
                    in_range = False

                is_expired = expiry and expiry < today

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
                        st.markdown(f"📄 [ROVER公式【SEVs一覧ページ】で詳細条件を確認する ↗️]({ROVER_SEVS_URL})")

                    with c2:
                        st.markdown("**② 総合輸出判定**")
                        if not in_range:
                            st.error("❌ 輸出不可（製造年月 対象外） 😿")
                            st.caption(f"{build_year}年{build_month}月は対象期間外です。")
                        elif is_expired:
                            st.warning("⚠️ 要確認（SEV有効期限切れ） 🙀")
                            st.caption(f"有効期限 ({exp_str}) が過ぎています。")
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

            st.markdown("---")
            st.subheader("📊 検索結果一覧（データシート） 🐨🦘🐰")
            st.dataframe(matched, use_container_width=True)
