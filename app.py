from flask import Flask, render_template, request, jsonify, session, redirect
from llama_cpp import Llama
import mysql.connector

REPO_ID = "bartowski/Qwen2.5-0.5B-Instruct-GGUF"
FILENAME = "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"

print(f"Загрузка модели {FILENAME} из {REPO_ID}...")
llm = Llama.from_pretrained(
    repo_id=REPO_ID,
    filename=FILENAME,
    n_ctx=2048,
    verbose=False
)
print("Модель успешно загружена.")

app = Flask(__name__)
app.secret_key = "1581"

def connect():
    return mysql.connector.connect(
        host="185.114.247.43",
        port=3306,
        database="sch688_vvedenie",
        user="sch688_vvedenie",
        password="Qwerty123"
    )


@app.route('/api/user_register', methods=['POST'])
def user_register():
    req = request.get_json()
    name = req.get('name')
    email = req.get('email')
    password = req.get('password')

    cnx = connect()
    try:
        cur = cnx.cursor(dictionary=True)
        cur.execute('SELECT id FROM users WHERE email = %s', (email,))
        if cur.fetchone():
            return jsonify({'error': 'пользователь с таким email уже существует'})

        # При регистрации ставим начальный баланс, например, 100 (если колонка не имеет DEFAULT значения в БД)
        cur.execute(
            'INSERT INTO `users`(`username`, `email`, `password_hash`, `balance`) VALUES (%s, %s, %s, 100)',
            (name, email, password)
        )
        cnx.commit()
    finally:
        cur.close()
        cnx.close()

    return jsonify({'ok': True})

@app.route('/api/login', methods=['POST'])
def login():
    req = request.get_json()
    email = req.get('email')
    password = req.get('password')

    cnx = connect()
    try:
        cur = cnx.cursor(dictionary=True)
        cur.execute(
            'SELECT id, username, email, password_hash FROM users WHERE email = %s',
            (email,)
        )
        user = cur.fetchone()
    finally:
        cur.close()
        cnx.close()

    if not user or user['password_hash'] != password:
        return jsonify({'error': 'неверный email или пароль'})

    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']

    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'email': user['email']
    })

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'не авторизован'}), 401
    
    user_id = session['user_id']
    
    req = request.get_json(silent=True) or {}
    message = (req.get('message') or '').strip()
    if not message:
        return jsonify({'error': 'пустое сообщение'}), 400

    COST = 1 # Стоимость одного запроса к ИИ
    
    cnx = connect()
    try:
        cur = cnx.cursor(dictionary=True)
        
        # 1. Проверяем текущий баланс пользователя
        cur.execute('SELECT balance FROM users WHERE id = %s', (user_id,))
        user_data = cur.fetchone()
        
        if not user_data:
            return jsonify({'error': 'Пользователь не найден'}), 404
            
        current_balance = user_data['balance']
        if current_balance < COST:
            return jsonify({'error': 'Недостаточно средств на балансе для генерации'}), 403

        # 2. Если средств хватает, уменьшаем баланс
        new_balance = current_balance - COST
        cur.execute('UPDATE users SET balance = %s WHERE id = %s', (new_balance, user_id))

        # 3. Добавляем запись в лог транзакций для вашего HTML-шаблона
        cur.execute(
            '''INSERT INTO transactions (user_id, amount, type, cost, description, balance_after, created_at)
               VALUES (%s, %s, "withdrawal", %s, %s, %s, NOW())''',
            (user_id, COST, COST, f"Запрос ИИ: {message[:30]}...", new_balance)
        )
        
        # Фиксируем финансовую операцию в БД
        cnx.commit()
        
    except mysql.connector.Error as err:
        cnx.rollback()
        return jsonify({'error': f'Ошибка транзакции базы данных: {err}'}), 500
    finally:
        cur.close()
        cnx.close()

    # 4. Запускаем генерацию ответа нейросетью после успешного списания
    prompt = f"<|im_start|>system\nТы полезный ассистент. Отвечай кратко и по-русски.<|im_end|>\n<|im_start|>user\n{message}<|im_end|>\n<|im_start|>assistant\n"
    
    output = llm(
        prompt,
        max_tokens=150,
        temperature=0.7,
        stop=["<|im_end|>"]
    )
    reply = output['choices'][0]['text'].strip()
    
    # Возвращаем ответ и актуальный остаток на балансе
    return jsonify({
        'reply': reply,
        'remaining_balance': new_balance
    })

@app.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return redirect('/login')

    cnx = connect()
    try:
        cur = cnx.cursor(dictionary=True)
        cur.execute(
            'SELECT id, username, email, balance FROM users WHERE id = %s',
            (session['user_id'],)
        )
        user = cur.fetchone()
    finally:
        cur.close()
        cnx.close()

    if not user:
        session.clear()
        return redirect('/login')

    return render_template('profile.html', user=user)


@app.route('/logout', methods=['POST'])
def api_logout():
    session.clear()
    return redirect('/login')

@app.route('/transactions')
def transactions_page():
    if 'user_id' not in session:
        return redirect('/login')

    cnx = connect()
    try:
        cur = cnx.cursor(dictionary=True)
        cur.execute(
            '''SELECT id, amount, type, cost, description, balance_after, created_at
               FROM transactions
               WHERE user_id = %s
               ORDER BY created_at DESC, id DESC''',
            (session['user_id'],)
        )
        transactions = cur.fetchall()
    finally:
        cur.close()
        cnx.close()

    return render_template('transactions.html', transactions=transactions)

@app.route("/")
def registration():
    return render_template('registration.html')

@app.route("/login")
def login_page():
    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)
