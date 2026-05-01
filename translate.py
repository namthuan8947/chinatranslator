import streamlit as st
import os
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv
from google import genai

# 1. Tải API Key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# --- HÀM CÀO DỮ LIỆU ---
def crawl_content(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        domain = urlparse(url).netloc
        
        if "shuhaige" in domain:
            target_elements = soup.find_all(class_=['headline', 'content'])
            extracted_texts = []
            for element in target_elements:
                text = element.get_text(separator='\n', strip=True)
                if text:
                    extracted_texts.append(text)
            return '\n\n'.join(extracted_texts)
            
        else:
            for code_tag in soup(['script', 'style']):
                code_tag.decompose()
            text = soup.get_text(separator='\n\n', strip=True)
            return text
            
    except Exception as e:
        return f"ERROR_CRAWL: {e}"

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Dịch Truyện Online", page_icon="📖", layout="wide")

st.title("📖 Đọc Truyện & Dịch Tự Động")
st.write("Dán link chương truyện tiếng Trung (hoặc bất kỳ web nào), AI sẽ dịch và hiển thị ngay tại đây.")

if not api_key:
    st.error("❌ Không tìm thấy GOOGLE_API_KEY. Vui lòng kiểm tra lại Streamlit Secrets!")
    st.stop()

# --- XỬ LÝ NÚT XÓA LINK (CLEAR BUTTON) ---
# Khởi tạo biến lưu trữ link trong session_state nếu chưa có
if "url_input" not in st.session_state:
    st.session_state.url_input = ""

# Hàm xóa link
def clear_url():
    st.session_state.url_input = ""

# --- KHU VỰC NHẬP LINK MỚI ---
# Chia làm 3 cột: Ô nhập link (7 phần) - Nút X (1 phần) - Nút Dịch (2 phần)
col1, col2, col3 = st.columns([7, 1, 2]) 

with col1:
    # Gán key="url_input" để ô text_input liên kết trực tiếp với biến trong session_state
    target_url = st.text_input(
        "Dán link website vào đây:", 
        label_visibility="collapsed", 
        placeholder="Nhấn giữ và chọn Dán (Paste) link vào đây...",
        key="url_input"
    )
with col2:
    # Gọi hàm clear_url khi nhấn nút X
    st.button("❌", on_click=clear_url, use_container_width=True, help="Xóa link đang nhập")
with col3:
    start_button = st.button("🚀 Bắt đầu dịch", use_container_width=True)

st.divider() 

# --- XỬ LÝ LẤY DỮ LIỆU VÀ DỊCH ---
if start_button:
    if not target_url:
        st.warning("⚠️ Vui lòng nhập link website trước!")
    else:
        with st.spinner('🔍 Đang lấy dữ liệu từ website...'):
            crawled_text = crawl_content(target_url)
            
        if "ERROR_CRAWL" in crawled_text:
            st.error(f"❌ Lỗi truy cập web: {crawled_text}")
        elif not crawled_text:
            st.warning("⚠️ Không tìm thấy nội dung văn bản nào trên trang này.")
        else:
            try:
                client = genai.Client(api_key=api_key)
                
                with st.spinner('🤖 AI Gemini đang tiến hành dịch thuật...'):
                    prompt_instruction = (
                        "Dịch toàn bộ nội dung sau đây sang tiếng Việt một cách tự nhiên. "
                        "TUYỆT ĐỐI GIỮ NGUYÊN cấu trúc đoạn văn. Mỗi đoạn văn phải cách nhau bằng một dòng trống. "
                        "Chỉ trả về bản dịch cuối cùng, không kèm giải thích:\n\n"
                    )
                    
                    response = client.models.generate_content(
                        model='gemini-flash-latest', 
                        contents=prompt_instruction + crawled_text
                    )
                    
                    translated_text = response.text
                    display_text = re.sub(r'\n+', '\n\n', translated_text)
                    
                    st.success("✅ Dịch hoàn tất!")
                    
                    st.subheader("Bản Dịch")
                    with st.container(height=600, border=True):
                        st.markdown(display_text)
                    
                    st.write("") 
                    col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
                    with col_dl2:
                        st.download_button(
                            label="📥 Tải file bản dịch về máy (.txt)",
                            data=translated_text,
                            file_name="website_dich.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                        
            except Exception as e:
                st.error(f"❌ Lỗi AI: {e}")
