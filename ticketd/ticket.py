from enum import Enum

class TicketStatus(Enum):
    LIVE = 'Live'
    VOTED = 'Voted'
    MISSED = 'Missed'

class Ticket():
    def __init__(self, txhash, purchase_date, price, status):
        self.txhash = txhash
        self.price = price
        self.status = status
        self.purchase_date = purchase_date
        self.vote_date = None

