import streamlit as st
import pypdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
import re
import base64
import pandas as pd
import json

# Configuration
CALIBRATION_FILE = "calibration.json"
FONT_PATH = "fonts/Rubik-VariableFont_wght.ttf"
DEFAULT_FONT = 'Helvetica'

# Default coordinates and sizes (Perfected by user)
DEFAULT_CALIBRATION = {
    "date": {"x": 518, "y": 48, "size": 8},
    "amount_figures": {"x": 550, "y": 96, "size": 12},
    "amount_words": {"x": 69, "y": 97, "size": 10},
    "payee": {"x": 69, "y": 129, "size": 11},
    "address": {"x": 69, "y": 143, "size": 9}
}

def load_calibration():
    cal = DEFAULT_CALIBRATION.copy()
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, 'r') as f:
                saved = json.load(f)
                # Merge saved data into defaults to handle new fields
                for field in cal:
                    if field in saved:
                        cal[field].update(saved[field])
        except: pass
    return cal

def save_calibration(data):
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Register Rubik Font
if os.path.exists(FONT_PATH):
    try:
        pdfmetrics.registerFont(TTFont('Rubik', FONT_PATH))
        DEFAULT_FONT = 'Rubik'
    except Exception as e:
        st.warning(f"Could not load Rubik font: {e}. Falling back to Helvetica.")

def extract_zoho_data(pdf_file):
    reader = pypdf.PdfReader(pdf_file)
    text = reader.pages[0].extract_text()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    data = {
        "date": "",
        "amount_words": "",
        "amount_figures": "",
        "payee": "",
        "address": "",
        "memo_data": []
    }
    
    if len(lines) > 0: data["date"] = lines[0]
    if len(lines) > 1:
        amount_match = re.search(r'(.*)\s+(\d+\.\d{2})', lines[1])
        if amount_match:
            data["amount_words"] = amount_match.group(1).strip()
            data["amount_figures"] = amount_match.group(2).strip()
        else:
            data["amount_words"] = lines[1]
    if len(lines) > 2: data["payee"] = lines[2]
    
    addr_lines = []
    curr_line = 3
    while curr_line < len(lines):
        line = lines[curr_line]
        if any(keyword in line for keyword in ["Bill Date", "Bill ID"]): break
        if data["payee"] in line and re.search(r'\d{4}[/-]\d{2}[/-]\d{2}', line): break
        addr_lines.append(line)
        curr_line += 1
    data["address"] = "\n".join(addr_lines)
        
    memo_started = False
    for line in lines[curr_line:]:
        if "Bill Date" in line:
            memo_started = True
            continue
        if line.startswith(data["payee"]) and memo_started: break
        if memo_started:
            if "Total" in line: continue
            parts = line.split()
            if len(parts) >= 4:
                data["memo_data"].append({"Bill Date": parts[0], "Bill ID": parts[1], "Bill Amount": parts[2], "Payment Amount": parts[3]})
            else:
                data["memo_data"].append({"Bill Date": line, "Bill ID": "", "Bill Amount": "", "Payment Amount": ""})
    return data

def reformat_date(date_str):
    try:
        if '/' in date_str: y, m, d = date_str.split('/')
        elif '-' in date_str: y, m, d = date_str.split('-')
        else: return date_str
        # Restored tight spacing within groups, added 5 spaces between groups
        return f"{m[0]} {m[1]}     {d[0]} {d[1]}     {y[0]} {y[1]} {y[2]} {y[3]}"
    except: return date_str

def create_cheque_pdf(data, calibration, include_background=False):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    
    if include_background:
        bg_path = "Metafix_Cheque.jpg"
        if os.path.exists(bg_path):
            try: c.drawImage(bg_path, 0, 0, width=width, height=height)
            except: pass
    
    def draw_stub(y_offset):
        c.setFont(DEFAULT_FONT, 10)
        c.drawString(60, height - y_offset - 45, data['payee'])
        c.drawRightString(width - 60, height - y_offset - 45, data['date'])
        c.setFont(DEFAULT_FONT, 9)
        c.setLineWidth(0.5)
        c.line(50, height - y_offset - 65, width - 50, height - y_offset - 65)
        c.drawString(60, height - y_offset - 78, "BILL DATE")
        c.drawString(160, height - y_offset - 78, "BILL ID")
        c.drawRightString(width - 180, height - y_offset - 78, "BILL AMOUNT")
        c.drawRightString(width - 60, height - y_offset - 78, "PAYMENT AMOUNT")
        c.line(50, height - y_offset - 85, width - 50, height - y_offset - 85)
        curr_y = height - y_offset - 100
        for item in data['memo_data']:
            c.drawString(60, curr_y, str(item.get("Bill Date", "")))
            c.drawString(160, curr_y, str(item.get("Bill ID", "")))
            c.drawRightString(width - 180, curr_y, str(item.get("Bill Amount", "")))
            c.drawRightString(width - 60, curr_y, str(item.get("Payment Amount", "")))
            curr_y -= 14
        c.line(width - 150, curr_y - 5, width - 50, curr_y - 5)
        c.drawRightString(width - 180, curr_y - 20, "TOTAL:")
        c.drawRightString(width - 60, curr_y - 20, f"${data['amount_figures']}")

    def draw_cheque(y_offset):
        formatted_date = reformat_date(data['date'])
        c.setFont(DEFAULT_FONT, calibration['date']['size'])
        c.drawString(calibration['date']['x'], height - y_offset - calibration['date']['y'], formatted_date)
        
        c.setFont('Helvetica-Bold', calibration['amount_figures']['size'])
        c.drawString(calibration['amount_figures']['x'], height - y_offset - calibration['amount_figures']['y'], data['amount_figures'])
        
        c.setFont(DEFAULT_FONT, calibration['amount_words']['size'])
        c.drawString(calibration['amount_words']['x'], height - y_offset - calibration['amount_words']['y'], data['amount_words'])
        
        c.setFont('Helvetica-Bold', calibration['payee']['size'])
        c.drawString(calibration['payee']['x'], height - y_offset - calibration['payee']['y'], data['payee'])
        
        c.setFont(DEFAULT_FONT, calibration['address']['size'])
        curr_y = height - y_offset - calibration['address']['y']
        address_lines = data['address'].split('\n')
        for addr_line in address_lines:
            c.drawString(calibration['address']['x'], curr_y, addr_line)
            curr_y -= (calibration['address']['size'] + 3) # Dynamic line spacing

    draw_stub(0)
    draw_cheque(264)
    draw_stub(528)
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def main():
    st.set_page_config(page_title="ZOHO CHEQUE CONVERTER", page_icon="🏦", layout="wide")
    
    # Custom CSS for the Mockup Look
    st.markdown("""
        <style>
        /* Hide default Streamlit header */
        [data-testid="stHeader"] { visibility: hidden; }
        [data-testid="stSidebar"] { padding-top: 2rem; }
        
        .main { background-color: #ffffff; }
        
        .custom-header {
            background-color: #3d5a4d;
            padding: 2.5rem 0;
            text-align: center;
            color: #ffffff;
            font-family: 'Rubik', sans-serif;
            font-size: 1.8rem;
            font-weight: 600;
            letter-spacing: 0.1rem;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: -6rem;
            margin-bottom: 3rem;
            text-transform: uppercase;
        }
        
        .custom-footer {
            color: #6c757d;
            text-align: center;
            padding: 2rem 0;
            font-size: 0.8rem;
            border-top: 1px solid #f0f2f6;
            width: 100vw;
            margin-left: calc(-50vw + 50%);
            margin-top: 4rem;
        }
                /* Style the Native File Uploader to match Mockup */
        [data-testid="stFileUploader"] {
            border: 1px dashed #ced4da !important;
            border-radius: 12px !important;
            padding: 20px !important;
            background-color: #ffffff !important;
            transition: border-color 0.3s ease;
            min-height: 250px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        [data-testid="stFileUploader"]:hover {
            border-color: #3d5a4d !important;
        }

        [data-testid="stFileUploader"] section {
            background-color: transparent !important;
            padding: 0 !important;
            width: 100%;
        }

        /* Hide default Streamlit uploader elements */
        [data-testid="stFileUploader"] section > label,
        [data-testid="stFileUploader"] section > div [data-testid="stMarkdownContainer"],
        [data-testid="stFileUploader"] section > div > i {
            display: none !important;
        }
        
        /* Hide the default "Drag and drop file here" text and "Limit 200MB per file • PDF" */
        [data-testid="stFileUploaderDropzone"] > div > span {
            display: none !important;
        }

        /* Inject Mockup Content */
        [data-testid="stFileUploaderDropzone"]::before {
            content: "";
            width: 80px;
            height: 80px;
            background-color: #ecf3f0;
            border-radius: 50%;
            margin: 0 auto 20px auto;
            display: flex;
            align-items: center;
            justify-content: center;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 24 24' fill='none' stroke='%233d5a4d' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'%3E%3C/path%3E%3Cpolyline points='17 8 12 3 7 8'%3E%3C/polyline%3E%3Cline x1='12' y1='3' x2='12' y2='15'%3E%3C/line%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: center;
        }

        [data-testid="stFileUploaderDropzone"]::after {
            content: "Drag & drop PDF files";
            font-size: 1.5rem;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 4px;
            font-family: 'Rubik', sans-serif;
            display: block;
            text-align: center;
        }

        /* Style the "or browse to select files" part */
        [data-testid="stFileUploader"] button {
            background-color: transparent !important;
            color: #3b82f6 !important;
            border: none !important;
            font-weight: 500 !important;
            font-size: 1rem !important;
            padding: 0 !important;
            margin: 0 !important;
            text-decoration: none !important;
            font-family: 'Rubik', sans-serif !important;
            display: inline-block !important;
            box-shadow: none !important;
        }
        
        [data-testid="stFileUploader"] button:hover {
            text-decoration: underline !important;
            color: #2563eb !important;
        }
        
        /* Container for the browse text */
        [data-testid="stFileUploader"] section > div {
            text-align: center !important;
        }

        [data-testid="stFileUploader"] section > div::before {
            content: "or ";
            color: #6b7280;
            font-size: 1rem;
            font-weight: 400;
        }
        
        [data-testid="stFileUploader"] section > div::after {
            content: " to select files";
            color: #6b7280;
            font-size: 1rem;
            font-weight: 400;
        }
        
        /* Supports text */
        [data-testid="stFileUploader"] section::after {
            content: "Supports PDF files up to 50MB";
            color: #9ca3af;
            font-size: 0.85rem;
            margin-top: 15px;
            font-family: 'Rubik', sans-serif;
            display: block;
            text-align: center;
        }
        
        /* Premium buttons */
        .stButton>button {
            border-radius: 5px;
            background-color: #3d5a4d;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
        }
        .stButton>button:hover {
            background-color: #2e4a3c;
            color: white;
            border: none;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # State Initialization
    if 'cheque_data' not in st.session_state: st.session_state.cheque_data = None
    if 'calibration' not in st.session_state: st.session_state.calibration = load_calibration()

    # Fixed Header
    st.markdown('<div class="custom-header">ZOHO CHEQUE CONVERTER</div>', unsafe_allow_html=True)
    
    # Sidebar only for Calibration (and small upload refresher)
    with st.sidebar:
        st.header("🛠️ Settings")
        cal_mode = st.toggle("Enable Live Calibration", value=False)
        if cal_mode:
            st.info("Adjust the sliders to fine-tune placements.")
            for field, coords in st.session_state.calibration.items():
                st.subheader(field.replace('_', ' ').title())
                coords['x'] = st.slider(f"{field} X", 0, 612, coords['x'], key=f"{field}_x")
                coords['y'] = st.slider(f"{field} Y", 0, 300, coords['y'], key=f"{field}_y")
                coords['size'] = st.slider(f"{field} Sizing", 6, 24, coords.get('size', 10), key=f"{field}_size")
            
            if st.button("💾 Save Calibration"):
                save_calibration(st.session_state.calibration)
                st.success("Calibration saved!")
        
        st.markdown("---")
        if st.session_state.cheque_data:
            if st.button("🔄 Upload New File"):
                st.session_state.cheque_data = None
                st.rerun()

    # Main Content Area
    if st.session_state.cheque_data is None:
        # Exact Mockup Match using Styled Native Uploader
        _, center_col, _ = st.columns([1, 2, 1])
        with center_col:
            uploaded_file = st.file_uploader("Upload", type="pdf", label_visibility="collapsed")
            if uploaded_file:
                st.session_state.cheque_data = extract_zoho_data(uploaded_file)
                st.rerun()
    else:
        # Side-by-Side Interface
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            st.header("📝 Edit Cheque Details")
            c1, c2 = st.columns(2)
            st.session_state.cheque_data['date'] = c1.text_input("Date", st.session_state.cheque_data['date'])
            st.session_state.cheque_data['amount_figures'] = c2.text_input("Amount ($)", st.session_state.cheque_data['amount_figures'])
            st.session_state.cheque_data['payee'] = st.text_input("Payee", st.session_state.cheque_data['payee'])
            st.session_state.cheque_data['amount_words'] = st.text_input("Amount Words", st.session_state.cheque_data['amount_words'])
            st.session_state.cheque_data['address'] = st.text_area("Address", st.session_state.cheque_data['address'], height=100)
            
            df = pd.DataFrame(st.session_state.cheque_data['memo_data'])
            if not df.empty:
                edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                st.session_state.cheque_data['memo_data'] = edited_df.to_dict('records')
            
            st.markdown("---")
            preview_pdf = create_cheque_pdf(st.session_state.cheque_data, st.session_state.calibration, include_background=True)
            download_pdf = create_cheque_pdf(st.session_state.cheque_data, st.session_state.calibration, include_background=False)
            
            st.download_button(
                label="📥 DOWNLOAD METAFIX CHEQUE",
                data=download_pdf,
                file_name=f"Metafix_Cheque_{st.session_state.cheque_data['date'].replace('/','-')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        with col2:
            st.header("👁️ Live Preview")
            try:
                from streamlit_pdf_viewer import pdf_viewer
                pdf_viewer(preview_pdf.getvalue(), height=800)
            except ImportError:
                base64_pdf = base64.b64encode(preview_pdf.getvalue()).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)

    # Footer
    st.markdown(f'<div class="custom-footer">© {re.sub(r"-.*", "", str(pd.Timestamp.now().year))} ZOHO CHEQUE CONVERTER. All rights reserved.</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
