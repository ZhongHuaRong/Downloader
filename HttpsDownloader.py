
import time
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

    # 初始化函数
    def __init__(self,parent = None):
        super(HttpsDownloader,self).__init__(parent)

        self._manager = QNetworkAccessManager(self)
        self._attributes = DownloaderAttributes(DownloaderAttributes.UrlType.Https,self)
        self._tmpFile = QFile(self)
        self._configFile = QFile(self)
        self._reply = None
        self._readAheadReply = None

        # 保存跳转后的url
        self._jumpUrl = ""

    # 析构函数
    def __del__(self):
        # 这些析构函数会报错
        # if self._tmpFile.isOpen():
        #     self._tmpFile.close()
        # if self._configFile.isOpen():
        #     self._configFile.close()
        # if self._reply:
        #     self._reply.deleteLater()
        # if self._readAheadReply:
        #     self._readAheadReply.deleteLater()
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

    # 任务状态的改变，用于用户操作或者出现异常情况时设置
    # 通过UI通知用户，不弹窗
    def changeState(self,state):
        self.attributes.setState(state)

    # 这里判断目录是否存在，不存在则创建
    def isDirExist(self,fullPath):
        dir = QDir(fullPath)
        if dir.exists():
            return True
        else:
            return dir.mkpath(fullPath)

    # 开始下载，设置下载信息
    def _getSource(self):
        if len(self._jumpUrl) == 0:
            # 软件重启时并没有该跳转链接，需要重新获取
            return False
        request = QNetworkRequest()
        request.setRawHeader(str("Range").encode(),str("bytes=" + str(self.attributes.preProgress) + "-").encode())

        # 这里采用jumpUrl有两个原因，
        # 一个是在于每个url都会预先加载跳转链接，如果没有也会设置成url，有的话
        # jumpUrl就是指向正确的地址
        # 另一个原因是在多个文件下载时，这个是保存转换后的url
        request.setUrl(QUrl(self._jumpUrl))

        # if self._reply != None:
        #     self._reply.deleteLater()
        self._reply = self._manager.get(request)
        self._reply.downloadProgress.connect(self.writeFile)
        self._reply.finished.connect(self.downloadError)
        return True
    
    # 打开配置文件
    def _openConfig(self):
        config = self.attributes.fileName + '.tmp.cfg'
        self._configFile.setFileName(self.attributes.path + config)
        self._configFile.open(QFile.ReadWrite)

    # 打开临时文件，用于保存下载信息
    # 在这里重置文件大小
    def _openTemp(self):
        tempname = self.attributes.fileName + '.tmp'
        if self._tmpFile.isOpen():
            self._tmpFile.close()
        self._tmpFile.setFileName(self.attributes.path + tempname)
        self._tmpFile.open(QFile.Append)
        self._tmpFile.seek(self.attributes.preProgress)

    # 保存config
    def _saveConfig(self):
        if not self._configFile.isOpen():
            return False
        info = self.attributes.toJson()
        self._configFile.resize(0)
        self._configFile.seek(0)
        self._configFile.write(QJsonDocument(info).toJson())
        self._configFile.flush()
        return True

    # 读取config
    def _loadConfig(self):
        self._configFile.seek(0)
        cfg = self._configFile.readAll()
        if len(cfg) <= 0:
            return False
        j = QJsonDocument.fromJson(cfg).object()
        self.attributes.fromJson(j)
        return True

    
    # HTTPS类型的文件预下载，用于判断是否含有跳转或者其他情况
    # url:下载链接
    def _readAhead_https(self,url):
        self._jumpUrl = url
        request = QNetworkRequest()
        request.setUrl(QUrl(url))
        self._readAheadReply = self._manager.get(request)
        self._readAheadReply.downloadProgress.connect(self.onReadAhead_https)
        
    # 开始下载文件
    def startDownload(self,url,path,fileName,startNum,fileTotal,isPause):
        self.attributes.url = url
        self.attributes.path = path
        self.attributes.setStartNum(startNum)
        self.attributes.setTotalFile(fileTotal)

        # 这里区分批量下载和单个文件下载
        if fileTotal == 1:
            # 这里不需要重新计算文件名，因为在UI已经确认过了，这里如果文件名相同则会是
            # 继续下载，所以不存在会文件名相同
            self.attributes.fileName = fileName
            # 单个文件下载则任务名和文件名同名
            self.attributes.taskName = fileName
            # 打开配置文件并保存,这一步放在设置文件名后执行
            self._openConfig()
            if self._loadConfig():
                # 存在历史纪录
                pass
            else:
                self._saveConfig()
            self._openTemp()
            if not isPause:
                # 如果不是暂停，则下载
                self.changeState(DownloaderAttributes.States.downloading)
                self._readAhead_https(url)
            else:
                self.changeState(DownloaderAttributes.States.pause)
        else:
            self.attributes.path = path[:-2] + fileName
            # 生成目录
            self.isDirExist(self.attributes.path)
            # 重置文件名，用于生成配置文件而已
            self.attributes.fileName = self.attributes.checkFileName(fileName.split('/')[-2],self.attributes.path)
            # 多个文件下载则是文件夹的名字
            self.attributes.taskName = self.attributes.fileName
            # 打开配置文件并保存,这一步放在设置文件名后执行
            self._openConfig()
            if self._loadConfig():
                # 存在历史纪录
                pass
            else:
                self._saveConfig()
            if not isPause:
                # 如果不是暂停，则下载
                # 设置为另一个接口主要的意图在于，多个文件下载完都会调用一次该接口
                self._download_mult()
            
    # 下载单个文件
    # total用来表示文件大小，这样的优点在于预加载就可以显示文件大小的信息
    def _download_signal(self,total):
        if total > self.attributes.total:
            # 如果下载的大小大于记载的大小
            # 这个情况应该在新增任务时出现
            self.attributes.total = total
            self._tmpFile.resize(total)
        self._getSource()
        pass

    # 下载多个文件
    def _download_mult(self):
        name = self.attributes.url.split('/')[-1].split('.')
        newNum = str(int(name[0]) + self.attributes.finishFile).zfill(len(name[0]))
        newNum = newNum + "." + name[1]
        self.attributes.fileName = newNum
        url = self.attributes.url[:self.attributes.url.rfind('/') + 1] + newNum
        self._openTemp()
        print(url)
        self._readAhead_https(url)
        pass

    # 把数据写入文件的指令
    def _writeFile(self,data):
        self._tmpFile.seek(self.attributes.curProgress)
        b = self._tmpFile.writeData(data)
        return b
    
    # 槽函数
    # 用于任务终止时输出错误信息，下载完成也会触发
    @pyqtSlot()
    def downloadError(self):
        print("IOError",self._reply.errorString())
        print("NetworkError",self._reply.error())
        logging.info("IOError" + self._reply.errorString())

    # 槽函数
    # 把下载的内容写入文件
    # receive:已接收的字节数
    # total:文件总大小
    @pyqtSlot("qint64","qint64")
    def writeFile(self,receive,total):
        print("receive",receive)
        print("total",total)
        
        # 这里是刚开始下载的时候，total默认是0,设置下载的文件大小
        if self.attributes.total != total:
            self.attributes.total = total + self.attributes.preProgress
            if self._tmpFile.isOpen():
                if self._tmpFile.size() < total:
                   self._tmpFile.resize(total)
            else:
                self.changeState(DownloaderAttributes.States.fileOpenError)
                return
        
        # 这里是暂停续传部分，因为暂停发生后，reply.abort()
        # 关闭下载通道，但是还是会触发这个槽函数
        if self.attributes._state == DownloaderAttributes.States.pause:
            # 暂停触发，不处理后面接受到的字节数
            if self._reply.isRunning():
                # 如果reply还没有关闭则关闭下载通道
                # 这个在软件重开续传和预读头文件的时候预防下载通道还没关闭的情况
                self._reply.abort()
            return
        elif not self._reply.isOpen():
            # 下载完成触发
            if self.attributes.curProgress == self.attributes.total:
                pass
            else:
                # 如果不是因为暂停而关闭reply的通道的情况则需要通报用户下载失败
                self.changeState(DownloaderAttributes.States.networkError)
                return
        else:
            #  正常情况
            data = self._reply.readAll()
            if len(data) == 0:
                #  没有数据读取
                if self._reply.error() == QNetworkReply.NoError:
                    self.success()
                else:
                    self.changeState(DownloaderAttributes.States.networkError)
                return
            if self._tmpFile.writeData(data) <= 0:
                self.changeState(DownloaderAttributes.States.fileWriteError)
                return
            
        # 获取时间戳，因为我不知道qml如何获取，然后发射信号给qml更新界面
        self._tmpFile.flush()
        self.attributes.curTime = int(time.time())
        self.attributes.curProgress = receive + self.attributes.preProgress
        self._saveConfig()
        # 下载完成的处理，不使用finish是因为那个信号啥都会触发
        if self.attributes.curProgress == self.attributes.total:
            self.success()

    # 槽函数
    # 暂停/继续下载
    @pyqtSlot(bool)
    def pauseDown(self):
        if self.attributes._state == DownloaderAttributes.States.downloading:
            # 正在下载，应该处理暂停
            self.changeState(DownloaderAttributes.States.pause)
            if self._reply != None:
                self._reply.abort()
            self.attributes.preProgress = self.attributes.curProgress
        else:
            self.changeState(DownloaderAttributes.States.downloading)
            self._readAhead_https(self.attributes.url)

    # 槽函数
    # 停止下载，所有标志位重置为FALSE，关闭下载通道，关闭文件.
    @pyqtSlot()
    def stopDown(self):
        if self._reply != None:
            self._reply.abort()
            self._reply.deleteLater()

    # 槽函数
    # 下载成功，设置标志位finish为true，然后停止下载.
    @pyqtSlot()
    def success(self):
        self.attributes.completedOne()
        name = self.attributes.checkFileName(self.attributes.fileName,self.attributes.path)
        self._tmpFile.rename(self.attributes.path + name)
        self._tmpFile.close()
        # 下载完所有文件，同样适用于下载单个文件
        if self.attributes.finishFile == self.attributes.totalFile:
            pass
        else:
            # 这个情况只有下载多个文件的时候才会出现
            self._saveConfig()
            self._download_mult()
            return
        self._configFile.remove()
        self.changeState(DownloaderAttributes.States.finish)
        self.stopDown()

    # 槽函数
    # 预读开始的一部分数据，判断是否含有跳转，如果含有继续预加载
    # 否则开始正式下载
    @pyqtSlot("qint64","qint64")
    def onReadAhead_https(self,receive,total):
        u = self._readAheadReply.attribute(QNetworkRequest.RedirectionTargetAttribute)
        msg = self._readAheadReply.readAll()
        self._readAheadReply.downloadProgress.disconnect(self.onReadAhead_https)
        self._readAheadReply.deleteLater()
        self._readAheadReply.abort()
        
        print(u)
        if u != None:
            self._readAhead_https(u.toString())
        else:
            if total <= 0 :
                 #-1有可能是下载错误
                self._readAhead_https(self.attributes.url)
            elif receive == total:
                # 预加载时下载完成的情况
                self._tmpFile.writeData(msg)
                self._tmpFile.flush()
                self.success()
                pass
            else:
                self._download_signal(total)
        return