import streamlit as st
import streamlit.components.v1 as components

# スマホ用：画面最上部に確実に動作するキャラクター付き「車種を検索」ボタンを表示
components.html(
    """
    <div style="margin: 0; padding: 4px 0;">
      <button id="mobile-search-trigger" style="
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        width: 100%;
        max-width: 340px;
        background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
        color: #ffffff;
        border: none;
        border-radius: 999px;
        padding: 10px 20px;
        font-family: 'Meiryo', 'Hiragino Kaku Gothic ProN', sans-serif;
        font-size: 15px;
        font-weight: bold;
        box-shadow: 0 4px 12px rgba(21, 101, 192, 0.35);
        cursor: pointer;
      ">
        <span style="font-size: 20px; line-height: 1;">🐨</span>
        <span>🔍 車種を検索する（条件入力）</span>
      </button>
    </div>

    <script>
      document.getElementById('mobile-search-trigger').addEventListener('click', function() {
        const doc = window.parent.document;
        // Streamlitの標準サイドバー開閉ボタンを探してクリックを実行
        const candidates = [
          '[data-testid="stSidebarCollapsedControl"] button',
          '[data-testid="collapsedControl"] button',
          '[data-testid="stExpandSidebarButton"]',
          'button[kind="header"]'
        ];
        for (const selector of candidates) {
          const btn = doc.querySelector(selector);
          if (btn) {
            btn.click();
            return;
          }
        }
        // アイコンテキスト（keyboard_double_arrow_right）からボタンを特定するフォールバック
        const allButtons = doc.querySelectorAll('button');
        for (const b of allButtons) {
          if (b.innerText && b.innerText.includes('keyboard_double_arrow_right')) {
            b.click();
            return;
          }
        }
      });
    </script>
    """,
    height=56,
)
