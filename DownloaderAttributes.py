
import time
import json
from enum import Enum
from PyQt5.Qt import QApplication,Qt,QObject
from PyQt5.Qt import pyqtSlot,pyqtSignal,pyqtProperty
from PyQt5.Qt import QThread,QUrl,QFile,QDir,QTextStream
from PyQt5.QtCore import QJsonDocument
from PyQt5.QtCore import QJsonValue

class DownloaderAttributes(QObject):
    UrlType = Enum('Type', ( 'Unknown', 'Null', 'Https', 'BitTorrent'))
    States = Enum('State', ( # 该枚举类型用于更新UI
        'downloadError',    # 下载错误
        'NoDownload',       # 未开始下载，任务未开始
        'downloading',      # 正在下载
        'pause',            # 暂停中
        'finish',           # 下载完成
        'fileOpenError',    # 文件打开错误
        'fileWriteError',   # 文件写入错误
        'networkError',     # 网络错误
        )
    )
    # 初始化函数
    def __init__(self,type,parent = None):
        super(DownloaderAttributes,self).__init__(parent)

        self._type = type
        self._state = DownloaderAttributes.States.NoDownload

        self._total = 0
        self._curProgress = 0
        self._preProgress = 0

        self._startTime = 0
        self._curTime = 0

        self._taskname = ""
        self._filename = ""
        self._url = ""
        self._path = ""

        self._totalFile = 1
        self._finishFile = 0
        #批量下载标志位
        self._startNum = 1

    totalChanged = pyqtSignal()
    curProgressChanged = pyqtSignal()
    preProgressChanged = pyqtSignal()
    curTimeChanged = pyqtSignal()
    startTimeChanged = pyqtSignal()
    urlChanged = pyqtSignal()
    fileNameChanged = pyqtSignal()
    taskNameChanged = pyqtSignal()
    pathChanged = pyqtSignal()
    totalFileChanged = pyqtSignal()
    finishFileChanged = pyqtSignal()
    stateChanged = pyqtSignal()

    # 类的属性，提供给qml使用# # # # # # # # # # # # # # # # # # # # # # 
    # # # # # # # # # # # # # # # # # # # # total# # # # # # # # # # # # # # # 
    @pyqtProperty(int,notify = totalChanged)
    def total(self):
        return self._total

    @total.setter
    def total(self, value):
        self._total = value
        self.totalChanged.emit()
    # # # # # # # # # # # # # # # # curProgress# # # # # # # # # # # # # # # # 
    @pyqtProperty(int,notify = curProgressChanged)
    def curProgress(self):
        return self._curProgress

    @curProgress.setter
    def curProgress(self, value):
        self._curProgress = value
        self.curProgressChanged.emit()
    # # # # # # # # # # # # # # # # preProgress# # # # # # # # # # # # # # # # 
    @pyqtProperty(int,notify = preProgressChanged)
    def preProgress(self):
        return self._preProgress

    @preProgress.setter
    def preProgress(self, value):
        self._preProgress = value
        self.preProgressChanged.emit()
    # # # # # # # # # # # # # # # # # curTime# # # # # # # # # # # # # # # # # 
    @pyqtProperty(int,notify = curTimeChanged)
    def curTime(self):
        return self._curTime

    @curTime.setter
    def curTime(self, value):
        self._curTime = value
        self.curTimeChanged.emit()
    # # # # # # # # # # # # # # # # # startTime# # # # # # # # # # # # # # # # 
    @pyqtProperty(int,notify = startTimeChanged)
    def startTime(self):
        return self._startTime

    @startTime.setter
    def startTime(self, value):
        self._startTime = value
        self.startTimeChanged.emit()
    # # # # # # # # # # # # # # # # # # # # # url# # # # # # # # # # # # # # # 
    @pyqtProperty(str,notify = urlChanged)
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value
        self.urlChanged.emit()
    # # # # # # # # # # # # # # # # # # # # # path# # # # # # # # # # # # # # # 
    @pyqtProperty(str,notify = pathChanged)
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value
        self.pathChanged.emit()
    # # # # # # # # # # # # # # # # # fileName# # # # # # # # # # # # # # # # # 
    @pyqtProperty(str,notify = fileNameChanged)
    def fileName(self):
        return self._filename

    @fileName.setter
    def fileName(self, value):
        self._filename = value
        self.fileNameChanged.emit()
    # # # # # # # # # # # # # # # # # taskName# # # # # # # # # # # # # # # # # 
    @pyqtProperty(str,notify = taskNameChanged)
    def taskName(self):
        return self._taskname

    @taskName.setter
    def taskName(self, value):
        self._taskname = value
        self.taskNameChanged.emit()
    # # # # # # # # # # # # # # # # # # # state # # # # # # # # # # # # # # # #
    # 这里特别注明一下，enum在qml无法使用，所以采用string的方式
    @pyqtProperty(str,notify = stateChanged)
    def state(self):
        return self.getState2String()
    # # # # # # # # # # # # # # # # # # # totalFile# # # # # # # # # # # # # # 
    @pyqtProperty(int,notify = totalFileChanged)
    def totalFile(self):
        return self._totalFile
    # # # # # # # # # # # # # # # # # # # finishFile# # # # # # # # # # # # # # 
    @pyqtProperty(int,notify = finishFileChanged)
    def finishFile(self):
        return self._finishFile
    # # # # # # # # # # # # # # # # # # # startNum# # # # # # # # # # # # # # 
    @pyqtProperty(int)
    def startNum(self):
        return self._startNum
    # 类的属性，提供给qml使用# # # # # # # # # # # # # # # # # # # # # # # 

    def setState(self,value):
        if self._state == value:
            return
        self._state = value
        self.stateChanged.emit()

    def setTotalFile(self,value):
        if self._totalFile == value:
            return
        self._totalFile = value
        self.totalFileChanged.emit()
    
    def setFinishFile(self,value):
        if self._finishFile == value:
            return
        self._finishFile = value
        self.finishFileChanged.emit()

    def completedOne(self):
        self._finishFile = self._finishFile + 1
        self.finishFileChanged.emit()

    def setStartNum(self,value):
        if self._startNum == value:
            return
        self._startNum = value
    
    # 准备下载前的所有参数重置(下载标志位不重置)
    def downloadParamReset(self):
        self.curProgress = 0
        self.preProgress = 0
        self.curTime = time.time()
        self.startTime = self.curTime
        self.total = 0
        self.filename = ""
        self.url = ""
        self.path = ""

    #将enum转为string
    def getType2String(self):
        return {
            DownloaderAttributes.UrlType.Unknown:"Unknown",
            DownloaderAttributes.UrlType.Null:"Null",
            DownloaderAttributes.UrlType.Https:"Https",
            DownloaderAttributes.UrlType.BitTorrent:"BitTorrent",
        }.get(self._type,"Unknown")

    # 将State转为string
    def getState2String(self):
        return {
            DownloaderAttributes.States.downloadError:"downloadError",
            DownloaderAttributes.States.NoDownload:"NoDownload",
            DownloaderAttributes.States.downloading:"downloading",
            DownloaderAttributes.States.pause:"pause",
            DownloaderAttributes.States.finish:"finish",
            DownloaderAttributes.States.fileOpenError:"fileOpenError",
            DownloaderAttributes.States.fileWriteError:"fileWriteError",
            DownloaderAttributes.States.networkError:"networkError",
        }.get(self._state,"downloadError")

    #将string转为type enum
    def setString2Type(self,str):
        self._type = {
            "Unknown" : DownloaderAttributes.UrlType.Unknown,
            "Null" : DownloaderAttributes.UrlType.Null,
            "Https" : DownloaderAttributes.UrlType.Https,
            "BitTorrent" : DownloaderAttributes.UrlType.BitTorrent,
        }.get(str,DownloaderAttributes.UrlType.Unknown)
        return self._type
        
    #将string转为state enum
    def setString2State(self,str):
        s = {
            "downloadError" : DownloaderAttributes.States.downloadError,
            "NoDownload" : DownloaderAttributes.States.NoDownload,
            "downloading" : DownloaderAttributes.States.downloading,
            "pause" : DownloaderAttributes.States.pause,
            "finish" : DownloaderAttributes.States.finish,
            "fileOpenError" : DownloaderAttributes.States.fileOpenError,
            "fileWriteError" : DownloaderAttributes.States.fileWriteError,
            "networkError" : DownloaderAttributes.States.networkError,
        }.get(str,DownloaderAttributes.States.downloadError)
        self.setState(s)
        return self._state

    # 输出json格式的字符串
    def toJson(self):
        j =  QJsonDocument().object()
        j["type"] = self.getType2String()
        j["state"] = self.getState2String()
        j["url"] = self.url
        j["filename"] = self.fileName
        j["curProgress"] = self.curProgress
        j["totalFile"] = self.totalFile
        j["finishFile"] = self.finishFile
        j["startNum"] = self._startNum
        j["fileSize"] = self._total
        return j

    # 输出json格式的字符串
    def fromJson(self,j):
        print(j)
        self.setString2Type(j["type"].toString())
        self.setString2State(j["state"].toString())
        self.url = j["url"].toString()
        self.fileName = j["filename"].toString()
        self.preProgress = j["curProgress"].toInt()
        self.curProgress = self.preProgress
        self.setTotalFile(j["totalFile"].toInt())
        self.setFinishFile(j["finishFile"].toInt())
        self._startNum = j["startNum"].toInt()
        self.total = j["fileSize"].toInt()

    
    # 判断文件是否在此目录
    # path:文件所在路径
    # filename:文件名(不带路径，带后缀名)
    def isFileExist(self,path,filename):
        dir = QDir(path)
        return filename in dir.entryList()

    # 命名下载文件，重名则加(num),这个是连tmp文件也一并检查
    def checkFileNameAndTemp(self,name,path):
        # 分离文件名和后缀名
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

    
    # 命名下载文件，重名则加(num),这个是只检查当前文件名
    def checkFileName(self,name,path):
        # 分离文件名和后缀名
        info = list()
        index = name.rfind('.')
        if index <= 0:
            info = [ name, "" ]
        else:
            info = [ name[0:index] , name[index + 1:] ]

        dirList = QDir(path).entryList()
        filename = name
        if not filename in dirList:
            return filename
        num = 1
        filename = info[0] + ( '.' if len(info[1]) != 0 else '' ) + info[1]
        while filename in dirList:
            filename = info[0] + "(" + str(num) + ")" + ( '.' if len(info[1]) != 0 else '' ) + info[1]
            num += 1

        return filename