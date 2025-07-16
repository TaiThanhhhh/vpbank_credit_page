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
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'vpbank-credit-lookup-secret'

# Khởi tạo client S3 và Bedrock
s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')  # Thay region nếu cần
BUCKET_NAME = 'credit-scoring-data-vpbank'  # Thay bằng bucket name thực
DATA_FILE_KEY = 'individual_input.json'  # Thay bằng key file JSON trên S3

# Sample data for demonstration
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

# Load model
def load_model(path: str):
    try:
        return joblib.load(path)
    except Exception as e:
        print(f"Error loading model: {e}")
        return None

# Preprocess input (tích hợp từ file đầu tiên)
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

# Compute SHAP values (tích hợp từ file đầu tiên)
def compute_shap_values(model, X):
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    return shap_values

# Get top features (tích hợp từ file đầu tiên)
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
            shap_score = float(shap_score.mean())  # hoặc shap_score[0]
        top_features.append((X.columns[i], X.iloc[0, i], round(shap_score, 4)))

    return top_features

# Generate prompt (tích hợp từ file đầu tiên)
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

# Call Bedrock Claude (tích hợp từ file đầu tiên, sử dụng Claude 3 Sonnet như file đầu)
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
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",  # Claude 3 Sonnet như file đầu
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    except Exception as e:
        print(f"Error calling Bedrock: {e}")
        return ""

# Explain credit score (tích hợp đầy đủ logic từ hàm explain_credit_score của file đầu tiên)
def explain_credit_score(model_path, input_data):
    try:
        # Load model
        model = load_model(model_path)
        if model is None:
            raise Exception("Model could not be loaded")

        # Chuẩn hóa key để tránh lỗi 'Full Name' vs 'full_name'
        normalized_data = {k.strip().lower().replace(" ", "_"): v for k, v in input_data.items()}

        # Tách original_info và input_data
        original_info = {
            "full_name": normalized_data.get("full_name"),
            "national_id": normalized_data.get("national_id")
        }

        input_features = {k: v for k, v in normalized_data.items() if k not in ["full_name", "national_id"]}

        df = pd.DataFrame([input_features])
        df = preprocess_input(df)

        # SHAP
        shap_values = compute_shap_values(model, df)
        top_features = get_top_features(df, shap_values)

        # Predict class & probability
        prediction = model.predict(df)[0]
        proba = model.predict_proba(df)[0]
        fico_score = round(proba[0] * 439.5 + proba[1] * 624.5 + proba[2] * 760)

        # Prompt
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
    """Tạo dữ liệu tín dụng ngẫu nhiên cho user mới"""
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
    """Xác định mức độ điểm tín dụng"""
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
    """Kiểm tra định dạng CMND/CCCD"""
    national_id = re.sub(r'[^0-9]', '', national_id)
    if len(national_id) not in [9, 12]:
        return False
    return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/lookup', methods=['POST'])
def lookup_credit_score():
    try:
        data = request.get_json()
        full_name = data.get('full_name', '').strip().upper()  # Upper để khớp
        national_id = data.get('national_id', '').strip()
        
        # Validate input
        if not full_name or not national_id:
            return jsonify({'success': False, 'message': 'Vui lòng nhập đầy đủ thông tin họ tên và số CMND/CCCD'}), 400
        
        # Validate national ID
        if not validate_national_id(national_id):
            return jsonify({'success': False, 'message': 'Số CMND/CCCD không hợp lệ. Vui lòng nhập 9 hoặc 12 chữ số'}), 400
        
        # Clean national ID
        national_id = re.sub(r'[^0-9]', '', national_id)
        
        # Truy vấn S3 để lấy dữ liệu
        try:
            s3_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=DATA_FILE_KEY)
            users_data = json.loads(s3_response['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"Error fetching data from S3: {e}")
            return jsonify({'success': False, 'message': 'Lỗi khi truy vấn dữ liệu từ hệ thống. Vui lòng thử lại sau.'}), 500
        
        # Tìm user khớp national_id và full_name
        user_data = next((user for user in users_data if user['national_id'] == national_id and user['full_name'].upper() == full_name), None)
        
        if not user_data:
            return jsonify({'success': False, 'message': 'Không tìm thấy thông tin người dùng. Vui lòng kiểm tra lại họ tên và số CMND/CCCD.'}), 404
        
        # Run prediction
        model_path = "models/credit_score_model.pkl"
        prediction, fico_score, explanation = explain_credit_score(model_path, user_data)
        print("dadad: ", prediction, fico_score, explanation)
        
        return jsonify({
            'success': True,
            'data': {
                'full_name': user_data['full_name'],
                'national_id': user_data['national_id'],
                'credit_score': fico_score,  # Sử dụng fico_score từ hàm tích hợp
                'score_level': prediction,  # Sử dụng prediction làm category (Poor/Standard/Good)
                'credit_card_utilization': user_data['credit_utilization_ratio'],
                'payment_history': 100 - user_data['num_of_delayed_payment'] * 2,
                'credit_history_years': user_data['credit_history_year'],
                'credit_history_months': user_data['credit_history_month'],
                'explanation': explanation,
                'lookup_time': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
        })
        
    except Exception as e:
        print(f"Error in lookup_credit_score: {e}")
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi trong quá trình tra cứu. Vui lòng thử lại sau.'}), 500

@app.route('/api/history', methods=['GET'])
def get_credit_history():
    """API lấy lịch sử tra cứu (giả lập)"""
    history = [
        {
            'customer_info': {
                'name': 'John Smith',
                'date_of_birth': '1876-0423',
                'occupation': 'Teacher',
                'average_monthly_income': '$5,000',
                'credit_history': '1 active loan (mortgage)'
            },
            'credit_score_explanation': {
                'credit_score': 730,
                'explanation': 'Low risk',
                'top_contributing_factors': [
                    'High income',
                    'Moderate social media use and high income, with moderate social media activity'
                ],
                'usage_level': 'Moderate use'
            },
            'lookup_time': '05/07/2025 10:30:00'
        },
        {
            'customer_info': {
                'name': 'Nguyen Van A',
                'date_of_birth': '1980-0501',
                'occupation': 'Engineer',
                'average_monthly_income': '$4,500',
                'credit_history': '2 active cards'
            },
            'credit_score_explanation': {
                'credit_score': 680,
                'explanation': 'Fair',
                'top_contributing_factors': [
                    'Good payment history',
                    'Moderate credit utilization'
                ],
                'usage_level': 'Moderate use'
            },
            'lookup_time': '01/06/2025 14:20:00'
        },
        {
            'customer_info': {
                'name': 'Tran Thi B',
                'date_of_birth': '1990-0715',
                'occupation': 'Accountant',
                'average_monthly_income': '$6,000',
                'credit_history': '1 active loan'
            },
            'credit_score_explanation': {
                'credit_score': 820,
                'explanation': 'Excellent',
                'top_contributing_factors': [
                    'Excellent payment history',
                    'Long credit history'
                ],
                'usage_level': 'Low use'
            },
            'lookup_time': '15/05/2025 09:45:00'
        }
    ]
    return jsonify({
        'success': True,
        'data': history
    })

@app.route('/api/tips', methods=['GET'])
def get_credit_tips():
    """API lấy tips cải thiện điểm tín dụng"""
    tips = [
        "Thanh toán hóa đơn đúng hạn để duy trì lịch sử thanh toán tốt",
        "Giữ mức sử dụng thẻ tín dụng dưới 30% so với hạn mức",
        "Không đóng các tài khoản tín dụng cũ để duy trì lịch sử tín dụng dài",
        "Kiểm tra báo cáo tín dụng định kỳ để phát hiện sai sót",
        "Đa dạng hóa các loại tín dụng (thẻ tín dụng, vay ngân hàng, etc.)",
        "Tránh mở quá nhiều tài khoản tín dụng mới trong thời gian ngắn"
    ]
    return jsonify({
        'success': True,
        'data': tips
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)