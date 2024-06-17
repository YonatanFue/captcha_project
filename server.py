from captcha_creator import create_captcha
import http.cookies
import socketserver
import urllib.parse
import http.server
import threading
import hashlib
import base64
import socket
import bcrypt
import json
import time
import os

PORT = 8000
main_ip = ''

self_website = "https://bc9c-2a10-8012-d-6e3-947f-6f3f-9abf-6e82.ngrok-free.app/captchahandleWebsite.html?"

active_users = {}


#RSA decryptor
def decrypt_rsa(data):
    privatekey = 2753
    mod = 3233

    def powmod(a, x, n):
        xbits = num_to_bit(x)
        y = 1
        for bit in xbits:
            y = y * y % n
            if bit == '1':
                y = a * y % n
        return y

    def num_to_bit(numb):
        quotient = numb
        result = ''
        while quotient > 0:
            m = quotient % 2
            quotient //= 2
            result += str(m)
        return result[::-1]

    decrypted = ""
    for c in data:
        try:
            num = ord(c)
            num = powmod(num, privatekey, mod)
            decrypted += chr(num)
        except ValueError:
            decrypted += " "
    return decrypted


# connector to database server
def send_request_to_database_server(function_name, *args):
    request = {
        "function": function_name,
        "args": args
    }
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('localhost', 9000))
        s.sendall(json.dumps(request).encode())
        response = s.recv(1024).decode()
        return json.loads(response)


send_request_to_database_server('create_clients_table', ())
send_request_to_database_server('create_users_table', ())
send_request_to_database_server('create_blacklisted_table', ())

blacklisted_lock = threading.Lock()
userdict_lock = threading.Lock()


# DDoS thread
def ddos_protection():
    while True:
        # Check request counts and blacklist IPs
        blacklisted_lock.acquire()
        for user_ip in list(active_users.keys()):
            if active_users[user_ip] > 25:
                send_request_to_database_server("blacklist_ip", (user_ip,))
                del active_users[user_ip]
            else:
                active_users[user_ip] -= 1
        blacklisted_lock.release()

        # remove inactive
        inactive_users = [ip for ip, count in active_users.items() if count <= 1500]  # around 2.5 min of inactiveness
        userdict_lock.acquire()
        for ip in inactive_users:
            del active_users[ip]
        userdict_lock.release()
        time.sleep(0.1)


ddos_thread = threading.Thread(target=ddos_protection)
ddos_thread.daemon = True
ddos_thread.start()


class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        user_ip = self.client_address[0]
        if user_ip not in active_users:
            blacklisted_lock.acquire()
            if send_request_to_database_server("find_blacklisted_ip", (user_ip,)):
                blacklisted_lock.release()
                # block user
                self.send_error(403, "Access denied")
                return
            else:
                blacklisted_lock.release()
                # add user to active users
                userdict_lock.acquire()
                active_users[user_ip] = 1
                userdict_lock.release()
        else:
            # increment request count for existing user
            userdict_lock.acquire()
            if active_users[user_ip] < 0:  # stopped being "idle"
                active_users[user_ip] = 1
            active_users[user_ip] += 1
            userdict_lock.release()

        if self.path in ('/captcha1', '/captcha2', '/captcha3'):
            referer = self.headers.get('Referer')  # URL of requester

            if send_request_to_database_server("find_client", (referer,)) or referer == self_website:
                captcha_photo, captcha_answer = create_captcha(int(self.path[-1]))  # extracting difficulty from the request
                hashed_answer = hashlib.sha256(captcha_answer.encode()).hexdigest()  # simple hash, same as JS's

                response_data = {
                    "image": captcha_photo,  # base64 string as utf-8
                    "hashed_answer": hashed_answer
                }
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())
            else:
                # referer not allowed
                self.send_response(403)
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'Forbidden')

        elif self.path == '/username':
            cookie_header = self.headers.get('Cookie')
            if cookie_header:
                cookies = http.cookies.SimpleCookie(cookie_header)
                session_cookie = cookies.get('session')
                if session_cookie and (user := send_request_to_database_server('find_user', (session_cookie.value,))):
                    response_data = {'username': user[1], 'score': user[3]}
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode())
                    return

            # no valid session cookie or user not found
            self.send_response(404)
            self.end_headers()

        elif self.path == '/leaderboard':
            leaderboardspots = send_request_to_database_server("get_leaderboard", ())

            leaderboard_data = [{'username': user[0], 'score': user[1]} for user in leaderboardspots]

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(leaderboard_data).encode())

        elif self.path == '/':
            self.handle_landing_page()

        elif self.path == '/logout':
            self.send_response(302)
            self.send_header('Location', '/login.html')
            self.send_header('Set-Cookie', 'session=; expires=Thu, 01 Jan 1970 00:00:00 GMT')  # Clear session cookie
            self.end_headers()

        else:
            super().do_GET()

    def do_POST(self):
        user_ip = self.client_address[0]
        if user_ip not in active_users:
            blacklisted_lock.acquire()
            if send_request_to_database_server("find_blacklisted_ip", (user_ip,)):
                blacklisted_lock.release()
                # block user
                self.send_error(403, "Access denied")
                return
            else:
                blacklisted_lock.release()
                # add user to active users
                userdict_lock.acquire()
                active_users[user_ip] = 1
                userdict_lock.release()
        else:
            # increment request count for existing user
            userdict_lock.acquire()
            if active_users[user_ip] < 0:  # stopped being "idle"
                active_users[user_ip] = 1
            active_users[user_ip] += 1
            userdict_lock.release()

        if self.path == '/captcha_attempt':
            content_length = int(self.headers['Content-Length'])  # data sent from JS in query string
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed_data = urllib.parse.parse_qs(post_data)  # into dict

            # converted to string, defaults to false if isn't there (ends up as bool)
            is_captcha_correct = parsed_data.get('isCaptchaCorrect', ['false'])[0] == 'true'

            cookie_header = self.headers.get('Cookie')
            if not cookie_header:
                self.send_response(302)
                self.send_header('Location', '/login.html')
                self.end_headers()
                return

            cookies = http.cookies.SimpleCookie(cookie_header)
            session_cookie = cookies.get('session')
            username = session_cookie.value

            if is_captcha_correct:
                # correct answer, increment score by one
                send_request_to_database_server("update_captcha_score", (username,))
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success'}).encode())
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'fail'}).encode())

        elif self.path == '/signup_client':
            content_length = int(self.headers['Content-Length'])  # data sent from JS in query string
            post_data = self.rfile.read(content_length).decode('utf-8')
            encrypted_url = urllib.parse.parse_qs(post_data)['encrypted-url'][0]  # into dict
            # decrypt the URL
            url = decrypt_rsa(encrypted_url)
            url = ''.join(url)
            # if URL is legitimate and not duplicate
            if (url.startswith('http://') or url.startswith('https://')) and not send_request_to_database_server("find_client", (url,)):
                send_request_to_database_server("signup_url", (url,))

                self.send_response(302)
                self.send_header('Location', '/signup_success.html')
                self.end_headers()
            else:
                # different redirection type because 400
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                with open('duplicateurl.html', 'rb') as f:
                    self.wfile.write(f.read())

        elif self.path == '/signup_user':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed_data = urllib.parse.parse_qs(post_data)
            username = parsed_data['username'][0]
            encrypted_password = parsed_data['encrypted-password'][0]
            # decrypt the password
            password = decrypt_rsa(encrypted_password)
            password = ''.join(password)
            if not send_request_to_database_server('find_user', (username,)):
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                send_request_to_database_server("add_user", (username, base64.b64encode(hashed_password).decode('utf-8')))
                self.send_response(302)
                self.send_header('Location', '/login.html')
                self.end_headers()
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                with open('signup_user.html', 'r') as f:
                    signup_user_html = f.read()
                    toast_script = """
                    <script>
                        const toast = document.createElement('div');
                        toast.classList.add('toast');
                        toast.textContent = 'Username already taken. use a different name';
                        document.body.appendChild(toast);
                        setTimeout(() => {
                            toast.classList.add('fade-out');
                        }, 500);
                        setTimeout(() => {
                            toast.remove();
                        }, 2000);
                    </script>
                    """
                    signup_user_html = signup_user_html.replace('</body>', f'{toast_script}</body>')
                    self.wfile.write(signup_user_html.encode())

        elif self.path == '/login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed_data = urllib.parse.parse_qs(post_data)
            username = parsed_data['username'][0]
            encrypted_password = parsed_data['encrypted-password'][0]
            password = decrypt_rsa(encrypted_password)
            password = ''.join(password)
            user = send_request_to_database_server('find_user', (username,))
            if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
                # set cookie
                self.send_response(302)
                self.send_header('Location', '/')
                self.send_header('Set-Cookie', f'session={username}; Path=/')
                self.end_headers()
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                # Write the login form with JavaScript for the toast message
                with open('login.html', 'r') as f:
                    login_html = f.read()
                    toast_script = """
                    <script>
                        const toast = document.createElement('div');
                        toast.classList.add('toast');
                        toast.textContent = 'Invalid username or password. Please try again.';
                        document.body.appendChild(toast);

                        setTimeout(() => {
                            toast.classList.add('fade-out');
                        }, 500);

                        setTimeout(() => {
                            toast.remove();
                        }, 2000);
                    </script>
                                    """
                    login_html = login_html.replace('</body>', f'{toast_script}</body>')
                    self.wfile.write(login_html.encode())

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')

    def handle_landing_page(self):
        # check if present cookie, if else go to log in
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            cookies = http.cookies.SimpleCookie(cookie_header)
            session_cookie = cookies.get('session')
            if session_cookie and send_request_to_database_server('find_user', (session_cookie.value,)):
                with open('index.html', 'r') as file:
                    landing_page = file.read()
                    landing_page = landing_page.replace('{{ username }}', session_cookie.value)
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(landing_page.encode())
                return
        # If no valid session cookie, show login page
        self.send_response(302)
        self.send_header('Location', '/login.html')
        self.end_headers()

    def log_message(self, *args):  # disable logs (delete to reenable)
        pass


os.chdir('C:\\yonatan\\.CodingP3.10\\..Projects\\.Captcha')

# Start the server
with socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
    print(f"{PORT} - {main_ip}")
    httpd.serve_forever()
