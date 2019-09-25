
from enum import Enum

class UrlType(Enum):
    ''' 用于表示Url的类型 '''
    Unknown             = 0 # 未知类型，用于标识非URL
    Https               = 1 # http下载，用于下载服务器文件
    BitTorrent          = 2 # BT下载，BT下载首先要下载种子，属于Http下载
    Magnet              = 3 # 磁力链接

class TaskState(Enum):
    ''' 用于表示任务当前的状态 '''
    NoDownload          = 0 # 未开始下载，任务未开始
    DownloadError       = 1 # 下载错误
    Downloading         = 2 # 正在下载
    Pause               = 3 # 暂停中
    Finish              = 4 # 下载完成
    FileOpenError       = 5 # 文件打开错误(http)
    FileWriteError      = 6 # 文件写入错误(http)
    NetworkError        = 7 # 网络错误
    totalLessThanZero   = 8 # 这个错误是获取到的文件总大小为-1，暂时设置用于显示错误