import streamlit as st
from pypdf import PdfWriter, PdfReader
from datetime import datetime
import re
import random
import string
import io
import base64

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
    """Merge multiple uploaded PDF files into one PdfWriter object"""
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

def display_pdf(file_bytes):
    """Display PDF in the browser using base64"""
    base64_pdf = base64.b64encode(file_bytes).decode("utf-8")
    pdf_display = f"""
        <iframe 
            src="data:application/pdf;base64,{base64_pdf}" 
            width="100%" 
            height="800px" 
            type="application/pdf">
        </iframe>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

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

# ======================
# Sidebar - Login
# ======================
st.sidebar.header("🔐 Login with Email")

if not st.session_state.logged_in:
    if not st.session_state.code_sent:
        with st.sidebar.form("email_form"):
            email = st.text_input("Email address", placeholder="you@example.com")
            send_btn = st.form_submit_button("Send Verification Code", use_container_width=True, type="primary")
            
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
                verify_btn = st.form_submit_button("Verify & Login", use_container_width=True, type="primary")
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
        st.rerun()

# ======================
# Main App
# ======================
if not st.session_state.logged_in:
    st.title("📄 PDF Tools")
    st.info("👈 Please login with your email in the sidebar to continue.")
    st.stop()

# ----- Logged-in content -----
st.title("📄 PDF Tools")
st.markdown(f"Welcome, **{st.session_state.user_email}**!")

# Create two tabs
tab1, tab2 = st.tabs(["🔗 Combine Multiple PDFs", "👁️ View & Download Single PDF"])

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
        
        # Ensure it ends with .pdf
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

# =====================================================
# TAB 2: View & Download Single PDF
# =====================================================
with tab2:
    st.subheader("View PDF & Download with Custom Name")
    st.markdown("Upload a PDF → Preview it on screen → Download it with your own file name")

    single_file = st.file_uploader(
        "Upload a PDF file",
        type=["pdf"],
        accept_multiple_files=False,
        key="single_uploader"
    )

    if single_file is not None:
        # Read the file into memory
        pdf_bytes = single_file.read()
        st.session_state.single_pdf_bytes = pdf_bytes
        st.session_state.single_pdf_name = single_file.name

        st.success(f"✅ Uploaded: **{single_file.name}** ({len(pdf_bytes)/1024:.1f} KB)")

        # Show number of pages
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            st.info(f"This PDF has **{len(reader.pages)}** page(s)")
        except:
            st.warning("Could not read page count.")

        st.markdown("---")
        st.subheader("📄 PDF Preview")

        # Display the PDF
        display_pdf(pdf_bytes)

        st.markdown("---")
        st.subheader("Download with Custom Name")

        # Suggest a default name
        original_name = single_file.name
        if original_name.lower().endswith(".pdf"):
            original_name = original_name[:-4]

        custom_filename = st.text_input(
            "Enter your preferred file name",
            value=original_name,
            key="single_custom_name",
            help="You don't need to type .pdf – it will be added automatically"
        )

        # Clean the filename
        custom_filename = custom_filename.strip()
        if not custom_filename:
            custom_filename = "downloaded_file"
        
        if not custom_filename.lower().endswith(".pdf"):
            custom_filename += ".pdf"

        st.download_button(
            label="📥 Download PDF with Custom Name",
            data=pdf_bytes,
            file_name=custom_filename,
            mime="application/pdf",
            use_container_width=True,
            type="primary",
            key="download_single"
        )

        st.caption(f"Will be downloaded as: **{custom_filename}**")

# Footer
st.markdown("---")
st.caption("💡 Tip: For best PDF preview experience, use Chrome or Edge browser.")
