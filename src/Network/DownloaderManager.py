
from PyQt5.Qt import QApplication,Qt,QObject
from PyQt5.Qt import pyqtSlot,pyqtSignal,pyqtProperty
from PyQt5.QtNetwork import QNetworkAccessManager,QNetworkRequest,QNetworkReply
from PyQt5.Qt import QThread,QUrl,QFile,QDir,QTextStream
from Network.DownloaderAttributes import DownloaderAttributes
from Network.HttpsDownloader import HttpsDownloader

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
        self._http.attributes.path = value

    # 设置下载链接
    @pyqtSlot(str)
    def setUrl(self,value):
        self._http.attributes.url = value.strip()
    
    # 设置下载文件数量（只限于http下载）
    @pyqtSlot(int)
    def setFileTotal(self,value):
        self._http.attributes.setTotalFile(value)

    # 设置文件名（这里的文件名在只有一个文件时是文件名，
    # 在多个文件下载时时文件夹的名字）
    @pyqtSlot(str)
    def setFileName(self,value):
        self._http.attributes.fileName = value

    # 判断url是哪种下载链接
    # url:用于判断的url
    # def urlType(self,url):
    #     if len(url) == 0:
    #         return DownloaderAttributes.UrlType.Null
    #     text = url.split('://')
    #     if len(text) < 1:
    #         return DownloaderAttributes.UrlType.Unknown
    #     elif  text[0] == "http" or text[0] == "https":
    #         return DownloaderAttributes.UrlType.Https
    #     elif text[0] == "thunder":
    #         return DownloaderAttributes.UrlType.BitTorrent
    #     else:
    #         return DownloaderAttributes.UrlType.Unknown

    # 下载文件
    # isPause:启动的时候是暂停的还是直接下载
    @pyqtSlot(bool,result = DownloaderAttributes)
    def downloadFile(self,isPause):
        # 先取消类型判断，直接下载
        self._http.startDownload(isPause)
        return self._http.attributes
        # self._type = self.urlType(self._http.attributes.url)

        # if self._type == DownloaderAttributes.UrlType.Null:
        #     return None
        # elif self._type == DownloaderAttributes.UrlType.Unknown:
        #     return None
        # elif self._type == DownloaderAttributes.UrlType.Https:
        #     self._http.startDownload(isPause)
        #     return self._http.attributes
        # elif self._type == DownloaderAttributes.UrlType.BitTorrent:
        #     self._http.startDownload(isPause)
        #     return self._http.attributes
        # else:
        #     return None

    # 槽函数
    # 暂停/继续下载
    @pyqtSlot()
    def pauseDown(self):
        self._http.pauseDown()
        # if self._type == DownloaderAttributes.UrlType.Unknown:
        #     pass
        # elif self._type == DownloaderAttributes.UrlType.Https:
        #     self._http.pauseDown()

    # 删除这次任务，当然，这里只是关闭文件而已
    # 正真删除操作在setting类
    # 因为只有正在下载的任务有这个类
    # 重构后，可能在这里实现文件的删除操作
    @pyqtSlot()
    def deleteFile(self):
        self._http.deleteFile()
        # if self._type == DownloaderAttributes.UrlType.Null:
        #     pass
        # elif self._type == DownloaderAttributes.UrlType.Unknown:
        #     pass
        # elif self._type == DownloaderAttributes.UrlType.Https:
        #     self._http.deleteFile()
        # else:
        #     pass