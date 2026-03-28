import streamlit as st
from pypdf import PdfWriter
from pdf2image import convert_from_bytes
from streamlit_sortables import sort_items
import io

# 設定頁面與主題顏色（歐可風格）
st.set_page_config(
    page_title="歐可 PDF 專業合併工具",
    page_icon="📄",
    layout="wide"
)

# 自定義 CSS 美化介面
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; background-color: #FF4B4B; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 20px; height: 3em; background-color: #008CBA; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("📄 歐可 PDF 線上合併工具")
st.info("💡 步驟：1. 上傳檔案 -> 2. 拖拉方塊調整順序 -> 3. 預覽確認 -> 4. 點擊合併下載")

# 1. 檔案上傳
uploaded_files = st.file_uploader("請選擇要合併的 PDF 檔案 (可多選)", type="pdf", accept_multiple_files=True)

# 建立一個快取函式來生成縮圖，避免每次操作都重新轉換，提升效能
@st.cache_data(show_spinner=False)
def get_pdf_preview(file_bytes):
    # 只取第一頁，解析度設為 70 兼顧清晰與速度
    images = convert_from_bytes(file_bytes, first_page=1, last_page=1, dpi=70)
    return images[0] if images else None

if uploaded_files:
    # 將上傳的檔案存入字典以便檢索
    file_dict = {f.name: f for f in uploaded_files}
    file_names = list(file_dict.keys())

    st.subheader("1. 調整合併順序 (左右拖拉)")
    # 2. 拖拉排序元件 (這裡回傳排序後的檔案名稱列表)
    sorted_names = sort_items(file_names, direction="horizontal")

    st.divider()

    # 3. 顯示對應排序後的預覽縮圖
    st.subheader("2. 預覽順序確認")
    cols = st.columns(min(len(sorted_names), 5)) # 每列最多顯示 5 個
    for idx, name in enumerate(sorted_names):
        with cols[idx % 5]:
            preview_img = get_pdf_preview(file_dict[name].getvalue())
            if preview_img:
                st.image(preview_img, caption=f"第 {idx+1} 份：{name}", use_container_width=True)
            else:
                st.warning(f"無法產生 {name} 的預覽")

    st.divider()

    # 4. 合併與輸出
    st.subheader("3. 產生結果")
    col_btn, col_empty = st.columns([1, 2])
    
    with col_btn:
        if st.button("🚀 開始執行合併任務"):
            merger = PdfWriter()
            progress_bar = st.progress(0)
            
            try:
                for i, name in enumerate(sorted_names):
                    merger.append(file_dict[name])
                    progress_bar.progress((i + 1) / len(sorted_names))
                
                output_pdf = io.BytesIO()
                merger.write(output_pdf)
                merger.close()
                
                st.success("✅ 合併完成！高品質 PDF 已準備就緒。")
                
                st.download_button(
                    label="📥 立即下載合併後的 PDF",
                    data=output_pdf.getvalue(),
                    file_name="OK_Merged_Document.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"合併失敗，原因：{e}")
else:
    st.write("---")
    st.caption("等待上傳檔案中... 請將 PDF 拖入上方上傳區。")
