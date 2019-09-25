
from enum import Enum

class UrlType(Enum):
    ''' 用于表示Url的类型 '''
    Unknown = 0
    Https = 1
    BitTorrent = 2
    Magnet = 3