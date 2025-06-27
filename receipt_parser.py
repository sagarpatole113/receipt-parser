import os
import re
import csv
import pandas as pd
from bs4 import BeautifulSoup
import pdfplumber
from datetime import datetime

# --- STEP 1: Load Schema ---
def load_schema(file_path):
    df = pd.read_excel(file_path)
    df.columns = [col.strip().lower() for col in df.columns]
    if 'schema' not in df.columns or 'data type' not in df.columns:
        raise ValueError("Excel must contain 'Schema' and 'Data type' columns.")
    schema = []
    for _, row in df.iterrows():
        if pd.isna(row['schema']):
            continue
        schema.append({
            "name": row['schema'],
            "type": str(row['data type']).strip().lower()
        })
    return schema


# --- STEP 2A: Extract from HTML Receipt (Swiggy) ---
def extract_data_from_html(soup, filename):
    base_data = {
        "mid": filename.replace(".html", ""),
        "company": "Swiggy",
        "email_timestamp": "2025-06-25T10:00:00",
        "year": 2025,
        "month": 6,
        "day": 25,
    }

    trans_match = soup.find(string=re.compile(r"order id", re.I))
    if trans_match:
        trans_id = re.search(r"order id:\s*(\d+)", trans_match, re.I)
        if trans_id:
            base_data["transaction_id"] = trans_id.group(1)

    address_td = soup.find("td", string=re.compile(r"Rd,", re.I))
    if address_td:
        base_data["address"] = address_td.get_text(strip=True)

    summary_labels = {
        "item bill": "item_bill",
        "handling fee": "handling_fee",
        "convenience fee": "convenience_fee",
        "delivery partner fee": "delivery_fee",
        "grand total": "grand_total"
    }

    for td in soup.find_all("td", string=True):
        label = td.get_text(strip=True).lower()
        if label in summary_labels:
            next_td = td.find_next_sibling("td")
            if next_td:
                base_data[summary_labels[label]] = next_td.get_text(strip=True).replace("₹", "").strip()

    rows = []
    item_rows = soup.find_all("td", string=re.compile(r"^\d+ x ", re.I))

    for item_td in item_rows:
        row = base_data.copy()
        text = item_td.get_text(strip=True)
        qty_name_match = re.match(r"(\d+)\s*x\s*(.+)", text)
        if qty_name_match:
            row["product_sequence"] = qty_name_match.group(1)
            row["product_name"] = qty_name_match.group(2)
            price_td = item_td.find_next_sibling("td")
            if price_td:
                row["product_price"] = price_td.get_text(strip=True).replace("₹", "").strip()
            rows.append(row)

    return rows


# --- STEP 2B: Extract from Zomato PDF ---
def extract_text_from_pdf(pdf_path):
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
    return full_text

def extract_data_from_zomato_pdf(text, filename):
    import re
    from datetime import datetime

    base_data = {
        "mid": filename.replace(".pdf", ""),
        "company": "Zomato"
    }

    def get(pattern, flags=0):
        match = re.search(pattern, text, flags)
        return match.group(1).strip() if match else ""

    base_data["order_id"] = get(r"Order ID:\s*(\d+)")
    base_data["customer_name"] = get(r"Customer Name:\s*(.+)")
    base_data["delivery_address"] = get(r"Delivery Address:\s*(.+)")
    base_data["restaurant_name"] = get(r"Restaurant Name:\s*(.+)")

    addr_match = re.search(r"Restaurant Address:\s*(.+?)\nDelivery partner", text, re.S)
    base_data["restaurant_address"] = addr_match.group(1).replace("\n", " ").strip() if addr_match else ""

    base_data["delivery_partner"] = get(r"Delivery partner.*?:\s*(.+)")

    dt_str = get(r"Order Time:\s*(\d{1,2} \w+ \d{4}, \d{1,2}:\d{2} [APMapm]{2})")
    try:
        dt = datetime.strptime(dt_str, "%d %B %Y, %I:%M %p")
        base_data["email_timestamp"] = dt.isoformat()
        base_data["year"] = dt.year
        base_data["month"] = dt.month
        base_data["day"] = dt.day
    except Exception:
        base_data["email_timestamp"] = ""
        base_data["year"] = base_data["month"] = base_data["day"] = ""

    # Financial fields
    def amount(label):
        match = re.search(rf"{re.escape(label)}\s*(?:\(₹)?₹?([\d\.]+)", text)
        return match.group(1).strip() if match else ""

    base_data["order_convenience_fee"] = amount("Platform fee")
    base_data["order_delivery_fee"] = amount("Delivery charge subtotal")
    base_data["order_cod_fee"] = ""  # Not present
    base_data["order_gift_wrapping_fee"] = ""  # Not present

    # Product rows
    rows = []
    item_pattern = re.compile(r"(.+?)\s+(\d+)\s+₹(\d+)\s+₹(\d+)")
    for match in item_pattern.finditer(text):
        row = base_data.copy()
        row["product_name"] = match.group(1).strip()
        row["product_quantity"] = match.group(2)
        row["product_price"] = match.group(3)
        row["product_total"] = match.group(4)
        row["product_mrp"] = ""  # Optional
        row["product_discount"] = ""  # Optional
        rows.append(row)

    # Subtotal: sum of product_total
    if rows:
        try:
            subtotal = sum(float(row["product_total"]) for row in rows)
            for row in rows:
                row["order_subtotal"] = f"{subtotal:.2f}"
        except Exception:
            for row in rows:
                row["order_subtotal"] = ""
    return rows


# --- STEP 3: Write to Final CSV ---
def write_to_csv(data_list, schema, output_path="final_output.csv"):
    fieldnames = [col["name"] for col in schema]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data_list:
            full_row = {key: row.get(key, "") for key in fieldnames}
            writer.writerow(full_row)


# --- STEP 4: Main ---
def main():
    schema = load_schema("schema.xlsx")
    receipt_folder = "receipts"
    all_data = []

    for filename in os.listdir(receipt_folder):
        file_path = os.path.join(receipt_folder, filename)

        if filename.lower().endswith(".html"):
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
                rows = extract_data_from_html(soup, filename)
                all_data.extend(rows)

        elif filename.lower().endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
            rows = extract_data_from_zomato_pdf(text, filename)
            print(f"🧪 Extracted from PDF: {len(rows)} rows from {filename}")
            all_data.extend(rows)

    write_to_csv(all_data, schema)
    print(f"✅ Parsed {len(all_data)} rows from 'receipts/'. Output saved to 'final_output.csv'")

if __name__ == "__main__":
    main()
