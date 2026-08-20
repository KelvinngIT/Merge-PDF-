# 📄 PDF Combiner Web App

A simple Streamlit web application that allows users to:

1. Login with email + verification code
2. Upload multiple PDF files
3. Combine them into a single PDF
4. Download the merged PDF

## Features

- Email-based login with 6-digit verification code (demo mode)
- Multi-file PDF upload
- PDF merging using `pypdf`
- Clean download of the combined file
- Session-based authentication

## How to Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/pdf-merger-app.git
cd pdf-merger-app

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py