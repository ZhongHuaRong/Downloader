
from PyQt5.Qt import QApplication,Qt,QObject
from PyQt5.Qt import pyqtSlot,pyqtSignal,pyqtProperty
from PyQt5.QtNetwork import QNetworkAccessManager,QNetworkRequest,QNetworkReply
from PyQt5.Qt import QThread,QUrl,QFile,QDir,QTextStream
from DownloaderAttributes import DownloaderAttributes
from HttpsDownloader import HttpsDownloader

class DownloaderManager(QObject):
    
    # 初始化函数
    def __init__(self,parent = None):
        super(DownloaderManager,self).__init__(parent)

        self._manager = QNetworkAccessManager(self)
        self._http = HttpsDownloader(self)
        # self._thread = QThread()
        # self._manager.moveToThread(self._thread)
        # self._http.moveToThread(self._thread)
        
        self._type = DownloaderAttributes.UrlType.Null
        self._url = ""
        self._path = ""
        self._startNum = 0
        self._fileTotal = 1
        self._fileName = ""

    # 析构函数
    def __del__(self):
        # if self._thread:
        #     if self._thread.isRunning():
        #         self._thread.exit()
        #         self._thread.wait()
        #     self._thread.deleteLater()
        pass

    # 设置下载路径
    @pyqtSlot(str)
    def setPath(self,value):
        self._path = value

    # 设置下载链接
    @pyqtSlot(str)
    def setUrl(self,value):
        self._url = value.strip()
    
    # 设置下载文件数量（只限于http下载）
    @pyqtSlot(int)
    def setFileTotal(self,value):
        self._fileTotal = value
    
    # 设置下载文件的开始数量（用于爬虫）
    @pyqtSlot(int)
    def setStartNum(self,value):
        self._startNum = value

    # 设置文件名（这里的文件名在只有一个文件时是文件名，
    # 在多个文件下载时时文件夹的名字）
    @pyqtSlot(str)
    def setFileName(self,value):
        self._fileName = value

    # 判断url是哪种下载链接
    # url:用于判断的url
    def urlType(self,url):
        if len(url) == 0:
            return DownloaderAttributes.UrlType.Null
        text = url.split('://')
        if len(text) < 1:
            return DownloaderAttributes.UrlType.Unknown
        elif  text[0] == "http" or text[0] == "https":
            return DownloaderAttributes.UrlType.Https
        elif text[0] == "thunder":
            return DownloaderAttributes.UrlType.BitTorrent
        else:
            return DownloaderAttributes.UrlType.Unknown

    # 下载文件
    # isPause:启动的时候是暂停的还是直接下载
    @pyqtSlot(bool,result = DownloaderAttributes)
    def downloadFile(self,isPause):
        self._type = self.urlType(self._url)

        if self._type == DownloaderAttributes.UrlType.Null:
            return None
        elif self._type == DownloaderAttributes.UrlType.Unknown:
            return None
        elif self._type == DownloaderAttributes.UrlType.Https:
            self._http.startDownload(self._url,self._path,self._fileName,self._fileTotal,isPause)
            return self._http.attributes
        else:
            return None

    # 槽函数
    # 暂停/继续下载
    @pyqtSlot()
    def pauseDown(self):
        if self._type == DownloaderAttributes.UrlType.Unknown:
            return None
        elif self._type == DownloaderAttributes.UrlType.Https:
            self._http.pauseDown()