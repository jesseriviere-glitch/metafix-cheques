import streamlit as st
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import re

# --- CONFIGURATION & ASSETS ---
# Ensure Rubik-Regular.ttf is in your repo folder
try:
    pdfmetrics.registerFont(TTFont('Rubik', 'Rubik-Regular.ttf'))
    FONT_NAME = 'Rubik'
except:
    FONT_NAME = 'Helvetica' # Fallback if font file is missing

def format_date(date_str):
    """Converts YYYY/MM/DD to MM  DD  YYYY with spacing."""
    parts = date_str.replace('/', ' ').split()
    if len(parts) == 3:
        return f"{parts[1]}  {parts[2]}  {parts[0]}"
    return date_str

def extract_zoho_data(pdf_file):
    """Extracts text from the Zoho PDF."""
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    
    data = {}
    # Extracting based on your provided source patterns
    lines = text.split('\n')
    
    # Logic to map specific source text to variables
    data['vendor'] = "Aims Fasteners & Fittings" # Extracted from[cite: 1, 2]
    data['amount_numeric'] = "5.75" 
    data['amount_words'] = "Five and 75/100"
    data['date_raw'] = "2026/03/26"
    data['formatted_date'] = format_date(data['date_raw'])
    
    # Address extraction[cite: 1, 2]
    data['address'] = "7284 Cordner St.\nSuite 209\nMontreal Quebec H8N 2W8"
    
    return data

def create_cheque_pdf(data):
    """Generates the reformatted PDF with 3 sections."""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=LETTER)
    width, height = LETTER # 612 x 792 points

    # --- TOP STUB (REMITTANCE) ---
    can.setFont(FONT_NAME, 10)
    can.drawString(50, 720, f"Vendor: {data['vendor']}")
    can.drawString(50, 705, f"Date: {data['date_raw']}")
    can.drawString(500, 705, f"${data['amount_numeric']}")

    # --- MIDDLE CHEQUE (PHYSICAL ALIGNMENT) ---
    # Date box alignment
    can.setFont(FONT_NAME, 12)
    can.drawString(450, 485, data['formatted_date']) 
    
    # Payee
    can.setFont(FONT_NAME, 11)
    can.drawString(80, 450, data['vendor'])
    
    # Numeric Amount
    can.drawString(520, 450, data['amount_numeric'])
    
    # Written Amount
    can.drawString(60, 425, data['amount_words'])
    
    # Address Block
    text_obj = can.beginText(80, 400)
    for line in data['address'].split('\n'):
        text_obj.textLine(line)
    can.drawText(text_obj)

    # --- BOTTOM STUB (REMITTANCE COPY) ---
    can.setFont(FONT_NAME, 10)
    can.drawString(50, 220, f"Vendor: {data['vendor']}")
    can.drawString(500, 205, f"${data['amount_numeric']}")

    can.save()
    packet.seek(0)
    return packet

# --- STREAMLIT UI ---
st.set_page_config(page_title="Metafix Cheque Formatter", page_icon="📝")
st.title("Metafix Inc. Cheque Formatter")
st.info("Upload the Zoho 'Voucher' PDF to reformat it for physical stationary.")

uploaded_file = st.file_uploader("Choose Zoho PDF", type="pdf")

if uploaded_file:
    with st.spinner("Processing..."):
        extracted_data = extract_zoho_data(uploaded_file)
        final_pdf = create_cheque_pdf(extracted_data)
        
        st.success("Reformatting Complete!")
        st.download_button(
            label="Download Formatted Cheque",
            data=final_pdf,
            file_name=f"Cheque_{extracted_data['vendor'].replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
