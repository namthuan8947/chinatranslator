import streamlit as st
import os
import requests
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv
from google import genai

# 1. Tải API Key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")


# --- HÀM CÀO DỮ LIỆU ---
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

        next_chapter_url = None
        pager = soup.find(class_='pager')
        if pager:
            links = pager.find_all('a')
            if len(links) >= 3:
                next_chapter_url = urljoin(base_url, links[2].get('href'))

        headline_tag = soup.find(class_='headline')
        chapter_title_raw = headline_tag.get_text(strip=True) if headline_tag else "Chương mới"

        if "shuhaige" in domain:
            target_elements = soup.find_all(class_=['headline', 'content'])
            extracted_texts = [el.get_text(separator='\n', strip=True) for el in target_elements if
                               el.get_text().strip()]
            full_raw_text = '\n\n'.join(extracted_texts)
        else:
            for code_tag in soup(['script', 'style']):
                code_tag.decompose()
            full_raw_text = soup.get_text(separator='\n\n', strip=True)

        return full_raw_text, next_chapter_url, chapter_title_raw
    except Exception as e:
        return f"ERROR_CRAWL: {e}", None, "Lỗi cào dữ liệu"


# --- HÀM DỊCH AI ---
def translate_text(text):
    client = genai.Client(api_key=api_key)
    model_name = 'gemini-flash-lite-latest'
    prompt = "Dịch nội dung sau sang tiếng Việt mượt mà, văn phong truyện chuyên nghiệp, giữ cấu trúc đoạn văn, chỉ trả về bản dịch:\n\n"

    max_retries = 10
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=model_name, contents=prompt + text)
            return re.sub(r'\n+', '\n\n', response.text)
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                else:
                    return f"⚠️ Bé iu đợi anh xíu nha, máy chủ AI đang kẹt xe. Bấm nút thêm lần nữa giúp anh nò! ❤️"
            else:
                return f"Lỗi AI: {error_msg}"


# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Dịch Truyện Cho Giang", page_icon="📖", layout="wide")
st.title("📖 Web đọc truyện của bé Giangg")

# --- QUẢN LÝ SESSION STATE ---
if "chapters" not in st.session_state:
    st.session_state.chapters = []
if "target_next_url" not in st.session_state:
    st.session_state.target_next_url = None
if "prefetch_data" not in st.session_state:
    st.session_state.prefetch_data = None
if "prefetch_error" not in st.session_state:  # THÊM BIẾN LƯU LỖI DỊCH NGẦM
    st.session_state.prefetch_error = None


def clear_data():
    st.session_state.chapters = []
    st.session_state.target_next_url = None
    st.session_state.prefetch_data = None
    st.session_state.prefetch_error = None
    st.session_state.url_input = ""


# --- THANH NHẬP LIỆU ---
col_input, col_del = st.columns([9, 1.5], vertical_alignment="bottom")
with col_input:
    target_url = st.text_input("Dán link chương đầu tiên nò:", key="url_input",
                               placeholder="https://m.shuhaige.net/...")
with col_del:
    st.button("❌ Xóa hết", on_click=clear_data, use_container_width=True)

# --- NÚT BẮT ĐẦU CHƯƠNG ĐẦU TIÊN ---
if len(st.session_state.chapters) == 0:
    if st.button("🚀 Bắt đầu đọc thui embe", type="primary"):
        if target_url:
            with st.spinner("Đang dịch chương đầu cho bé..."):
                raw, nxt, title = crawl_content_and_next_link(target_url)
                if "ERROR_CRAWL" not in raw:
                    trans = translate_text(raw)
                    # NGĂN CHẶN LỖI NGAY TỪ CHƯƠNG ĐẦU
                    if trans.startswith("⚠️") or trans.startswith("Lỗi AI"):
                        st.error(trans)
                    else:
                        st.session_state.chapters.append({"url": target_url, "content": trans, "title": title})
                        st.session_state.target_next_url = nxt
                        st.rerun()
                else:
                    st.error(raw)

st.divider()

# --- HIỂN THỊ DANH SÁCH CHƯƠNG ĐÃ ĐỌC ---
for chap in st.session_state.chapters:
    with st.container(height=550, border=True):
        st.markdown(chap["content"])
    st.caption(f"🔗 Nguồn: {chap['url']}")
    st.divider()

# --- XỬ LÝ DỊCH NGẦM (PREFETCH) VÀ NÚT CHUYỂN CHƯƠNG ---
if st.session_state.target_next_url:
    # 1. TRƯỜNG HỢP THÀNH CÔNG: Đã dịch ngầm xong
    if st.session_state.prefetch_data and st.session_state.prefetch_data['url'] == st.session_state.target_next_url:
        st.success("✨ Chương tiếp theo đã sẵn sàng! Bấm là đọc được luôn nò 👇")
        if st.button("⏭️ Chuyển chương tiếp theo", type="primary", use_container_width=True):
            st.session_state.chapters.append(st.session_state.prefetch_data)
            st.session_state.target_next_url = st.session_state.prefetch_data['next_url']
            st.session_state.prefetch_data = None
            st.session_state.prefetch_error = None  # Xóa sạch lỗi cũ nếu có
            st.rerun()

    # 2. TRƯỜNG HỢP THẤT BẠI: Dịch ngầm bị kẹt xe 503
    elif st.session_state.prefetch_error:
        st.warning(st.session_state.prefetch_error)
        if st.button("🔄 Thử dịch ngầm lại chương sau nha bé", use_container_width=True):
            st.session_state.prefetch_error = None  # Xóa lỗi để chạy lại tiến trình dịch
            st.rerun()

    # 3. TRƯỜNG HỢP CHỜ: Tiến hành cào và dịch ngầm
    else:
        st.info("🤫 Bé iu cứ đọc nhoo, AI đang âm thầm chuẩn bị sẵn chương tiếp theo cho bé...")
        with st.spinner("Đang dịch ngầm..."):
            raw, nxt, title = crawl_content_and_next_link(st.session_state.target_next_url)
            if "ERROR_CRAWL" not in raw:
                trans = translate_text(raw)

                # BỘ LỌC QUAN TRỌNG: Kiểm tra xem bản dịch có phải là câu báo lỗi không
                if trans.startswith("⚠️") or trans.startswith("Lỗi AI"):
                    st.session_state.prefetch_error = trans  # Ghi nhận lỗi để hiển thị nút Retry
                    st.rerun()
                else:
                    st.session_state.prefetch_data = {
                        "url": st.session_state.target_next_url,
                        "content": trans,
                        "title": title,
                        "next_url": nxt
                    }
                    st.rerun()
            else:
                st.session_state.prefetch_error = "Gặp lỗi khi cào chương sau rồi bé ơi!"
                st.rerun()
elif len(st.session_state.chapters) > 0:
    st.write("🎉 Hết truyện rồi bé yêu uiii!")
