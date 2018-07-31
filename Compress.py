
import logging
from PyQt5.Qt import Qt,QObject
from PyQt5.Qt import QProcess,QThread,QDir,QByteArray
from PyQt5.Qt import pyqtSlot,pyqtSignal,pyqtProperty


class Compress(QObject):
    startRunning = pyqtSignal(str,str,str)

    def __init__(self,parent = None):
        super(Compress,self).__init__(parent)
        self.createList()
        
        self._process = QProcess(self)
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.start()

        self._fileName = ""
        self._outPath = ""

        self.startRunning.connect(self.startCompress)
        self._process.readyReadStandardOutput.connect(self.readMsg)
        self._process.readyReadStandardError.connect(self.readError)
        self._process.finished.connect(self.finished)
            
    def __del__(self):
        if self._thread.isRunning:
            self._thread.exit()
            self._thread.wait()
        if self._process.isOpen():
            self._process.close()
            self._process.waitForFinished()
        del self._thread
        del self._process
        self.deleteLater()

    #生成压缩包类型list
    def createList(self):
        self._typeList = []
        self._typeList.append("rar")
        self._typeList.append("7z")
        self._typeList.append("zip")
        self._typeList.append("tgz")

        self._pwList = []
        self._pwIndex = 0

    #生成密码列表
    def createPWList(self,pw):
        self._pwList = pw.split(";")
        self._pwIndex = 0
        print("密码集",self._pwList)

    #文件是否存在
    def isFileExist(self,path,filename):
        dir = QDir(path)
        return filename in dir.entryList()

    #文件是否是压缩包
    def isCompress(self,name):
        _list = name.split('.')
        if len(_list) < 2:
            return False
        _type = _list[-1].lower()
        return _type in self._typeList

    @pyqtSlot(str,str,str)
    #槽里面开始运行7z，因为是多线程
    def startCompress(self,filename,outputPath,password):
        cur = QDir.current()
        if not self.isFileExist(cur.path(),"7z.exe"):
            cur.cdUp()
        currPath = cur.path() + "\\7z.exe"
        if not len(outputPath):
            outputPath = "./"
        args = list( [ "x" , "-y" ] )
        args.append("-o" + outputPath)
        #密码判断
        if len(password) != 0:
            args.append("-p" + password)
            self._pwIndex += 1
            print("使用密码'" + password + "'解压")
        args.append(filename)
        self._process.start(currPath,args)
        print(self._process.arguments())
    
    @pyqtSlot(str,str,str)
    #外部接口
    def compressFile(self,filename,outputPath,pwList):
        self.createPWList(pwList)
        self._fileName = filename
        self._outPath = outputPath
        if self.isCompress(filename):
            #第一次解压默认不加密码
            self.startRunning.emit(self._fileName,self._outPath,"")

    @pyqtSlot()
    def readMsg(self):
        s = str(self._process.readAllStandardOutput())
        logging.info("readMsg:" + s)
        print("readMsg:" + s)
        if "Enter password" in s:
            self._process.kill()

    @pyqtSlot()
    def readError(self):
        s = str(self._process.readAllStandardError())
        logging.info("readError:" + s)
        print("readError:" + s)
    
    @pyqtSlot(int,"QProcess::ExitStatus")
    def finished(self,code,status):
        print("解压结束,exitCode:" + str(code))
        logging.info("解压结束,exitCode:" + str(code))

        #解压失败，尝试使用密码遍历解压
        if code != 0:
            if len(self._pwList) != 0 and len(self._pwList) > self._pwIndex:
                self.startRunning.emit(self._fileName,self._outPath,self._pwList[self._pwIndex])