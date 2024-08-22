import os
import re
import json
import requests
import pdfplumber
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_key_value_pairs_from_pdf(pdf_path):
    """Extract key-value pairs from a PDF file."""
    key_value_pairs = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            key_value_pairs[f'key_value_page_{page_num}'] = {}
            pattern = r'([^:\n]+):\s*([^:\n]+(?:\n\s+[^:\n]+)*)'
            matches = re.findall(pattern, text)
            for key, value in matches:
                key = key.strip()
                value = value.strip()
                key_value_pairs[f'key_value_page_{page_num}'][key] = value
    return key_value_pairs

def extract_table_data_from_pdf(pdf_path):
    """Extract table data from a PDF file."""
    table_data = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            table_data[f'table_page_{page_num}'] = {}
            tables = page.extract_tables()
            for table_num, table in enumerate(tables, start=1):
                table_data[f'table_page_{page_num}'][f'table_{table_num}'] = []
                if table and len(table) > 1:
                    headers = [header.strip() if header else '' for header in table[0]]
                    for row in table[1:]:
                        row_values = [cell.strip() if cell else '' for cell in row]
                        table_data[f'table_page_{page_num}'][f'table_{table_num}'].append(dict(zip(headers, row_values)))
    return table_data

def download_file(url, save_path):
    """Download a file from a URL and save it to the specified path."""
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    else:
        raise Exception(f"Failed to download file, status code {response.status_code}. URL: {url}")


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file URL and return extracted data in JSON format."""
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'No URL provided'}), 400

    url = data['url']
    if not url.lower().endswith('.pdf'):
        return jsonify({'error': 'URL does not point to a PDF file'}), 400

    filename = secure_filename(url.split('/')[-1])
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        download_file(url, file_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    if not allowed_file(filename):
        return jsonify({'error': 'Invalid file type'}), 400

    key_value_pairs = extract_key_value_pairs_from_pdf(file_path)
    table_data = extract_table_data_from_pdf(file_path)

    output_data = {
        'key_value_pairs': key_value_pairs,
        'table_data': table_data
    }

    return jsonify(output_data), 200

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True) 
    app.run(debug=True)
