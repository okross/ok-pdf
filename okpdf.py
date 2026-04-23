import streamlit as st
from pypdf import PdfWriter
from pdf2image import convert_from_bytes
from streamlit_sortables import sort_items
import io
from PIL import Image

# 設定頁面與主題顏色
st.set_page_config(
    page_title="歐可 PDF & 圖片全能合併工具",
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

st.title("📄 歐可 PDF & 圖片全能合併工具 (高畫質版)")
st.info("💡 支援 PDF、JPG、PNG。圖片會以 200 DPI 品質自動調整為 A4 尺寸。")

# 1. 檔案上傳
uploaded_files = st.file_uploader(
    "請選擇要合併的檔案 (PDF, JPG, PNG)", 
    type=["pdf", "jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

# 2. 優化預覽清晰度 (設定為 120 DPI)
@st.cache_data(show_spinner=False)
def get_preview(file_bytes, file_name):
    try:
        if file_name.lower().endswith(".pdf"):
            images = convert_from_bytes(file_bytes, first_page=1, last_page=1, dpi=100)
            return images[0] if images else None
        else:
            img = Image.open(io.BytesIO(file_bytes))
            img.thumbnail((500, 500))
            return img
    except Exception as e:
        return None

# 3. 核心邏輯：將圖片轉為 200 DPI 的 A4 PDF
def img_to_a4_pdf(img_bytes):
    img = Image.open(io.BytesIO(img_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    # 200 DPI 下的 A4 像素尺寸 (8.27 * 200, 11.69 * 200)
    a4_w, a4_h = 1654, 2338 
    
    img_w, img_h = img.size
    ratio = min(a4_w / img_w, a4_h / img_h)
    new_size = (int(img_w * ratio), int(img_h * ratio))
    
    # 使用最高品質縮放濾鏡 LANCZOS
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # 建立白底 A4 畫布並置中
    new_img = Image.new("RGB", (a4_w, a4_h), (255, 255, 255))
    offset = ((a4_w - new_size[0]) // 2, (a4_h - new_size[1]) // 2)
    new_img.paste(img, offset)
    
    img_pdf_buf = io.BytesIO()
    # 儲存設定：200 DPI, 品質 85 (兼顧畫質與體積), 並啟用優化
    new_img.save(img_pdf_buf, format="PDF", resolution=200.0, quality=85, optimize=True)
    img_pdf_buf.seek(0)
    return img_pdf_buf

if uploaded_files:
    file_dict = {f.name: f for f in uploaded_files}
    file_names = list(file_dict.keys())

    st.subheader("1. 調整合併順序")
    sorted_names = sort_items(file_names, direction="horizontal")

    st.divider()

    st.subheader("2. 預覽順序確認")
    cols = st.columns(min(len(sorted_names), 5)) 
    for idx, name in enumerate(sorted_names):
        with cols[idx % 5]:
            file_data = file_dict[name].getvalue()
            preview_img = get_preview(file_data, name)
            if preview_img:
                st.image(preview_img, caption=f"{idx+1}: {name}", use_container_width=True)
            else:
                st.warning(f"無法預覽: {name}")

    st.divider()

    st.subheader("3. 產生結果")
    col_btn, _ = st.columns([1, 2])
    
    with col_btn:
        if st.button("🚀 開始合併任務"):
            merger = PdfWriter()
            progress_bar = st.progress(0)
            
            try:
                for i, name in enumerate(sorted_names):
                    file_obj = file_dict[name]
                    if name.lower().endswith(".pdf"):
                        merger.append(io.BytesIO(file_obj.getvalue()))
                    else:
                        pdf_page = img_to_a4_pdf(file_obj.getvalue())
                        merger.append(pdf_page)
                    
                    progress_bar.progress((i + 1) / len(sorted_names))
                
                output_pdf = io.BytesIO()
                merger.write(output_pdf)
                merger.close()
                
                st.success("✅ 合併完成！")
                st.download_button(
                    label="📥 下載高畫質 PDF",
                    data=output_pdf.getvalue(),
                    file_name="Merged_Document_200dpi.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"合併過程中發生錯誤：{e}")
else:
    st.write("---")
    st.caption("請上傳檔案以開始使用。")
