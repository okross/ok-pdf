import streamlit as st
from pypdf import PdfWriter
from pdf2image import convert_from_bytes
from streamlit_sortables import sort_items
import io
from PIL import Image

# 設定頁面
st.set_page_config(page_title="歐可 PDF 專業工具箱", page_icon="📄", layout="wide")

# 自定義 CSS
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { border-radius: 20px; height: 3em; background-color: #FF4B4B; color: white; }
    .stDownloadButton>button { border-radius: 20px; height: 3em; background-color: #008CBA; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("📄 歐可 PDF & 圖片進階合併工具")

# --- 側邊欄設定區 ---
with st.sidebar:
    st.header("⚙️ 輸出設定")
    
    # 1. DPI 選擇
    dpi_options = {
        200: "200 DPI (推薦：一般文件、網路傳輸，大小適中)",
        300: "300 DPI (標準：正式公文、高品質列印)",
        600: "600 DPI (極致：精密圖表、檔案典藏，檔案較大)"
    }
    selected_dpi = st.selectbox("選擇輸出解析度 (DPI)", options=[200, 300, 600], format_func=lambda x: dpi_options[x])
    
    st.divider()
    
    # 2. 縮放選項
    fill_a4 = st.checkbox("將圖片放大至填滿 A4", value=True, help="勾選：圖片會自動縮放至 A4 最大範圍；不勾選：保持圖片原尺寸置中。")
    
    st.divider()
    
    # 3. 證件合併模式
    id_card_mode = st.checkbox("開啟『證件/雙面』合併模式", value=False, help="將兩張圖片合併在同一頁 A4 (上下排列)，適合身分證正反面。")
    if id_card_mode:
        st.warning("⚠️ 證件模式下，圖片會自動『兩兩一組』合併，單數張最後一張會獨立一頁。")

# --- 主要功能區 ---

uploaded_files = st.file_uploader("上傳 PDF 或圖片", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)

@st.cache_data(show_spinner=False)
def get_preview(file_bytes, file_name):
    try:
        if file_name.lower().endswith(".pdf"):
            images = convert_from_bytes(file_bytes, first_page=1, last_page=1, dpi=80)
            return images[0] if images else None
        else:
            img = Image.open(io.BytesIO(file_bytes))
            img.thumbnail((400, 400))
            return img
    except:
        return None

def process_img_to_a4(img_list, dpi, is_fill, is_id_mode):
    """
    處理圖片轉為 PDF 頁面的邏輯
    img_list: 傳入 PIL Image 物件列表
    """
    # A4 吋: 8.27 x 11.69
    a4_px_w = int(8.27 * dpi)
    a4_px_h = int(11.69 * dpi)
    
    pages = []
    
    if is_id_mode:
        # 證件模式：每兩張一張 A4
        for i in range(0, len(img_list), 2):
            new_img = Image.new("RGB", (a4_px_w, a4_px_h), (255, 255, 255))
            pair = img_list[i:i+2]
            
            for idx, img in enumerate(pair):
                # 證件模式強迫縮放至 A4 的一半高度 (扣掉邊距)
                max_w = a4_px_w * 0.8
                max_h = a4_px_h * 0.4
                
                img_w, img_h = img.size
                ratio = min(max_w / img_w, max_h / img_h)
                res_img = img.resize((int(img_w * ratio), int(img_h * ratio)), Image.Resampling.LANCZOS)
                
                # 計算位置 (上或下置中)
                x = (a4_px_w - res_img.size[0]) // 2
                y = (a4_px_h // 2 - res_img.size[1]) // 2 + (idx * a4_px_h // 2)
                new_img.paste(res_img, (x, y))
            
            pages.append(new_img)
    else:
        # 一般模式：一圖一頁
        for img in img_list:
            new_img = Image.new("RGB", (a4_px_w, a4_px_h), (255, 255, 255))
            img_w, img_h = img.size
            
            if is_fill:
                ratio = min(a4_px_w / img_w, a4_px_h / img_h)
            else:
                # 原尺寸：但如果比 A4 大還是要縮小一點避免出界
                ratio = min(1.0, a4_px_w / img_w, a4_px_h / img_h)
            
            res_img = img.resize((int(img_w * ratio), int(img_h * ratio)), Image.Resampling.LANCZOS)
            x = (a4_px_w - res_img.size[0]) // 2
            y = (a4_px_h - res_img.size[1]) // 2
            new_img.paste(res_img, (x, y))
            pages.append(new_img)
            
    # 將所有處理好的 Image 轉成一個 PDF bytes
    output = io.BytesIO()
    if pages:
        pages[0].save(output, format="PDF", save_all=True, append_images=pages[1:], resolution=float(dpi), optimize=True)
    output.seek(0)
    return output

if uploaded_files:
    file_dict = {f.name: f for f in uploaded_files}
    sorted_names = sort_items(list(file_dict.keys()), direction="horizontal")

    st.subheader("1. 預覽與排序")
    cols = st.columns(min(len(sorted_names), 5)) 
    for idx, name in enumerate(sorted_names):
        with cols[idx % 5]:
            p_img = get_preview(file_dict[name].getvalue(), name)
            if p_img: st.image(p_img, caption=name, use_container_width=True)

    if st.button("🚀 開始執行任務"):
        merger = PdfWriter()
        image_pool = [] # 用來存放待處理的圖片
        
        try:
            for name in sorted_names:
                f_obj = file_dict[name]
                if name.lower().endswith(".pdf"):
                    # 如果中間夾雜 PDF，先處理掉之前的圖片池
                    if image_pool:
                        img_pdf = process_img_to_a4(image_pool, selected_dpi, fill_a4, id_card_mode)
                        merger.append(img_pdf)
                        image_pool = []
                    merger.append(io.BytesIO(f_obj.getvalue()))
                else:
                    # 圖片先放入池中，因為可能要進行兩兩合併
                    image_pool.append(Image.open(io.BytesIO(f_obj.getvalue())).convert("RGB"))
            
            # 處理剩餘的圖片
            if image_pool:
                img_pdf = process_img_to_a4(image_pool, selected_dpi, fill_a4, id_card_mode)
                merger.append(img_pdf)
            
            final_output = io.BytesIO()
            merger.write(final_output)
            
            st.success(f"✅ 完成！輸出解析度：{selected_dpi} DPI")
            st.download_button("📥 下載合併文件", final_output.getvalue(), "OK_Pro_Merged.pdf", "application/pdf")
        except Exception as e:
            st.error(f"錯誤：{e}")
