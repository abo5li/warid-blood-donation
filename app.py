import os
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from datetime import datetime

app = Flask(__name__)
# مفتاح سرّي آمن لتشغيل الجلسات (Sessions) لمنع تداخل بيانات المستخدمين
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'warid-secure-secret-key-1427')

# إعداد Socket.IO مع دعم البيئات السحابية (مثل Vercel)
socketio = SocketIO(app, cors_allowed_origins="*")

# قواعد البيانات المؤقتة في الذاكرة (أو يمكنك ربطها بقاعدة بيانات حقيقية لاحقاً)
db = {
    "donors": [],
    "requests": [],
    "messages": [],
    "roles": {
        "admin": "مدير النظام 🛡️",
        "supervisor": "مسؤول المنصة 🔑",
        "support": "مشرف الدعم الفني 🎧",
        "user": "متبرع مسجل 👤"
    }
}

@app.route('/')
def index():
    return render_template('index.html')

# جلب بيانات المنصة بالكامل والحرص على إرجاع بيانات المستخدم المسجل دخوله حالياً فقط
@app.route('/api/data', methods=['GET'])
def get_data():
    current_user = None
    user_id = session.get('user_id')
    
    if user_id:
        for donor in db["donors"]:
            if donor.get('id') == user_id:
                current_user = donor
                break

    return jsonify({
        "donors": db["donors"],
        "requests": db["requests"],
        "messages": db["messages"],
        "roles": db["roles"],
        "current_user": current_user
    })

# تسجيل مستخدم أو متبرع جديد
@app.route('/api/register-donor', methods=['POST'])
def register_donor():
    data = request.json
    phone = data.get('phone')
    
    # التحقق إن كان المتبرع مسجلاً من قبل لتحديث بياناته أو منحه معرف فريد
    existing_donor = None
    for d in db["donors"]:
        if d['phone'] == phone:
            existing_donor = d
            break
            
    if existing_donor:
        existing_donor.update({
            "name": data.get('name'),
            "blood_type": data.get('blood_type'),
            "region": data.get('region'),
            "governorate": data.get('governorate'),
            "status": "متاح للتبرع الفوري"
        })
        donor = existing_donor
    else:
        donor = {
            "id": str(datetime.now().timestamp()),
            "name": data.get('name'),
            "blood_type": data.get('blood_type'),
            "phone": phone,
            "region": data.get('region'),
            "governorate": data.get('governorate'),
            "status": "متاح للتبرع الفوري",
            "role": "user",
            "certified": False,
            "password": data.get('password', '123456') # كلمة مرور افتراضية إن لم تُحدد
        }
        db["donors"].append(donor)
    
    # حفظ معرف المستخدم في جلسة المتصفح الخاصة به فقط لمنع التداخل
    session['user_id'] = donor['id']
    
    socketio.emit('update_data')
    return jsonify({"status": "success", "message": "تم حفظ وتحديث الملف الشخصي بنجاح", "donor": donor})

# تسجيل الدخول الآمن برقم الجوال وكلمة المرور لتجنب تداخل البيانات
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    phone = data.get('phone')
    password = data.get('password')
    
    matched_user = None
    for donor in db["donors"]:
        if donor.get('phone') == phone and donor.get('password', '123456') == password:
            matched_user = donor
            break
            
    # حساب افتراضي للإدارة إن لم يكن مسجلاً
    if not matched_user and phone == "0557137307" and password == "Mkkmg1427":
        matched_user = {
            "id": "admin_master_id",
            "name": "مدير النظام",
            "blood_type": "O-",
            "phone": "0557137307",
            "region": "منطقة جازان",
            "governorate": "جازان",
            "status": "مشرف عام",
            "role": "admin",
            "certified": True
        }
        db["donors"].append(matched_user)

    if matched_user:
        session['user_id'] = matched_user['id']
        return jsonify({"status": "success", "message": "تم تسجيل الدخول بنجاح", "donor": matched_user})
    else:
        return jsonify({"status": "error", "message": "رقم الجوال أو كلمة المرور غير صحيحة"}), 401

# إطلاق نداء دم طارئ جديد
@app.route('/api/request-blood', methods=['POST'])
def request_blood():
    data = request.json
    new_request = {
        "id": str(datetime.now().timestamp()),
        "hospital": data.get('hospital'),
        "region": data.get('region'),
        "governorate": data.get('governorate'),
        "blood_type": data.get('blood_type'),
        "urgency": data.get('urgency'),
        "patient_name": data.get('patient_name', ''),
        "file_number": data.get('file_number', ''),
        "contact_phone": data.get('contact_phone'),
        "date": datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    db["requests"].insert(0, new_request)
    socketio.emit('update_data')
    return jsonify({"status": "success", "message": "تم نشر النداء بنجاح وإرساله للمتطوعين"})

# إرسال رسالة للدعم الفني
@app.route('/api/support/send', methods=['POST'])
def support_send():
    data = request.json
    new_msg = {
        "id": str(datetime.now().timestamp()),
        "name": data.get('name'),
        "phone": data.get('phone'),
        "message": data.get('message'),
        "date": datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    db["messages"].insert(0, new_msg)
    socketio.emit('update_data')
    return jsonify({"status": "success", "message": "تم إرسال رسالتك لفريق الدعم الفني بنجاح"})

# مسارات لوحة التحكم والإدارة
@app.route('/api/admin/delete-request/<req_id>', methods=['DELETE'])
def delete_request(req_id):
    db["requests"] = [r for r in db["requests"] if r['id'] != req_id]
    socketio.emit('update_data')
    return jsonify({"status": "success"})

@app.route('/api/admin/delete-message/<msg_id>', methods=['DELETE'])
def delete_message(msg_id):
    db["messages"] = [m for m in db["messages"] if m['id'] != msg_id]
    socketio.emit('update_data')
    return jsonify({"status": "success"})

@app.route('/api/admin/delete-donor/<donor_id>', methods=['DELETE'])
def delete_donor(donor_id):
    db["donors"] = [d for d in db["donors"] if d['id'] != donor_id]
    socketio.emit('update_data')
    return jsonify({"status": "success", "message": "تم حذف المتبرع بنجاح"})

@app.route('/api/admin/update-role/<donor_id>', methods=['POST'])
def update_role(donor_id):
    new_role = request.json.get('role')
    for d in db["donors"]:
        if d['id'] == donor_id:
            d['role'] = new_role
            break
    socketio.emit('update_data')
    return jsonify({"status": "success", "message": "تم تحديث صلاحية المستخدم بنجاح"})

@app.route('/api/admin/toggle-certificate/<donor_id>', methods=['POST'])
def toggle_certificate(donor_id):
    for d in db["donors"]:
        if d['id'] == donor_id:
            d['certified'] = not d.get('certified', False)
            break
    socketio.emit('update_data')
    return jsonify({"status": "success"})

if __name__ == '__main__':
    socketio.run(app, debug=True)
