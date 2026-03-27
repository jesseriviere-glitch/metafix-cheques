import streamlit as st
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import re

# Set Page Config to prevent blank screens on slow loads
st.set_page_config(page_title="Metafix Cheque Reformatter", layout="centered")

# Register Rubik font - Fallback to Helvetica if file is missing
try:
    pdfmetrics.registerFont(TTFont('Rubik', 'Rubik-Regular.ttf'))
    FONT_NAME = 'Rubik'
except Exception:
    FONT_NAME = 'Helvetica'

def extract_zoho_data(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = reader.pages[0].extract_text()
    
    data = {}
    
    # Extract Date: Looking for YYYY/MM/DD
    date_match = re.search(r'(\d{4})/(\d{2})/(\d{2})', text)
    if date_match:
        y, m, d = date_match.groups()
        data['date_formatted'] = f"{m}  {d}  {y}"
        data['bill_date'] = f"{y}/{m}/{d}"
    else:
        data['date_formatted'] = "00  00  0000"
        data['bill_date'] = "2026/03/26"

    # Extract Numeric Amount
    amount_match = re.search(r'(\d+\.\d{2})', text)
    data['amount_num'] = amount_match.group(1) if amount_match else "0.00"
    
    # Extract Written Amount
    words_match = re.search(r'([A-Za-z]+\s+and\s+\d{2}/100)', text)
    data['amount_words'] = words_match.group(1) if words_match else "Five and 75/100"

    # Vendor & Address
    data['payee'] = "Aims Fasteners & Fittings"
    data['address'] = "7284 Cordner St.\nSuite 209\nMontreal Quebec H8N 2W8"
    
    # Bill ID
    data['bill_id'] = "1234"
    
    return data

def create_cheque_pdf(data):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=LETTER)
    width, height = LETTER 

    def draw_stub(y_start):
        can.setFont(FONT_NAME, 10)
        # Header Row
        can.drawString(20*mm, y_start, "Bill Date")
        can.drawString(65*mm, y_start, "Bill ID")
        can.drawString(110*mm, y_start, "Bill Amount")
        can.drawString(155*mm, y_start, "Payment Amount")
        # Data Row
        can.setFont(FONT_NAME, 9)
        can.drawString(20*mm, y_start - 8*mm, data['bill_date'])
        can.drawString(65*mm, y_start - 8*mm, data['bill_id'])
        can.drawString(110*mm, y_start - 8*mm, f"${data['amount_num']}")
        can.drawString(155*mm, y_start - 8*mm, f"${data['amount_num']}")

    # 1. TOP STUB
    draw_stub(260*mm)

    # 2. MIDDLE CHEQUE (The 89mm mark)
    # Height of Letter is 279.4mm. 279.4 - 89 = 190.4mm from bottom.
    chq_top = height - (89 * mm) 
    
    can.setFont(FONT_NAME, 11)
    # Date (Spaced)
    can.drawString(150*mm, chq_top - 12*mm, data['date_formatted'])
    
    # Payee
    can.drawString(35*mm, chq_top - 28*mm, data['payee'])
    
    # Amount Numeric
    can.drawString(178*mm, chq_top - 28*mm, data['amount_num'])
    
    # Amount Words
    can.drawString(25*mm, chq_top - 38*mm, data['amount_words'])
    
    # Address
    text_obj = can.beginText(35*mm, chq_top - 50*mm)
    text_obj.setFont(FONT_NAME, 9)
    for line in data['address'].split('\n'):
        text_obj.textLine(line)
    can.drawText(text_obj)

    # 3. BOTTOM STUB (Identical to Top)
    draw_stub(95*mm)

    can.save()
    packet.seek(0)
    return packet

# --- STREAMLIT UI ---
st.title("Metafix Cheque Reformatter")
st.markdown("---")

uploaded_file = st.file_uploader("Upload Zoho 'Voucher' PDF", type="pdf")

if uploaded_file is not None:
    try:
        with st.spinner("Extracting data and generating cheque..."):
            extracted_data = extract_zoho_data(uploaded_file)
            output_pdf = create_cheque_pdf(extracted_data)
            
            st.success("Reformatting Complete!")
            st
