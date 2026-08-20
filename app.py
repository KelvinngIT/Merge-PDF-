import streamlit as st
from pypdf import PdfWriter, PdfReader
from datetime import datetime
import os
import re
import random
import string
import io

# ======================
# Page Config
# ======================
st.set_page_config(
    page_title="PDF Combiner",
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
        st.rerun()

# ======================
# Main App
# ======================
if not st.session_state.logged_in:
    st.title("📄 PDF Combiner")
    st.info("👈 Please login with your email in the sidebar to continue.")
    st.stop()

# ----- Logged-in content -----
st.title("📄 PDF Combiner")
st.markdown(f"Welcome, **{st.session_state.user_email}**!")
st.markdown("Upload multiple PDF files → Combine them → Download the final PDF")

st.markdown("---")

# Upload section
st.subheader("1️⃣ Upload PDF Files")
uploaded_files = st.file_uploader(
    "Choose one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True,
    help="You can select multiple PDFs at once. The order of selection will be the order in the final file."
)

if uploaded_files:
    st.success(f"✅ {len(uploaded_files)} file(s) uploaded")
    
    # Show file list with order
    st.markdown("**Files in merge order:**")
    for i, f in enumerate(uploaded_files, 1):
        st.write(f"{i}. `{f.name}` ({f.size / 1024:.1f} KB)")

    st.markdown("---")
    
    # Merge button
    st.subheader("2️⃣ Combine PDFs")
    if st.button("🔗 Combine All PDFs", type="primary", use_container_width=True):
        with st.spinner("Merging PDFs..."):
            writer = merge_pdfs(uploaded_files)
            
            if writer is not None:
                # Write to bytes buffer
                buffer = io.BytesIO()
                writer.write(buffer)
                buffer.seek(0)
                
                st.session_state.merged_pdf = buffer.getvalue()
                st.success(f"✅ Successfully combined {len(uploaded_files)} PDFs into one file!")
            else:
                st.error("Failed to merge PDFs. Please check the files.")

# Download section
if st.session_state.merged_pdf is not None:
    st.markdown("---")
    st.subheader("3️⃣ Download Combined PDF")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"combined_{timestamp}.pdf"
    
    st.download_button(
        label="📥 Download Combined PDF",
        data=st.session_state.merged_pdf,
        file_name=file_name,
        mime="application/pdf",
        use_container_width=True,
        type="primary"
    )
    
    st.caption(f"File size: {len(st.session_state.merged_pdf) / 1024:.1f} KB")

# Footer tip
st.markdown("---")
st.info("💡 Tip: The order of the uploaded files determines the page order in the final PDF.")