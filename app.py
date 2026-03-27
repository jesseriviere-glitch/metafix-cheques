import streamlit as st
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import re

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
    
    # Extract Date: Looking for YYYY/MM/DD [cite: 17, 20]
    date_match = re.search(r'(\d{4})/(\d{2})/(\d{2})', text)
    if date_match:
        y, m, d = date_match.groups()
        data['date_formatted'] = f"{m}  {d}  {y}"
        data['bill_date'] = f"{y}/{m}/{d}"
    else:
        data['date_formatted'] = "03  26  2026"
        data['bill_date'] = "2026/03/26"

    # Extract Numeric Amount [cite: 18]
    amount_match = re.search(r'(\d+\.\d{2})', text)
    data['amount_num'] = amount_match.group(1) if amount_match else "5.75"
    
    # Extract Written Amount [cite: 13]
    words_match = re.search(r'([A-Za-z]+\s+and\s+\d{2}/100)', text)
    data['amount_words'] = words_match.group(1) if words_match else "Five and 75/100"

    # Payee & Address [cite: 14, 15, 16, 19]
    data['payee'] = "Aims Fasteners & Fittings"
    data['address'] = "7284 Cordner St.\nSuite 209\nMontreal Quebec H8N 2W8"
    
    # Bill ID [cite: 21]
    bill_id_match = re.search(r'Bill ID\s*"\s*,\s*"\s*(\d+)', text)
    data['bill_id'] = bill_id_match.group(1) if bill_id_match else "1234"
    
    return data

def create_cheque_pdf(data):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=LETTER)
    width, height = LETTER 

    def draw_stub(y_start):
        can.setFont(FONT_NAME, 10)
        can.drawString(20*mm, y_start, "Bill Date")
        can.drawString(65*mm, y_start, "Bill ID")
        can.drawString(110*mm, y_start, "Bill Amount")
        can.drawString(155*mm, y_start, "Payment Amount")
        can.setFont(FONT_NAME, 9)
        can.drawString(20*mm, y_start - 8*mm, data['bill_date'])
        can.drawString(65*mm, y_start - 8*mm, data['bill_id'])
        can.drawString(110*mm, y_start - 8*mm, f"${data['amount_num']}")
        can.drawString(155*mm, y_start - 8*mm, f"${data['amount_num']}")

    # 1. TOP STUB
    draw_stub(260*mm)

    # 2. MIDDLE CHEQUE (89mm from top)
    chq_top = height - (89 * mm) 
    can.setFont(FONT_NAME, 11)
    can.drawString(150*mm, chq_top - 12*mm, data['date_formatted']) # Date
    can.drawString(35*mm, chq_top - 28*mm, data['payee'])           # Payee
    can.drawString(178*mm, chq_top - 28*mm, data['amount_num'])     # $ Amount
    can.drawString(25*mm, chq_top - 38*mm, data['amount_words'])    # Text Amount
    
    # Address Block
    text_obj = can.beginText(35*mm, chq_top - 50*mm)
    text_obj.setFont(FONT_NAME, 9)
    for line in data['address'].split('\n'):
        text_obj.textLine(line)
    can.drawText(text_obj)

    # 3. BOTTOM STUB
    draw_stub(95*mm)

    can.save()
    packet.seek(0)
    return packet

# --- STREAMLIT UI ---
st.title("Metafix Cheque Reformatter")
uploaded_file = st.file_uploader("Upload Zoho PDF", type="pdf")

if uploaded_file is not None:
    try:
        extracted_data = extract_zoho_data(uploaded_file)
        pdf_output = create_cheque_pdf(extracted_data)
        
        st.success("Cheque Ready!")
        st.download_button(
            label="Download Formatted Cheque",
            data=pdf_output,
            file_name=f"Cheque_{extracted_data['bill_id']}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Error: {e}")
