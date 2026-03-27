import streamlit as st
from pypdf import PdfReader, PdfWriter, Transformation
import io

st.set_page_config(page_title="Metafix Cheque Tool", page_icon="🏦")

st.title("🏦 Metafix Cheque Reformatter")
st.write("Upload the Zoho 'Voucher' PDF to shift the top cheque data to the 89mm center position.")

uploaded_file = st.file_uploader("Upload Zoho PDF", type="pdf")

if uploaded_file:
    reader = PdfReader(uploaded_file)
    writer = PdfWriter()

    # 89mm is ~252 points from the top. 
    # Since Zoho starts at the top (~792 points on a standard Letter page),
    # we shift the y-axis by approximately -540 points to land at your 89mm mark.
    # Note: If it lands slightly too high or low, adjust this number.
    SHIFT_Y = -540 

    for page in reader.pages:
        # Create a new blank page
        new_page = writer.add_blank_page(width=page.mediabox.width, height=page.mediabox.height)

        # 1. Overlay the original stubs (for the top and bottom sections)
        new_page.merge_page(page)

        # 2. Create the 'Cheque' layer by shifting the top data down to the middle
        # This moves the Payee, Date, and Amount lines to the Metafix green boxes.
        op = Transformation().translate(tx=0, ty=SHIFT_Y)
        new_page.merge_transformed_page(page, op)

    # Export buffer
    pdf_out = io.BytesIO()
    writer.write(pdf_out)

    st.success("Reformatting Complete!")
    st.download_button(
        label="Download Aligned Cheque",
        data=pdf_out.getvalue(),
        file_name="Metafix_Aligned_Cheque.pdf",
        mime="application/pdf"
    )
