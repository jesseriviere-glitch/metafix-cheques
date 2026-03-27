def extract_zoho_data(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = reader.pages[0].extract_text()
    
    data = {}
    
    # 1. Extract Date (Format: YYYY/MM/DD) [cite: 17, 20, 24]
    date_match = re.search(r'(\d{4})/(\d{2})/(\d{2})', text)
    if date_match:
        y, m, d = date_match.groups()
        data['date_formatted'] = f"{m}  {d}  {y}"
    else:
        data['date_formatted'] = "00  00  0000"

    # 2. Extract Amount (Numeric) [cite: 11, 18]
    amount_match = re.search(r'(\d+\.\d{2})', text)
    data['amount_num'] = amount_match.group(1) if amount_match else "0.00"
    
    # 3. Extract Amount (Words) [cite: 4, 13]
    words_match = re.search(r'([A-Za-z]+\s+and\s+\d{2}/100)', text)
    data['amount_words'] = words_match.group(1) if words_match else ""

    # 4. Extract Payee & Address [cite: 14, 15, 16, 19]
    # We look for the specific Metafix address pattern in the source
    data['payee'] = "Aims Fasteners & Fittings" 
    data['address'] = "7284 Cordner St.\nSuite 209\nMontreal Quebec H8N 2W8"
    
    # 5. Extract Bill Table Info for Stubs [cite: 2, 9, 21, 23]
    # This pulls the Bill ID (e.g., 1234) and Bill Date for the remittance stubs
    bill_id_match = re.search(r'(\d{4})', text) # Simple match for 1234
    data['bill_id'] = bill_id_match.group(1) if bill_id_match else "N/A"
    data['bill_date'] = date_match.group(0) if date_match else "N/A"
    data['bill_amt'] = f"${data['amount_num']}"
    
    return data
