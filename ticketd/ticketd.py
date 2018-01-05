import os
import subprocess
import signal
import sys
import json
import argparse
import threading
import zerorpc
import urllib.request

from datetime import datetime
from ticket import Ticket, TicketStatus, TicketJSONSerializer
from ticketd_utils import parse_datetime

dcrwallet_log_file = os.path.expanduser('~/.dcrwallet/logs/mainnet/dcrwallet.log')
cmc_api_url = 'https://api.coinmarketcap.com/v1/ticker/decred/'

# Important global variables
default_dcrctl_command = ['dcrctl', '--wallet']
tickets = {}
mempool_tickets = set()
immature_tickets = set()
caught_up = False

# Network stats
block_height = 0
wallet_unlocked = False
dcr_price_usd = 0.0
ticket_price = 0.0
ticket_pool_size = 0

# Configure argument parser
parser = argparse.ArgumentParser()
parser.add_argument('-l', help='The dcrwallet log file to watch.')
parser.add_argument('--simnet', help='Indicates that the log file is a simnet log file.', action='store_true')
parser.add_argument('--port', help='The port that the RPC server should run on', type=int, default=44556)

# Signal handler to catch SIGINT
def signal_handler(signal, frame):
    print('\nExiting ticketd...')
    sys.exit(0)


# Executes a 'dcrctl --wallet' command with the given options and returns a parsed JSON object.
def execute_dcrwallet_command(command):
    result = subprocess.check_output(default_dcrctl_command + command).decode('utf-8')
    return json.loads(result)


def update_network_stats():
    global wallet_unlocked
    global dcr_price_usd
    global ticket_price
    global ticket_pool_size

    data = execute_dcrwallet_command(['getstakeinfo'])
    ticket_pool_size = int(data['poolsize'])
    ticket_price = float(data['difficulty'])
    
    data = execute_dcrwallet_command(['walletinfo'])
    wallet_unlocked = bool(data['unlocked'])

    data = urllib.request.urlopen(cmc_api_url).read().decode()
    data = json.loads(data)[0]
    dcr_price_usd = float(data['price_usd'])


# Function that gets called every block. It check all of the mempool and immature tickets to see if they
# were included in the block or matured.
def handle_new_block():
    global mempool_tickets
    global immature_tickets

    mempool_tickets_copy = [x for x in mempool_tickets]
    for ticket in mempool_tickets_copy:
        txinfo = execute_dcrwallet_command(['gettransaction', ticket.txhash])
        if txinfo.blockhash:
            ticket.status = TicketStatus.IMMATURE
            immature_tickets.add(ticket)
            mempool_tickets.remove(ticket)
    
    if immuture_tickets.empty():
        return

    immature_tickets_copy = [x for x in immature_tickets]
    for ticket in immature_tickets_copy:
        if block_height - ticket.block > 256:
            ticket.status = TicketStatus.LIVE
            immature_tickets.remove(ticket)


# Function that gets called every time a new ticket is bought.
def handle_new_ticket(pieces):
    purchase_date = parse_datetime(pieces[:2])
    txhash = pieces[-1]
    
    txinfo = execute_dcrwallet_command(['gettransaction', txhash])
    price = abs(txinfo['details'][0]['amount'])
    fee = txinfo['details'][0]['fee']

    ticket = Ticket(txhash, purchase_date, price, fee, TicketStatus.MEMPOOL)
    mempool_tickets.add(ticket)
    tickets[txhash] = ticket


# Function that gets called every time a ticket is called to votes.
def handle_vote(pieces):
    vote_date = parse_datetime(pieces[:2])
    txhash = pieces[-6]
    vote_hash = pieces[-3]

    ticket = tickets[txhash]
    ticket.vote_date = vote_date
    ticket.status = TicketStatus.VOTED

    transaction_overview = execute_dcrwallet_command(['gettransaction', vote_hash])
    rawdata = transaction_overview['hex']
    decoded_transaction = execute_dcrwallet_command(['decoderawtransaction', rawdata])
    for input_ in decoded_transaction['vin']:
        if int(input_['txid'], 16) == 0:
            ticket.reward = int(input_['amountin'])
            break


# Function that gets called every time a ticket misses.
def handle_miss(pieces):
    miss_date = parse_datetime(pieces[:2])
    txhash = pieces[11][:-1]

    ticket = tickets[txhash]
    ticket.vote_date = miss_date
    ticket.status = TicketStatus.MISSED


class ticketdRPC():
    def getTickets(self):
        global tickets
        global block_height

        obj = {
                'block_height' : block_height,
                'ticket_price' : ticket_price,
                'ticket_pool_size': ticket_pool_size,
                'price_usd' : dcr_price_usd,
                'tickets' : [t for t in tickets]
        }
        return json.dumps(obj, cls=TicketJSONSerializer)


def run_daemon(parent_pid):
    global tickets
    global dcrwallet_log_file
    
    # Read network stats and store them before we try to catch up.
    update_network_stats()

    # Find the date and time of the most recent log entry in the dcrwallet log file
    most_recent_log_date = None
    f = subprocess.Popen(['tail', '-n', '1', dcrwallet_log_file], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    res, err = f.communicate()
    if err:
        print('An error occured while reading log file: ' + err.decode())
        os.kill(parent_pid, signal.SIGINT)
        return
    else:
        pieces = res.decode().split()
        most_recent_log_date = parse_datetime(pieces[:2])

    # Open tail process and monitor the output for line changes
    f = subprocess.Popen(['tail', '-n', '+1', '-f', dcrwallet_log_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while True:
        line = f.stdout.readline().decode('utf-8');
        pieces = line.split()
        date = parse_datetime(pieces[:2])

        if 'Successfully sent SStx purchase transaction' in line:
            handle_new_ticket(pieces)
        elif 'Voted on block' in line:
            handle_vote(pieces)
        elif 'Failed to sign vote for ticket hash' in line:
            handle_miss(pieces)
        elif 'Connecting block' in line:
            block_height = int(pieces[-1])
            handle_new_block()



# Entry point. 
def main():
    global dcrwallet_log_file
    global tickets

    tickets = {}
    
    signal.signal(signal.SIGINT, signal_handler)

    args = parser.parse_args()

    # Check if we will we watching a simnet wallet
    if args.simnet:
        default_dcrctl_command.append('--simnet')

    # Check if user has specified a different log file than the default
    if args.l:
        dcrwallet_log_file = os.path.expanduser(args.l)

    thread = threading.Thread(target=run_daemon, args=(os.getpid(),))
    thread.daemon = True
    thread.start()

    # Start RPC server
    server = zerorpc.Server(ticketdRPC())
    server.bind('tcp://0.0.0.0:' + str(args.port))
    server.run()

# Main
if __name__ == '__main__':
    main()

