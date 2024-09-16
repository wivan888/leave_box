from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime, timedelta, date

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用於session加密，請更改為隨機字符串

# 1. 模擬用戶數據庫
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
    "sara": {
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

# 2. 模擬請假記錄
leave_requests = []

# 3. 登入功能
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

# 4. 儀表板功能
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

# 5. 請假申請功能
@app.route('/request_leave', methods=['GET', 'POST'])
def request_leave():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('request_leave.html', leave_days=users[session['username']]['leave_days'])

@app.route('/submit_leave', methods=['POST'])
def submit_leave():
    leave_type = request.form.get('leave_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    reason = request.form.get('reason')
    
    # 計算請假天數
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    days = (end - start).days + 1

    # 更新用戶的剩餘請假天數
    username = session['username']
    if leave_type in users[username]['leave_days']:
        if users[username]['leave_days'][leave_type] >= days:
            users[username]['leave_days'][leave_type] -= days
            
            # 添加新的請假記錄
            leave_request = {
                "employee": username,
                "leave_type": leave_type,
                "start_date": start_date,
                "end_date": end_date,
                "days": days,
                "reason": reason,
                "status": "待審核"
            }
            leave_requests.append(leave_request)
            
            return jsonify({'success': True, 'message': f'請假申請已提交，剩餘{leave_type}天數：{users[username]["leave_days"][leave_type]}天'})
        else:
            return jsonify({'success': False, 'message': f'剩餘{leave_type}天數不足，無法申請'})
    else:
        return jsonify({'success': False, 'message': f'無效的請假類型'})

# 6. 請假審核功能
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

# 7. 刪除請假記錄功能
@app.route('/delete_leave/<int:request_id>', methods=['POST'])
def delete_leave(request_id):
    if 'username' not in session:
        return jsonify({'error': '未登錄'}), 401

    username = session['username']
    user_leave_requests = [req for req in leave_requests if req['employee'] == username]

    if 0 <= request_id < len(user_leave_requests):
        leave_request = user_leave_requests[request_id]
        leave_requests.remove(leave_request)
        if leave_request['status'] == '已同意':
            users[username]['leave_days'][leave_request['leave_type']] += leave_request['days']
        return jsonify({'success': True}), 200
    else:
        return jsonify({'error': '找不到請假記錄'}), 404

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
    current_date = date.today().strftime('%Y-%m-%d')  # 將日期轉換為字符串
    return render_template('employee_leave_records.html', leave_requests=employee_requests, current_date=current_date)

if __name__ == '__main__':
    app.run(debug=True)