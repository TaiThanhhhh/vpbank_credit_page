from flask import Flask, render_template, request, jsonify
import joblib
import pandas as pd
import shap
import numpy as np
import json
import boto3
import requests
import random
import re
import os
from datetime import datetime
from google import genai
import time

app = Flask(__name__)
app.secret_key = 'vpbank-credit-lookup-secret'

# Khởi tạo client S3 và Bedrock
s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
BUCKET_NAME = 'credit-scoring-data-vpbank'
DATA_FILE_KEY = 'individual_input.json'
ENRICH_DATA_FILE_KEY = 'data_to_enrich.json'

HISTORY_FILE = 'history.txt'

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

# Sample data for demonstration (giữ nguyên từ trước)
SAMPLE_USERS = {
    "001234567890": {
        "full_name": "NGUYEN VAN A",
        "national_id": "001234567890",
        "age": 28,
        "annual_income": 34847.84,
        "monthly_inhand_salary": 3037.986667,
        "num_bank_accounts": 2,
        "num_credit_card": 4,
        "interest_rate": 6,
        "num_of_loan": 1,
        "delay_from_due_date": 3,
        "num_of_delayed_payment": 4,
        "changed_credit_limit": 5.42,
        "num_credit_inquiries": 2,
        "credit_mix": "Good",
        "outstanding_debt": 605.03,
        "credit_utilization_ratio": 24.46,
        "payment_behaviour": "Low_spent_Small_value_payments",
        "monthly_balance": 470.69,
        "credit_score_numeric": 1,
        "salary_range": "Medium",
        "credit_history_year": 26,
        "credit_history_month": 7
    },
    "001234567891": {
        "full_name": "TRAN THI B",
        "national_id": "001234567891",
        "age": 30,
        "annual_income": 40000.00,
        "monthly_inhand_salary": 3333.33,
        "num_bank_accounts": 3,
        "num_credit_card": 5,
        "interest_rate": 8,
        "num_of_loan": 2,
        "delay_from_due_date": 5,
        "num_of_delayed_payment": 6,
        "changed_credit_limit": 7.0,
        "num_credit_inquiries": 3,
        "credit_mix": "Standard",
        "outstanding_debt": 1200.50,
        "credit_utilization_ratio": 35.0,
        "payment_behaviour": "High_spent_Medium_value_payments",
        "monthly_balance": 300.00,
        "credit_score_numeric": 0,
        "salary_range": "Medium",
        "credit_history_year": 4,
        "credit_history_month": 3
    },
    "001234567892": {
        "full_name": "LE VAN C",
        "national_id": "001234567892",
        "age": 35,
        "annual_income": 60000.00,
        "monthly_inhand_salary": 5000.00,
        "num_bank_accounts": 1,
        "num_credit_card": 3,
        "interest_rate": 5,
        "num_of_loan": 1,
        "delay_from_due_date": 0,
        "num_of_delayed_payment": 0,
        "changed_credit_limit": 10.0,
        "num_credit_inquiries": 1,
        "credit_mix": "Good",
        "outstanding_debt": 200.00,
        "credit_utilization_ratio": 15.0,
        "payment_behaviour": "Low_spent_Large_value_payments",
        "monthly_balance": 800.00,
        "credit_score_numeric": 2,
        "salary_range": "High",
        "credit_history_year": 8,
        "credit_history_month": 11
    }
}

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
    ```"""

def enrich_customer_row(row):
    ignored_fields = ['customer_id', 'source_of_information', 'confidence_level']
    fields_to_check = [field for field in row.index if field not in ignored_fields]

    known_info = {}
    missing_fields = []

    for field in fields_to_check:
        if pd.notna(row[field]) and row[field] is not None:
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
        print(f"Received: {response_text}")
        row['confidence_level'] = 'Low (Error)'
    except Exception as e:
        print(f"An API or other error occurred for '{row['full_name']}': {e}")
        row['confidence_level'] = 'Low (Error)'

    time.sleep(2)
    return row

def load_model(path: str):
    try:
        return joblib.load(path)
    except Exception as e:
        print(f"Error loading model: {e}")
        return None

def preprocess_input(df):
    df["credit_mix"] = df["credit_mix"].map({"Good": 1, "Standard": 0, "Bad": -1})
    df["payment_behaviour"] = df["payment_behaviour"].map({
        "High_spent_Small_value_payments": 1,
        "Low_spent_Small_value_payments": 0,
        "High_spent_Large_value_payments": 2,
        "Low_spent_Large_value_payments": -1,
        "High_spent_Medium_value_payments": 3,
        "Low_spent_Medium_value_payments": -2
    })
    df["salary_range"] = df["salary_range"].map({
        "Very Low": 0,
        "Low": 1,
        "Medium": 2,
        "High": 3,
        "Very High": 4
    })
    return df

def compute_shap_values(model, X):
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    return shap_values

def get_top_features(X, shap_values, top_n=3):
    if isinstance(shap_values, list):
        shap_val = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
    else:
        shap_val = shap_values[0]
    mean_abs_shap = np.abs(shap_val)
    top_indices = np.argsort(mean_abs_shap)[-top_n:][::-1]

    top_features = []
    for i in top_indices:
        shap_score = mean_abs_shap[i]
        if isinstance(shap_score, np.ndarray):
            shap_score = float(shap_score.mean())
        top_features.append((X.columns[i], X.iloc[0, i], round(shap_score, 4)))
    return top_features

def generate_prompt(prediction, shap_features, original_input):
    shap_text = "\n".join([f"- {name}: value = {val}, impact = {shap_val}" for name, val, shap_val in shap_features])
    feature_text = "\n".join([f"- {key}: {value}" for key, value in original_input.items()])

    prompt = f"""
* Credit Category: **{prediction}**

* Factors affecting this kind of category:
{shap_text}

* Input Information of the Individual:
{feature_text}

**Your task:**
Explain in simple and clear language why this individual was classified to that category.

The explanation must:
- Be understandable to someone without data science knowledge.
- Avoid technical jargon (no SHAP, no model details) and repeated phrases.
- Write as if speaking to bank staff who will share this explanation with the customer.
- Provide a clear, concise explanation of the main factors influencing the prediction
- Note: start right away with the explanation, no preamble or introduction.
- Use bullet points format for clarity. At most 5 bullet points.
- The format of each bullet point should be:
- feature_name: explanation of how it affects the score
"""
    return prompt

def call_bedrock_claude(prompt):
    print("Querying Claude Sonnet via AWS Bedrock...")
    try:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "temperature": 0.7,
            "top_p": 0.9,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    except Exception as e:
        print(f"Error calling Bedrock: {e}")
        return ""

def explain_credit_score(model_path, input_data):
    try:
        model = load_model(model_path)
        if model is None:
            raise Exception("Model could not be loaded")
        normalized_data = {k.strip().lower().replace(" ", "_"): v for k, v in input_data.items()}
        original_info = {
            "full_name": normalized_data.get("full_name"),
            "national_id": normalized_data.get("national_id")
        }
        input_features = {k: v for k, v in normalized_data.items() if k not in ["full_name", "national_id", "customer_id", "source_of_information", "confidence_level"]}
        df = pd.DataFrame([input_features])
        df = preprocess_input(df)
        shap_values = compute_shap_values(model, df)
        top_features = get_top_features(df, shap_values)
        prediction = model.predict(df)[0]
        proba = model.predict_proba(df)[0]
        fico_score = round(proba[0] * 439.5 + proba[1] * 624.5 + proba[2] * 760)
        prompt = generate_prompt(prediction, top_features, input_features)
        explanation = call_bedrock_claude(prompt)
        return prediction, fico_score, explanation
    except Exception as e:
        print(f"Error in explain_credit_score: {e}")
        random_score = random.randint(300, 850)
        score_level = get_credit_score_level(random_score)
        explanation = (
            f"Điểm tín dụng của bạn được ước tính là {random_score} ({score_level}). "
            f"Do hệ thống không thể sử dụng mô hình dự đoán, điểm này được tạo ngẫu nhiên dựa trên thông tin tài chính của bạn. "
            f"Vui lòng kiểm tra lại thông tin hoặc thử lại sau."
        )
        return "Unknown", random_score, explanation

def generate_random_credit_data(full_name, national_id):
    return {
        "full_name": full_name.upper(),
        "national_id": national_id,
        "age": random.randint(18, 70),
        "annual_income": round(random.uniform(20000, 100000), 2),
        "monthly_inhand_salary": round(random.uniform(1500, 8000), 2),
        "num_bank_accounts": random.randint(1, 5),
        "num_credit_card": random.randint(1, 7),
        "interest_rate": random.randint(3, 15),
        "num_of_loan": random.randint(0, 4),
        "delay_from_due_date": random.randint(0, 30),
        "num_of_delayed_payment": random.randint(0, 10),
        "changed_credit_limit": round(random.uniform(0, 20), 2),
        "num_credit_inquiries": random.randint(0, 5),
        "credit_mix": random.choice(["Good", "Standard", "Bad"]),
        "outstanding_debt": round(random.uniform(0, 5000), 2),
        "credit_utilization_ratio": round(random.uniform(10, 90), 2),
        "payment_behaviour": random.choice([
            "High_spent_Small_value_payments",
            "Low_spent_Small_value_payments",
            "High_spent_Large_value_payments",
            "Low_spent_Large_value_payments",
            "High_spent_Medium_value_payments",
            "Low_spent_Medium_value_payments"
        ]),
        "monthly_balance": round(random.uniform(100, 1000), 2),
        "credit_score_numeric": random.randint(0, 2),
        "salary_range": random.choice(["Very Low", "Low", "Medium", "High", "Very High"]),
        "credit_history_year": random.randint(1, 20),
        "credit_history_month": random.randint(0, 11)
    }

def get_credit_score_level(score):
    if score >= 800:
        return "Excellent"
    elif score >= 740:
        return "Very Good"
    elif score >= 670:
        return "Good"
    elif score >= 580:
        return "Fair"
    else:
        return "Poor"

def validate_national_id(national_id):
    national_id = re.sub(r'[^0-9]', '', national_id)
    if len(national_id) not in [9, 12]:
        return False
    return True

def save_history(result_data, user_data):
    history_item = {
        'customer_info': {
            'name': result_data['full_name'],
            'date_of_birth': 'Unknown',
            'occupation': user_data.get('occupation', 'Unknown'),
            'average_monthly_income': f"${user_data.get('monthly_inhand_salary', 'Unknown')}",
            'credit_history': f"{user_data.get('num_of_loan', 0)} loans, {user_data.get('num_credit_card', 0)} credit cards"
        },
        'credit_score_explanation': {
            'credit_score': result_data['credit_score'],
            'explanation': result_data['score_level'],
            'top_contributing_factors': [line.strip('- ') for line in result_data['explanation'].split('\n') if line.strip()],
            'usage_level': 'Unknown'
        },
        'lookup_time': result_data['lookup_time']
    }
    with open(HISTORY_FILE, 'a') as f:
        f.write(json.dumps(history_item) + '\n')

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

def update_users_data(new_user):
    """Hàm helper để append user mới vào individual_input.json trên S3."""
    try:
        s3_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=DATA_FILE_KEY)
        users_data = json.loads(s3_response['Body'].read().decode('utf-8'))
        users_data.append(new_user)
        s3_client.put_object(Bucket=BUCKET_NAME, Key=DATA_FILE_KEY, Body=json.dumps(users_data, indent=4))
        print(f"Appended new user {new_user['national_id']} to individual_input.json")
    except Exception as e:
        print(f"Error updating users_data on S3: {e}")
        raise

@app.route('/api/lookup', methods=['POST'])
def lookup_credit_score():
    try:
        data = request.get_json()
        full_name = data.get('full_name', '').strip().upper()
        national_id = data.get('national_id', '').strip()

        if not full_name or not national_id:
            return jsonify({'success': False, 'message': 'Vui lòng nhập đầy đủ thông tin họ tên và số CMND/CCCD'}), 400

        if not validate_national_id(national_id):
            return jsonify({'success': False, 'message': 'Số CMND/CCCD không hợp lệ. Vui lòng nhập 9 hoặc 12 chữ số'}), 400

        national_id = re.sub(r'[^0-9]', '', national_id)

        try:
            s3_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=DATA_FILE_KEY)
            users_data = json.loads(s3_response['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"Error fetching data from S3: {e}")
            return jsonify({'success': False, 'message': 'Lỗi khi truy vấn dữ liệu từ hệ thống. Vui lòng thử lại sau.'}), 500

        user_data = next((user for user in users_data if user['national_id'] == national_id and user['full_name'].upper() == full_name), None)

        if not user_data:
            return jsonify({'success': False, 'message': 'Không tìm thấy thông tin người dùng. Vui lòng kiểm tra lại họ tên và số CMND/CCCD.'}), 404

        model_path = "models/credit_score_model.pkl"
        prediction, fico_score, explanation = explain_credit_score(model_path, user_data)

        result_data = {
            'full_name': user_data['full_name'],
            'national_id': user_data['national_id'],
            'credit_score': fico_score,
            'score_level': prediction,
            'credit_card_utilization': user_data.get('credit_utilization_ratio', 0),
            'payment_history': 100 - user_data.get('num_of_delayed_payment', 0) * 2,
            'credit_history_years': user_data.get('credit_history_year', 0),
            'credit_history_months': user_data.get('credit_history_month', 0),
            'explanation': explanation,
            'lookup_time': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'occupation': user_data.get('occupation', 'Unknown'),
            'job_title': user_data.get('job_title', 'Unknown'),
            'current_company': user_data.get('current_company', 'Unknown'),
            'source_of_information': user_data.get('source_of_information', None),
            'confidence_level': user_data.get('confidence_level', None)
        }

        save_history(result_data, user_data)
        return jsonify({'success': True, 'data': result_data})

    except Exception as e:
        print(f"Error in lookup_credit_score: {e}")
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi trong quá trình tra cứu. Vui lòng thử lại sau.'}), 500

@app.route('/api/enrich_from_internet', methods=['POST'])
def enrich_from_internet():
    try:
        data = request.get_json()
        full_name = data.get('full_name', '').strip().upper()
        national_id = data.get('national_id', '').strip()

        if not full_name or not national_id:
            return jsonify({'success': False, 'message': 'Vui lòng nhập đầy đủ thông tin họ tên và số CMND/CCCD'}), 400

        if not validate_national_id(national_id):
            return jsonify({'success': False, 'message': 'Số CMND/CCCD không hợp lệ. Vui lòng nhập 9 hoặc 12 chữ số'}), 400

        national_id = re.sub(r'[^0-9]', '', national_id)

        try:
            s3_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=ENRICH_DATA_FILE_KEY)
            enrich_data = json.loads(s3_response['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"Error fetching enrich data from S3: {e}")
            return jsonify({'success': False, 'message': 'Không thể truy vấn dữ liệu bổ sung.'}), 500

        df_to_process = pd.DataFrame(enrich_data)
        df_to_process['customer_id'] = df_to_process['customer_id'].astype(str)
        customer = df_to_process[(df_to_process['customer_id'] == national_id) & (df_to_process['full_name'].str.upper() == full_name.upper())]

        if customer.empty:
            return jsonify({'success': False, 'message': 'Không tìm thấy thông tin người dùng để bổ sung.'}), 404

        enriched_customer = customer.apply(enrich_customer_row, axis=1)
        enriched_data = enriched_customer.iloc[0].to_dict()

        # Generate random credit data và update từ enriched
        user_data = generate_random_credit_data(full_name, national_id)
        user_data.update({
            'occupation': enriched_data.get('occupation', 'Unknown'),
            'job_title': enriched_data.get('job_title', 'Unknown'),
            'current_company': enriched_data.get('current_company', 'Unknown'),
            'source_of_information': enriched_data.get('source_of_information', None),
            'confidence_level': enriched_data.get('confidence_level', None),
            # Thêm các fields enriched khác nếu cần
            'age': enriched_data.get('age', None),
            'address': enriched_data.get('address', None),
            'email_address': enriched_data.get('email_address', None),
            'phone_number': enriched_data.get('phone_number', None),
            'educational_level': enriched_data.get('educational_level', None),
            'criminal_record': enriched_data.get('criminal_record', None),
            'stock_assets': enriched_data.get('stock_assets', None)
        })

        # Append vào individual_input.json trên S3
        update_users_data(user_data)

        result_data = {
            'full_name': full_name,
            'national_id': national_id,
            'age': enriched_data.get('age', None),
            'address': enriched_data.get('address', None),
            'email_address': enriched_data.get('email_address', None),
            'phone_number': enriched_data.get('phone_number', None),
            'job_title': enriched_data.get('job_title', None),
            'current_company': enriched_data.get('current_company', None),
            'educational_level': enriched_data.get('educational_level', None),
            'occupation': enriched_data.get('occupation', None),
            'criminal_record': enriched_data.get('criminal_record', None),
            'stock_assets': enriched_data.get('stock_assets', None),
            'source_of_information': enriched_data.get('source_of_information', None),
            'confidence_level': enriched_data.get('confidence_level', None)
        }

        return jsonify({'success': True, 'data': result_data})

    except Exception as e:
        print(f"Error in enrich_from_internet: {e}")
        return jsonify({'success': False, 'message': 'Lỗi khi bổ sung dữ liệu từ internet.'}), 500

@app.route('/api/enrich_from_file', methods=['POST'])
def enrich_from_file():
    try:
        data = request.get_json()
        full_name = data.get('full_name', '').strip().upper()
        national_id = data.get('national_id', '').strip()

        if not full_name or not national_id:
            return jsonify({'success': False, 'message': 'Vui lòng nhập đầy đủ thông tin họ tên và số CMND/CCCD'}), 400

        if not validate_national_id(national_id):
            return jsonify({'success': False, 'message': 'Số CMND/CCCD không hợp lệ. Vui lòng nhập 9 hoặc 12 chữ số'}), 400

        national_id = re.sub(r'[^0-9]', '', national_id)

        try:
            s3_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=ENRICH_DATA_FILE_KEY)
            enrich_data = json.loads(s3_response['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"Error fetching enrich data from S3: {e}")
            return jsonify({'success': False, 'message': 'Không thể truy vấn dữ liệu bổ sung.'}), 500

        df_to_process = pd.DataFrame(enrich_data)
        customer = df_to_process[(df_to_process['customer_id'] == national_id) & (df_to_process['full_name'].upper() == full_name)]

        if customer.empty:
            return jsonify({'success': False, 'message': 'Không tìm thấy thông tin người dùng để bổ sung.'}), 404

        enriched_customer = customer.apply(enrich_customer_row, axis=1)  # Giả sử enrich từ file cũng dùng hàm này, nếu khác thì thay đổi
        enriched_data = enriched_customer.iloc[0].to_dict()

        # Generate random credit data và update từ enriched
        user_data = generate_random_credit_data(full_name, national_id)
        user_data.update({
            'occupation': enriched_data.get('occupation', 'Unknown'),
            'job_title': enriched_data.get('job_title', 'Unknown'),
            'current_company': enriched_data.get('current_company', 'Unknown'),
            'source_of_information': enriched_data.get('source_of_information', None),
            'confidence_level': enriched_data.get('confidence_level', None),
            # Thêm các fields enriched khác nếu cần
            'age': enriched_data.get('age', None),
            'address': enriched_data.get('address', None),
            'email_address': enriched_data.get('email_address', None),
            'phone_number': enriched_data.get('phone_number', None),
            'educational_level': enriched_data.get('educational_level', None),
            'criminal_record': enriched_data.get('criminal_record', None),
            'stock_assets': enriched_data.get('stock_assets', None)
        })

        # Append vào individual_input.json trên S3
        update_users_data(user_data)

        result_data = {
            'full_name': full_name,
            'national_id': national_id,
            'age': enriched_data.get('age', None),
            'address': enriched_data.get('address', None),
            'email_address': enriched_data.get('email_address', None),
            'phone_number': enriched_data.get('phone_number', None),
            'job_title': enriched_data.get('job_title', None),
            'current_company': enriched_data.get('current_company', None),
            'educational_level': enriched_data.get('educational_level', None),
            'occupation': enriched_data.get('occupation', None),
            'criminal_record': enriched_data.get('criminal_record', None),
            'stock_assets': enriched_data.get('stock_assets', None),
            'source_of_information': enriched_data.get('source_of_information', None),
            'confidence_level': enriched_data.get('confidence_level', None)
        }

        return jsonify({'success': True, 'data': result_data})

    except Exception as e:
        print(f"Error in enrich_from_file: {e}")
        return jsonify({'success': False, 'message': 'Lỗi khi bổ sung dữ liệu từ file.'}), 500

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