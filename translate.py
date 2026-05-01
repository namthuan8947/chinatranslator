import streamlit as st
import os
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv
from google import genai

# 1. Tải API Key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")


# --- HÀM CÀO DỮ LIỆU & LẤY LINK CHƯƠNG TIẾP THEO ---
def crawl_content_and_next_link(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        domain = urlparse(url).netloc
        base_url = f"{urlparse(url).scheme}://{domain}"

        # --- Lấy link chương tiếp theo ---
        next_chapter_url = None
        pager = soup.find(class_='pager')
        if pager:
            links = pager.find_all('a')
            if len(links) >= 3:
                # Lấy href của thẻ a thứ 3 và nối với domain nếu là link tương đối
                next_chapter_url = urljoin(base_url, links[2].get('href'))

        # --- Lấy nội dung văn bản ---
        if "shuhaige" in domain:
            # SỬA LỖI TẠI ĐÂY: Xóa[cite: 1]
            target_elements = soup.find_all(class_=['headline', 'content'])
            extracted_texts = []
            for element in target_elements:
                text = element.get_text(separator='\n', strip=True)
                if text:
                    extracted_texts.append(text)
            content = '\n\n'.join(extracted_texts)
        else:
            for code_tag in soup(['script', 'style']):
                code_tag.decompose()
            content = soup.get_text(separator='\n\n', strip=True)

        return content, next_chapter_url

    except Exception as e:
        return f"ERROR_CRAWL: {e}", None


# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Dịch Truyện Online", page_icon="📖", layout="wide")

st.title("📖 Đọc Truyện & Dịch Tự Động")

if not api_key:
    st.error("❌ Không tìm thấy GOOGLE_API_KEY trong Secrets!")
    st.stop()

# --- QUẢN LÝ TRẠNG THÁI (SESSION STATE) ---
if "url_input" not in st.session_state:
    st.session_state.url_input = ""
if "next_url" not in st.session_state:
    st.session_state.next_url = None


def clear_url():
    st.session_state.url_input = ""
    st.session_state.next_url = None


def go_to_next_chapter():
    if st.session_state.next_url:
        st.session_state.url_input = st.session_state.next_url


# --- KHU VỰC NHẬP LINK ---
col1, col2, col3 = st.columns([7, 1, 2])
with col1:
    target_url = st.text_input("Dán link vào đây:", label_visibility="collapsed", key="url_input")
with col2:
    st.button("❌", on_click=clear_url, use_container_width=True)
with col3:
    start_button = st.button("🚀 Bắt đầu dịch", use_container_width=True)

st.divider()

# --- XỬ LÝ DỊCH ---
# Điều kiện chạy dịch: Nhấn nút Start HOẶC link trong ô input vừa mới được cập nhật từ nút "Chương Tiếp Theo"
if start_button or (st.session_state.url_input and st.session_state.url_input == st.session_state.next_url):
    if not st.session_state.url_input:
        st.warning("⚠️ Vui lòng nhập link!")
    else:
        with st.spinner('🔍 Đang lấy dữ liệu...'):
            crawled_text, next_link = crawl_content_and_next_link(st.session_state.url_input)
            st.session_state.next_url = next_link

        if "ERROR_CRAWL" in crawled_text:
            st.error(f"❌ Lỗi: {crawled_text}")
        else:
            try:
                client = genai.Client(api_key=api_key)
                with st.spinner('🤖 AI đang dịch chương mới...'):
                    prompt = "Dịch nội dung sau sang tiếng Việt mượt mà, giữ cấu trúc đoạn văn, chỉ trả về bản dịch:\n\n"
                    response = client.models.generate_content(
                        model='gemini-flash-latest',
                        contents=prompt + crawled_text
                    )
                    translated_text = response.text
                    display_text = re.sub(r'\n+', '\n\n', translated_text)

                    st.success("✅ Dịch hoàn tất!")

                    # Cột hiển thị Bản dịch và Nút chuyển chương
                    title_col, next_btn_col = st.columns([8, 2])
                    with title_col:
                        st.subheader("Bản Dịch")
                    with next_btn_col:
                        if st.session_state.next_url:
                            st.button("⏭️ Chương Tiếp Theo", on_click=go_to_next_chapter, type="primary",
                                      use_container_width=True)

                    with st.container(height=600, border=True):
                        st.markdown(display_text)

                    st.download_button("📥 Tải file .txt", translated_text, file_name="truyen_dich.txt",
                                       use_container_width=True)

            except Exception as e:
                st.error(f"❌ Lỗi AI: {e}")
