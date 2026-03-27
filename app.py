import streamlit as st
from pypdf import PdfReader, PdfWriter, Transformation
import io

st.set_page_config(page_title="Metafix Cheque Reformatter", page_icon="🏦")

st.title("🏦 Metafix Cheque Reformatter")
st.write("Rearranging Zoho 'Voucher' blocks for Metafix Centered Cheques.")

uploaded_file = st.file_uploader("Upload Zoho PDF", type="pdf")

if uploaded_file:
    reader = PdfReader(uploaded_file)
    writer = PdfWriter()

    for page in reader.pages:
        # Create a blank canvas
        new_page = writer.add_blank_page(width=page.mediabox.width, height=page.mediabox.height)
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        third = height / 3

        # BLOCK 1: Move the original TOP (Cheque) to the MIDDLE (Metafix Cheque Zone)
        # Shift down by roughly 1/3 of the page to hit the 89mm mark
        cheque_shift = Transformation().translate(tx=0, ty=-third)
        new_page.merge_transformed_page(page, cheque_shift)

        # BLOCK 2: Move the original MIDDLE (Stub 1) to the BOTTOM
        stub1_shift = Transformation().translate(tx=0, ty=-third)
        new_page.merge_transformed_page(page, stub1_shift)

        # BLOCK 3: Move the original BOTTOM (Stub 2) to the TOP
        stub2_shift = Transformation().translate(tx=0, ty=third * 2)
        new_page.merge_transformed_page(page, stub2_shift)

    # Export
    pdf_out = io.BytesIO()
    writer.write(pdf_out)
    
    st.success("Reformatting Complete!")
    st.download_button(
        label="Download Metafix PDF",
        data=pdf_out.getvalue(),
        file_name="Metafix_Cheque_Final.pdf",
        mime="application/pdf"
    )
