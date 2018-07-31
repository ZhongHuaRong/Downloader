
import time
import logging
import os
from PyQt5.Qt import QApplication,Qt,QObject
from PyQt5.Qt import pyqtSlot,pyqtSignal,pyqtProperty
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import QNetworkAccessManager,QNetworkRequest,QNetworkReply
from PyQt5.Qt import QThread,QUrl,QFile,QDir
from PyQt5.Qt import QProcess

class Downloader(QObject):
    #pyqtSignal
    downloadProgress = pyqtSignal("qint64","qint64","qint64",arguments = [ "receiver" , "total" , "timeStamp" ])
    showMsg = pyqtSignal(str,str,arguments = [ "title","msg" ])
    showError = pyqtSignal(str,arguments = [ "err" ])
    pasteUrlChanged = pyqtSignal(str,arguments = [ "url" ])

    totalChanged = pyqtSignal()
    curProgressChanged = pyqtSignal()
    preProgressChanged = pyqtSignal()
    curTimeChanged = pyqtSignal()
    startTimeChanged = pyqtSignal()
    downloadingChanged = pyqtSignal()
    pauseChanged = pyqtSignal()
    finishChanged = pyqtSignal()
    urlChanged = pyqtSignal()
    fileNameChanged = pyqtSignal()

    #成员变量
    reply = None

    #类的属性，提供给qml使用######################
    ####################total###################
    @pyqtProperty(int,notify = totalChanged)
    def total(self):
        return self._total

    @total.setter
    def total(self, value):
        self._total = value
        self.totalChanged.emit()
    ################curProgress##################
    @pyqtProperty(int,notify = curProgressChanged)
    def curProgress(self):
        return self._curProgress

    @curProgress.setter
    def curProgress(self, value):
        self._curProgress = value
        self.curProgressChanged.emit()
    ################preProgress##################
    @pyqtProperty(int,notify = preProgressChanged)
    def preProgress(self):
        return self._preProgress

    @preProgress.setter
    def preProgress(self, value):
        self._preProgress = value
        self.preProgressChanged.emit()
    #################curTime###################
    @pyqtProperty(int,notify = curTimeChanged)
    def curTime(self):
        return self._curTime

    @curTime.setter
    def curTime(self, value):
        self._curTime = value
        self.curTimeChanged.emit()
    #################startTime###################
    @pyqtProperty(int,notify = startTimeChanged)
    def startTime(self):
        return self._startTime

    @startTime.setter
    def startTime(self, value):
        self._startTime = value
        self.startTimeChanged.emit()
    #####################url###################
    @pyqtProperty(int,notify = urlChanged)
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value
        self.urlChanged.emit()
    #################fileName###################
    @pyqtProperty(int,notify = fileNameChanged)
    def fileName(self):
        return self._filename

    @fileName.setter
    def fileName(self, value):
        self._filename = value
        self.fileNameChanged.emit()
    ################downloading###################
    @pyqtProperty(bool,notify = downloadingChanged)
    def downloading(self):
        return self._isDownloading
    ###################pause#####################
    @pyqtProperty(bool,notify = pauseChanged)
    def pause(self):
        return self._isPause
    ###################finished#####################
    @pyqtProperty(bool,notify = finishChanged)
    def finish(self):
        return self._isFinished
    #类的属性，提供给qml使用#######################
    
    #初始化函数
    def __init__(self,parent = None):
        super(Downloader,self).__init__(parent)
        # QObject.__init__(self,parent)

        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self.boardDataChanged)
        self._manager = QNetworkAccessManager(self)
        self._file = QFile(self)
        self._isDownloading = False
        self._isPause = False
        self._isFinished = False
        self._total = 0
        self._curProgress = 0
        self._preProgress = 0
        self._startTime = 0
        self._curTime = 0
        self._filename = ""
        self._url = ""

    #析构函数
    def __del__(self):
        pass

    def setDownloading(self,flag):
        if self._isDownloading == flag:
            return
        self._isDownloading = flag
        self.downloadingChanged.emit()

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

    #文件是否存在
    def isFileExist(self,path,filename):
        dir = QDir(path)
        return filename in dir.entryList()

    #错误处理，停止下载操作 + 通知用户
    def errorHandling(self,msg):
        self.setDownloading(False)
        self.stopDown()
        if self._file.isOpen():
            self._file.close()
        self.showError.emit(msg)

    #准备下载前的所有参数重置(下载标志位不重置)
    def downloadParamReset(self):
        self.curProgress = 0
        self.curTime = time.time()
        self.startTime = self.curTime
        self.total = 0
        self.setPause(False)
        self.setFinish(False)

    @pyqtSlot(str,int,result = bool)
    def getUrl(self,url):
        #获取文件资源
        # if self.downloading:
        #     if self.total <= 0:
        #         #这个条件是用来判断是否是续传
        #         self.showMsg.emit("下载","已经存在任务，先停止之前的任务再进行下载")
        #         self._file.close()
        #         return False

        request = QNetworkRequest()
        request.setRawHeader(str("Range").encode(),str("bytes=" + str(self.curProgress) + "-").encode())
        if url == None:
            url = self.url
        else:
            self.url = url
        request.setUrl(QUrl(url))
        
        if self.reply != None:
            self.reply.deleteLater()
        self.reply = self._manager.get(request)
        self.reply.downloadProgress.connect(self.writeFile)
        print("IOError",self.reply.errorString())
        print("NetworkError",self.reply.error())
        logging.info("IOError" + self.reply.errorString())
        return True

    @pyqtSlot(str,str,result = bool)
    def setFile(self,fileName,path):
        #打开文件，写入下载的文件
        if self.total <= 0:
            #这个条件用于续传判断，不过续传不需要重新打开文件，这里保守判断
            if self.isFileExist(path,fileName):
                self.errorHandling("文件已存在，请修改路径")
                return False
            else:
                self._file.setFileName(path + "\\" + fileName)
                print("下载路径:" + path + "\\" + fileName)

        self.fileName = fileName
        self._file.open(QFile.WriteOnly)
        self._file.seek(self._file.size())
        return True

    @pyqtSlot("qint64","qint64")
    def writeFile(self,receiver,total):
        #写入文件
        if self.total != total:
            self.total = total + self.preProgress
            if self._file.isOpen():
                if self._file.size() < total:
                    self._file.resize(total)
            else:
                self.errorHandling("文件打开错误，关闭下载")
                return
        
        if self.pause:
            return
        elif not self.reply.isOpen():
            if self.downloading:
                self.errorHandling("网络通道已关闭，下载终止")
                return
        elif self._file.writeData(self.reply.readAll()) <= 0:
            self.errorHandling("文件写入错误，关闭下载")
            return
            
        #获取时间戳，因为我不知道qml如何获取，然后发射信号给qml更新界面
        self.curTime = int(time.time())
        self.curProgress = receiver + self.preProgress
        # self.total = total + self.preProgress
        if self.curProgress == self.total:
            self.success()

    #开始下载文件，另外写这个接口为了qml文件使用方便
    @pyqtSlot(str,str,str)
    def startDownload(self,url,filename,path):
        self.downloadParamReset()
        if  self.setFile(filename,path):
            if self.getUrl(url):
                self.setDownloading(True)
                self.startTime = int(time.time())

    @pyqtSlot(bool)
    def pauseDown(self,flag = True):
        self.setPause(flag)
        if self.pause:
            if self.reply != None:
                self.reply.abort()
            self.preProgress = self.curProgress
        else:
            self.getUrl(None)

    @pyqtSlot()
    def stopDown(self):
        if self._isDownloading == True:
            self.setDownloading(False)
        if self.reply != None:
            self.reply.abort()
        self._file.close()

    @pyqtSlot()
    def success(self):
        self.setFinish(True)
        self.stopDown()

    @pyqtSlot()
    def boardDataChanged(self):
        #剪贴板内容发生改变
        if self.downloading:
            QApplication.beep()
            return

        mimeData = self._clipboard.mimeData()
        print("剪贴板数据改变")
        if mimeData.hasImage():
            print("含有图片信息")
        if mimeData.hasHtml():
            print("含有HTML:",mimeData.html())
        if mimeData.hasText():
            print("含有文本:",mimeData.text())

        text = mimeData.text().split('://')
        if len(text) > 1 and ( text[0] == "http" or text[0] == "https"):
            self.pasteUrlChanged.emit(mimeData.text())
    
    @pyqtSlot(str,str,result = str)
    def checkFileName(self,name,path):
        #命名下载文件，提供接口给qml自动更改名字，重名则加(num)
        text = name.split('/')
        if len(text) <= 1:
            text = name.split('\\')

        info = list()
        index = text[ -1 ].rfind('.')
        if index <= 0:
            info = [ "未命名" , "tmp" ]
        else:
            info = [ text[-1][0:index] , text[-1][index + 1:] ]

        dirList = QDir(path).entryList()
        num = 1
        filename = info[0] + "." + info[1]
        while filename in dirList:
            filename = info[0] + "(" + str(num) + ")" + "." + info[1]
            num += 1

        return filename