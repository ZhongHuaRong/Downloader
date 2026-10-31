
import time
import logging
import os
import json
import re
from PyQt5.Qt import QApplication, Qt, QObject
from PyQt5.Qt import pyqtSlot, pyqtSignal, pyqtProperty
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.Qt import QThread, QUrl, QFile, QDir, QJsonDocument
from Network.DownloaderAttributes import DownloaderAttributes
from Network.M3u8Playlist import request_headers

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
        self._tmpFile.open(QFile.ReadWrite)
        if self._tmpFile.size() < self.attributes.preProgress:
            self.attributes.preProgress = 0
            self.attributes.curProgress = 0
        self._tmpFile.resize(self.attributes.preProgress)
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
        if not j or "filename" not in j:
            return False
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
            
    # 单文件和编号批量继续使用同一下载通道；视频只补充请求上下文。
    def _download_signal(self,url):
        if not self._tmpFile.isOpen() or not self._configFile.isOpen():
            self.changeState(DownloaderAttributes.States.fileOpenError)
            return False
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(QNetworkRequest.FollowRedirectsAttribute,True)
        self._resumeStart = self.attributes.preProgress
        if self._resumeStart:
            request.setRawHeader(b'Range', ('bytes=' + str(self._resumeStart) + '-').encode())
        for name, value in request_headers(self.attributes.taskOptions, url).items():
            if '\r' in value or '\n' in value:
                self.attributes.message = '请求头包含无效字符'
                self.changeState(DownloaderAttributes.States.downloadError)
                return False
            request.setRawHeader(name.encode('ascii'),value.encode('utf-8'))
        self._headersChecked = False
        self.attributes.message = ''
        self.attributes.curProgress = self._resumeStart
        reply = self._manager.get(request)
        self._reply = reply
        reply.readyRead.connect(self._readReply)
        reply.downloadProgress.connect(self.writeFile)
        reply.finished.connect(lambda: self.downloadError(reply))
        self.changeState(DownloaderAttributes.States.downloading)
        return True

    def _acceptReply(self,reply):
        if self._headersChecked:
            return True
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0
        if not status or 300 <= status < 400:
            return False
        if not 200 <= status < 300:
            self._failed('下载失败，HTTP ' + str(status))
            return False
        if status == 206:
            value = bytes(reply.rawHeader(b'Content-Range')).decode('ascii', errors='replace')
            match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+|\*)',value)
            if not match or int(match[1]) != self._resumeStart:
                self._failed('服务器返回的续传范围不正确')
                return False
            self.attributes.total = int(match[3]) if match[3] != '*' else 0
        else:
            # 不支持 Range 的服务器会重发整个文件，先清空旧半片再重新写入。
            self._resumeStart = 0
            self.attributes.preProgress = 0
            self.attributes.curProgress = 0
            self._tmpFile.resize(0)
            self._tmpFile.seek(0)
            length = bytes(reply.rawHeader(b'Content-Length')).decode('ascii', errors='replace')
            self.attributes.total = int(length) if length.isdigit() else 0
        self._headersChecked = True
        return True

    def _readReply(self):
        reply = self._reply
        if reply is None or not self._acceptReply(reply):
            return
        data = reply.readAll()
        if not data:
            return
        self._tmpFile.seek(self.attributes.curProgress)
        written = self._tmpFile.write(data)
        if written != len(data):
            self._failed('无法写入下载文件',DownloaderAttributes.States.fileWriteError)
            return
        self._tmpFile.flush()
        self.attributes.curProgress += written
        self.attributes.curTime = int(time.time())
        self._saveConfig()

    @pyqtSlot("qint64","qint64")
    def writeFile(self,receive,total):
        if self._reply is not None and self._acceptReply(self._reply) and total > 0:
            self.attributes.total = total + self._resumeStart

    def downloadError(self,reply):
        if reply is not self._reply:
            reply.deleteLater()
            return
        self._readReply()
        if reply is not self._reply:
            return
        if reply.error() != QNetworkReply.NoError or not self._headersChecked:
            self._failed('网络下载失败：' + reply.errorString())
            return
        self._reply = None
        reply.deleteLater()
        if self.attributes.total and self.attributes.curProgress != self.attributes.total:
            self._failed('下载文件不完整')
            return
        self.attributes.total = self.attributes.curProgress
        self.success()

    def _stopReply(self):
        reply, self._reply = self._reply, None
        if reply is not None:
            try:
                reply.readyRead.disconnect(self._readReply)
                reply.downloadProgress.disconnect(self.writeFile)
            except TypeError:
                pass
            reply.abort()
            reply.deleteLater()

    def _failed(self,message,state=None):
        self._stopReply()
        self.attributes.preProgress = self.attributes.curProgress
        self.attributes.message = message
        self.changeState(state or DownloaderAttributes.States.networkError)
        self._saveConfig()

    # 下载多个文件，保留原有漫画目录和连续编号规则。
    def _download_mult(self):
        url = QUrl(self.attributes.url)
        stem, separator, suffix = url.fileName().rpartition('.')
        if not separator or not stem.isdigit():
            self._failed('批量下载地址的文件名需要使用连续数字编号')
            return
        name = str(int(stem) + self.attributes.finishFile).zfill(len(stem)) + '.' + suffix
        self.attributes.fileName = name
        url.setPath(url.path()[:url.path().rfind('/') + 1] + name)
        self._openTemp()
        self._download_signal(url.toString())

    @pyqtSlot()
    def pauseDown(self):
        if self.attributes._state == DownloaderAttributes.States.downloading:
            self._stopReply()
            self.attributes.preProgress = self.attributes.curProgress
            self.changeState(DownloaderAttributes.States.pause)
            self._saveConfig()
        elif self.attributes.totalFile > 1:
            self._download_mult()
        else:
            self._download_signal(self.attributes.url)

    @pyqtSlot()
    def success(self):
        name = self.attributes.checkFileName(self.attributes.fileName,self.attributes.path)
        self._tmpFile.resize(self.attributes.curProgress)
        self._tmpFile.close()
        if not self._tmpFile.rename(self.attributes.path + name):
            self.attributes.message = '无法保存下载文件'
            self.changeState(DownloaderAttributes.States.fileWriteError)
            return
        self.attributes.completedOne()
        if self.attributes.totalFile == 1:
            self.attributes.fileName = name
            self.attributes.taskName = name
        if self.attributes.finishFile < self.attributes.totalFile:
            self.attributes.downloadParamReset()
            self._saveConfig()
            self._download_mult()
            return
        self._configFile.remove()
        self.changeState(DownloaderAttributes.States.finish)

    # 删除任务前停止下载并关闭文件，实际文件清理由设置管理器处理。
    def deleteFile(self):
        self._stopReply()
        if self._configFile.isOpen():
            self.attributes.preProgress = self.attributes.curProgress
            self._saveConfig()
        self._tmpFile.close()
        self._configFile.close()
