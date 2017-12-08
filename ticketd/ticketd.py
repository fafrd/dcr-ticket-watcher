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

def signal_handler(signal, frame):
    print('\nExiting ticketd...')
    sys.exit(0)

def execute_dcrwallet_command(command):
    result = subprocess.check_output(['dcrctl', '--wallet'] + command).decode('utf-8')
    return json.loads(result)

def handle_new_ticket(line):
    pieces = line.split()
    purchase_date = datetime.strptime(' '.join(pieces[:2])[:-4], datetime_format)
    txhash = pieces[-1]
    price = 0 #TODO
    ticket = Ticket(txhash, purchase_date, price, TicketStatus.LIVE)
    
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
    print('status\ttxhash')
    for ticket in tickets.values():
        print(ticket.status.name + '\t' + ticket.txhash)

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
    

main()
