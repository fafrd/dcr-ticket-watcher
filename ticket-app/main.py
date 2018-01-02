import zerorpc
import argparse
from webapp import app

parser = argparse.ArgumentParser()
parser.add_argument('--port', help='The port that the web app should run on', type=int, default=8080)
parser.add_argument('--password', help='Require the given password in order to access the web app', default='')
args = parser.parse_args()

client = zerorpc.Client(timeout=3)
client.connect('tcp://localhost:44556')

app.rpc_client = client
app.password = args.password
app.run(host='0.0.0.0', port=args.port)

