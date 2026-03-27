import streamlit as st
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
import re
import copy

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
        date_raw = re.search(r'(\d{4}/\d{2}/\d{2})', text).group(1) if re.search(r'(\d{4}/\d{2}/\d{2})', text) else ""
        amount_num = re.search(r'\d+\.\d{2}', text).group(0) if re.search(r'\d+\.\d{2}', text) else ""
        
        # Create a blank canvas for the new layout
        new_page = writer.add_blank_page(width=page.mediabox.width, height=page.mediabox.height)
        
        # --- ZONE 1: TOP STUB (Original Zoho Look, Nudged Down) ---
        top_stub = copy.copy(page)
        top_stub.mediabox.lower_left = (0, 528) # Crop to top 1/3
        # Shift it down about 15mm to clear the cheque number 13296
        top_op = Transformation().translate(tx=0, ty=-45) 
        new_page.merge_transformed_page(top_stub, top_op)

        # --- ZONE 2: BOTTOM STUB (Original Zoho Look, Untouched) ---
        bottom_stub = copy.copy(page)
        bottom_stub.mediabox.upper_right = (page.mediabox.right, 264) # Crop to bottom 1/3
        new_page.merge_page(bottom_stub)

        # --- ZONE 3: MIDDLE CHEQUE (Precision Text Overlay) ---
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        
        # DATE: Spaced MM DD YYYY
        can.setFont("Courier", 12)
        can.drawString(482, 546, format_date_spaced(date_raw)) 
        
        # AMOUNT (Numerical)
        can.drawString(525, 506, amount_num) 
        
        # WRITTEN AMOUNT
        can.setFont("Helvetica", 10)
        can.drawString(75, 516, "Five and 75/100 *********************************")
        
        # PAYEE & ADDRESS
        can.drawString(75, 486, "Aims Fasteners & Fittings")
        can.drawString(75, 473, "7284 Cordner St. Suite 209")
        can.drawString(75, 460, "Montreal Quebec H8N 2W8")

        can.save()
        packet.seek(0)
        overlay_pdf = PdfReader(packet).pages[0]
        new_page.merge_page(overlay_pdf)
        
    pdf_out = io.BytesIO()
    writer.write(pdf_out)
    st.success("Full Layout Preserved")
    st.download_button("Download Final Metafix PDF", pdf_out.getvalue(), "Metafix_Full_Cheque.pdf")
