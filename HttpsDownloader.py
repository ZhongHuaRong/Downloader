
import logging
import os
import json
from PyQt5.Qt import QApplication,Qt,QObject
from PyQt5.Qt import pyqtSlot,pyqtSignal,pyqtProperty
from PyQt5.QtNetwork import QNetworkAccessManager,QNetworkRequest,QNetworkReply
from PyQt5.Qt import QThread,QUrl,QFile,QDir,QJsonDocument
from DownloaderAttributes import DownloaderAttributes

class HttpsDownloader(QObject):
    # pyqtSignal
    downloadProgress = pyqtSignal("qint64","qint64","qint64",arguments = [ "receiver" , "total" , "timeStamp" ])
    showError = pyqtSignal(str,arguments = [ "err" ])

    # 初始化函数
    def __init__(self,parent = None):
        super(HttpsDownloader,self).__init__(parent)

        self._manager = QNetworkAccessManager(self)
        self._attributes = DownloaderAttributes(DownloaderAttributes.UrlType.Https,self)
        self._tmpFile = QFile(self)
        self._configFile = QFile(self)

    # 析构函数
    def __del__(self):
        if self._tmpFile.isOpen():
            self._tmpFile.close()
        if self._tmpFile.isOpen():
            self._tmpFile.close()
        pass

    # 类的属性，提供给qml使用# # # # # # # # # # # # # # # # # # # # # # 
    # # # # # # # # # # # # # # # # # # # # attributes# # # # # # # # # 
    @pyqtProperty(DownloaderAttributes)
    def attributes(self):
        return self._attributes

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
        if self._configFile.isOpen():
            self._configFile.close()
        if self._tmpFile.isOpen():
            self._tmpFile.close()
        self.showError.emit(msg)

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
    
    # 打开配置文件
    def _setTemp(self):
        tempname = self.attributes.fileName + '.tmp'
        config = self.attributes.fileName + '.tmp.cfg'
            
        self._configFile.setFileName(self.attributes.path + config)
        self._tmpFile.setFileName(self.attributes.path + tempname)

        self._configFile.open(QFile.ReadWrite)
        self._tmpFile.open(QFile.WriteOnly)

    # 保存config
    def _saveConfig(self):
        info = self.attributes.toJson()
        self._configFile.write(QJsonDocument(info).toJson())
        self._configFile.flush()

    # 读取config
    def _loadConfig(self):
        cfg = self._configFile.readAll()
        cfg = self.attributes.toJson()
        cfg =  QJsonDocument(cfg).toJson()
        print("cfg",cfg)
        j = QJsonDocument.fromJson(cfg).object()
        self.attributes.fromJson(j)
    
    # 加载临时文件，继续下载,没有则是开始下载并生成配置文件
    def loadTemp(self):
        self._setTemp()

        self._saveConfig()
        self._loadConfig()
        

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
    def writeFile(self,receive,total):
        print("receive",receive)
        print("total",total)
        
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
    # 开始下载文件
    @pyqtSlot(str,str,str)
    def startDownload(self):
        self.loadTemp()

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