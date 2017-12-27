import os
import subprocess
import signal
import sys
import json

from datetime import datetime
from ticket import Ticket, TicketStatus

dcrwallet_log_file = os.path.expanduser('~/.dcrwallet/logs/mainnet/dcrwallet.log')
datetime_format = '%Y-%m-%d %H:%M:%S'

tickets = {}
mempool_tickets = set()
immature_tickets = set()
block_height = 0

def signal_handler(signal, frame):
    print('\nExiting ticketd...')
    sys.exit(0)

def execute_dcrwallet_command(command):
    result = subprocess.check_output(['dcrctl', '--wallet'] + command).decode('utf-8')
    return json.loads(result)

def handle_new_block():
    mempool_tickets_copy = [x for x in mempool_tickets]
    for ticket in mempool_tickets_copy:
        txinfo = execute_dcrwallet_command(['gettransaction', ticket.txhash])
        if txinfo.blockhash != '':
            ticket.status = TicketStatus.IMMATURE
            immature_tickets.add(ticket)
            mempool_tickets.remove(ticket)
    
    immature_tickets_copy = [x for x in immature_tickets]
    for ticket in immature_tickets_copy:
        if block_height - ticket.block > 256:
            ticket.status = TicketStatus.LIVE
            immature_tickets.remove(ticket)

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

def handle_vote(line):
    pieces = line.split()

    vote_date = datetime.strptime(' '.join(pieces[:2])[:-4], datetime_format)
    txhash = pieces[-6]
    vote_hash = pieces[-3]

    ticket = tickets[txhash]
    ticket.vote_date = vote_date
    ticket.status = TicketStatus.VOTED

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

def main():
    signal.signal(signal.SIGINT, signal_handler)

    os.system('clear')

    tickets = {} # ticket hash to Ticket dictionary
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
    
main()
