from json import JSONEncoder
from enum import Enum

class TicketJSONSerializer(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, TicketStatus):
            return obj.name
        return JSONEncoder.default(self, obj)

class TicketStatus(Enum):
    LIVE = 'Live'
    VOTED = 'Voted'
    MISSED = 'Missed'
    IMMATURE = 'Immature'
    MEMPOOL = 'Mempool'
    EXPIRED = 'Expired'

class Ticket():
    def __init__(self, txhash, purchase_date, price, fee, status):
        self.txhash = txhash
        self.price = price
        self.status = status
        self.purchase_date = purchase_date
        self.fee = fee
        self.block = 0
        self.reward = 0
        self.vote_date = None

