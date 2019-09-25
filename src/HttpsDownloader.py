
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

    # 析构函数
    def __del__(self):
        # 这些析构函数会报错
        # if self._tmpFile.isOpen():
        #     self._tmpFile.close()
        # if self._configFile.isOpen():
        #     self._configFile.close()
        # if self._reply:
        #     self._reply.deleteLater()
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
        
    # 开始下载文件
    def startDownload(self,isPause):
        # 这里区分批量下载和单个文件下载
        if self.attributes.totalFile == 1:
            # 这里不需要重新计算文件名，因为在UI已经确认过了，这里如果文件名相同则会是
            # 继续下载，所以不存在会文件名相同
            # 单个文件下载则任务名和文件名同名
            self.attributes.taskName = self.attributes.fileName
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
                self._download_signal(self.attributes.url)
            else:
                self.changeState(DownloaderAttributes.States.pause)
        else:
            self.attributes.path = self.attributes.path[:-1] + self.attributes.fileName
            # 生成目录
            self.isDirExist(self.attributes.path)
            # 重置文件名，用于生成配置文件而已
            if len(self.attributes.fileName.split('/')) >= 2:
                self.attributes.fileName = self.attributes.checkFileName(self.attributes.fileName.split('/')[-2],self.attributes.path)
            else:
                self.attributes.fileName = self.attributes.checkFileName(self.attributes.fileName,self.attributes.path)
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
            else:
                self.changeState(DownloaderAttributes.States.pause)
            
    # 下载单个文件
    # total用来表示文件大小，这样的优点在于预加载就可以显示文件大小的信息
    def _download_signal(self,url):
        
        request = QNetworkRequest()        
        request.setRawHeader(str("Range").encode(),str("bytes=" + str(self.attributes.preProgress) + "-").encode())
        # 设置自动重定向,之前自己实现的链接跳转就可以去掉了
        request.setAttribute(QNetworkRequest.FollowRedirectsAttribute,True)
        request.setUrl(QUrl(url))

        self.changeState(DownloaderAttributes.States.downloading)
        self._reply = self._manager.get(request)
        self._reply.downloadProgress.connect(self.writeFile)
        self._reply.finished.connect(self.downloadError)
        return True

    # 下载多个文件
    def _download_mult(self):
        # 任务开始前先重置下载进度
        name = self.attributes.url.split('/')[-1].split('.')
        newNum = str(int(name[0]) + self.attributes.finishFile).zfill(len(name[0]))
        newNum = newNum + "." + name[1]
        self.attributes.fileName = newNum
        url = self.attributes.url[:self.attributes.url.rfind('/') + 1] + newNum
        self._openTemp()
        print(url)
        self._download_signal(url)
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
        # print("receive",receive)
        # print("total",total)
        # print(self._reply.error())

        if total <= 0 :
            # -1有可能是下载错误
            if receive <= 0:
                self.changeState(DownloaderAttributes.States.networkError)
                # 这里不打算中断网络链接，经过观察再决定这里是否中断
                return
            else:
                # 这种情况是total返回-1，但是实际上是有下载的
                self.changeState(DownloaderAttributes.States.totalLessThanZero)

        # 这里是刚开始下载的时候，total默认是0,设置下载的文件大小
        if self.attributes.total != total:
            self.attributes.total = total + self.attributes.preProgress
            if self._tmpFile.isOpen():
                if self._tmpFile.size() < total:
                   self._tmpFile.resize(total)
            else:
                self.changeState(DownloaderAttributes.States.fileOpenError)
                return
        
        # 这里是暂停续传部分，因为更改了暂停机制，在暂停前取消信号连接，
        # 所以这里基本不存在触发的情况
        if self.attributes._state == DownloaderAttributes.States.pause:
            # 暂停触发，不处理后面接受到的字节数
            if self._reply.isRunning():
                # 如果reply还没有关闭则关闭下载通道
                # 这个在软件重开续传和预读头文件的时候预防下载通道还没关闭的情况
                self._reply.downloadProgress.disconnect(self.writeFile)
                self._reply.abort()
            return
        elif not self._reply.isOpen():
            if self.attributes.curProgress == self.attributes.total:
                # 其实这里已经排除abort触发的情况因为在abort之前已经断开信号连接
                # 这里的条件判断以及输出是用于日志输出
                print("abort 触发")
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
            if self._reply != None and self._reply.isRunning():
                self._reply.downloadProgress.disconnect(self.writeFile)
                self._reply.abort()
            self.attributes.preProgress = self.attributes.curProgress
        else:
            self.changeState(DownloaderAttributes.States.downloading)
            if self.attributes.totalFile > 1:
                self._download_mult()
            else:
                self._download_signal(self.attributes.url)

    # 槽函数
    # 下载成功，设置标志位finish为true，然后停止下载.
    @pyqtSlot()
    def success(self):
        self.attributes.completedOne()
        # 虽然下载完成，但是还是需要关闭通道
        # 这里解决了只能下载第一个文件的情况，也解决了下载完成所有任务后，多下载两个文件
        # 貌似是下载文件时多次触发success，所以要断开信号和关闭下载通道
        self._reply.downloadProgress.disconnect(self.writeFile)
        self._reply.abort()
        name = self.attributes.checkFileName(self.attributes.fileName,self.attributes.path)
        self._tmpFile.rename(self.attributes.path + name)
        self._tmpFile.close()
        # 下载完所有文件，同样适用于下载单个文件
        if self.attributes.finishFile == self.attributes.totalFile:
            pass
        else:
            # 这个情况只有下载多个文件的时候才会出现
            # 重置多个文件下载时的参数
            self.attributes.downloadParamReset()
            self._saveConfig()
            self._download_mult()
            return
        self._configFile.remove()
        self.changeState(DownloaderAttributes.States.finish)
    
    # 删除这次任务，当然，这里只是关闭文件而已
    # 正真删除操作在setting类
    # 因为只有正在下载的任务有这个类
    # 重构后，可能在这里实现文件的删除操作
    def deleteFile(self):
        self._tmpFile.close()
        self._configFile.close()