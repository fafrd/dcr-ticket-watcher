import zerorpc
from webapp import app

client = zerorpc.Client(timeout=3)
client.connect('tcp://localhost:44556')

app.rpc_client = client 
app.run(host='0.0.0.0', port=80)

