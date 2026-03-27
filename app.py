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
        
        # Regex extraction for Date and Amount from Zoho
        date_raw = re.search(r'(\d{4}/\d{2}/\d{2})', text).group(1) if re.search(r'(\d{4}/\d{2}/\d{2})', text) else ""
        amount_num = re.search(r'\d+\.\d{2}', text).group(0) if re.search(r'\d+\.\d{2}', text) else ""
        
        # 1. Start with a blank canvas to build our 3-zone layout
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        
        # --- ZONE 1: TOP STUB (Nudged down to avoid 13296) ---
        can.setFont("Helvetica-Bold", 10)
        can.drawString(50, 750, "METAFIX INC. - REMITTANCE")
        can.setFont("Helvetica", 9)
        # Re-drawing the table header and info from your scan
        can.drawString(50, 735, "Bill Date          Bill ID          Bill Amount          Payment Amount")
        can.drawString(50, 722, f"{date_raw}         1234            ${amount_num}                ${amount_num}")
        can.drawString(450, 710, f"Total: ${amount_num}")

        # --- ZONE 2: MIDDLE CHEQUE (Precision Aligned at 89mm mark) ---
        # Date: Spaced MM DD YYYY
        can.setFont("Courier", 12)
        can.drawString(480, 545, format_date_spaced(date_raw)) # Date Box
        
        # Amount (Numerical)
        can.drawString(525, 505, amount_num) # Amount Box
        
        # Written Amount
        can.setFont("Helvetica", 10)
        can.drawString(75, 515, "Five and 75/100 *********************************")
        
        # Payee & Address
        can.drawString(75, 485, "Aims Fasteners & Fittings")
        can.drawString(75, 472, "7284 Cordner St. Suite 209")
        can.drawString(75, 459, "Montreal Quebec H8N 2W8")

        can.save()
        packet.seek(0)
        overlay_pdf = PdfReader(packet).pages[0]

        # 2. Merge our new Top and Middle onto the Original (which provides the Bottom Stub)
        # First, we mask the top 2/3 of the original so only its bottom stub shows
        mask_packet = io.BytesIO()
        m_can = canvas.Canvas(mask_packet, pagesize=letter)
        m_can.setFillColorRGB(1, 1, 1)
        m_can.rect(0, 300, 612, 500, fill=1, stroke=0) # Mask Top and Middle
        m_can.save()
        mask_packet.seek(0)
        mask_page = PdfReader(mask_packet).pages[0]
        
        page.merge_page(mask_page)    # Hide original top/middle
        page.merge_page(overlay_pdf)  # Add our new top/middle
        
        writer.add_page(page)

    pdf_out = io.BytesIO()
    writer.write(pdf_out)
    st.success("Metafix Layout Ready")
    st.download_button("Download Final Metafix PDF", pdf_out.getvalue(), "Metafix_Full_Cheque.pdf")
