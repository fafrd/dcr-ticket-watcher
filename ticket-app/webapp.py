import zerorpc
from flask import Flask

app = Flask('ticket-app', static_url_path='', static_folder='web/static', template_folder='web/templates')

@app.route('/')
def index():
    try:
        return app.rpc_client.getTickets()
    except zerorpc.exceptions.TimeoutExpired:
        return 'Error: could not connect to RPC server. Is ticketd running?'

