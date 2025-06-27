# 🧾 E-Receipt Parser (HTML + PDF)

This project extracts structured data from Swiggy (HTML) and Zomato (PDF) e-receipts and generates a standardized CSV output based on a predefined schema.

It is designed for use in data engineering tasks where input data is semi-structured (emails, receipts) and needs to be cleaned, normalized, and formatted for analysis or database insertion.

## 📦 Features

- ✅ Parses Swiggy receipts in `.html` format using BeautifulSoup  
- ✅ Parses Zomato receipts in `.pdf` format using pdfplumber  
- ✅ Supports multi-item receipts (each row per product)  
- ✅ Extracts data such as item names, prices, customer info, address, order summary, and more  
- ✅ Validates and maps data fields according to `schema.xlsx`  
- ✅ Outputs a clean `final_output.csv` ready for analysis or ingestion  

## 🧰 Tech Stack

- **Python 3.8+**
- **pandas** – for schema & CSV operations  
- **BeautifulSoup** – for parsing HTML receipts  
- **pdfplumber** – for parsing PDF receipts  
- **openpyxl** – to read `.xlsx` schema file  

## 🗂️ Project Structure

html-receipt-parser/
├── receipts/ # All .html and .pdf receipts go here
│ ├── swiggy_123.html
│ ├── Order_ID_6438474982.pdf
│ └── ...
├── schema.xlsx # The schema to map extracted fields to
├── receipt_parser.py # Main script to extract, clean, and export data
├── final_output.csv # Output file (auto-generated)
├── requirements.txt # List of dependencies (optional)
└── README.md # This file


## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/html-receipt-parser.git
cd html-receipt-parser

(Optional) Set Up a Virtual Environment
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

Install Dependencies

pip install -r requirements.txt

Run the Script

python receipt_parser.py
