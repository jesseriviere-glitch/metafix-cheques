import streamlit as st
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

st.set_page_config(page_title="Metafix Cheque Tool", page_icon="🏦")

st.title("🏦 Metafix Cheque Reformatter")
st.write("v3: Masks the top Zoho data and re-stamps it at the 89mm center.")

uploaded_file = st.file_uploader("Upload Zoho PDF", type="pdf")

if uploaded_file:
    reader = PdfReader(uploaded_file)
    writer = PdfWriter()

    # This is the 'Nudge' value to hit your 89mm center line
    shift_down = -515 

    for page in reader.pages:
        # 1. Create a White Mask to hide the top 3.5 inches of the Zoho PDF
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        can.setFillColorRGB(1, 1, 1) # White
        # This box covers the original 'Top' cheque so it doesn't print
        can.rect(0, 520, 612, 300, fill=1, stroke=0) 
        can.save()
        packet.seek(0)
        mask_pdf = PdfReader(packet).pages[0]

        # 2. Layer the original page, then the mask, then the 'Shifted' data
        # Merge the original (shows bottom stubs)
        page.merge_page(mask_pdf)
        
        # Merge a copy of itself, but shifted down to the 89mm mark
        op = Transformation().translate(tx=0, ty=shift_down)
        page.merge_transformed_page(page, op)
        
        writer.add_page(page)

    # Export
    pdf_out = io.BytesIO()
    writer.write(pdf_out)
    
    st.success("Reformatting Complete!")
    st.download_button(
        label="Download Final Metafix Cheque",
        data=pdf_out.getvalue(),
        file_name="Metafix_Final.pdf",
        mime="application/pdf"
    )
