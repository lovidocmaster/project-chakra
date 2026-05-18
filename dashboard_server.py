#!/usr/bin/env python3
from flask import Flask
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    with open('dashboard_live.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/status')
def api_status():
    try:
        r = requests.get('http://localhost:5000/api/status', timeout=2)
        return r.json()
    except:
        return {'error': 'offline'}, 500

if __name__ == '__main__':
    print("\nDASHBOARD: http://localhost:5001\n")
    app.run(host='0.0.0.0', port=5001, debug=False)
