from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime, timedelta, date

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用於session加密，請更改為隨機字符串

# 模擬用戶數據庫
users = {
    "ivan": {
        "password": "0plmzaq12", 
        "role": "employee", 
        "leave_days": {
            "特別休假": 7,
            "普通傷病假(非住院)": 30,
            "普通傷病假(住院)": 365,
            "事假": 14
        }
    },
    "michael": {
        "password": "0plmzaq12", 
        "role": "manager", 
        "leave_days": {
            "特別休假": 7,
            "普通傷病假(非住院)": 30,
            "普通傷病假(住院)": 365,
            "事假": 14
        }
    },
    "sara": {  # 新增 sara 用戶
        "password": "0plmzaq12",
        "role": "employee",
        "leave_days": {
            "特別休假": 7,
            "普通傷病假(非住院)": 30,
            "普通傷病假(住院)": 365,
            "事假": 14
        }
    }
}

# 模擬請假記錄
leave_requests = []

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]["password"] == password:
            session['username'] = username
            session['role'] = users[username]["role"]
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="用戶名或密碼錯誤")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    if session['role'] == 'manager':
        user_leave_requests = [req for req in leave_requests if req['employee'] == session['username']]
        return render_template('manager_dashboard.html', leave_requests=leave_requests, user_leave_requests=user_leave_requests, leave_days=users[session['username']]['leave_days'])
    else:
        user_leave_requests = [req for req in leave_requests if req['employee'] == session['username']]
        return render_template('employee_dashboard.html', leave_requests=user_leave_requests, leave_days=users[session['username']]['leave_days'])

@app.route('/request_leave', methods=['GET', 'POST'])
def request_leave():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('request_leave.html', leave_days=users[session['username']]['leave_days'])

@app.route('/submit_leave', methods=['POST'])
def submit_leave():
    if 'username' not in session:
        return jsonify({"success": False, "message": "請先登入"})
    
    data = request.json
    start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
    end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
    leave_days = (end_date - start_date).days + 1
    leave_type = data['leave_type']

    user = users[session['username']]
    
    # 檢查是否有重疊的請假日期
    for existing_request in leave_requests:
        if existing_request['employee'] == session['username']:
            existing_start = datetime.strptime(existing_request['start_date'], '%Y-%m-%d')
            existing_end = datetime.strptime(existing_request['end_date'], '%Y-%m-%d')
            if (start_date <= existing_end and end_date >= existing_start):
                return jsonify({"success": False, "message": "您在這個時間段內已經有請假記錄，請重新填寫假。"})

    if leave_type == "婚假" and leave_days > 8:
        return jsonify({"success": False, "message": "婚假一次最多只能請8天"})
    elif leave_type == "喪假" and leave_days > 6:
        return jsonify({"success": False, "message": "喪假一次最多只能請6天"})
    elif leave_type in user['leave_days']:
        if leave_days > user['leave_days'][leave_type]:
            return jsonify({"success": False, "message": f"您的{leave_type}剩餘天數不足，目前剩餘 {user['leave_days'][leave_type]} 天"})
    
    if leave_type == "普通傷病假(非住院)" or leave_type == "普通傷病假(住院)":
        total_sick_leave = sum(req['days'] for req in leave_requests 
                                if req['employee'] == session['username'] 
                                and req['leave_type'] in ["普通傷病假(非住院)", "普通傷病假(住院)"]
                                and (datetime.now() - datetime.strptime(req['start_date'], '%Y-%m-%d')).days <= 730)
        if total_sick_leave + leave_days > 365:
            return jsonify({"success": False, "message": "普通傷病假(非住院)與普通傷病假(住院)二年內合計不可超過一年"})

    leave_request = {
        "employee": session['username'],
        "leave_type": leave_type,
        "start_date": data['start_date'],
        "end_date": data['end_date'],
        "reason": data['reason'],
        "status": "待審核",
        "days": leave_days
    }
    leave_requests.append(leave_request)
    
    if leave_type in user['leave_days']:
        user['leave_days'][leave_type] -= leave_days
        return jsonify({
            "success": True, 
            "message": f"請假申請已提交，剩餘{leave_type}天數：{user['leave_days'][leave_type]} 天"
        })
    else:
        return jsonify({
            "success": True, 
            "message": "請假申請已提交"
        })

@app.route('/review_leave/<int:request_id>', methods=['POST'])
def review_leave(request_id):
    if 'username' not in session or session['role'] != 'manager':
        return redirect(url_for('login'))
    if 0 <= request_id < len(leave_requests):
        decision = request.form['decision']
        leave_requests[request_id]["status"] = "已同意" if decision == "同意" else "已拒絕"
        if decision == "拒絕":
            employee = leave_requests[request_id]["employee"]
            leave_type = leave_requests[request_id]["leave_type"]
            days = leave_requests[request_id]["days"]
            if leave_type in users[employee]['leave_days']:
                users[employee]['leave_days'][leave_type] += days
    return redirect(url_for('dashboard'))

@app.route('/delete_leave/<int:request_id>', methods=['POST'])
def delete_leave(request_id):
    if 'username' not in session:
        return jsonify({"success": False, "message": "請先登入"})
    if 0 <= request_id < len(leave_requests) and leave_requests[request_id]['employee'] == session['username']:
        leave_type = leave_requests[request_id]['leave_type']
        if leave_requests[request_id]['status'] != '已拒絕' and leave_type in users[session['username']]['leave_days']:
            users[session['username']]['leave_days'][leave_type] += leave_requests[request_id]['days']
        leave_requests.pop(request_id)
        return jsonify({"success": True, "message": "請假記錄已成功刪除"})
    return jsonify({"success": False, "message": "無法刪除請假記錄"})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/leave_statistics')
def leave_statistics():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    user_leave_requests = [req for req in leave_requests if req['employee'] == username]
    
    # 計算各類型請假的使用天數
    leave_usage = {}
    for leave_type in users[username]['leave_days'].keys():
        used_days = sum(req['days'] for req in user_leave_requests if req['leave_type'] == leave_type and req['status'] == '已同意')
        remaining_days = users[username]['leave_days'][leave_type]
        leave_usage[leave_type] = {
            'used': used_days,
            'remaining': remaining_days
        }
    
    return render_template('leave_statistics.html', leave_usage=leave_usage, leave_requests=user_leave_requests)

@app.route('/employee_leave_records')
def employee_leave_records():
    if 'username' not in session or session['role'] != 'manager':
        return redirect(url_for('login'))
    
    employee_requests = [req for req in leave_requests if req['employee'] != session['username']]
    current_date = date.today()
    return render_template('employee_leave_records.html', leave_requests=employee_requests, current_date=current_date)

if __name__ == '__main__':
    app.run(debug=True)