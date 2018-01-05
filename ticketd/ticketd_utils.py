from datetime import datetime

datetime_format = '%Y-%m-%d %H:%M:%S'

def parse_datetime(pieces):
    return datetime.strptime(' '.join(pieces)[:-4], datetime_format)
