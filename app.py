import streamlit as st
from pypdf import PdfWriter, PdfReader
from datetime import datetime
import re
import random
import string
import io

# ======================
# Page Config
# ======================
st.set_page_config(
    page_title="PDF Tools",
    page_icon="📄",
    layout="centered"
)

# ======================
# Helper Functions
# ======================
def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))

def generate_verification_code(length=6):
    return "".join(random.choices(string.digits, k=length))

def merge_pdfs(uploaded_files):
    writer = PdfWriter()
    for uploaded_file in uploaded_files:
        try:
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                writer.add_page(page)
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")
            return None
    return writer

def extract_pages(pdf_bytes, selected_pages):
    """Extract selected pages (1-based index) from PDF"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    for page_num in selected_pages:
        idx = page_num - 1
        if 0 <= idx < len(reader.pages):
            writer.add_page(reader.pages[idx])

    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def rotate_pages(pdf_bytes, selected_pages, angle):
    """
    Rotate selected pages (1-based index) by the given angle (clockwise).
    Angle must be a multiple of 90 (typically 90, 180, 270).
    Non-selected pages are kept as-is.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    selected_set = set(selected_pages)

    for i, page in enumerate(reader.pages):
        page_num = i + 1  # 1-based
        if page_num in selected_set:
            writer.add_page(page.rotate(angle))
        else:
            writer.add_page(page)

    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def preview_pdf(pdf_bytes: bytes, key: str = "pdf_preview", max_pages: int = 8):
    """
    Reliable PDF preview that works in Chrome / Edge / Firefox.
    Uses pypdfium2 to render pages as images.
    """
    if not pdf_bytes:
        st.warning("No PDF data to preview.")
        return

    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(pdf_bytes)
        n_pages = len(pdf)

        st.caption(f"📄 Preview — showing {min(n_pages, max_pages)} of {n_pages} page(s)")

        pages_to_show = min(n_pages, max_pages)

        for i in range(pages_to_show):
            page = pdf[i]
            bitmap = page.render(scale=1.5)   # good quality / speed balance
            pil_image = bitmap.to_pil()

            st.image(
                pil_image,
                caption=f"Page {i + 1}",
                use_container_width=True
            )

        if n_pages > max_pages:
            st.info(f"Only the first {max_pages} pages are shown for performance. Download the file to view all pages.")

    except ImportError:
        st.error("❌ Missing dependency: `pypdfium2`")
        st.markdown(
            """
            Please install it with:

            ```bash
            pip install pypdfium2
