import streamlit as st
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
import re

st.set_page_config(page_title="Metafix Precision Cheque", page_icon="🏦")

def format_date_spaced(date_str):
    # Converts 2026/03/26 to 03  26  2026
    parts = re.split(r'[/|-]', date_str)
    if len(parts) == 3:
        return f"{parts[1]}  {parts[2]}  {parts[0]}"
    return date_str

st.title("🏦 Metafix Precision Reformatter")
uploaded_file = st.file_uploader("Upload Zoho PDF", type="pdf")

if uploaded_file:
    reader = PdfReader(uploaded_file)
    writer = PdfWriter()

    for page in reader.pages:
        text = page.extract_text()
        
        # Regex extraction from your Zoho format
        date_raw = re.search(r'(\d{4}/\d{2}/\d{2})', text).group(1) if re.search(r'(\d{4}/\d{2}/\d{2})', text) else ""
        amount_num = re.search(r'\d+\.\d{2}', text).group(0) if re.search(r'\d+\.\d{2}', text) else ""
        
        # 1. Start with the Zoho page but MASK the top and middle to clear space
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        
        # White out the top and middle to prevent interference with "13296"
        can.setFillColorRGB(1, 1, 1)
        can.rect(0, 350, 612, 500, fill=1, stroke=0) 
        
        # 2. RE-DRAW the TOP STUB (Nudged down to avoid 13296)
        can.setFillColorRGB(0, 0, 0)
        can.setFont("Helvetica-Bold", 10)
        can.drawString(50, 750, "METAFIX INC. - REMITTANCE")
        
        # 3. DRAW the CHEQUE DATA (Precision Aligned)
        # DATE: Spaced MM DD YYYY
        can.setFont("Courier", 12)
        can.drawString(485, 545, format_date_spaced(date_raw))
        
        # AMOUNT (Numerical) - Moved up and right
        can.drawString(510, 505, amount_num)
        
        # WRITTEN AMOUNT - Moved up
        can.setFont("Helvetica", 11)
        can.drawString(75, 515, "Five and 75/100 *********************************")
        
        # PAYEE & ADDRESS - Moved up
        can.setFont("Helvetica", 10)
        can.drawString(75, 485, "Aims Fasteners & Fittings")
        can.drawString(75, 472, "7284 Cordner St. Suite 209")
        can.drawString(75, 459, "Montreal Quebec H8N 2W8")
        
        can.save()
        packet.seek(0)
        overlay_pdf = PdfReader(packet).pages[0]
        
        page.merge_page(overlay_pdf)
        writer.add_page(page)

    pdf_out = io.BytesIO()
    writer.write(pdf_out)
    st.download_button("Download Precision Cheque", pdf_out.getvalue(), "Metafix_Final.pdf")
