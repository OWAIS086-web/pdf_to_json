import json
import os
import re
import camelot
import pdfplumber
import fitz  # PyMuPDF
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to extract key-value pairs from PDF using PyMuPDF
def extract_key_value_pairs_from_pdf(pdf_path):
    key_value_pairs = {}

    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()

        key_value_pairs[f'key_value_page_{page_num+1}'] = {}

        pattern = r'([^:\n]+):\s*([^:\n]+(?:\n\s+[^:\n]+)*)'
        matches = re.findall(pattern, text)
        for key, value in matches:
            key = key.strip()
            value = value.strip()
            key_value_pairs[f'key_value_page_{page_num+1}'][key] = value

    return key_value_pairs

# Function to extract tables from PDF using Camelot
def extract_table_data_from_pdf(pdf_path):
    table_data = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            table_data[f'table_page_{page_num}'] = {}

            tables = page.extract_tables()
            for table_num, table in enumerate(tables, start=1):
                table_data[f'table_page_{page_num}'][f'table_{table_num}'] = []

                if table is not None and len(table) > 1:
                    headers = [header.strip() if header else '' for header in table[0]]
                    for row in table[1:]:
                        row_values = [cell.strip() if cell else '' for cell in row]
                        table_data[f'table_page_{page_num}'][f'table_{table_num}'].append(dict(zip(headers, row_values)))

    return table_data


# Route to upload file and process
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        key_value_pairs = extract_key_value_pairs_from_pdf(file_path)
        table_data = extract_table_data_from_pdf(file_path)

        output_data = {
            'key_value_pairs': key_value_pairs,
            'table_data': table_data
        }

        json_filename = os.path.splitext(filename)[0] + '.json'
        json_file_path = os.path.join(app.config['OUTPUT_FOLDER'], json_filename)
        with open(json_file_path, 'w') as f:
            json.dump(output_data, f, indent=4)

        return jsonify({'message': 'File successfully uploaded and converted to JSON'}), 200

    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == "__main__":
    app.run(debug=True)
