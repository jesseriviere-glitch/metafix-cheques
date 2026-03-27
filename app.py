import streamlit as st
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import re
import os

# --- FONT REGISTRATION ---
def register_fonts():
    # Attempt to load Rubik if files are in the repo
    fonts = {"Regular": "Rubik-Regular.ttf", "Bold": "Rubik-Bold.ttf"}
    try:
        for name, file in fonts.items():
            pdfmetrics.registerFont(TTFont(f'Rubik-{name}', file))
        return "Rubik-Regular", "Rubik-Bold"
    except:
        return "Helvetica", "Helvetica-Bold"

FONT_REG, FONT_BOLD = register_fonts()

def extract_dynamic_data(pdf_file):
    reader = PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
    
    # Regex Patterns for Zoho Voucher logic
    date_pattern = r"(\d{4}/\d{2}/\d{2})"
    amount_num_pattern = r"Total\s*[\$]?\s*([\d,]+\.\d{2})"
    # Captures "Two Thousand... and 50/100" style strings
    words_pattern = r"([A-Z][a-z]+.*?\d{1,2}/100)" 
    
    date_match = re.search(date_pattern, full_text)
    amount_match = re.search(amount_num_pattern, full_text)
    words_match = re.search(words_pattern, full_text)
    
    # Logic to find Payee: Usually follows "Pay to" or is the first prominent name
    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
    payee = lines[0] if lines else "Unknown Payee"
    
    # Extract Bill details (Table data)
    # Simple logic: find a line with a date and an amount that isn't the total
    bill_id = "Voucher"
    for line in lines:
        if "BILL-" in line or "INV-" in line:
            bill_id = line.split()[0]
            break

    return {
        "payee": payee,
        "date": date_match.group(1) if date_match else "2024/01/01",
        "amount_num": amount_match.group(1) if amount_match else "0.00",
        "amount_words": words_match.group(1) if words_match else "Zero Dollars",
        "bill_id": bill_id
    }

def format_cheque_date(date_str):
    """Reformats YYYY/MM/DD to MM  DD  YYYY with extra spacing"""
    p = date_str.split('/')
    return f"{p[1]}    {p[2]}    {p[0]}"

def generate_pdf(data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    
    def draw_remittance(y_top):
        c.setFont(FONT_BOLD, 10)
        c.drawString(72, y_top, f"PAYEE: {data['payee']}")
        c.drawRightString(540, y_top, f"DATE: {data['date']}")
        
        c.setFont(FONT_REG, 9)
        c.drawString(72, y_top - 30, "REF NO.")
        c.drawString(200, y_top - 30, "DESCRIPTION")
        c.drawRightString(540, y_top - 30, "AMOUNT")
        c.line(72, y_top - 35, 540, y_top - 35)
        
        c.drawString(72, y_top - 50, data['bill_id'])
        c.drawString(200, y_top - 50, f"Payment to {data['payee']}")
        c.drawRightString(540, y_top - 50, data['amount_num'])

    # 1. TOP STUB
    draw_remittance(740)

    # 2. MIDDLE CHEQUE (The critical alignment area)
    # Date Boxes (Adjust X/Y to hit your pre-printed boxes exactly)
    c.setFont(FONT_REG, 12)
    c.drawRightString(530, 485, format_cheque_date(data['date']))
    
    # Payee
    c.setFont(FONT_BOLD, 11)
    c.drawString(100, 445, data['payee'])
    
    # Numerical Amount
    c.drawString(485, 445, f"**{data['amount_num']}**")
    
    # Written Amount
    c.setFont(FONT_REG, 10)
    c.drawString(72, 420, f"{data['amount_words']} ********************************")

    # 3. BOTTOM STUB
    draw_remittance(250)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI ---
st.title("Metafix PDF Cheque Transformer")
st.info("Upload any Zoho Voucher PDF to map data to Metafix Stationary.")

uploaded_file = st.file_uploader("Upload Source PDF", type="pdf")

if uploaded_file:
    data = extract_dynamic_data(uploaded_file)
    
    st.subheader("Extracted Data Confirmation")
    col1, col2 = st.columns(2)
    col1.write(f"**Payee:** {data['payee']}")
    col1.write(f"**Date:** {data['date']}")
    col2.write(f"**Amount:** ${data['amount_num']}")
    col2.write(f"**ID:** {data['bill_id']}")

    final_pdf = generate_pdf(data)
    
    st.download_button(
        label="Download Reformatted Cheque",
        data=final_pdf,
        file_name=f"Metafix_{data['payee']}.pdf",
        mime="application/pdf"
    )
