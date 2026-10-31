
import base64
import json
from pathlib import Path
import re
import uuid
from PyQt5.Qt import QApplication, QObject, QDir, QUrl, QFile
from PyQt5.Qt import pyqtSlot, pyqtSignal, pyqtProperty
from PyQt5.QtNetwork import QNetworkProxy
from Core.Enum import UrlType
from Core.FFmpegManager import FFmpegManager
from Core.VideoExtractor import VideoExtractor
from Core.VideoBrowser import published_date
from Network.M3u8Downloader import cleanup_workdir

class SettingsManager(QObject):
    '''
    设置管理器
    用于管理设置相关的信息

    '''
    
    haveNewUrl = pyqtSignal(str, arguments = [ "url" ])

     # 初始化函数
    def __init__(self,parent = None):
        super(SettingsManager,self).__init__(parent)

        self._ffmpeg = FFmpegManager(self)
        self._video = VideoExtractor(self._ffmpeg, self)
        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self.boardDataChanged)

    @pyqtProperty(QObject, constant=True)
    def ffmpeg(self):
        return self._ffmpeg

    @pyqtProperty(QObject, constant=True)
    def video(self):
        return self._video

    @staticmethod
    def cleanVideoName(name):
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip().rstrip(' .')
        if not name:
            name = 'video'
        stem = name.split('.', 1)[0].strip(' .').upper()
        if stem in {'CON', 'PRN', 'AUX', 'NUL'} or re.fullmatch(r'(COM|LPT)[1-9]', stem):
            name = '_' + name
        if len(name) > 180:
            suffix = Path(name).suffix
            suffix = suffix if len(suffix) <= 12 else ''
            name = name[:180-len(suffix)].rstrip(' .') + suffix
        return name

    @pyqtSlot(str, str, result=str)
    def videoFileName(self, url, kind):
        name = QUrl(url).fileName() or 'video'
        if kind == 'm3u8':
            name = (name.rsplit('.', 1)[0] if '.' in name else name) or 'video'
            name += '.mkv'
        elif not Path(name).suffix:
            name += '.mp4'
        return self.cleanVideoName(name)

    @pyqtSlot(str, str, str, result=str)
    def titleFileName(self, title, date, current_name):
        extension = Path(current_name).suffix or '.mkv'
        title = title.strip()
        if not title:
            return current_name
        dates = re.findall(r'\d{4}\s*[-/.年]\s*\d{1,2}\s*[-/.月]\s*\d{1,2}',title)
        if date and date not in [published_date(value) for value in dates]:
            title = '[' + date + '] ' + title
        if title.lower().endswith(extension.lower()):
            title = title[:-len(extension)]
        return self.cleanVideoName(title) + extension

    def _reserveVideoName(self, name, path, occupied, options=None):
        options = options or {}
        parent = Path(path)
        stem, suffix = Path(name).stem, Path(name).suffix
        candidate = name
        index = 1
        while True:
            work = parent / (candidate + '.tmp')
            resume = False
            if options.get('id') and options.get('kind') in ('m3u8', 'mp4'):
                try:
                    config = work / (candidate + '.tmp.cfg') if options['kind'] == 'm3u8' else parent / (candidate + '.tmp.cfg')
                    data = json.loads(config.read_text(encoding='utf-8'))
                    saved = data.get('options', {}) if options['kind'] == 'm3u8' else data.get('taskOptions', {})
                    resume = saved.get('id') == options['id'] and saved.get('kind') == options['kind']
                except (OSError, ValueError):
                    pass
            temporary = not resume and (work.exists() or (parent / (candidate + '.tmp.cfg')).exists())
            if candidate.lower() not in occupied and not (parent / candidate).exists() and not temporary:
                return candidate
            candidate = stem + '(' + str(index) + ')' + suffix
            index += 1

    @pyqtSlot('QVariantList', str, 'QVariantList', result='QVariantList')
    def prepareVideoTasks(self, tasks, path, occupied):
        try:
            parent = Path(path).expanduser().resolve()
            if not path.strip() or not parent.is_dir():
                raise ValueError('请选择存在的下载目录')
            used = {str(value).lower() for value in occupied}
            result = []
            for task in tasks:
                options = dict(task.get('options') or {})
                kind = options.get('kind')
                if kind not in ('mp4', 'm3u8'):
                    raise ValueError('暂不支持该资源类型')
                if kind == 'm3u8' and not self._ffmpeg.ready:
                    raise ValueError('请先在设置中检测 FFmpeg')
                url = str(task.get('url', '')).strip()
                parsed = QUrl(url)
                if not parsed.isValid() or not parsed.host() or parsed.scheme().lower() not in ('http', 'https'):
                    raise ValueError('视频地址无效')
                name = str(task.get('name', '')).strip()
                if not name:
                    raise ValueError('请填写视频文件名')
                name = self.cleanVideoName(name)
                if not Path(name).suffix:
                    name += '.mkv' if kind == 'm3u8' else '.mp4'
                if kind == 'm3u8' and Path(name).suffix.lower() not in ('.mkv', '.mp4'):
                    raise ValueError('m3u8 输出文件名应以 .mkv 或 .mp4 结尾')
                name = self._reserveVideoName(name, str(parent), used)
                used.add(name.lower())
                options.update(id=str(uuid.uuid4()), url=url)
                options.setdefault('headerUrl', url)
                result.append({'url': url, 'name': name, 'path': parent.as_posix() + '/',
                               'files': 1, 'options': options})
            self._video.setError('')
            return result
        except (OSError, ValueError) as error:
            self._video.setError(str(error))
            return []

    @pyqtSlot(str, str, 'QVariantMap', 'QVariantList', result=str)
    def reserveVideoName(self, name, path, options, occupied):
        return self._reserveVideoName(name, path, {str(value).lower() for value in occupied}, options)

    # 判断url是哪种下载链接
    # 为了qml能够使用返回值，改为返回int
    @pyqtSlot(str,result = int)
    def getUrlType(self,url):
        url = url.strip()
        if len(url) <= 8:
            return UrlType.Unknown.value
        if url[:8] == 'magnet:?':
            return UrlType.Magnet.value
        text = url.split('://')
        # 转小写
        text[0] = text[0].lower()
        if text[0] == "http" or text[0] == "https":
            if QUrl(url).path().lower().endswith('.m3u8'):
                return UrlType.M3u8.value
            return  UrlType.Https.value
        else:
            # 其他类型url
            __url = self.getBaseUrl(url)
            if __url == url:
                return UrlType.Unknown.value 
            else:
                return self.getUrlType(__url)

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

        type = self.getUrlType(mimeData.text())
        if type == UrlType.Unknown.value:
            return
        else:
            self.haveNewUrl.emit(mimeData.text())

    # 判断文件是否在此目录
    # path:文件所在路径
    # filename:文件名(不带路径，带后缀名)
    def isFileExist(self,path,filename):
        dir = QDir(path)
        return filename in dir.entryList()

    # 命名下载文件，重名则加(数字),下载未完成的临时文件名也会判断是否重名,统一三个文件
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

    # 批量下载的时候，获取文件夹的名字
    @pyqtSlot(str, result = str)
    def getFolderName(self,url):
        u = QUrl(url)
        
        return u.path()[:len(u.path()) - len(u.fileName())]

    # 设置代理服务器
    @pyqtSlot(bool,str,int,str,str)
    def setProxy(self,enable,hostname,port,username,password):
        proxy =  QNetworkProxy()
        if enable:
            proxy.setType(QNetworkProxy.HttpProxy)
            print("启动代理")
            print("主机名",hostname)
            print("端口",port)
            print("用户名",username)
            print("密码",password)
        else:
            proxy.setType(QNetworkProxy.NoProxy)
            print("取消代理")
        proxy.setHostName(hostname)
        proxy.setPort(port)
        proxy.setUser(username)
        proxy.setPassword(password)
        QNetworkProxy.setApplicationProxy(proxy)

    # 永久删除文件，删除临时文件和配置文件，不删除已下载完成的文件
    @pyqtSlot(str,str)
    @pyqtSlot(str,str,'QVariantMap')
    def deleteFile(self,path,name,options=None):
        if options and options.get('kind') == 'm3u8':
            cleanup_workdir(path, name, options.get('id', ''))
            return
        file = QFile(path + name + ".tmp")
        print(file.fileName())
        if file.exists():
            print(file.remove())
        file.setFileName(path + name + ".tmp.cfg")
        if file.exists():
            print(file.remove())

    # 批量清理临时文件和续传配置。
    @pyqtSlot("QVariantList")
    def deleteFiles(self,tasks):
        for task in tasks:
            self.deleteFile(task["path"],task["name"],task.get("options", {}))

    def _getThunderUrl(self,url):
        src = url.split('/')[-1]
        src = base64.b64decode(src)[2:-2]
        src = src.decode('utf-8')
        print(src)
        # 这里有时候会编码失败而程序奔溃
        return src
        
    @pyqtSlot(str,result = str)
    def getBaseUrl(self,url):
        # 现在只需要判断迅雷链接就可以了
        if len(url) < 10 or url[:7].lower() != 'thunder':
            return url
        return self._getThunderUrl(url)
