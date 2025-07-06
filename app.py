from flask import Flask, render_template, request, jsonify
import random
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'vpbank-credit-lookup-secret'

# Sample data for demonstration
SAMPLE_USERS = {
    "001234567890": {
        "full_name": "NGUYEN VAN A",
        "national_id": "001234567890",
        "credit_score": 735,
        "credit_card_utilization": 24,
        "payment_history": 99,
        "credit_history_years": 6,
        "credit_history_months": 7
    },
    "001234567891": {
        "full_name": "TRAN THI B",
        "national_id": "001234567891",
        "credit_score": 680,
        "credit_card_utilization": 35,
        "payment_history": 95,
        "credit_history_years": 4,
        "credit_history_months": 3
    },
    "001234567892": {
        "full_name": "LE VAN C",
        "national_id": "001234567892",
        "credit_score": 820,
        "credit_card_utilization": 15,
        "payment_history": 100,
        "credit_history_years": 8,
        "credit_history_months": 11
    }
}

def generate_random_credit_data(full_name, national_id):
    """Tạo dữ liệu tín dụng ngẫu nhiên cho user mới"""
    return {
        "full_name": full_name.upper(),
        "national_id": national_id,
        "credit_score": random.randint(300, 850),
        "credit_card_utilization": random.randint(10, 90),
        "payment_history": random.randint(70, 100),
        "credit_history_years": random.randint(1, 15),
        "credit_history_months": random.randint(0, 11)
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
    # Loại bỏ ký tự không phải số
    national_id = re.sub(r'[^0-9]', '', national_id)
    
    # Kiểm tra độ dài (9 hoặc 12 số)
    if len(national_id) not in [9, 12]:
        return False
    
    return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/lookup', methods=['POST'])
def lookup_credit_score():
    """API endpoint để tra cứu điểm tín dụng"""
    try:
        data = request.get_json()
        full_name = data.get('full_name', '').strip()
        national_id = data.get('national_id', '').strip()
        
        # Validate input
        if not full_name or not national_id:
            return jsonify({
                'success': False,
                'message': 'Vui lòng nhập đầy đủ thông tin họ tên và số CMND/CCCD'
            }), 400
        
        # Validate national ID format
        if not validate_national_id(national_id):
            return jsonify({
                'success': False,
                'message': 'Số CMND/CCCD không hợp lệ. Vui lòng nhập 9 hoặc 12 chữ số'
            }), 400
        
        # Clean national ID
        national_id = re.sub(r'[^0-9]', '', national_id)
        
        # Check if user exists in sample data
        if national_id in SAMPLE_USERS:
            user_data = SAMPLE_USERS[national_id]
            
            # Verify name (simple check)
            if full_name.upper() != user_data['full_name']:
                return jsonify({
                    'success': False,
                    'message': 'Thông tin họ tên không khớp với số CMND/CCCD'
                }), 400
        else:
            # Generate random data for new user
            user_data = generate_random_credit_data(full_name, national_id)
        
        # Get credit score explanation
        score_level = get_credit_score_level(user_data['credit_score'])
        
        # Generate explanation text
        explanation = generate_explanation(user_data)
        
        return jsonify({
            'success': True,
            'data': {
                'full_name': user_data['full_name'],
                'national_id': user_data['national_id'],
                'credit_score': user_data['credit_score'],
                'score_level': score_level,
                'credit_card_utilization': user_data['credit_card_utilization'],
                'payment_history': user_data['payment_history'],
                'credit_history_years': user_data['credit_history_years'],
                'credit_history_months': user_data['credit_history_months'],
                'explanation': explanation,
                'lookup_time': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Đã xảy ra lỗi trong quá trình tra cứu. Vui lòng thử lại sau.'
        }), 500

def generate_explanation(user_data):
    """Tạo văn bản giải thích điểm tín dụng"""
    score = user_data['credit_score']
    utilization = user_data['credit_card_utilization']
    payment = user_data['payment_history']
    years = user_data['credit_history_years']
    
    if score >= 740:
        quality = "tốt"
    elif score >= 670:
        quality = "khá tốt"
    elif score >= 580:
        quality = "trung bình"
    else:
        quality = "cần cải thiện"
    
    explanation = f"Điểm tín dụng của bạn là {score} ({quality}), phản ánh thói quen tài chính {quality}. "
    explanation += f"Bạn đã duy trì mức sử dụng thẻ tín dụng {utilization}%, "
    explanation += f"lịch sử thanh toán {payment}%, và có lịch sử tín dụng dài {years} năm"
    
    if years > 0:
        explanation += f", trong đó bao gồm việc không có rủi ro tín dụng."
    
    return explanation

@app.route('/api/history', methods=['GET'])
def get_credit_history():
    """API lấy lịch sử tra cứu (giả lập)"""
    # Giả lập dữ liệu lịch sử với định dạng dựa trên hình ảnh
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