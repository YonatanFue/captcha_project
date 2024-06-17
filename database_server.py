import socket
import sqlite3
import base64
import json

main_db = 'zDB/clients.db'
user_db = 'zDB/users.db'
blacklisted_db = 'zDB/blacklisted.db'

lbcount = 1
sccount = 1


def handle_request(request):
    function_name = request['function']
    args = request['args']
    args = args[0]

    if function_name in globals():
        function = globals()[function_name]
        if not args:
            return function()
        returner = function(*args)
        if not returner:
            return returner
        return tuple(item.decode('utf-8') if isinstance(item, bytes) else item for item in returner)
    raise KeyError("NO FUNCTION")


def create_clients_table():
    with sqlite3.connect(main_db) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS clients (
                            id INTEGER PRIMARY KEY,
                            url TEXT NOT NULL
                        )''')
        # cursor.execute('INSERT INTO clients (url) VALUES (?)', ('http://10.0.0.23:8000/captchahandleWebsite.html?',))
        # cursor.execute('INSERT INTO clients (url) VALUES (?)', ('http://10.0.0.23:8000/captchahandle.html',))
        conn.commit()


def create_users_table():
    with sqlite3.connect(user_db) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY,
                            username TEXT NOT NULL,
                            password TEXT NOT NULL,
                            score INTEGER DEFAULT 0
                        )''')
        conn.commit()


def create_blacklisted_table():
    with sqlite3.connect(blacklisted_db) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS blacklisted (
                            id INTEGER PRIMARY KEY,
                            ip TEXT NOT NULL
                        )''')
        conn.commit()


def blacklist_ip(ip_address):
    with sqlite3.connect(blacklisted_db) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO blacklisted (ip) VALUES (?)', (ip_address,))
        conn.commit()


def find_blacklisted_ip(ip_address):
    with sqlite3.connect(blacklisted_db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT ip FROM blacklisted WHERE ip = ?', (ip_address,))
        blacklisted_ip = cursor.fetchone()
        return blacklisted_ip


def find_client(referer):
    with sqlite3.connect(main_db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT url FROM clients WHERE url = ?', (referer,))
        client = cursor.fetchone()
        return client


def find_user(username):
    with sqlite3.connect(user_db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password, score FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        return user


def add_user(username, hashed_password):
    with sqlite3.connect(user_db) as conn:
        cursor = conn.cursor()
        hashed_password = base64.b64decode(hashed_password)
        hashed_password = hashed_password
        cursor.execute('INSERT INTO users (username, password, score) VALUES (?, ?, ?)', (username, hashed_password, 0))
        conn.commit()


def get_leaderboard():
    global lbcount
    with sqlite3.connect(user_db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT username, score FROM users ORDER BY score DESC LIMIT 10')
        leaderboard = cursor.fetchall()
    lbcount += 1
    return leaderboard


def update_captcha_score(username):
    global sccount
    sccount += 1
    with sqlite3.connect(user_db) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET score = score + 1 WHERE username = ?', (username,))
        conn.commit()


def signup_url(url):
    with sqlite3.connect(main_db) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO clients (url) VALUES (?)', (url,))
        conn.commit()


def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(('localhost', 9000))
        server_socket.listen()
        print("Running")

        while True:
            conn, addr = server_socket.accept()
            with conn:
                data = conn.recv(1024)
                if not data:
                    break
                request = json.loads(data.decode())
                response = handle_request(request)
                conn.sendall(json.dumps(response).encode())


if __name__ == "__main__":
    start_server()
