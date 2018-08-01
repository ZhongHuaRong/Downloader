
import time
import logging
import os
from PyQt5.Qt import QApplication,Qt,QObject
from PyQt5.Qt import pyqtSlot,pyqtSignal,pyqtProperty
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import QNetworkAccessManager,QNetworkRequest,QNetworkReply
from PyQt5.Qt import QThread,QUrl,QFile,QDir,QTextStream
from PyQt5.Qt import QProcess

class Downloader(QObject):
    # pyqtSignal
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

    # 成员变量
    reply = None

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
    @pyqtProperty(int,notify = urlChanged)
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value
        self.urlChanged.emit()
    # # # # # # # # # # # # # # # # # fileName# # # # # # # # # # # # # # # # # 
    @pyqtProperty(int,notify = fileNameChanged)
    def fileName(self):
        return self._filename

    @fileName.setter
    def fileName(self, value):
        self._filename = value
        self.fileNameChanged.emit()
    # # # # # # # # # # # # # # # # downloading# # # # # # # # # # # # # # # #
    @pyqtProperty(bool,notify = downloadingChanged)
    def downloading(self):
        return self._isDownloading
    # # # # # # # # # # # # # # # # # # # pause# # # # # # # # # # # # # # # #
    @pyqtProperty(bool,notify = pauseChanged)
    def pause(self):
        return self._isPause
    # # # # # # # # # # # # # # # # # # # finished# # # # # # # # # # # # # # # 
    @pyqtProperty(bool,notify = finishChanged)
    def finish(self):
        return self._isFinished
    # 类的属性，提供给qml使用# # # # # # # # # # # # # # # # # # # # # # # 
    
    # 初始化函数
    def __init__(self,parent = None):
        super(Downloader,self).__init__(parent)
        #  QObject.__init__(self,parent)

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
        self._isRelative = True

    # 析构函数
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

    # 判断文件是否在此目录
    # path:文件所在路径
    # filename:文件名(不带路径，带后缀名)
    def isFileExist(self,path,filename):
        dir = QDir(path)
        return filename in dir.entryList()

    # 错误处理，停止下载操作,关闭文件,通知用户
    # msg:错误信息，反馈给用户
    def errorHandling(self,msg):
        self.setDownloading(False)
        self.stopDown()
        if self._file.isOpen():
            self._file.close()
        self.showError.emit(msg)

    # 准备下载前的所有参数重置(下载标志位不重置)
    def downloadParamReset(self):
        self.curProgress = 0
        self.preProgress = 0
        self.curTime = time.time()
        self.startTime = self.curTime
        self.total = 0
        self.setPause(False)
        self.setFinish(False)
        self._isRelative = True
        
    # 开始下载，设置下载信息
    # url:链接，如果为空则使用上一次留下来的URL，此功能用于暂停续传
    # 如果为HTTPS链接，则下载
    def getUrl(self,url):
        request = QNetworkRequest()
        request.setRawHeader(str("Range").encode(),str("bytes=" + str(self.curProgress) + "-").encode())
        # 当URL参数是none时，则是续传，否则是一个新任务
        if url == None:
            url = self.url
        else:
            url = url.strip()
            self.url = url
        request.setUrl(QUrl(url))

        if self.reply != None:
            self.reply.deleteLater()
        self.reply = self._manager.get(request)
        self.reply.downloadProgress.connect(self.writeFile)
        self.reply.finished.connect(self.downloadError)
        return True

    # 设置文件，用于存储下载的数据
    # fileName:文件名，不带路径，带后缀名
    # path:路径，绝对路径
    def setFile(self,fileName,path):
        if self.total <= 0:
            # 这个条件用于续传判断，不过续传不需要重新打开文件，这里保守判断
            if self.isFileExist(path,fileName):
                self.errorHandling("文件已存在，请修改路径")
                return False
            else:
                self._file.setFileName(path + "\\" + fileName)
                print("下载路径:" + path + "\\" + fileName)

        self.fileName = fileName
        self._file.open(QFile.WriteOnly)
        # 这里不需要seek，因为暂停续传不需要重新打开文件
        # 不清楚以后的任务续传需不需要使用此函数接口
        self._file.seek(self._file.size())
        return True

    # 槽函数
    # 用于任务终止时输出错误信息，下载完成也会触发
    @pyqtSlot()
    def downloadError(self):
        print("IOError",self.reply.errorString())
        print("NetworkError",self.reply.error())
        logging.info("IOError" + self.reply.errorString())

    # 槽函数
    # 把下载的内容写入文件
    # receive:已接收的字节数
    # total:文件总大小
    @pyqtSlot("qint64","qint64")
    def writeFile(self,receiver,total):
        print("receiver",receiver)
        print("total",total)

        # # 先判断是否重定向
        if self._isRelative:
            u = self.reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
            if u != None:
                self._isRelative = True
                print(u)
                self.reply.downloadProgress.disconnect(self.writeFile)
                self.reply.abort()
                self.getUrl(u.toString())
                return
            else:
                self._isRelative = False
        
        # 这里是刚开始下载的时候，total默认是0,设置下载的文件大小
        if self.total != total:
            self.total = total + self.preProgress
            if self._file.isOpen():
                if self._file.size() < total:
                   self._file.resize(total)
            else:
                self.errorHandling("文件打开错误，关闭下载")
                return
        
        # 这里是暂停续传部分，因为暂停发生后，reply.abort()
        # 关闭下载通道，但是还是会触发这个槽函数
        if self.pause:
            # 暂停触发，不处理后面接受到的字节数
            return
        elif not self.reply.isOpen():
            # 如果不是因为暂停而关闭reply的通道的情况则需要通报用户下载失败
            if self.downloading:
                self.errorHandling("网络通道已关闭，下载终止")
                return
        else:
            #  正常情况
            data = self.reply.readAll()
            if len(data) == 0:
                #  没有数据读取
                self.success()
                return
            if self._file.writeData(data) <= 0:
                self.errorHandling("文件写入错误，关闭下载")
                return
            
        # 获取时间戳，因为我不知道qml如何获取，然后发射信号给qml更新界面
        self.curTime = int(time.time())
        self.curProgress = receiver + self.preProgress
        # 下载完成的处理，不使用finish是因为那个信号啥都会触发
        if self.curProgress == self.total:
            self.success()

    # 槽函数
    # 开始下载文件，另外写这个接口为了qml文件使用方便
    # url:下载的链接，目前只接受http
    # filename:这个在下载链接中可以提取出文件名，不过有时候用户需要更改名字
    # path:路径，用于生产文件.
    @pyqtSlot(str,str,str)
    def startDownload(self,url,filename,path):
        # 防止UI发生异常
        if self.downloading:
            QApplication.beep()
            return
        # 需要重置参数，因为该函数是重新下载
        self.downloadParamReset()
        # 先生成文件，再下载
        if  self.setFile(filename,path):
            if self.getUrl(url):
                self.setDownloading(True)
                self.startTime = int(time.time())

    # 槽函数
    # 暂停/继续下载
    # flag:默认为TRUE
    #      ture:暂停，使用abort终止下载，然后设置当前进度
    #      false:继续下载，通过getUrl传入None实现.
    @pyqtSlot(bool)
    def pauseDown(self,flag = True):
        self.setPause(flag)
        if self.pause:
            if self.reply != None:
                self.reply.abort()
            self.preProgress = self.curProgress
        else:
            self.getUrl(None)

    # 槽函数
    # 停止下载，所有标志位重置为FALSE，关闭下载通道，关闭文件.
    @pyqtSlot()
    def stopDown(self):
        if self._isDownloading == True:
            self.setDownloading(False)
        if self.reply != None:
            self.reply.abort()
        self._file.close()

    # 槽函数
    # 下载成功，设置标志位finish为true，然后停止下载.
    @pyqtSlot()
    def success(self):
        self.setFinish(True)
        self.stopDown()

    # 槽函数
    # 用于判断是否复制下载链接，用于自动下载.
    @pyqtSlot()
    def boardDataChanged(self):
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
    
    # 槽函数
    # 命名下载文件，提供接口给qml自动更改名字，重名则加(num)
    @pyqtSlot(str,str,result = str)
    def checkFileName(self,name,path):
        text = QUrl(name.strip()).fileName()

        # 分离文件名和后缀名
        info = list()
        index = text.rfind('.')
        if index <= 0:
            info = [ text, "" ]
        else:
            info = [ text[0:index] , text[index + 1:] ]

        dirList = QDir(path).entryList()
        num = 1
        filename = info[0] + ( '.' if len(info[1]) != 0 else '' ) + info[1]
        while filename in dirList:
            filename = info[0] + "(" + str(num) + ")" + ( '.' if len(info[1]) != 0 else '' ) + info[1]
            num += 1

        return filename