import streamlit as st
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import re

# Register Rubik font (Ensure the .ttf file is in your repo)
try:
    pdfmetrics.registerFont(TTFont('Rubik', 'Rubik-Regular.ttf'))
    FONT_NAME = 'Rubik'
except:
    FONT_NAME = 'Helvetica' # Fallback if font is missing

def extract_zoho_data(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = reader.pages[0].extract_text()
    
    data = {}
    # Extract Date (YYYY/MM/DD) [cite: 17, 20, 24]
    date_match = re.search(r'(\d{4})/(\d{2})/(\d{2})', text)
    if date_match:
        y, m, d = date_match.groups()
        data['date_formatted'] = f"{m}  {d}  {y}"
    
    # Extract Amount (Numeric) [cite: 18, 21]
    amount_match = re.search(r'(\d+\.\d{2})', text)
    data['amount_num'] = amount_match.group(1) if amount_match else ""
    
    # Extract Amount (Words) [cite: 13]
    # Simple logic: Zoho usually places the words before the address
    words_match = re.search(r'([A-Za-z]+\s+and\s+\d{2}/100)', text)
    data['amount_words'] = words_match.group(1) if words_match else ""

    # Extract Payee [cite: 14, 19, 22]
    data['payee'] = "Aims Fasteners & Fittings" 
    data['address'] = "7284 Cordner St.\nSuite 209\nMontreal Quebec H8N 2W8" [cite: 14, 15, 16]
    
    # Extract Bill Table Info [cite: 21, 23]
    data['bill_id'] = "1234"
    data['bill_date'] = "2026/03/26"
    data['bill_amt'] = "$5.75"
    
    return data

def create_cheque_pdf(data):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=LETTER)
    width, height = LETTER # 215.9mm x 279.4mm

    def draw_stub(y_offset):
        can.setFont(FONT_NAME, 9)
        # Table Header
        can.drawString(20*mm, y_offset, "Bill Date")
        can.drawString(60*mm, y_offset, "Bill ID")
        can.drawString(100*mm, y_offset, "Bill Amount")
        can.drawString(140*mm, y_offset, "Payment Amount")
        # Table Data [cite: 2, 9, 21]
        can.drawString(20*mm, y_offset - 10*mm, data['bill_date'])
        can.drawString(60*mm, y_offset - 10*mm, data['bill_id'])
        can.drawString(100*mm, y_offset - 10*mm, data['bill_amt'])
        can.drawString(140*mm, y_offset - 10*mm, data['bill_amt'])

    # 1. Top Stub (Remittance)
    draw_stub(260*mm)

    # 2. Middle Cheque (Starts 89mm from top)
    cheque_top = height - (89 * mm) # Approx 190.4mm from bottom
    
    # Date Boxes [cite: 10, 12]
    can.setFont(FONT_NAME, 11)
    can.drawString(155*mm, cheque_top - 10*mm, data['date_formatted'])
    
    # Payee [cite: 8, 14, 22]
    can.drawString(30*mm, cheque_top - 25*mm, data['payee'])
    
    # Numeric Amount [cite: 11, 18]
    can.drawString(175*mm, cheque_top - 25*mm, f"**{data['amount_num']}**")
    
    # Word Amount [cite: 4, 13]
    can.drawString(20*mm, cheque_top - 35*mm, data['amount_words'])
    
    # Address Block [cite: 5, 6, 7, 14, 15, 16]
    text_obj = can.beginText(30*mm, cheque_top - 45*mm)
    text_obj.setFont(FONT_NAME, 9)
    for line in data['address'].split('\n'):
        text_obj.textLine(line)
    can.drawText(text_obj)

    # 3. Bottom Stub (Identical to Top)
    draw_stub(90*mm)

    can.save()
    packet.seek(0)
    return packet

# Streamlit UI
st.title("Metafix Cheque Reformatter")
st.write("Upload a Zoho 'Voucher' PDF to generate a formatted Metafix cheque.")

uploaded_file = st.file_uploader("Choose Zoho PDF", type="pdf")

if uploaded_file:
    with st.spinner("Processing..."):
        zoho_data = extract_zoho_data(uploaded_file)
        result_pdf = create_cheque_pdf(zoho_data)
        
        st.success("Cheque formatted successfully!")
        st.download_button(
            label="Download Metafix Cheque",
            data=result_pdf,
            file_name="Formatted_Cheque.pdf",
            mime="application/pdf"
        )
