
from PyQt5.Qt import QApplication,Qt,QObject
from PyQt5.Qt import pyqtSlot,pyqtSignal,pyqtProperty
from PyQt5.QtNetwork import QNetworkAccessManager,QNetworkRequest,QNetworkReply
from PyQt5.Qt import QThread,QUrl,QFile,QDir,QTextStream
from DownloaderAttributes import DownloaderAttributes
from HttpsDownloader import HttpsDownloader

class DownloaderManager(QObject):
    showError = pyqtSignal(str,arguments = [ "err" ])
    
    urlChanged = pyqtSignal()
    pathChanged = pyqtSignal()

    # # # # # # # # # # # # # # # # # # # # # url# # # # # # # # # # # # # 
    @pyqtProperty(int,notify = urlChanged)
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value
        self.urlChanged.emit()
    # # # # # # # # # # # # # # # # # # # # # path# # # # # # # # # # # # # 
    @pyqtProperty(str,notify = pathChanged)
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value
        self.pathChanged.emit()
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    # 初始化函数
    def __init__(self,parent = None):
        super(DownloaderManager,self).__init__(parent)

        self._manager = QNetworkAccessManager(self)
        self._http = HttpsDownloader(self)
        
        self._url = ""
        self._path = ""

        #单个文件下载保存的文件名,也可以用于多个文件下载的暂存文件名
        self._fileName = ""
        self._reply = None
        
        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self.boardDataChanged)

        self._http.showError.connect(self.showError)
    
    # 判断文件是否在此目录
    # path:文件所在路径
    # filename:文件名(不带路径，带后缀名)
    def isFileExist(self,path,filename):
        dir = QDir(path)
        return filename in dir.entryList()

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

    # 命名下载文件，重名则加(num),下载未完成的临时文件名也会判断是否重名
    def checkFileName(self,name,path):
        # 分离文件名和后缀名
        info = list()
        index = name.rfind('.')
        if index <= 0:
            info = [ name, "" ]
        else:
            info = [ name[0:index] , name[index + 1:] ]

        dirList = QDir(path).entryList()
        num = 1
        filename = info[0] + ( '.' if len(info[1]) != 0 else '' ) + info[1]
        tempname = filename + '.tmp'
        while filename in dirList or tempname in dirList:
            filename = info[0] + "(" + str(num) + ")" + ( '.' if len(info[1]) != 0 else '' ) + info[1]
            tempname = filename + '.tmp'
            num += 1

        return filename
        
    # HTTPS类型的单个文件预下载，用于判断是否含有跳转或者其他情况
    # path：文件路径
    # url:下载链接
    def _readAhead_https(self,url):
        request = QNetworkRequest()
        request.setUrl(QUrl(url))
        self._reply = self._manager.get(request)
        self._reply.downloadProgress.connect(self.onReadAhead_https)

    # HTTPS类型的单个文件预下载，用于判断是否含有跳转或者其他情况
    # url:下载链接
    # total:文件大小,通过预读获取，也可以不输入，让HttpsDownloader判断
    def _downloadFile_https(self,total = 0):
        att = self._http.attributes
        att.fileName = self.checkFileName(self._fileName,self.path)
        att.url = self.url
        att.path = self.path
        att.total = total
        self._http.startDownload()
        return att

    # 下载单个文件,不允许自定义文件名
    # path:下载路径
    # url:下载链接
    def downloadFile(self,url = None,path = None):
        if url == None:
            url = self.url
        else:
            self.url = url
        if path == None:
            path = self.path
        else:
            self.path = path
        type = self.urlType(url)

        if type == DownloaderAttributes.UrlType.Null:
            return None
        elif type == DownloaderAttributes.UrlType.Unknown:
            self.showError.emit("URL格式错误")
            return None
        elif type == DownloaderAttributes.UrlType.Https:
            self._fileName = QUrl(url).fileName()
            self._readAhead_https(url)
            self._http.attributes.downloadParamReset()
            return self._http.attributes
        else:
            return None

    # 槽函数
    # 预读开始的一部分数据，判断是否含有跳转，如果含有继续downloadFile
    # 否则调用HTTPSDownloader.
    @pyqtSlot("qint64","qint64")
    def onReadAhead_https(self,receive,total):
        u = self._reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
        msg = self._reply.readAll()
        self._reply.downloadProgress.disconnect(self.onReadAhead_https)
        self._reply.deleteLater()
        self._reply.abort()
        
        print(u)
        if u != None:
            self._readAhead_https(u.toString())
        else:
            if total < 1024 * 200:
                #200K以下
                if total <= 0 :
                    #-1有可能是下载错误
                    self._readAhead_https(self.url)
                print("total:",total)
                pass
            else:
                self._downloadFile_https(total)
        return
    
    # 槽函数
    # 用于判断是否复制下载链接，用于自动下载.
    @pyqtSlot()
    def boardDataChanged(self):
        mimeData = self._clipboard.mimeData()
        print("剪贴板数据改变")
        if mimeData.hasImage():
            print("含有图片信息")
        if mimeData.hasHtml():
            print("含有HTML:",mimeData.html())
        if mimeData.hasText():
            print("含有文本:",mimeData.text())

        url = self.urlType(mimeData.text())
        if url == DownloaderAttributes.UrlType.Unknown and url == DownloaderAttributes.UrlType.Null:
            return
        else:
            self.url = mimeData.text()