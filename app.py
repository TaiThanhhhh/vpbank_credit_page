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

# Preprocess input (merge từ cả hai file: lọc features và mapping)
def preprocess_input(input_data: dict, model=None) -> pd.DataFrame:
    # Danh sách các cột đặc trưng theo thứ tự mô hình mong đợi
    expected_features = [
        "age", "annual_income", "monthly_inhand_salary", "num_bank_accounts",
        "num_credit_card", "interest_rate", "num_of_loan", "delay_from_due_date",
        "num_of_delayed_payment", "changed_credit_limit", "num_credit_inquiries",
        "credit_mix", "outstanding_debt", "credit_utilization_ratio",
        "payment_behaviour", "monthly_balance", "salary_range",
        "credit_history_year", "credit_history_month", "credit_score_numeric"
    ]
    
    # Nếu có mô hình, lấy thứ tự đặc trưng từ model.feature_names_in_
    if model and hasattr(model, 'feature_names_in_'):
        expected_features = list(model.feature_names_in_)
    
    # Lọc chỉ các cột cần thiết
    filtered_data = {k: input_data[k] for k in expected_features if k in input_data}
    df = pd.DataFrame([filtered_data])
    
    # Đảm bảo tất cả các cột trong expected_features đều tồn tại
    for feature in expected_features:
        if feature not in df.columns:
            df[feature] = 0  # Giá trị mặc định nếu thiếu

    # Sắp xếp cột theo thứ tự expected_features
    df = df[expected_features]

    # Ánh xạ giá trị danh mục (từ main.py)
    df["credit_mix"] = df["credit_mix"].map({"Good": 1, "Standard": 0, "Bad": -1, 0: 0})
    df["payment_behaviour"] = df["payment_behaviour"].map({
        "High_spent_Small_value_payments": 1,
        "Low_spent_Small_value_payments": 0,
        "High_spent_Large_value_payments": 2,
        "Low_spent_Large_value_payments": -1,
        "High_spent_Medium_value_payments": 3,
        "Low_spent_Medium_value_payments": -2,
        0: 0
    })
    df["salary_range"] = df["salary_range"].map({
        "Very Low": 0, "Low": 1, "Medium": 2, "High": 3, "Very High": 4, 0: 0
    })
    
    return df

# Generate SHAP values
def get_shap_values(model, df):
    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer(df)
        return shap_values
    except Exception as e:
        print(f"Error generating SHAP values: {e}")
        return None

# Extract top contributing features (từ main.py, giống nhau)
def get_top_features(df, shap_values, pred_index, top_n=5):
    shap_vals = shap_values.values[0, :, pred_index]
    feature_names = df.columns.tolist()
    top_indices = np.argsort(np.abs(shap_vals))[::-1][:top_n]
    return [(feature_names[i], shap_vals[i]) for i in top_indices]

# Save SHAP values
def save_shap_values(shap_values, path):
    try:
        shap_dict = shap_values.values[0].tolist()
        with open(path, "w") as f:
            json.dump(shap_dict, f)
        print(f"SHAP values saved to {path}")
    except Exception as e:
        print(f"Error saving SHAP values: {e}")

# Generate prompt (cập nhật từ main.py: bao gồm input_data, format bullet points)
def generate_prompt(input_data, prediction, top_features):
    # Format the input features into text
    feature_text = "\n".join([f"- {key}: {value}" for key, value in input_data.items()])

    # Format SHAP contributions into text
    shap_text = "\n".join([
        f"- {feat}: contributed {'+' if val >= 0 else '-'}{abs(val):.2f} points" 
        for feat, val in top_features
    ])

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

# Thay ask_ollama bằng gọi Claude Sonnet qua Bedrock
def ask_claude(prompt):
    print("Querying Claude Sonnet via AWS Bedrock...")
    try:
        # Format cho Bedrock Claude
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })

        response = bedrock_client.invoke_model(
            body=body,
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",  # Model ID cho Claude 3.5 Sonnet
            accept="application/json",
            contentType="application/json"
        )

        response_body = json.loads(response.get("body").read())
        return response_body.get("content", [{}])[0].get("text", "")
    except Exception as e:
        print(f"Error calling Bedrock: {e}")
        return ""

# Explain credit score (thay ask_ollama bằng ask_claude)
def explain_credit_score(model_path, input_data):
    try:
        model = load_model(model_path)
        if model is None:
            raise Exception("Model could not be loaded")

        df = preprocess_input(input_data, model=model)
        prediction = model.predict(df)[0]

        shap_values = get_shap_values(model, df)
        if shap_values is None:
            raise Exception("SHAP values could not be generated")

        class_labels = model.classes_
        pred_index = list(class_labels).index(prediction)
        top_features = get_top_features(df, shap_values, pred_index)
        save_shap_values(shap_values, "shap_outputs/shap_values.json")
        prompt = generate_prompt(input_data, prediction, top_features)
        explanation = ask_claude(prompt)  # Thay bằng Claude
        return prediction, explanation
    except Exception as e:
        print(f"Error in explain_credit_score: {e}")
        random_score = random.randint(300, 850)
        score_level = get_credit_score_level(random_score)
        explanation = (
            f"Điểm tín dụng của bạn được ước tính là {random_score} ({score_level}). "
            f"Do hệ thống không thể sử dụng mô hình dự đoán, điểm này được tạo ngẫu nhiên dựa trên thông tin tài chính của bạn. "
            f"Vui lòng kiểm tra lại thông tin hoặc thử lại sau."
        )
        return str(random_score), explanation

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
        prediction, explanation = explain_credit_score(model_path, user_data)
        
        if prediction is None:
            return jsonify({'success': False, 'message': 'Lỗi khi dự đoán điểm tín dụng. Vui lòng thử lại.'}), 500
        
        # Convert score
        try:
            score = int(prediction) if prediction.isdigit() else user_data.get('credit_score_numeric', 0) * 100 + 600
        except ValueError:
            score = user_data.get('credit_score_numeric', 0) * 100 + 600
        score_level = get_credit_score_level(score)
        
        return jsonify({
            'success': True,
            'data': {
                'full_name': user_data['full_name'],
                'national_id': user_data['national_id'],
                'credit_score': score,
                'score_level': score_level,
                'credit_card_utilization': user_data['credit_utilization_ratio'],
                'payment_history': 100 - user_data['num_of_delayed_payment'] * 2,  # Không dùng get() vì field tồn tại
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