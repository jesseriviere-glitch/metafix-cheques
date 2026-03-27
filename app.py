import streamlit as st
from pypdf import PdfReader, PdfWriter, Transformation
import io
import copy

st.set_page_config(page_title="Metafix Cheque Tool", page_icon="🏦")

st.title("🏦 Metafix Cheque Reformatter")
st.write("Corrected version: Clears top data and shifts to center.")

uploaded_file = st.file_uploader("Upload Zoho PDF", type="pdf")

if uploaded_file:
    reader = PdfReader(uploaded_file)
    writer = PdfWriter()

    # Offset to hit the 89mm center mark from the top
    # Adjusted to ensure it lands precisely in the Metafix green boxes
    SHIFT_Y = -515 

    for page in reader.pages:
        # 1. Create the Background (Stubs only)
        # We use a copy to avoid modifying the original data prematurely
        bg_page = writer.add_blank_page(width=page.mediabox.width, height=page.mediabox.height)
        
        # We only merge the bottom 2/3 of the original page to clear the top cheque
        # This prevents the "repeated info" you saw at the bottom
        stub_page = copy.copy(page)
        stub_page.mediabox.upper_right = (page.mediabox.right, page.mediabox.top / 1.5)
        bg_page.merge_page(stub_page)

        # 2. Create the Cheque Layer
        # We take the TOP portion of the original and shift it to the middle
        cheque_layer = copy.copy(page)
        # Crop to just the top cheque data
        cheque_layer.mediabox.lower_left = (0, page.mediabox.top / 1.5)
        
        # Apply the transformation to move it to the 89mm center
        op = Transformation().translate(tx=0, ty=SHIFT_Y)
        bg_page.merge_transformed_page(cheque_layer, op)

    # Export
    pdf_out = io.BytesIO()
    writer.write(pdf_out)
    
    st.success("Reformatting Complete!")
    st.download_button(
        label="Download Fixed Metafix Cheque",
        data=pdf_out.getvalue(),
        file_name="Metafix_Fixed_Cheque.pdf",
        mime="application/pdf"
    )
