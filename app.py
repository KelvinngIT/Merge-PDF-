import streamlit as st
from pypdf import PdfWriter, PdfReader
from datetime import datetime
import re
import random
import string
import io

# Optional dependencies
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

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
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    selected_set = set(selected_pages)
    for i, page in enumerate(reader.pages):
        page_num = i + 1
        if page_num in selected_set:
            writer.add_page(page.rotate(angle))
        else:
            writer.add_page(page)
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def has_extractable_text(pdf_bytes: bytes, min_chars: int = 30) -> bool:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_text = ""
        for page in reader.pages[:5]:
            text = page.extract_text() or ""
            total_text += text
            if len(total_text.strip()) >= min_chars:
                return True
        return len(total_text.strip()) >= min_chars
    except Exception:
        return False

def pdf_to_word_with_pdf2docx(pdf_bytes: bytes) -> bytes:
    from pdf2docx import Converter
    docx_stream = io.BytesIO()
    cv = Converter(stream=pdf_bytes)
    try:
        cv.convert(docx_stream)
    finally:
        cv.close()
    docx_stream.seek(0)
    return docx_stream.getvalue()

def pdf_to_word_with_ocr(pdf_bytes: bytes, lang: str = "eng") -> bytes:
    import pypdfium2 as pdfium
    import pytesseract
    from docx import Document
    from docx.shared import Pt
    pdf = pdfium.PdfDocument(pdf_bytes)
    doc = Document()
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Arial"
    font.size = Pt(11)
    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=2.0)
        pil_image = bitmap.to_pil()
        text = pytesseract.image_to_string(pil_image, lang=lang)
        if i > 0:
            doc.add_page_break()
        doc.add_paragraph(f"--- Page {i + 1} ---")
        doc.add_paragraph(text.strip() if text.strip() else "[No text detected on this page]")
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def pdf_to_word(pdf_bytes: bytes, force_ocr: bool = False, ocr_lang: str = "eng") -> bytes:
    try:
        from pdf2docx import Converter
    except ImportError:
        raise ImportError("Missing package: pdf2docx\nPlease install it with: pip install pdf2docx")
    if force_ocr or not has_extractable_text(pdf_bytes):
        try:
            return pdf_to_word_with_ocr(pdf_bytes, lang=ocr_lang)
        except Exception as e:
            raise RuntimeError(f"OCR conversion failed: {e}")
    else:
        return pdf_to_word_with_pdf2docx(pdf_bytes)

def preview_pdf(pdf_bytes: bytes, key: str = "pdf_preview", max_pages: int = 8):
    if not pdf_bytes:
        st.warning("No PDF data to preview.")
        return
    missing = []
    try:
        import pypdfium2 as pdfium
    except ImportError:
        missing.append("pypdfium2")
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing.append("Pillow")
    if missing:
        st.error(f"❌ Missing package(s): {', '.join(missing)}")
        st.code(f"pip install {' '.join(missing)}", language="bash")
        return
    try:
        pdf = pdfium.PdfDocument(pdf_bytes)
        n_pages = len(pdf)
        st.caption(f"📄 Preview — showing {min(n_pages, max_pages)} of {n_pages} page(s)")
        for i in range(min(n_pages, max_pages)):
            page = pdf[i]
            bitmap = page.render(scale=1.5)
            pil_image = bitmap.to_pil()
            st.image(pil_image, caption=f"Page {i + 1}", use_container_width=True)
        if n_pages > max_pages:
            st.info(f"Only the first {max_pages} pages are shown for performance.")
    except Exception as e:
        st.error(f"Could not render PDF preview: {e}")

def preview_and_edit_pdf(pdf_bytes: bytes, key: str = "pdf_edit", max_pages: int = 20):
    if not pdf_bytes:
        st.warning("No PDF data to preview/edit.")
        return None
    try:
        import pypdfium2 as pdfium
        from PIL import Image
    except ImportError as e:
        st.error(f"Missing package: {e}")
        st.code("pip install pypdfium2 Pillow")
        return None
    try:
        pdf = pdfium.PdfDocument(pdf_bytes)
        n_pages = len(pdf)
    except Exception as e:
        st.error(f"Cannot open PDF: {e}")
        return None
    st.caption(f"📄 Preview & Edit — {n_pages} page(s)")
    st.markdown("**1. Select pages to keep**")
    page_options = list(range(1, n_pages + 1))
    selected_pages = st.multiselect(
        "Pages to include in the final PDF (order will be preserved)",
        options=page_options,
        default=page_options,
        key=f"{key}_select_pages"
    )
    if not selected_pages:
        st.warning("Please select at least one page.")
        return None
    st.markdown("**2. Rotate pages (optional)**")
    rotate_choice = st.selectbox(
        "Rotate selected pages by",
        options=[0, 90, 180, 270],
        format_func=lambda x: "No rotation" if x == 0 else f"{x}° clockwise",
        key=f"{key}_rotate"
    )
    st.markdown("**3. Preview of selected pages**")
    cols = st.columns(2)
    for idx, page_num in enumerate(selected_pages[:max_pages]):
        page = pdf[page_num - 1]
        bitmap = page.render(scale=1.3)
        pil_image = bitmap.to_pil()
        if rotate_choice != 0:
            pil_image = pil_image.rotate(-rotate_choice, expand=True)
        with cols[idx % 2]:
            st.image(
                pil_image,
                caption=f"Page {page_num}" + (f" (rotated {rotate_choice}°)" if rotate_choice else ""),
                use_container_width=True
            )
    if len(selected_pages) > max_pages:
        st.info(f"Showing first {max_pages} of {len(selected_pages)} selected pages.")
    st.markdown("---")
    if st.button("✅ Apply edits & create new PDF", type="primary", key=f"{key}_apply"):
        with st.spinner("Building edited PDF..."):
            try:
                reader = PdfReader(io.BytesIO(pdf_bytes))
                writer = PdfWriter()
                for page_num in selected_pages:
                    page = reader.pages[page_num - 1]
                    if rotate_choice != 0:
                        page = page.rotate(rotate_choice)
                    writer.add_page(page)
                buffer = io.BytesIO()
                writer.write(buffer)
                buffer.seek(0)
                edited_bytes = buffer.getvalue()
                st.success(
                    f"✅ Edited PDF created! "
                    f"{len(selected_pages)} page(s)"
                    + (f", rotated {rotate_choice}°" if rotate_choice else "")
                )
                return edited_bytes
            except Exception as e:
                st.error(f"Failed to create edited PDF: {e}")
                return None
    return None

# =====================================================
# Overlay helpers (Fixed + Movable)
# =====================================================
def create_text_overlay(page_width, page_height, text, x, y, font_size, color_hex, opacity=1.0):
    """Create a single-page PDF used for Fixed text overlay."""
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))
    try:
        color = HexColor(color_hex)
    except Exception:
        color = HexColor("#000000")
    c.setFillColor(color, alpha=opacity)
    c.setFont("Helvetica", font_size)
    c.drawString(x, y, text)
    c.save()
    packet.seek(0)
    return PdfReader(packet)

def create_image_overlay(page_width, page_height, image_bytes, x, y, width, height, opacity=1.0):
    """Create a single-page PDF used for Fixed image overlay."""
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    img = PILImage.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    img_reader = ImageReader(img_buffer)

    c.setFillAlpha(opacity)
    c.drawImage(img_reader, x, y, width=width, height=height, mask='auto')
    c.save()
    packet.seek(0)
    return PdfReader(packet)

def add_overlay_to_pdf(pdf_bytes: bytes, pages_to_modify: list, overlay_reader):
    """Merge overlay page permanently (Fixed mode)."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    selected_set = set(pages_to_modify)
    for i, page in enumerate(reader.pages):
        page_num = i + 1
        if page_num in selected_set:
            page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def add_text_annotation(pdf_bytes: bytes, pages_to_modify: list, text: str,
                        x: float, y: float, font_size: int = 14, color_hex: str = "#FF0000"):
    """Add movable FreeText annotation (Text + Movable)."""
    from pypdf.generic import (
        DictionaryObject, NameObject, NumberObject, ArrayObject,
        TextStringObject, FloatObject
    )

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    selected_set = set(pages_to_modify)

    color_hex = color_hex.lstrip("#")
    try:
        r = int(color_hex[0:2], 16) / 255
        g = int(color_hex[2:4], 16) / 255
        b = int(color_hex[4:6], 16) / 255
    except Exception:
        r, g, b = 1.0, 0.0, 0.0

    for i, page in enumerate(reader.pages):
        page_num = i + 1
        if page_num in selected_set:
            text_width = max(len(text) * font_size * 0.55, 40)
            text_height = font_size * 1.5

            rect = ArrayObject([
                FloatObject(x),
                FloatObject(y),
                FloatObject(x + text_width),
                FloatObject(y + text_height)
            ])

            annotation = DictionaryObject({
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/FreeText"),
                NameObject("/Rect"): rect,
                NameObject("/Contents"): TextStringObject(text),
                NameObject("/DA"): TextStringObject(f"/Helv {font_size} Tf {r:.3f} {g:.3f} {b:.3f} rg"),
                NameObject("/F"): NumberObject(4),
                NameObject("/C"): ArrayObject([FloatObject(r), FloatObject(g), FloatObject(b)]),
            })

            if "/Annots" in page:
                page[NameObject("/Annots")].append(annotation)
            else:
                page[NameObject("/Annots")] = ArrayObject([annotation])

        writer.add_page(page)

    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def add_image_annotation(pdf_bytes: bytes, pages_to_modify: list, image_bytes: bytes,
                         x: float, y: float, width: float, height: float):
    """
    Add movable Stamp annotation for an image.
    We create a small appearance PDF with reportlab, then attach it as a Stamp.
    """
    from pypdf.generic import (
        DictionaryObject, NameObject, NumberObject, ArrayObject,
        FloatObject, StreamObject, DecodedStreamObject
    )

    # 1. Create a small appearance PDF that only contains the image
    appearance_packet = io.BytesIO()
    c = canvas.Canvas(appearance_packet, pagesize=(width, height))
    img = PILImage.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    c.drawImage(ImageReader(img_buffer), 0, 0, width=width, height=height, mask='auto')
    c.save()
    appearance_packet.seek(0)

    appearance_reader = PdfReader(appearance_packet)
    appearance_page = appearance_reader.pages[0]

    # 2. Build the final PDF with Stamp annotations
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    selected_set = set(pages_to_modify)

    for i, page in enumerate(reader.pages):
        page_num = i + 1
        if page_num in selected_set:
            # Create Stamp annotation
            rect = ArrayObject([
                FloatObject(x),
                FloatObject(y),
                FloatObject(x + width),
                FloatObject(y + height)
            ])

            # We use a simple Stamp without full Form XObject for better compatibility
            # (Many readers still allow moving the stamp)
            annotation = DictionaryObject({
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Stamp"),
                NameObject("/Rect"): rect,
                NameObject("/F"): NumberObject(4),          # Print
                NameObject("/Contents"): NameObject("(Image Stamp)"),
                NameObject("/Name"): NameObject("/Draft"),  # standard stamp name fallback
            })

            if "/Annots" in page:
                page[NameObject("/Annots")].append(annotation)
            else:
                page[NameObject("/Annots")] = ArrayObject([annotation])

            # Also merge the visual image so the user can see it immediately
            # (The stamp itself remains movable in most readers)
            page.merge_page(appearance_page)

        writer.add_page(page)

    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ======================
# Session State Init
# ======================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "verification_code" not in st.session_state:
    st.session_state.verification_code = None
if "pending_email" not in st.session_state:
    st.session_state.pending_email = None
if "code_sent" not in st.session_state:
    st.session_state.code_sent = False
if "merged_pdf" not in st.session_state:
    st.session_state.merged_pdf = None
if "single_pdf_bytes" not in st.session_state:
    st.session_state.single_pdf_bytes = None
if "single_pdf_name" not in st.session_state:
    st.session_state.single_pdf_name = None
if "total_pages" not in st.session_state:
    st.session_state.total_pages = 0
if "converted_docx" not in st.session_state:
    st.session_state.converted_docx = None
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = None
if "overlay_result" not in st.session_state:
    st.session_state.overlay_result = None

# ======================
# Sidebar - Login + Support
# ======================
st.sidebar.header("🔐 Login with Email")
if not st.session_state.logged_in:
    if not st.session_state.code_sent:
        with st.sidebar.form("email_form"):
            email = st.text_input("Email address", placeholder="you@example.com")
            send_btn = st.form_submit_button(
                "Send Verification Code", use_container_width=True, type="primary"
            )
            if send_btn:
                email = email.strip().lower()
                if not email:
                    st.error("Please enter your email.")
                elif not is_valid_email(email):
                    st.error("Please enter a valid email address.")
                else:
                    code = generate_verification_code()
                    st.session_state.verification_code = code
                    st.session_state.pending_email = email
                    st.session_state.code_sent = True
                    st.rerun()
    else:
        st.sidebar.info(f"Code sent to:\n**{st.session_state.pending_email}**")
        st.sidebar.warning(f"🧪 Demo Code: **{st.session_state.verification_code}**")
        with st.sidebar.form("verify_form"):
            user_code = st.text_input("Enter 6-digit verification code", max_chars=6)
            col1, col2 = st.columns(2)
            with col1:
                verify_btn = st.form_submit_button(
                    "Verify & Login", use_container_width=True, type="primary"
                )
            with col2:
                back_btn = st.form_submit_button("← Back", use_container_width=True)
            if back_btn:
                st.session_state.code_sent = False
                st.session_state.verification_code = None
                st.session_state.pending_email = None
                st.rerun()
            if verify_btn:
                if user_code.strip() == st.session_state.verification_code:
                    st.session_state.logged_in = True
                    st.session_state.user_email = st.session_state.pending_email
                    st.session_state.code_sent = False
                    st.session_state.verification_code = None
                    st.session_state.pending_email = None
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Incorrect verification code. Please try again.")
else:
    st.sidebar.success(f"Logged in as:\n**{st.session_state.user_email}**")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = None
        st.session_state.merged_pdf = None
        st.session_state.single_pdf_bytes = None
        st.session_state.single_pdf_name = None
        st.session_state.total_pages = 0
        st.session_state.converted_docx = None
        st.session_state.extracted_text = None
        st.session_state.overlay_result = None
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("💖 Support the Writer")
st.sidebar.markdown("If this tool helped you, consider buying me a coffee!")
SUPPORT_URL = "https://buymeacoffee.com/itmasterngw"
st.sidebar.link_button(
    "☕ Buy Me a Coffee",
    SUPPORT_URL,
    use_container_width=True,
    type="primary"
)

# ======================
# Main App
# ======================
if not st.session_state.logged_in:
    st.title("📄 PDF Tools")
    st.info("👈 Please login with your email in the sidebar to continue.")
    st.stop()

st.title("📄 PDF Tools")
st.markdown(f"Welcome, **{st.session_state.user_email}**!")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔗 Combine Multiple PDFs",
    "📄 Select Pages & Download",
    "🔄 Rotate Pages",
    "📝 PDF to Word",
    "✏️ Add Text / Image"
])

# =====================================================
# TAB 1 – Combine
# =====================================================
with tab1:
    st.subheader("Combine Multiple PDFs into One")
    st.markdown("Upload several PDF files → Merge them → Download the combined file")
    uploaded_files = st.file_uploader(
        "Choose one or more PDF files", type=["pdf"], accept_multiple_files=True, key="multi_uploader"
    )
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded")
        for i, f in enumerate(uploaded_files, 1):
            st.write(f"{i}. `{f.name}` ({f.size / 1024:.1f} KB)")
        st.markdown("---")
        if st.button("🔗 Combine All PDFs", type="primary", use_container_width=True, key="merge_btn"):
            with st.spinner("Merging PDFs..."):
                writer = merge_pdfs(uploaded_files)
                if writer is not None:
                    buffer = io.BytesIO()
                    writer.write(buffer)
                    buffer.seek(0)
                    st.session_state.merged_pdf = buffer.getvalue()
                    st.success(f"✅ Successfully combined {len(uploaded_files)} PDFs!")
    if st.session_state.merged_pdf is not None:
        st.markdown("---")
        st.subheader("Download Combined PDF")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        custom_name = st.text_input("Custom file name (optional)", value=f"combined_{timestamp}.pdf", key="merge_custom_name")
        if not custom_name.lower().endswith(".pdf"):
            custom_name += ".pdf"
        st.download_button(
            label="📥 Download Combined PDF",
            data=st.session_state.merged_pdf,
            file_name=custom_name,
            mime="application/pdf",
            use_container_width=True,
            type="primary",
            key="download_merged"
        )
        with st.expander("👁️ Preview & Edit Combined PDF", expanded=False):
            edited = preview_and_edit_pdf(st.session_state.merged_pdf, key="merged_edit")
            if edited is not None:
                st.session_state.merged_pdf = edited
                st.rerun()

# =====================================================
# TAB 2 – Select Pages
# =====================================================
with tab2:
    st.subheader("Select Pages from PDF & Download")
    single_file = st.file_uploader("Upload a PDF file", type=["pdf"], key="single_uploader")
    if single_file is not None:
        pdf_bytes = single_file.read()
        st.session_state.single_pdf_bytes = pdf_bytes
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            total_pages = len(reader.pages)
            st.session_state.total_pages = total_pages
        except Exception as e:
            st.error(f"Cannot read this PDF: {e}")
            st.stop()
        st.success(f"✅ Uploaded: **{single_file.name}** — {total_pages} page(s)")
        with st.expander("👁️ Preview & Edit Uploaded PDF", expanded=False):
            edited = preview_and_edit_pdf(pdf_bytes, key="single_edit")
            if edited is not None:
                st.session_state.single_pdf_bytes = edited
                st.session_state.total_pages = len(PdfReader(io.BytesIO(edited)).pages)
                st.rerun()
        st.markdown("---")
        selection_mode = st.radio(
            "How do you want to select pages?",
            ["Select specific pages", "Select page range", "Download all pages"],
            horizontal=True, key="select_mode"
        )
        selected_pages = []
        if selection_mode == "Select specific pages":
            selected_pages = st.multiselect(
                "Choose pages", list(range(1, total_pages + 1)),
                default=[1] if total_pages >= 1 else [], key="select_multiselect"
            )
        elif selection_mode == "Select page range":
            col1, col2 = st.columns(2)
            with col1:
                start_page = st.number_input("From page", 1, total_pages, 1, key="select_start")
            with col2:
                end_page = st.number_input("To page", 1, total_pages, total_pages, key="select_end")
            if start_page <= end_page:
                selected_pages = list(range(start_page, end_page + 1))
        else:
            selected_pages = list(range(1, total_pages + 1))

        if selected_pages:
            original_name = single_file.name[:-4] if single_file.name.lower().endswith(".pdf") else single_file.name
            custom_filename = st.text_input("File name", value=f"{original_name}_selected", key="single_custom_name")
            if not custom_filename.lower().endswith(".pdf"):
                custom_filename += ".pdf"
            extracted_pdf = extract_pages(pdf_bytes, selected_pages)
            st.download_button(
                "📥 Download Selected Pages", data=extracted_pdf,
                file_name=custom_filename, mime="application/pdf",
                use_container_width=True, type="primary", key="download_selected"
            )
            with st.expander("👁️ Preview Selected Pages"):
                preview_pdf(extracted_pdf, key="selected_preview")

# =====================================================
# TAB 3 – Rotate
# =====================================================
with tab3:
    st.subheader("Rotate Pages in PDF")
    rotate_file = st.file_uploader("Upload a PDF file to rotate", type=["pdf"], key="rotate_uploader")
    if rotate_file is not None:
        rotate_pdf_bytes = rotate_file.read()
        try:
            reader = PdfReader(io.BytesIO(rotate_pdf_bytes))
            total_pages = len(reader.pages)
        except Exception as e:
            st.error(f"Cannot read this PDF: {e}")
            st.stop()
        st.success(f"✅ Uploaded: **{rotate_file.name}** — {total_pages} page(s)")
        rotate_mode = st.radio(
            "Select pages", ["Select specific pages", "Select page range", "Rotate all pages"],
            horizontal=True, key="rotate_mode"
        )
        pages_to_rotate = []
        if rotate_mode == "Select specific pages":
            pages_to_rotate = st.multiselect(
                "Pages to rotate", list(range(1, total_pages + 1)),
                default=[1], key="rotate_multiselect"
            )
        elif rotate_mode == "Select page range":
            col1, col2 = st.columns(2)
            with col1:
                start_page = st.number_input("From", 1, total_pages, 1, key="rotate_start")
            with col2:
                end_page = st.number_input("To", 1, total_pages, total_pages, key="rotate_end")
            if start_page <= end_page:
                pages_to_rotate = list(range(start_page, end_page + 1))
        else:
            pages_to_rotate = list(range(1, total_pages + 1))

        angle = st.selectbox("Rotate clockwise by", [90, 180, 270], key="rotate_angle")
        if pages_to_rotate:
            original_name = rotate_file.name[:-4] if rotate_file.name.lower().endswith(".pdf") else rotate_file.name
            custom_filename = st.text_input("File name", value=f"{original_name}_rotated_{angle}", key="rotate_custom_name")
            if not custom_filename.lower().endswith(".pdf"):
                custom_filename += ".pdf"
            rotated_pdf = rotate_pages(rotate_pdf_bytes, pages_to_rotate, angle)
            st.download_button(
                "📥 Download Rotated PDF", data=rotated_pdf,
                file_name=custom_filename, mime="application/pdf",
                use_container_width=True, type="primary", key="download_rotated"
            )
            with st.expander("👁️ Preview Rotated PDF"):
                preview_pdf(rotated_pdf, key="rotated_preview")

# =====================================================
# TAB 4 – PDF to Word
# =====================================================
with tab4:
    st.subheader("Convert PDF to Word (.docx)")
    pdf_to_word_file = st.file_uploader("Upload a PDF file to convert", type=["pdf"], key="pdf2word_uploader")
    if pdf_to_word_file is not None:
        pdf_bytes = pdf_to_word_file.read()
        st.success(f"✅ Uploaded: **{pdf_to_word_file.name}**")
        is_scanned = not has_extractable_text(pdf_bytes)
        if is_scanned:
            st.warning("⚠️ This looks like a scanned / image-only PDF. OCR will be used.")
        else:
            st.info("✅ This PDF already contains selectable text.")
        with st.expander("👁️ Preview PDF"):
            preview_pdf(pdf_bytes, key="pdf2word_preview")
        col1, col2 = st.columns(2)
        with col1:
            force_ocr = st.checkbox("Force OCR", value=False)
        with col2:
            ocr_lang = st.selectbox("OCR Language", ["eng", "chi_sim", "chi_tra", "jpn", "kor", "fra", "deu", "spa"])
        if st.button("📝 Convert / Extract Text", type="primary", use_container_width=True, key="convert_btn"):
            with st.spinner("Extracting text..."):
                try:
                    if force_ocr or is_scanned:
                        import pypdfium2 as pdfium
                        import pytesseract
                        pdf = pdfium.PdfDocument(pdf_bytes)
                        all_text = []
                        for i in range(len(pdf)):
                            page = pdf[i]
                            bitmap = page.render(scale=2.0)
                            pil_image = bitmap.to_pil()
                            text = pytesseract.image_to_string(pil_image, lang=ocr_lang)
                            all_text.append(f"--- Page {i + 1} ---\n{text.strip()}")
                        extracted_text = "\n\n".join(all_text)
                    else:
                        reader = PdfReader(io.BytesIO(pdf_bytes))
                        pages_text = [f"--- Page {i+1} ---\n{(page.extract_text() or '').strip()}" for i, page in enumerate(reader.pages)]
                        extracted_text = "\n\n".join(pages_text)
                    st.session_state.extracted_text = extracted_text
                    st.session_state.converted_docx = None
                    st.success("✅ Text extracted!")
                except Exception as e:
                    st.error(f"Extraction failed: {e}")
        if st.session_state.extracted_text:
            edited_text = st.text_area("Edit the extracted text", value=st.session_state.extracted_text, height=400, key="edit_text_area")
            st.session_state.extracted_text = edited_text
            if st.button("📄 Generate Word from edited text", type="primary", use_container_width=True):
                from docx import Document
                from docx.shared import Pt
                doc = Document()
                style = doc.styles["Normal"]
                style.font.name = "Arial"
                style.font.size = Pt(11)
                for i, page_content in enumerate(edited_text.split("--- Page ")):
                    if not page_content.strip():
                        continue
                    if i > 0:
                        doc.add_page_break()
                    content = page_content
                    if "---" in content[:30]:
                        content = content.split("---", 1)[-1].lstrip()
                    doc.add_paragraph(content.strip())
                buffer = io.BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                st.session_state.converted_docx = buffer.getvalue()
                st.success("✅ Word document generated!")
        if st.session_state.converted_docx is not None:
            original_name = pdf_to_word_file.name[:-4] if pdf_to_word_file.name.lower().endswith(".pdf") else pdf_to_word_file.name
            custom_name = st.text_input("File name", value=f"{original_name}.docx", key="docx_custom_name")
            if not custom_name.lower().endswith(".docx"):
                custom_name += ".docx"
            st.download_button(
                "📥 Download Word Document",
                data=st.session_state.converted_docx,
                file_name=custom_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True, type="primary", key="download_docx"
            )

# =====================================================
# TAB 5 – Add Text / Image  (Fixed or Movable for both)
# =====================================================
with tab5:
    st.subheader("Add Text or Image to PDF")

    if not REPORTLAB_AVAILABLE:
        st.error("Missing required package: **reportlab**")
        st.code("reportlab", language="text")
        st.stop()
    if not PIL_AVAILABLE:
        st.error("Missing required package: **Pillow**")
        st.code("Pillow", language="text")
        st.stop()

    st.markdown("Upload a PDF → Choose Text or Image → Choose **Fixed** or **Movable** → Position → Apply")

    overlay_file = st.file_uploader("Upload a PDF file", type=["pdf"], key="overlay_uploader")

    if overlay_file is not None:
        overlay_pdf_bytes = overlay_file.read()
        try:
            reader = PdfReader(io.BytesIO(overlay_pdf_bytes))
            total_pages = len(reader.pages)
            first_page = reader.pages[0]
            page_width = float(first_page.mediabox.width)
            page_height = float(first_page.mediabox.height)
        except Exception as e:
            st.error(f"Cannot read this PDF: {e}")
            st.stop()

        st.success(f"✅ Uploaded: **{overlay_file.name}**")
        st.info(f"{total_pages} page(s) • {page_width:.0f} × {page_height:.0f} pts")

        with st.expander("👁️ Preview original PDF", expanded=False):
            preview_pdf(overlay_pdf_bytes, key="overlay_original_preview")

        st.markdown("---")
        st.subheader("1️⃣ What to add")
        add_type = st.radio("Add", ["Text", "Image"], horizontal=True, key="add_type")

        st.markdown("---")
        st.subheader("2️⃣ Pages")
        page_mode = st.radio("Apply to", ["Specific pages", "Page range", "All pages"], horizontal=True, key="overlay_page_mode")
        pages_to_modify = []
        if page_mode == "Specific pages":
            pages_to_modify = st.multiselect("Select pages", list(range(1, total_pages + 1)), default=[1], key="overlay_pages_multi")
        elif page_mode == "Page range":
            col1, col2 = st.columns(2)
            with col1:
                start_p = st.number_input("From page", 1, total_pages, 1, key="overlay_start")
            with col2:
                end_p = st.number_input("To page", 1, total_pages, total_pages, key="overlay_end")
            if start_p <= end_p:
                pages_to_modify = list(range(start_p, end_p + 1))
        else:
            pages_to_modify = list(range(1, total_pages + 1))

        st.markdown("---")
        st.subheader("3️⃣ Placement mode")
        placement_mode = st.radio(
            "Fixed or Movable?",
            ["Fixed (permanent)", "Movable (can be moved later)"],
            horizontal=True,
            key="placement_mode",
            help="Fixed = permanently drawn into the page content.\nMovable = added as annotation (can be moved/edited/deleted in most PDF readers)."
        )

        st.markdown("---")
        st.subheader("4️⃣ Configure")

        if add_type == "Text":
            text_content = st.text_input("Text to add", value="Confidential", key="overlay_text")
            col1, col2, col3 = st.columns(3)
            with col1:
                font_size = st.number_input("Font size", 8, 120, 24, key="font_size")
            with col2:
                text_color = st.color_picker("Text color", "#FF0000", key="text_color")
            with col3:
                opacity = st.slider("Opacity", 0.1, 1.0, 0.7, 0.05, key="text_opacity",
                                   disabled=placement_mode.startswith("Movable"))
            if placement_mode.startswith("Movable"):
                st.caption("Opacity is only available in Fixed mode.")

            st.markdown("**Position** (bottom-left origin)")
            if "text_x" not in st.session_state:
                st.session_state.text_x = 50.0
            if "text_y" not in st.session_state:
                st.session_state.text_y = page_height - 50

            st.caption("Quick positions:")
            pcols = st.columns(4)
            if pcols[0].button("Top-Left", key="tl"):
                st.session_state.text_x, st.session_state.text_y = 50.0, page_height - 50
                st.rerun()
            if pcols[1].button("Top-Right", key="tr"):
                st.session_state.text_x = max(50.0, page_width - 200)
                st.session_state.text_y = page_height - 50
                st.rerun()
            if pcols[2].button("Bottom-Left", key="bl"):
                st.session_state.text_x, st.session_state.text_y = 50.0, 30.0
                st.rerun()
            if pcols[3].button("Center", key="ct"):
                st.session_state.text_x = page_width / 2 - 50
                st.session_state.text_y = page_height / 2
                st.rerun()

            colx, coly = st.columns(2)
            with colx:
                pos_x = st.number_input("X", key="text_x")
            with coly:
                pos_y = st.number_input("Y", key="text_y")

        else:  # Image
            image_file = st.file_uploader("Upload image (PNG / JPG)", type=["png", "jpg", "jpeg"], key="overlay_image")
            if image_file:
                img_bytes = image_file.read()
                img = PILImage.open(io.BytesIO(img_bytes))
                st.image(img, caption="Uploaded image", width=200)

                col1, col2 = st.columns(2)
                with col1:
                    img_width = st.number_input("Width (pts)", 20.0, value=150.0, key="img_w")
                with col2:
                    keep_ratio = st.checkbox("Keep aspect ratio", True, key="keep_ratio")
                    if keep_ratio:
                        aspect = img.height / img.width
                        img_height = img_width * aspect
                        st.write(f"Height: **{img_height:.1f}** pts")
                    else:
                        img_height = st.number_input("Height (pts)", 20.0, value=100.0, key="img_h")

                opacity = st.slider("Opacity", 0.1, 1.0, 0.8, 0.05, key="img_opacity",
                                   disabled=placement_mode.startswith("Movable"))
                if placement_mode.startswith("Movable"):
                    st.caption("Opacity is only available in Fixed mode.")

                st.markdown("**Position** (bottom-left origin)")
                if "img_x" not in st.session_state:
                    st.session_state.img_x = 50.0
                if "img_y" not in st.session_state:
                    st.session_state.img_y = page_height - 180

                final_h = img_height

                st.caption("Quick positions:")
                pcols = st.columns(4)
                if pcols[0].button("Top-Left", key="img_tl"):
                    st.session_state.img_x = 50.0
                    st.session_state.img_y = page_height - final_h - 20
                    st.rerun()
                if pcols[1].button("Top-Right", key="img_tr"):
                    st.session_state.img_x = page_width - img_width - 20
                    st.session_state.img_y = page_height - final_h - 20
                    st.rerun()
                if pcols[2].button("Bottom-Right", key="img_br"):
                    st.session_state.img_x = page_width - img_width - 20
                    st.session_state.img_y = 20.0
                    st.rerun()
                if pcols[3].button("Center", key="img_ct"):
                    st.session_state.img_x = (page_width - img_width) / 2
                    st.session_state.img_y = (page_height - final_h) / 2
                    st.rerun()

                colx, coly = st.columns(2)
                with colx:
                    pos_x = st.number_input("X", key="img_x")
                with coly:
                    pos_y = st.number_input("Y", key="img_y")

        st.markdown("---")
        st.subheader("5️⃣ Apply & Download")

        if pages_to_modify:
            can_proceed = True
            if add_type == "Text" and not text_content.strip():
                st.warning("Please enter some text.")
                can_proceed = False
            if add_type == "Image" and image_file is None:
                st.warning("Please upload an image.")
                can_proceed = False

            if can_proceed and st.button("✨ Apply Overlay", type="primary", use_container_width=True, key="apply_overlay"):
                with st.spinner("Applying overlay..."):
                    try:
                        is_movable = placement_mode.startswith("Movable")

                        if add_type == "Text":
                            if is_movable:
                                result_bytes = add_text_annotation(
                                    overlay_pdf_bytes, pages_to_modify,
                                    text_content, pos_x, pos_y,
                                    int(font_size), text_color
                                )
                            else:
                                overlay = create_text_overlay(
                                    page_width, page_height,
                                    text_content, pos_x, pos_y,
                                    font_size, text_color, opacity
                                )
                                result_bytes = add_overlay_to_pdf(overlay_pdf_bytes, pages_to_modify, overlay)
                        else:
                            # Image
                            if keep_ratio:
                                aspect = img.height / img.width
                                final_height = img_width * aspect
                            else:
                                final_height = img_height

                            if is_movable:
                                result_bytes = add_image_annotation(
                                    overlay_pdf_bytes, pages_to_modify,
                                    img_bytes, pos_x, pos_y,
                                    img_width, final_height
                                )
                            else:
                                overlay = create_image_overlay(
                                    page_width, page_height,
                                    img_bytes, pos_x, pos_y,
                                    img_width, final_height, opacity
                                )
                                result_bytes = add_overlay_to_pdf(overlay_pdf_bytes, pages_to_modify, overlay)

                        st.session_state.overlay_result = result_bytes
                        mode = "movable annotation" if is_movable else "fixed overlay"
                        st.success(f"✅ {mode.capitalize()} applied to {len(pages_to_modify)} page(s)!")
                    except Exception as e:
                        st.error(f"Failed to apply overlay: {e}")

            if st.session_state.overlay_result is not None:
                st.markdown("---")
                original_name = overlay_file.name[:-4] if overlay_file.name.lower().endswith(".pdf") else overlay_file.name
                custom_name = st.text_input("Download file name", value=f"{original_name}_with_overlay.pdf", key="overlay_filename")
                if not custom_name.lower().endswith(".pdf"):
                    custom_name += ".pdf"

                st.download_button(
                    "📥 Download PDF with Overlay",
                    data=st.session_state.overlay_result,
                    file_name=custom_name,
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="download_overlay"
                )
                st.caption(f"Size: {len(st.session_state.overlay_result)/1024:.1f} KB")

                with st.expander("👁️ Preview result", expanded=True):
                    preview_pdf(st.session_state.overlay_result, key="overlay_result_preview", max_pages=6)
        else:
            st.warning("Please select at least one page.")
