import io
import os
import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

import streamlit as st
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = letter  # 612 x 792 pt
MM_TO_PT = 72.0 / 25.4
CHEQUE_TOP_FROM_PAGE_TOP_MM = 89
CHEQUE_TOP_Y = PAGE_HEIGHT - (CHEQUE_TOP_FROM_PAGE_TOP_MM * MM_TO_PT)


# Tuned from the supplied Metafix template and kept centralized for easy refinement.
LAYOUT = {
    "top_stub": {
        "company_y": 748,
        "date_y": 748,
        "line_1_y": 727,
        "line_2_y": 708,
        "header_y": 713,
        "row_y": 695,
        "total_y": 679,
    },
    "bottom_stub": {
        "company_y": 190,
        "date_y": 190,
        "line_1_y": 170,
        "line_2_y": 151,
        "header_y": 156,
        "row_y": 138,
        "total_y": 122,
    },
    "stub_columns": {
        "left": 22,
        "right": 590,
        "company_x": 22,
        "date_x": 586,
        "bill_date_x": 22,
        "bill_id_x": 160,
        "bill_amount_x": 404,
        "payment_amount_x": 520,
        "total_label_x": 430,
        "amount_x": 590,
    },
    "cheque": {
        "date_x": 519,
        "date_y": 515,
        "amount_words_x": 53,
        "amount_words_y": 486,
        "amount_num_x": 545,
        "amount_num_y": 470,
        "payee_x": 53,
        "payee_y": 432,
        "address_line_gap": 18,
    },
}


FONT_FILES = {
    "Rubik": [
        "Rubik-Regular.ttf",
        "fonts/Rubik-Regular.ttf",
        "./Rubik-Regular.ttf",
        "/mount/data/Rubik-Regular.ttf",
    ],
    "Rubik-Bold": [
        "Rubik-Bold.ttf",
        "fonts/Rubik-Bold.ttf",
        "./Rubik-Bold.ttf",
        "/mount/data/Rubik-Bold.ttf",
    ],
    "Rubik-Medium": [
        "Rubik-Medium.ttf",
        "fonts/Rubik-Medium.ttf",
        "./Rubik-Medium.ttf",
        "/mount/data/Rubik-Medium.ttf",
    ],
}


DEFAULT_FONTS = {
    "regular": "Helvetica",
    "bold": "Helvetica-Bold",
    "medium": "Helvetica-Bold",
}


def register_rubik_fonts() -> Dict[str, str]:
    fonts = DEFAULT_FONTS.copy()
    for font_name, candidates in FONT_FILES.items():
        for path in candidates:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(font_name, path))
                if font_name == "Rubik":
                    fonts["regular"] = font_name
                elif font_name == "Rubik-Bold":
                    fonts["bold"] = font_name
                elif font_name == "Rubik-Medium":
                    fonts["medium"] = font_name
                break
    return fonts


def clean_lines(text: str) -> List[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]


def parse_decimal(value: str) -> Optional[Decimal]:
    cleaned = value.replace("$", "").replace(",", "").strip()
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def money_str(value: Optional[Decimal]) -> str:
    if value is None:
        return ""
    return f"{value:,.2f}"


def extract_payment_data(pdf_bytes: bytes) -> Dict[str, object]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if not reader.pages:
        raise ValueError("The uploaded PDF does not contain any pages.")

    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    lines = clean_lines(text)
    if not lines:
        raise ValueError("No readable text was found in the uploaded PDF.")

    dates = re.findall(r"\b\d{4}/\d{2}/\d{2}\b", text)
    main_date = dates[0] if dates else ""

    bill_id_match = re.search(r"\b\d{4}/\d{2}/\d{2}\b\s+(\d+)\s+\$?([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})", text)
    bill_id = bill_id_match.group(1) if bill_id_match else ""
    bill_amount = parse_decimal(bill_id_match.group(2)) if bill_id_match else None
    payment_amount = parse_decimal(bill_id_match.group(3)) if bill_id_match else None

    total_match = re.search(r"Total\s+\$?([\d,]+\.\d{2})", text, re.IGNORECASE)
    total_amount = parse_decimal(total_match.group(1)) if total_match else payment_amount or bill_amount

    amount_words = ""
    amount_number = total_amount
    amount_line_index = None
    amount_line_pattern = re.compile(r"^(.+?)\s+(\d+(?:,\d{3})*\.\d{2})$")

    for idx, line in enumerate(lines):
        match = amount_line_pattern.match(line)
        if match and not re.fullmatch(r"\d{4}/\d{2}/\d{2}", match.group(1).strip()):
            maybe_words = match.group(1).strip()
            if re.search(r"/100\b", maybe_words, re.IGNORECASE):
                amount_words = maybe_words
                parsed = parse_decimal(match.group(2))
                if parsed is not None:
                    amount_number = parsed
                amount_line_index = idx
                break

    vendor_name = ""
    address_lines: List[str] = []
    if amount_line_index is not None:
        for line in lines[amount_line_index + 1 :]:
            if line.startswith("Bill Date") or line.startswith("Aims Fasteners & Fittings "):
                break
            if not vendor_name:
                vendor_name = line
            else:
                address_lines.append(line)

    # Fallbacks if the simple block parsing fails.
    if not vendor_name:
        for idx, line in enumerate(lines):
            if amount_line_index is not None and idx <= amount_line_index:
                continue
            if line.startswith("Bill Date") or re.fullmatch(r"\d{4}/\d{2}/\d{2}", line):
                continue
            if line.lower().startswith("total"):
                continue
            if "$" in line:
                continue
            if re.fullmatch(r"\d+", line):
                continue
            vendor_name = line
            break

    if vendor_name and not address_lines:
        start_collecting = False
        for line in lines:
            if line == vendor_name:
                start_collecting = True
                continue
            if start_collecting:
                if line.startswith("Bill Date") or line.lower().startswith("total") or "$" in line:
                    break
                if re.fullmatch(r"\d{4}/\d{2}/\d{2}", line):
                    break
                address_lines.append(line)

    month = day = year = ""
    if main_date:
        year, month, day = main_date.split("/")

    return {
        "source_page_count": len(reader.pages),
        "date": main_date,
        "month": month,
        "day": day,
        "year": year,
        "date_spaced": f"{month}  {day}  {year}".strip(),
        "vendor_name": vendor_name,
        "address_lines": address_lines,
        "amount_words": amount_words,
        "bill_id": bill_id,
        "bill_amount": bill_amount,
        "payment_amount": payment_amount,
        "total_amount": total_amount,
        "amount_number": amount_number,
    }


def draw_right(c: canvas.Canvas, x: float, y: float, text: str, font_name: str, size: float):
    c.setFont(font_name, size)
    c.drawRightString(x, y, text)


def draw_stub(c: canvas.Canvas, section: Dict[str, float], data: Dict[str, object], fonts: Dict[str, str]):
    cols = LAYOUT["stub_columns"]

    c.setLineWidth(1)
    c.line(cols["left"], section["line_1_y"], cols["right"], section["line_1_y"])
    c.setLineWidth(2)
    c.line(cols["left"], section["line_2_y"], cols["right"], section["line_2_y"])
    c.setLineWidth(1)

    c.setFont(fonts["regular"], 10)
    c.drawString(cols["company_x"], section["company_y"], str(data.get("vendor_name", "")))
    draw_right(c, cols["date_x"], section["date_y"], str(data.get("date", "")), fonts["regular"], 10)

    c.setFont(fonts["regular"], 9)
    c.drawString(cols["bill_date_x"], section["header_y"], "Bill Date")
    c.drawString(cols["bill_id_x"], section["header_y"], "Bill ID")
    c.drawString(cols["bill_amount_x"], section["header_y"], "Bill Amount")
    c.drawString(cols["payment_amount_x"], section["header_y"], "Payment Amount")

    c.setFont(fonts["regular"], 9)
    c.drawString(cols["bill_date_x"], section["row_y"], str(data.get("date", "")))
    c.drawString(cols["bill_id_x"], section["row_y"], str(data.get("bill_id", "")))
    draw_right(c, cols["bill_amount_x"] + 48, section["row_y"], f"${money_str(data.get('bill_amount'))}", fonts["regular"], 9)
    draw_right(c, cols["amount_x"], section["row_y"], f"${money_str(data.get('payment_amount'))}", fonts["regular"], 9)

    c.drawString(cols["total_label_x"], section["total_y"], "Total")
    draw_right(c, cols["amount_x"], section["total_y"], f"${money_str(data.get('total_amount'))}", fonts["regular"], 9)


def draw_cheque(c: canvas.Canvas, data: Dict[str, object], fonts: Dict[str, str]):
    cheque = LAYOUT["cheque"]

    # Date in spaced boxes: MM  DD  YYYY
    c.setFont(fonts["regular"], 12)
    draw_right(c, cheque["date_x"], cheque["date_y"], str(data.get("date_spaced", "")), fonts["regular"], 12)

    # Amount line
    c.setFont(fonts["regular"], 12)
    c.drawString(cheque["amount_words_x"], cheque["amount_words_y"], str(data.get("amount_words", "")))
    draw_right(c, cheque["amount_num_x"], cheque["amount_num_y"], money_str(data.get("amount_number")), fonts["regular"], 13)

    # Payee / address block
    payee_y = cheque["payee_y"]
    c.setFont(fonts["bold"], 11)
    c.drawString(cheque["payee_x"], payee_y, str(data.get("vendor_name", "")))

    c.setFont(fonts["regular"], 11)
    line_gap = cheque["address_line_gap"]
    for index, line in enumerate(data.get("address_lines", [])):
        c.drawString(cheque["payee_x"], payee_y - ((index + 1) * line_gap), line)


def build_output_pdf(pdf_bytes: bytes) -> bytes:
    data = extract_payment_data(pdf_bytes)
    fonts = register_rubik_fonts()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    draw_stub(c, LAYOUT["top_stub"], data, fonts)
    draw_cheque(c, data, fonts)
    draw_stub(c, LAYOUT["bottom_stub"], data, fonts)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()


st.set_page_config(page_title="Metafix Cheque Reformatter", page_icon="🏦", layout="centered")

st.title("🏦 Metafix Cheque Reformatter")
st.write(
    "Upload a Zoho Books Canadian Voucher PDF and export a clean cheque layout with a top stub, centered cheque, and bottom stub."
)

with st.expander("Notes"):
    st.markdown(
        """
- The cheque block is positioned so its top begins **89 mm from the top of the page**.
- The app rebuilds the page from the text in the Zoho Voucher export rather than shifting the original PDF.
- For an exact Rubik match on Streamlit Cloud, add the Rubik `.ttf` files to your repo. Without them, the app falls back to Helvetica.
- If a particular Zoho export varies slightly, adjust the coordinate values in the `LAYOUT` dictionary near the top of `app.py`.
        """
    )

uploaded_file = st.file_uploader("Upload Zoho Voucher PDF", type=["pdf"])

if uploaded_file is not None:
    source_bytes = uploaded_file.read()

    try:
        parsed = extract_payment_data(source_bytes)
        output_bytes = build_output_pdf(source_bytes)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Vendor", parsed.get("vendor_name") or "—")
            st.metric("Cheque date", parsed.get("date") or "—")
        with col2:
            st.metric("Payment amount", f"${money_str(parsed.get('payment_amount'))}" if parsed.get("payment_amount") is not None else "—")
            st.metric("Bill ID", parsed.get("bill_id") or "—")

        st.download_button(
            label="Download reformatted cheque PDF",
            data=output_bytes,
            file_name="metafix_reformatted_cheque.pdf",
            mime="application/pdf",
        )

        st.success("PDF processed successfully.")
    except Exception as exc:
        st.error(f"Could not process the PDF: {exc}")
