
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
    # 初始化函数
    def __init__(self,type,parent = None):
        super(DownloaderAttributes,self).__init__(parent)

        self._type = type
        self._isPause = False
        self._isFinished = False

        self._total = 0
        self._curProgress = 0

        self._startTime = 0
        self._curTime = 0

        self._filename = ""
        self._url = ""
        self._path = ""

        self._totalFile = -1
        self._finishFile = 0
        #批量下载标志位
        self._startNum = 1
        self._endNum = -1

    totalChanged = pyqtSignal()
    curProgressChanged = pyqtSignal()
    curTimeChanged = pyqtSignal()
    startTimeChanged = pyqtSignal()
    pauseChanged = pyqtSignal()
    finishChanged = pyqtSignal()
    urlChanged = pyqtSignal()
    fileNameChanged = pyqtSignal()
    pathChanged = pyqtSignal()
    totalFileChanged = pyqtSignal()
    finishFileChanged = pyqtSignal()

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
    # # # # # # # # # # # # # # # # # # # pause# # # # # # # # # # # # # # # #
    @pyqtProperty(bool,notify = pauseChanged)
    def pause(self):
        return self._isPause
    # # # # # # # # # # # # # # # # # # # finished# # # # # # # # # # # # # # # 
    @pyqtProperty(bool,notify = finishChanged)
    def finish(self):
        return self._isFinished
    # # # # # # # # # # # # # # # # # # # finished# # # # # # # # # # # # # # # 
    @pyqtProperty(int,notify = totalFileChanged)
    def totalFile(self):
        return self._totalFile
    # # # # # # # # # # # # # # # # # # # finished# # # # # # # # # # # # # # # 
    @pyqtProperty(int,notify = finishFileChanged)
    def finishFile(self):
        return self._finishFile
    # 类的属性，提供给qml使用# # # # # # # # # # # # # # # # # # # # # # # 

    def setPause(self,flag):
        if self._isPause == flag:
            return
        self._isPause = flag
        self.pauseChanged.emit()

    def setFinish(self,flag):
        if self._isFinished == flag:
            return
        self._isFinished = flag
        self.finishChanged.emit()

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
    
    # 准备下载前的所有参数重置(下载标志位不重置)
    def downloadParamReset(self):
        self._curProgress = 0
        self._curTime = time.time()
        self._startTime = self.curTime
        self._total = 0
        self._isPause = False
        self._isFinished = False
        self._filename = ""
        self._url = ""
        self._path = ""

    # 输出json格式的字符串
    def toJson(self):
        j =  QJsonDocument().object()
        j["type"] = int(self._type)
        j["url"] = self.url
        j["filename"] = self.fileName
        j["totalFile"] = self.totalFile
        j["finishFile"] = self.finishFile
        j["startNum"] = self._startNum
        j["endNum"] = self._endNum
        print(j)
        return j

    # 输出json格式的字符串
    def fromJson(self,j):
        print(j)
        print(j["filename"].toString())
        print(DownloaderAttributes.UrlType(j["type"].toVariant()))
        print(j["type"].toString())