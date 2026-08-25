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


def pdf_to_word(pdf_bytes: bytes) -> bytes:
    """
    Convert PDF bytes to Word (.docx) bytes using pdf2docx.
    Returns the .docx file as bytes.
    """
    try:
        from pdf2docx import Converter
    except ImportError:
        raise ImportError(
            "Missing package: pdf2docx\n"
            "Please install it with: pip install pdf2docx"
        )

    docx_stream = io.BytesIO()

    # Correct usage: pass raw bytes via stream=
    cv = Converter(stream=pdf_bytes)
    try:
        cv.convert(docx_stream)
    finally:
        cv.close()

    docx_stream.seek(0)
    return docx_stream.getvalue()


def preview_pdf(pdf_bytes: bytes, key: str = "pdf_preview", max_pages: int = 8):
    """
    Reliable PDF preview that works in Chrome / Edge / Firefox.
    Renders pages as images using pypdfium2 + Pillow.
    """
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
        st.info("After installing, restart the Streamlit app completely.")
        st.download_button(
            "📥 Download PDF to view instead",
            data=pdf_bytes,
            file_name="preview.pdf",
            mime="application/pdf",
            key=f"{key}_fallback"
        )
        return

    try:
        pdf = pdfium.PdfDocument(pdf_bytes)
        n_pages = len(pdf)
        st.caption(f"📄 Preview — showing {min(n_pages, max_pages)} of {n_pages} page(s)")
        for i in range(min(n_pages, max_pages)):
            page = pdf[i]
            bitmap = page.render(scale=1.5)
            pil_image = bitmap.to_pil()
            st.image(
                pil_image,
                caption=f"Page {i + 1}",
                use_container_width=True
            )
        if n_pages > max_pages:
            st.info(
                f"Only the first {max_pages} pages are shown for performance. "
                "Download the file to view all pages."
            )
    except Exception as e:
        st.error(f"Could not render PDF preview: {e}")
        st.download_button(
            "📥 Download PDF to view",
            data=pdf_bytes,
            file_name="preview.pdf",
            mime="application/pdf",
            key=f"{key}_error"
        )


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


# ======================
# Sidebar - Login
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
        st.sidebar.caption("In a real app this code would be sent by email.")

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
        st.rerun()


# ======================
# Main App
# ======================
if not st.session_state.logged_in:
    st.title("📄 PDF Tools")
    st.info("👈 Please login with your email in the sidebar to continue.")
    st.stop()

st.title("📄 PDF Tools")
st.markdown(f"Welcome, **{st.session_state.user_email}**!")

tab1, tab2, tab3, tab4 = st.tabs([
    "🔗 Combine Multiple PDFs",
    "📄 Select Pages & Download",
    "🔄 Rotate Pages",
    "📝 PDF to Word"
])


# =====================================================
# TAB 1: Combine Multiple PDFs
# =====================================================
with tab1:
    st.subheader("Combine Multiple PDFs into One")
    st.markdown("Upload several PDF files → Merge them → Download the combined file")

    uploaded_files = st.file_uploader(
        "Choose one or more PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        help="The order of selection will be the order in the final file.",
        key="multi_uploader"
    )

    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded")
        st.markdown("**Files in merge order:**")
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
                else:
                    st.error("Failed to merge PDFs.")

    if st.session_state.merged_pdf is not None:
        st.markdown("---")
        st.subheader("Download Combined PDF")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"combined_{timestamp}.pdf"
        custom_name = st.text_input(
            "Custom file name (optional)",
            value=default_name,
            key="merge_custom_name"
        )
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
        st.caption(f"File size: {len(st.session_state.merged_pdf) / 1024:.1f} KB")

        with st.expander("👁️ Preview Combined PDF", expanded=False):
            preview_pdf(st.session_state.merged_pdf, key="merged_preview")


# =====================================================
# TAB 2: Select Pages & Download
# =====================================================
with tab2:
    st.subheader("Select Pages from PDF & Download")
    st.markdown("Upload a PDF → Choose which pages you want → Download with your own file name")

    single_file = st.file_uploader(
        "Upload a PDF file",
        type=["pdf"],
        accept_multiple_files=False,
        key="single_uploader"
    )

    if single_file is not None:
        pdf_bytes = single_file.read()
        st.session_state.single_pdf_bytes = pdf_bytes
        st.session_state.single_pdf_name = single_file.name

        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            total_pages = len(reader.pages)
            st.session_state.total_pages = total_pages
        except Exception as e:
            st.error(f"Cannot read this PDF: {e}")
            st.stop()

        st.success(f"✅ Uploaded: **{single_file.name}**")
        st.info(f"This PDF has **{total_pages}** page(s)")

        with st.expander("👁️ Preview Uploaded PDF", expanded=False):
            preview_pdf(pdf_bytes, key="single_upload_preview")

        st.markdown("---")
        st.subheader("1️⃣ Select Pages")

        selection_mode = st.radio(
            "How do you want to select pages?",
            options=["Select specific pages", "Select page range", "Download all pages"],
            horizontal=True,
            key="select_mode"
        )

        selected_pages = []
        if selection_mode == "Select specific pages":
            page_options = list(range(1, total_pages + 1))
            selected_pages = st.multiselect(
                "Choose pages (you can select multiple)",
                options=page_options,
                default=[1] if total_pages >= 1 else [],
                help="Hold Ctrl (or Cmd on Mac) to select multiple pages",
                key="select_multiselect"
            )
        elif selection_mode == "Select page range":
            col1, col2 = st.columns(2)
            with col1:
                start_page = st.number_input(
                    "From page", min_value=1, max_value=total_pages, value=1, key="select_start"
                )
            with col2:
                end_page = st.number_input(
                    "To page", min_value=1, max_value=total_pages, value=total_pages, key="select_end"
                )
            if start_page > end_page:
                st.warning("Start page cannot be greater than end page.")
            else:
                selected_pages = list(range(start_page, end_page + 1))
                st.write(f"Selected pages: **{start_page} to {end_page}** ({len(selected_pages)} pages)")
        else:
            selected_pages = list(range(1, total_pages + 1))
            st.write(f"All **{total_pages}** pages will be included.")

        st.markdown("---")
        st.subheader("2️⃣ Download Selected Pages")

        if selected_pages:
            original_name = single_file.name
            if original_name.lower().endswith(".pdf"):
                original_name = original_name[:-4]

            custom_filename = st.text_input(
                "Enter your preferred file name",
                value=f"{original_name}_selected",
                key="single_custom_name",
                help="You don't need to type .pdf – it will be added automatically"
            )
            custom_filename = custom_filename.strip()
            if not custom_filename:
                custom_filename = "selected_pages"
            if not custom_filename.lower().endswith(".pdf"):
                custom_filename += ".pdf"

            try:
                with st.spinner("Preparing your PDF..."):
                    extracted_pdf = extract_pages(pdf_bytes, selected_pages)

                st.download_button(
                    label="📥 Download Selected Pages",
                    data=extracted_pdf,
                    file_name=custom_filename,
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="download_selected"
                )
                st.success(f"Ready to download **{len(selected_pages)}** page(s)")
                st.caption(f"File name: **{custom_filename}**")
                st.caption(f"File size: {len(extracted_pdf) / 1024:.1f} KB")

                with st.expander("👁️ Preview Selected Pages", expanded=False):
                    preview_pdf(extracted_pdf, key="selected_preview")
            except Exception as e:
                st.error(f"Error preparing PDF: {e}")
        else:
            st.warning("Please select at least one page.")


# =====================================================
# TAB 3: Rotate Pages
# =====================================================
with tab3:
    st.subheader("Rotate Pages in PDF")
    st.markdown("Upload a PDF → Select pages → Choose rotation angle → Download the rotated file")

    rotate_file = st.file_uploader(
        "Upload a PDF file to rotate",
        type=["pdf"],
        accept_multiple_files=False,
        key="rotate_uploader"
    )

    if rotate_file is not None:
        rotate_pdf_bytes = rotate_file.read()

        try:
            reader = PdfReader(io.BytesIO(rotate_pdf_bytes))
            total_pages = len(reader.pages)
        except Exception as e:
            st.error(f"Cannot read this PDF: {e}")
            st.stop()

        st.success(f"✅ Uploaded: **{rotate_file.name}**")
        st.info(f"This PDF has **{total_pages}** page(s)")

        with st.expander("👁️ Preview Uploaded PDF", expanded=False):
            preview_pdf(rotate_pdf_bytes, key="rotate_upload_preview")

        st.markdown("---")
        st.subheader("1️⃣ Select Pages to Rotate")

        rotate_mode = st.radio(
            "How do you want to select pages?",
            options=["Select specific pages", "Select page range", "Rotate all pages"],
            horizontal=True,
            key="rotate_mode"
        )

        pages_to_rotate = []
        if rotate_mode == "Select specific pages":
            page_options = list(range(1, total_pages + 1))
            pages_to_rotate = st.multiselect(
                "Choose pages to rotate",
                options=page_options,
                default=[1] if total_pages >= 1 else [],
                help="Hold Ctrl (or Cmd on Mac) to select multiple pages",
                key="rotate_multiselect"
            )
        elif rotate_mode == "Select page range":
            col1, col2 = st.columns(2)
            with col1:
                start_page = st.number_input(
                    "From page", min_value=1, max_value=total_pages, value=1, key="rotate_start"
                )
            with col2:
                end_page = st.number_input(
                    "To page", min_value=1, max_value=total_pages, value=total_pages, key="rotate_end"
                )
            if start_page > end_page:
                st.warning("Start page cannot be greater than end page.")
            else:
                pages_to_rotate = list(range(start_page, end_page + 1))
                st.write(f"Pages to rotate: **{start_page} to {end_page}** ({len(pages_to_rotate)} pages)")
        else:
            pages_to_rotate = list(range(1, total_pages + 1))
            st.write(f"All **{total_pages}** pages will be rotated.")

        st.markdown("---")
        st.subheader("2️⃣ Choose Rotation Angle")

        angle = st.selectbox(
            "Rotate clockwise by",
            options=[90, 180, 270],
            format_func=lambda x: f"{x}° clockwise",
            key="rotate_angle"
        )
        st.caption("90° = landscape ↔ portrait | 180° = upside down | 270° = opposite landscape")

        st.markdown("---")
        st.subheader("3️⃣ Download Rotated PDF")

        if pages_to_rotate:
            original_name = rotate_file.name
            if original_name.lower().endswith(".pdf"):
                original_name = original_name[:-4]

            custom_filename = st.text_input(
                "Enter your preferred file name",
                value=f"{original_name}_rotated_{angle}",
                key="rotate_custom_name",
                help="You don't need to type .pdf – it will be added automatically"
            )
            custom_filename = custom_filename.strip()
            if not custom_filename:
                custom_filename = f"rotated_{angle}"
            if not custom_filename.lower().endswith(".pdf"):
                custom_filename += ".pdf"

            try:
                with st.spinner("Rotating pages..."):
                    rotated_pdf = rotate_pages(rotate_pdf_bytes, pages_to_rotate, angle)

                st.download_button(
                    label="📥 Download Rotated PDF",
                    data=rotated_pdf,
                    file_name=custom_filename,
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="download_rotated"
                )
                st.success(
                    f"Ready! **{len(pages_to_rotate)}** page(s) rotated by **{angle}°** clockwise"
                )
                st.caption(f"File name: **{custom_filename}**")
                st.caption(f"File size: {len(rotated_pdf) / 1024:.1f} KB")

                with st.expander("👁️ Preview Rotated PDF", expanded=False):
                    preview_pdf(rotated_pdf, key="rotated_preview")
            except Exception as e:
                st.error(f"Error rotating PDF: {e}")
        else:
            st.warning("Please select at least one page to rotate.")


# =====================================================
# TAB 4: PDF to Word
# =====================================================
with tab4:
    st.subheader("Convert PDF to Word (.docx)")
    st.markdown("Upload a PDF → Convert it to an editable Word document → Download")

    pdf_to_word_file = st.file_uploader(
        "Upload a PDF file to convert",
        type=["pdf"],
        accept_multiple_files=False,
        key="pdf2word_uploader"
    )

    if pdf_to_word_file is not None:
        pdf_bytes = pdf_to_word_file.read()
        st.success(f"✅ Uploaded: **{pdf_to_word_file.name}**")
        st.caption(f"File size: {len(pdf_bytes) / 1024:.1f} KB")

        with st.expander("👁️ Preview PDF", expanded=False):
            preview_pdf(pdf_bytes, key="pdf2word_preview")

        st.markdown("---")

        if st.button("📝 Convert to Word", type="primary", use_container_width=True, key="convert_btn"):
            with st.spinner("Converting PDF to Word... This may take a few seconds."):
                try:
                    docx_bytes = pdf_to_word(pdf_bytes)
                    st.session_state.converted_docx = docx_bytes
                    st.success("✅ Conversion completed successfully!")
                except ImportError as e:
                    st.error(str(e))
                    st.code("pip install pdf2docx", language="bash")
                except Exception as e:
                    st.error(f"Conversion failed: {e}")
                    st.info(
                        "Tips:\n"
                        "- Scanned PDFs (image-only) usually convert poorly.\n"
                        "- Complex layouts with many tables/images may need manual cleanup."
                    )

        if st.session_state.converted_docx is not None:
            st.markdown("---")
            st.subheader("Download Word File")

            original_name = pdf_to_word_file.name
            if original_name.lower().endswith(".pdf"):
                original_name = original_name[:-4]

            custom_name = st.text_input(
                "Custom file name (optional)",
                value=f"{original_name}.docx",
                key="docx_custom_name"
            )
            if not custom_name.lower().endswith(".docx"):
                custom_name += ".docx"

            st.download_button(
                label="📥 Download Word Document",
                data=st.session_state.converted_docx,
                file_name=custom_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                type="primary",
                key="download_docx"
            )
            st.caption(f"File size: {len(st.session_state.converted_docx) / 1024:.1f} KB")


st.markdown("---")
st.caption("💡 Tip: Make sure `requirements.txt` contains: streamlit, pypdf, pdf2docx, pypdfium2, Pillow")
