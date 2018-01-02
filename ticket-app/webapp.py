import os
import zerorpc
from flask import Flask, session, redirect, url_for, request, render_template

app = Flask('ticket-app', static_url_path='', static_folder='web/static', template_folder='web/templates')
app.secret_key = os.urandom(24)

@app.route('/')
def index():
    if 'logged_in' in session or app.password == '':
        try:
            data = app.rpc_client.getTickets()
            return render_template('index.html', data=data)
        except zerorpc.exceptions.TimeoutExpired:
            return render_template('index.html', data=None)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', failed=False)

    if app.password == request.form['password'] or app.password == '':
        session['logged_in'] = True
        return redirect(url_for('index'))

    return render_template('login.html', failed=True)

