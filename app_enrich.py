from flask import Flask, render_template, request, jsonify
import joblib
import pandas as pd
import numpy as np
import json
import boto3
import requests
import random
import re
import os
from google import genai
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'vpbank-credit-lookup-secret'

# Khởi tạo client S3 và Bedrock
s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')  # Thay region nếu cần
BUCKET_NAME = 'credit-scoring-data-vpbank'  # Thay bằng bucket name thực
DATA_FILE_KEY = 'data_to_enrich.json'  # Thay bằng key file JSON trên S3

# Đường dẫn file lưu lịch sử
HISTORY_FILE = 'history.txt'


# innitialze LLMs
try:
    GOOGLE_API_KEY = "AIzaSyCI6IiiRj3O9SygGcZy5FbtWFE2F78g-LA"
    os.environ['GOOGLE_API_KEY'] = GOOGLE_API_KEY
    client = genai.Client()
    print("Google AI Client initialized successfully.")
except Exception as e:
    print(f"An error occurred during API configuration: {e}")

MODEL_ID = "gemini-2.5-flash"
GROUNDING_CONFIG = {"tools": [{"google_search": {}}]}
print(f"Using model: {MODEL_ID}")

def create_dynamic_prompt(known_info, missing_fields):
    known_info_str = "\n".join([f"- {key.replace('_', ' ').title()}: {value}" for key, value in known_info.items()])
    missing_fields_str = ", ".join([f"'{field}'" for field in missing_fields])

    return f"""
    You are a highly-skilled data enrichment AI assistant. Your task is to find public information about individuals using your search tool.

    **CRITICAL RULES:**
     **RULES:**
    1. Do not guess. If not found, return `null`.
    2. You MUST include source URLs in a 'sources' field.
    3. For 'criminal_record', return boolean `true` if a public record of legal convictions is found, otherwise return `false`.
    4. For 'stock_assets', estimate the total value of their public stock assets in VND and return an integer. If no info, return `null`.
    5. Return ONLY a valid JSON object.
    
    **KNOWN INFORMATION:**
    {known_info_str}

    **TASK:**
    Find the values for the following MISSING fields: {missing_fields_str}.

    **REQUIRED JSON OUTPUT FORMAT:**
    Provide a JSON object with keys for the missing fields AND a 'sources' key.
    ```json
    {{
      "age": 55,
      "job_title": "Chairman",
      "educational_level": null,
      "sources": ["https://www.forbes.com/profile/pham-nhat-vuong/", "https://en.wikipedia.org/wiki/Ph%E1%BA%A1m_Nh%E1%BA%ADt_V%C6%B0%E1%BB%A3ng"]
    }}
    ```
    """
def enrich_customer_row(row):
    ignored_fields = ['customer_id', 'source_of_information', 'confidence_level']
    fields_to_check = [field for field in row.index if field not in ignored_fields]

    known_info = {}
    missing_fields = []

    for field in fields_to_check:
        if pd.notna(row[field]):
            known_info[field] = row[field]
        else:
            missing_fields.append(field)

    if not missing_fields:
        print(f"Skipping '{row['full_name']}': No data to enrich.")
        return row

    print(f"Processing '{row['full_name']}': Looking for {', '.join(missing_fields)}...")

    prompt = create_dynamic_prompt(known_info, missing_fields)

    try:
        response = client.models.generate_content(
            model=f"models/{MODEL_ID}",
            contents=prompt,
            config={"tools": [{"google_search": {}}]},
        )

        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        extracted_data = json.loads(response_text)

        if isinstance(extracted_data, dict):
            print(f"Successfully processed '{row['full_name']}'.")

            for field, value in extracted_data.items():
                if field in missing_fields:
                    row[field] = value

            sources_list = extracted_data.get('sources', [])
            if sources_list:
                row['source_of_information'] = str(sources_list)
                row['confidence_level'] = 'High (Source Provided)'
            else:
                row['confidence_level'] = 'Medium (No Source)'
        else:
            print(f"No information found for '{row['full_name']}'.")
            row['confidence_level'] = 'Low (Not Found)'

    except json.JSONDecodeError:
        print(f"JSON Decode Error for '{row['full_name']}'. Response was not valid JSON.")
        print(f"Received: {response.text}")
        row['confidence_level'] = 'Low (Error)'
    except Exception as e:
        print(f"An API or other error occurred for '{row['full_name']}': {e}")
        row['confidence_level'] = 'Low (Error)'

    time.sleep(2)
    return row
def save_history(result_data):
    with open(HISTORY_FILE, 'a') as f:
        f.write(result_data + '\n')

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, 'r') as f:
        return [json.loads(line.strip()) for line in f if line.strip()]

def clear_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ping', methods=['GET'])
def ping():
    return "OK", 200
    
@app.route('/api/lookup', methods=['POST'])
def lookup_credit_score():
    try:
        data = request.get_json()
        full_name = data.get('full_name', '').strip().upper()  # Upper để khớp
        cus_id = data.get('national_id', '').strip()
        
        # Validate input
        if not full_name or not cus_id:
            return jsonify({'success': False, 'message': 'Vui lòng nhập đầy đủ thông tin họ tên và số customer id'}), 400
        
        cus_id = re.sub(r'[^0-9]', '', cus_id)
        
        # Truy vấn S3 để lấy dữ liệu
        try:
            s3_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=DATA_FILE_KEY)
            users_data = json.loads(s3_response['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"Error fetching data from S3: {e}")
            return jsonify({'success': False, 'message': 'Lỗi khi truy vấn dữ liệu từ hệ thống. Vui lòng thử lại sau.'}), 500
        
        # Tìm user khớp cus_id và full_name
        df_to_process = pd.DataFrame(users_data)
        customer = df_to_process[(df_to_process['customer_id'] == cus_id) & (df_to_process['full_name'].upper() == full_name.upper())]

        if not customer:
            return jsonify({'success': False, 'message': 'Không tìm thấy thông tin người dùng. Vui lòng kiểm tra lại họ tên và số customer id.'}), 404
        
        # Run prediction
        enriched_customer = customer.apply(enrich_customer_row, axis=1)
        enriched_customer['lookup_time'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        print("dadad: ",enriched_customer)
        
        result_data = enriched_customer.iloc[0].to_json(index=False)
        
        # Lưu lịch sử
        save_history(result_data)
        
        return jsonify({'success': True, 'data': result_data})
        
    except Exception as e:
        print(f"Error in lookup_credit_score: {e}")
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi trong quá trình tra cứu. Vui lòng thử lại sau.'}), 500

@app.route('/api/history', methods=['GET'])
def get_credit_history():
    history = load_history()
    return jsonify({
        'success': True,
        'data': history
    })

@app.route('/api/clear_history', methods=['POST'])
def clear_history_route():
    clear_history()
    return jsonify({'success': True})

@app.route('/api/tips', methods=['GET'])
def get_credit_tips():
    """API lấy tips cải thiện điểm tín dụng"""
    tips = [
        "Pay bills on time to maintain a good payment history",
        "Keep credit card usage below 30% of the credit limit",
        "Do not close old credit accounts to maintain a long credit history",
        "Check your credit report regularly to detect errors",
        "Diversify types of credit (credit cards, bank loans, etc.)",
        "Avoid opening too many new credit accounts in a short period"
    ]
    return jsonify({
        'success': True,
        'data': tips
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)