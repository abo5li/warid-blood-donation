from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'blood_donation_enterprise_2026'
socketio = SocketIO(app, cors_allowed_origins="*")

ROLES = {
    'admin': 'مدير النظام',
    'supervisor': 'مسؤول المنصة',
    'support': 'مشرف الدعم الفني',
    'user': 'متبرع مسجل'
}

donors = [
    {
        'id': 'd-admin',
        'name': 'المدير العام',
        'blood_type': 'O+',
        'phone': '0557137307',
        'password': 'Mkkmg1427',
        'region': 'منطقة جازان',
        'governorate': 'جازان',
        'status': 'متاح',
        'role': 'admin',
        'certified': True
    },
    {
        'id': 'd-102',
        'name': 'محمد خالد قحل',
        'blood_type': 'O-',
        'phone': '0550000000',
        'password': '123',
        'region': 'منطقة جازان',
        'governorate': 'صبيا',
        'status': 'متاح',
        'role': 'supervisor',
        'certified': True
    },
    {
        'id': 'd-103',
        'name': 'إبراهيم عيسى حكمي',
        'blood_type': 'A+',
        'phone': '0551111111',
        'password': '123',
        'region': 'منطقة جازان',
        'governorate': 'أبو عريش',
        'status': 'متاح',
        'role': 'support',
        'certified': False
    }
]

requests_list = [
    {
        'id': 'req-101',
        'hospital': 'مستشفى جازان العام',
        'region': 'منطقة جازان',
        'governorate': 'جازان',
        'blood_type': 'O+',
        'urgency': 'عاجل',
        'status': 'نشط',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'patient_name': 'محمد خالد قحل',
        'file_number': '98765',
        'contact_phone': '0557137307'
    }
]

# قائمة لتخزين رسائل واستفسارات الدعم الفني المرسلة من الموقع
support_messages = [
    {
        'id': 'msg-1',
        'name': 'زائر الموقع',
        'phone': '0559999999',
        'message': 'أرغب في الاستفسار عن شروط التبرع بالدم لأصحاب الأمراض المزمنة.',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify({
        'donors': donors,
        'requests': requests_list,
        'messages': support_messages,
        'roles': ROLES,
        'stats': {
            'total_donors': len(donors),
            'total_requests': len(requests_list),
            'saved_lives': len(donors) * 3 + 15
        }
    })


@app.route('/api/auth/login', methods=['POST'])
def login():
    phone = request.json.get('phone', '').strip()
    password = request.json.get('password', '').strip()

    if phone == '0557137307':
        if password == 'Mkkmg1427':
            donor = next((d for d in donors if d['phone'] == phone), None)
            return jsonify({'status': 'success', 'donor': donor, 'message': 'أهلاً بك يا مدير النظام!'})
        else:
            return jsonify({'status': 'error', 'message': 'كلمة المرور غير صحيحة!'})

    donor = next((d for d in donors if d['phone'] == phone), None)
    if not donor:
        donor = {
            'id': f"d-{str(uuid.uuid4())[:6]}",
            'name': 'متبرع جديد',
            'blood_type': 'O+',
            'phone': phone,
            'password': password,
            'region': 'منطقة جازان',
            'governorate': 'جازان',
            'status': 'متاح',
            'role': 'user',
            'certified': False
        }
        donors.append(donor)

    return jsonify({'status': 'success', 'donor': donor, 'message': f'أهلاً بك يا {donor["name"]}'})


# API استقبال رسائل الدعم الفني وإرسالها للإدارة
@app.route('/api/support/send', methods=['POST'])
def send_support_message():
    data = request.json
    name = data.get('name', 'زائر مجهول')
    phone = data.get('phone', 'غير مدخل')
    message = data.get('message', '')

    if not message:
        return jsonify({'status': 'error', 'message': 'يرجى كتابة نص الرسالة'})

    new_msg = {
        'id': f"msg-{str(uuid.uuid4())[:4]}",
        'name': name,
        'phone': phone,
        'message': message,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    support_messages.insert(0, new_msg)
    socketio.emit('update_data', {})
    return jsonify({'status': 'success', 'message': 'تم إرسال رسالتك لفريق الدعم الفني بنجاح!'})


@app.route('/api/admin/delete-message/<msg_id>', methods=['DELETE'])
def delete_support_message(msg_id):
    global support_messages
    support_messages = [m for m in support_messages if m['id'] != msg_id]
    socketio.emit('update_data', {})
    return jsonify({'status': 'success', 'message': 'تم حذف الرسالة بنجاح'})


@app.route('/api/register-donor', methods=['POST'])
def register_donor():
    data = request.json
    phone = data.get('phone')
    donor = next((d for d in donors if d['phone'] == phone), None)

    role = 'admin' if phone == '0557137307' else ('admin' if (donor and donor['role'] == 'admin') else 'user')

    if donor:
        donor.update({
            'name': data.get('name'),
            'blood_type': data.get('blood_type'),
            'region': data.get('region'),
            'governorate': data.get('governorate'),
            'role': role
        })
    else:
        donor = {
            'id': f"d-{str(uuid.uuid4())[:6]}",
            'name': data.get('name'),
            'blood_type': data.get('blood_type'),
            'phone': phone,
            'password': '123',
            'region': data.get('region'),
            'governorate': data.get('governorate'),
            'status': 'متاح',
            'role': role,
            'certified': False
        }
        donors.append(donor)

    socketio.emit('update_data', {})
    return jsonify({'status': 'success', 'message': 'تم حفظ وتحديث بياناتك بنجاح!', 'donor': donor})


@app.route('/api/request-blood', methods=['POST'])
def request_blood():
    data = request.json
    new_request = {
        'id': f"req-{str(uuid.uuid4())[:4]}",
        'hospital': data.get('hospital'),
        'region': data.get('region'),
        'governorate': data.get('governorate'),
        'blood_type': data.get('blood_type'),
        'urgency': data.get('urgency', 'عاجل'),
        'status': 'نشط',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'patient_name': data.get('patient_name', 'غير محدد'),
        'file_number': data.get('file_number', '-'),
        'contact_phone': data.get('contact_phone', '-')
    }
    requests_list.insert(0, new_request)
    socketio.emit('update_data', {})
    return jsonify({'status': 'success', 'message': 'تم إطلاق حالة الطوارئ بنجاح!'})


@app.route('/api/admin/delete-request/<req_id>', methods=['DELETE'])
def delete_request(req_id):
    global requests_list
    requests_list = [r for r in requests_list if r['id'] != req_id]
    socketio.emit('update_data', {})
    return jsonify({'status': 'success', 'message': 'تم حذف الحالة بنجاح'})


@app.route('/api/admin/delete-donor/<donor_id>', methods=['DELETE'])
def delete_donor(donor_id):
    global donors
    donor = next((d for d in donors if d['id'] == donor_id), None)
    if donor and donor['phone'] == '0557137307':
        return jsonify({'status': 'error', 'message': 'لا يمكن حذف حساب المدير العام الأساسي للمنصة'})

    donors = [d for d in donors if d['id'] != donor_id]
    socketio.emit('update_data', {})
    return jsonify({'status': 'success', 'message': 'تم حذف المتبرع بنجاح من النظام'})


@app.route('/api/admin/update-role/<donor_id>', methods=['POST'])
def update_role(donor_id):
    new_role = request.json.get('role')
    donor = next((d for d in donors if d['id'] == donor_id), None)
    if donor:
        if donor['phone'] == '0557137307':
            return jsonify({'status': 'error', 'message': 'لا يمكن تغيير صلاحيات المدير الأساسي للمنصة'})
        donor['role'] = new_role
        socketio.emit('update_data', {})
        return jsonify({'status': 'success', 'message': f'تم تغيير رتبة المتبرع إلى: {ROLES.get(new_role, new_role)}'})
    return jsonify({'status': 'error', 'message': 'المتبرع غير موجود'})


@app.route('/api/admin/toggle-certificate/<donor_id>', methods=['POST'])
def toggle_certificate(donor_id):
    donor = next((d for d in donors if d['id'] == donor_id), None)
    if donor:
        donor['certified'] = not donor.get('certified', False)
        socketio.emit('update_data', {})
        return jsonify({'status': 'success', 'message': 'تم تحديث حالة شهادة التقدير للمتبرع'})
    return jsonify({'status': 'error', 'message': 'المتبرع غير موجود'})


import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)