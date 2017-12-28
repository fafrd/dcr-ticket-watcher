import os
import subprocess
import signal
import sys
import json
import argparse

from datetime import datetime
from ticket import Ticket, TicketStatus

dcrwallet_log_file = os.path.expanduser('~/.dcrwallet/logs/mainnet/dcrwallet.log')
datetime_format = '%Y-%m-%d %H:%M:%S'

# Important global variables
default_dcrctl_command = ['dcrctl', '--wallet']
tickets = {}
mempool_tickets = set()
immature_tickets = set()
block_height = 0

# Configure argument parser
parser = argparse.ArgumentParser()
parser.add_argument('-l', help='The dcrwallet log file to watch.')
parser.add_argument('--simnet', help='Indicates that the log file is a simnet log file.', action='store_true')


# Signal handler to catch SIGINT
def signal_handler(signal, frame):
    print('\nExiting ticketd...')
    sys.exit(0)


# Executes a 'dcrctl --wallet' command with the given options and returns a parsed JSON object.
def execute_dcrwallet_command(command):
    result = subprocess.check_output(default_dcrctl_command + command).decode('utf-8')
    return json.loads(result)


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
def handle_new_ticket(line):
    pieces = line.split()
    purchase_date = datetime.strptime(' '.join(pieces[:2])[:-4], datetime_format)
    txhash = pieces[-1]
    
    txinfo = execute_dcrwallet_command(['gettransaction', txhash])
    price = abs(txinfo['details'][0]['amount'])
    fee = txinfo['details'][0]['fee']

    ticket = Ticket(txhash, purchase_date, price, fee, TicketStatus.MEMPOOL)
    mempool_tickets.add(ticket)
    tickets[txhash] = ticket


# Function that gets called every time a ticket is called to votes.
def handle_vote(line):
    pieces = line.split()
    vote_date = datetime.strptime(' '.join(pieces[:2])[:-4], datetime_format)
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
def handle_miss(line):
    pieces = line.split()

    miss_date = datetime.strptime(' '.join(pieces[:2])[:-4], datetime_format)
    txhash = pieces[11][:-1]

    ticket = tickets[txhash]
    ticket.vote_date = miss_date
    ticket.status = TicketStatus.MISSED


def print_tickets():
    os.system('clear')
    print('status\ttxhash\tprice')
    for ticket in tickets.values():
        print(ticket.status.name + '\t' + ticket.txhash + '\t' + str(ticket.price))


# Entry point. 
def main():
    global dcrwallet_log_file
    global tickets
    tickets = {}
    
    signal.signal(signal.SIGINT, signal_handler)
    os.system('clear')

    args = parser.parse_args()

    # Check if we will we watching a simnet wallet
    if args.simnet:
        default_dcrctl_command.append('--simnet')

    # Check if user has specified a different log file than the default
    if args.l:
        dcrwallet_log_file = os.path.expanduser(args.l)

    # Open tail process and monitor the output for line changes
    f = subprocess.Popen(['tail', '-n', '+1', '-f', dcrwallet_log_file], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    while True:
        line = f.stdout.readline().decode('utf-8');

        if 'Successfully sent SStx purchase transaction' in line:
            handle_new_ticket(line)
            print_tickets()
        elif 'Voted on block' in line:
            handle_vote(line)
            print_tickets()
        elif 'Failed to sign vote for ticket hash' in line:
            handle_miss(line)
            print_tickets()
        elif 'Connecting block' in line:
            block_height = int(line.split()[-1])
            handle_new_block()


# Main
if __name__ == '__main__':
    main()

