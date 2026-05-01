import streamlit as st
import os
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv
from google import genai

# 1. Tải API Key từ file .env
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")


# --- HÀM CÀO DỮ LIỆU ĐÃ SỬA XUỐNG DÒNG ---
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
            # SỬA Ở ĐÂY: Dùng \n\n để ghép các đoạn văn
            return '\n\n'.join(extracted_texts)

        else:
            for code_tag in soup(['script', 'style']):
                code_tag.decompose()

            # SỬA Ở ĐÂY: Dùng \n\n làm vách ngăn khi cào web khác
            text = soup.get_text(separator='\n\n', strip=True)
            return text

    except Exception as e:
        return f"ERROR_CRAWL: {e}"


# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Dịch Truyện Online", page_icon="📖", layout="wide")

st.title("📖 Đọc Truyện & Dịch Tự Động")
st.write("Dán link chương truyện tiếng Trung (hoặc bất kỳ web nào), AI sẽ dịch và hiển thị ngay tại đây.")

if not api_key:
    st.error("❌ Không tìm thấy GOOGLE_API_KEY. Vui lòng kiểm tra lại file `.env`!")
    st.stop()

# --- KHU VỰC NHẬP LINK ---
col1, col2 = st.columns([4, 1])
with col1:
    target_url = st.text_input("Dán link website vào đây:", label_visibility="collapsed",
                               placeholder="https://m.shuhaige.net/...")
with col2:
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
                    # Nâng cấp prompt: Ép AI phải xuống dòng rõ ràng
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

                    # --- XỬ LÝ LỖI DÍNH CHỮ CHO MÀN HÌNH ---
                    # Dùng Regex để biến tất cả các lần xuống dòng thành 2 dấu xuống dòng (chuẩn Markdown)
                    display_text = re.sub(r'\n+', '\n\n', translated_text)

                    st.success("✅ Dịch hoàn tất!")

                    # --- KHU VỰC ĐỌC TRỰC TIẾP ---
                    st.subheader("Bản Dịch")
                    with st.container(height=600, border=True):
                        # Giờ đây st.markdown sẽ nhận diện tốt các đoạn văn
                        st.markdown(display_text)

                    # --- KHU VỰC TẢI FILE ---
                    st.write("")
                    col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
                    with col_dl2:
                        # Khi lưu file text thì vẫn giữ nguyên văn bản gốc của AI (translated_text) để không bị thưa quá
                        st.download_button(
                            label="📥 Tải file bản dịch về máy (.txt)",
                            data=translated_text,
                            file_name="website_dich.txt",
                            mime="text/plain",
                            use_container_width=True
                        )

            except Exception as e:
                st.error(f"❌ Lỗi AI: {e}")