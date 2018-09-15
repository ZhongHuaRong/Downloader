
from PyQt5.Qt import QApplication,Qt,QObject,QDir,QUrl
from PyQt5.Qt import pyqtSlot,pyqtSignal,pyqtProperty
from DownloaderAttributes import DownloaderAttributes

class Setting(QObject):

    haveNewUrl = pyqtSignal(str,arguments = [ "url" ])

     # 初始化函数
    def __init__(self,parent = None):
        super(Setting,self).__init__(parent)

        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self.boardDataChanged)

    # 判断url是哪种下载链接
    # url:用于判断的url
    @pyqtSlot(str,result = DownloaderAttributes.UrlType)
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
            self.haveNewUrl.emit(mimeData.text())

    # 判断文件是否在此目录
    # path:文件所在路径
    # filename:文件名(不带路径，带后缀名)
    def isFileExist(self,path,filename):
        dir = QDir(path)
        return filename in dir.entryList()

    # 命名下载文件，重名则加(num),下载未完成的临时文件名也会判断是否重名,同一三个文件
    # 的名字，在续传会方便很多
    # 这里的重命名和DownloadAttributes的不同，这里传入的不是文件名，而是下载链接，
    # 由QUrl判断出文件名
    @pyqtSlot(str,str, result = str)
    def checkFileName(self,name,path):
        # 分离文件名和后缀名
        name = QUrl(name.strip()).fileName()
        info = list()
        index = name.rfind('.')
        if index <= 0:
            info = [ name, "" ]
        else:
            info = [ name[0:index] , name[index + 1:] ]

        dirList = QDir(path).entryList()
        filename = name
        tempname = filename + '.tmp'
        cfgname = tempname + '.cfg'
        if not filename in dirList and not tempname in dirList and not cfgname in dirList:
            return filename
        num = 1
        filename = info[0] + ( '.' if len(info[1]) != 0 else '' ) + info[1]
        while filename in dirList or tempname in dirList or cfgname in dirList:
            filename = info[0] + "(" + str(num) + ")" + ( '.' if len(info[1]) != 0 else '' ) + info[1]
            tempname = filename + '.tmp'
            cfgname = tempname + '.cfg'
            num += 1

        return filename