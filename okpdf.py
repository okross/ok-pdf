import streamlit as st
from pypdf import PdfWriter
from pdf2image import convert_from_bytes
from streamlit_sortables import sort_items
import io
from PIL import Image

# 設定頁面與主題顏色
st.set_page_config(
    page_title="歐可 PDF 專業合併工具",
    page_icon="📄",
    layout="wide"
)

# 自定義 CSS
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; background-color: #FF4B4B; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 20px; height: 3em; background-color: #008CBA; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("📄 歐可 PDF & 圖片全能合併工具")
st.info("💡 支援 PDF、JPG、PNG。圖片會自動調整為 A4 尺寸併入 PDF。")

# 1. 檔案上傳 (新增圖片格式)
uploaded_files = st.file_uploader(
    "請選擇要合併的檔案 (PDF, JPG, PNG)", 
    type=["pdf", "jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

# 快取：處理預覽圖
@st.cache_data(show_spinner=False)
def get_preview(file_bytes, file_name):
    if file_name.lower().endswith(".pdf"):
        try:
            images = convert_from_bytes(file_bytes, first_page=1, last_page=1, dpi=70)
            return images[0] if images else None
        except:
            return None
    else:
        # 如果是圖片，直接用 PIL 打開並生成縮圖
        img = Image.open(io.BytesIO(file_bytes))
        img.thumbnail((300, 300))
        return img

# 核心邏輯：將圖片轉為符合 A4 尺寸的 PDF 頁面
def img_to_a4_pdf(img_bytes):
    img = Image.open(io.BytesIO(img_bytes))
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    
    # A4 尺寸 (點): 595 x 842
    a4_w, a4_h = 595, 842
    
    # 計算縮放比例，確保圖片完整放入 A4 且不變形
    img_w, img_h = img.size
    ratio = min(a4_w / img_w, a4_h / img_h)
    new_size = (int(img_w * ratio), int(img_h * ratio))
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # 建立一個白底 A4 畫布，將圖片置中
    new_img = Image.new("RGB", (a4_w, a4_h), (255, 255, 255))
    offset = ((a4_w - new_size[0]) // 2, (a4_h - new_size[1]) // 2)
    new_img.paste(img, offset)
    
    # 轉為 PDF Bytes
    img_pdf_buf = io.BytesIO()
    new_img.save(img_pdf_buf, format="PDF")
    img_pdf_buf.seek(0)
    return img_pdf_buf

if uploaded_files:
    file_dict = {f.name: f for f in uploaded_files}
    file_names = list(file_dict.keys())

    st.subheader("1. 調整合併順序 (左右拖拉)")
    sorted_names = sort_items(file_names, direction="horizontal")

    st.divider()

    st.subheader("2. 預覽順序確認")
    cols = st.columns(min(len(sorted_names), 5)) 
    for idx, name in enumerate(sorted_names):
        with cols[idx % 5]:
            file_data = file_dict[name].getvalue()
            preview_img = get_preview(file_data, name)
            if preview_img:
                st.image(preview_img, caption=f"順序 {idx+1}: {name}", use_container_width=True)
            else:
                st.warning(f"無法預覽: {name}")

    st.divider()

    st.subheader("3. 產生結果")
    col_btn, _ = st.columns([1, 2])
    
    with col_btn:
        if st.button("🚀 開始合併 PDF 與圖片"):
            merger = PdfWriter()
            progress_bar = st.progress(0)
            
            try:
                for i, name in enumerate(sorted_names):
                    file_obj = file_dict[name]
                    if name.lower().endswith(".pdf"):
                        merger.append(io.BytesIO(file_obj.getvalue()))
                    else:
                        # 圖片處理：轉成 A4 PDF 後再合併
                        pdf_page = img_to_a4_pdf(file_obj.getvalue())
                        merger.append(pdf_page)
                    
                    progress_bar.progress((i + 1) / len(sorted_names))
                
                output_pdf = io.BytesIO()
                merger.write(output_pdf)
                merger.close()
                
                st.success("✅ 全部檔案已完美合併！")
                st.download_button(
                    label="📥 立即下載合併後的 PDF",
                    data=output_pdf.getvalue(),
                    file_name="OK_Smart_Merged.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"合併失敗：{e}")
else:
    st.write("---")
    st.caption("等待檔案中... 請將 PDF 或圖片（JPG/PNG）拖入上方區域。")
