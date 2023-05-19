# Cryptopaper Options Service
WSGI = True
from flask import Flask, render_template, request, send_file
from flask_cors import CORS
from datetime import datetime
if WSGI: from waitress import serve
import os, re, subprocess

LIBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
OPTIONS_FILE = os.path.join(LIBDIR, 'options.txt')
WATCH_WORDS_FILE = os.path.join(LIBDIR, 'watch-words.txt')

app = Flask(__name__, template_folder='lib')
CORS(app)

def sanitize_watch_words(watch_words: str):
    lines = watch_words.split('\n')
    # Remove non-alphanumeric characters and empty lines
    sanitized_lines = [re.sub(r'\W+', '', line) for line in lines if line.strip() != '']
    return '\n'.join(sorted(sanitized_lines, key=str.lower))

def sanitize_location(location: str):
    return ''.join(ch for ch in location if ch.isprintable())

def sanitize_threshold(s):
    try: return "{:.4f}".format(float(s)) if float(s) > 0 else '0.0001'
    except ValueError: return '0.0002'

def is_raspberry_pi():
    return any('BCM' in line for line in open('/proc/cpuinfo'))

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/')
def home():
    system_name = os.uname().nodename
    current_time = datetime.now().strftime('%y-%m-%d %H:%M:%S')
    update_disabled = '' if is_raspberry_pi() else ' disabled'
    return render_template('index.html', status = f'{system_name} :: {current_time}', ss_ts = datetime.now().second, update_disabled = update_disabled)

@app.route('/load_watch_words', methods=['GET'])
def load_watch_words():
    try:
        with open(WATCH_WORDS_FILE, 'r') as file:
            data = file.read()
        return {'data': data}
    except: return {'error': 'An error occurred while loading the watch-words file.'}

@app.route('/load_options', methods=['GET'])
def load_options():
    try:
        with open(OPTIONS_FILE, 'r') as file:
            lines = file.readlines()
            threshold = lines[0].strip() if len(lines) > 0 else ""
            location = lines[1].strip() if len(lines) > 1 else ""
        return {'location': location, 'threshold': threshold}
    except error as e: return {'error': 'An error occurred while loading the options file.' + str(e)}

@app.route('/save_watch_words', methods=['POST'])
def save_watch_words():
    text = sanitize_watch_words(request.form['text'])
    try:
        with open(WATCH_WORDS_FILE, 'w') as file:
            file.write(text)
        return {'message': 'File saved successfully.'}
    except: return {'error': 'An error occurred while saving the watch-words file.'}

@app.route('/save_options', methods=['POST'])
def save_options():
    threshold = sanitize_threshold(request.form['threshold'])
    location = sanitize_location(request.form['location'])
    try:
        with open(OPTIONS_FILE, 'w') as file:
            file.write(threshold + '\n' + location)
        return {'message': 'File saved successfully.'}
    except: return {'error': 'An error occurred while saving the options file.'}

@app.route('/reboot', methods=['GET'])
def run_reboot():
    reboot_command = 'sudo reboot' if is_raspberry_pi() else 'reboot'
    try: subprocess.check_output(reboot_command, shell=True)
    except subprocess.CalledProcessError as e:
        return {'error': 'An error occurred while running the command: ' + str(e)}

@app.route('/patch', methods=['GET'])
def run_patch():
    try: 
        result = subprocess.check_output("git pull", shell=True)
        return {'message': f"Patch command run successfully:\n{result.decode('utf-8')}"}
    except subprocess.CalledProcessError as e:
        return {'error': 'An error occurred while running the command: ' + str(e)}

@app.route('/screenshot')
def screenshot():
    file_path = 'screenshot.png'
    if os.path.exists(file_path):
        os.remove(file_path)
    env = os.environ.copy()
    env['DISPLAY'] = ':0'
    subprocess.run(['scrot', file_path], env=env, check=True)
    return send_file(file_path, mimetype='image/png', as_attachment=True)

@app.route('/stream')
def stream():
    wrapper = '''<!DOCTYPE html>
    <html>
    <head>
        <title>Stream</title>
        <script type="text/javascript">
            function refreshImage() {
                var img = document.getElementById('screenshot');
                var src = "/screenshot?" + new Date().getTime();
                img.src = src;
            }
            setInterval(refreshImage, 1000);
        </script>
    </head>
    <body style = "padding: 0px; margin: 0px; background-color: #000;">
        <img id="screenshot" src="/screenshot" alt="Screenshot">
    </body>
    </html>
    '''
    return wrapper

    
if __name__ == '__main__':
    if WSGI:
        serve(app, host="0.0.0.0", port=5000)
    else: 
        app.run(host = "0.0.0.0", port=5000)
