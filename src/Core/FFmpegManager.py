import os
from pathlib import Path

from PyQt5.QtCore import QObject, QProcess, QTimer, QUrl
from PyQt5.QtCore import pyqtProperty, pyqtSignal, pyqtSlot


class FFmpegManager(QObject):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._directory = ''
        self._executable = ''
        self._status = 'Not configured'
        self._process = None
        self._candidates = []

    @pyqtProperty(str, notify=changed)
    def directory(self):
        return self._directory

    @pyqtProperty(str, notify=changed)
    def executable(self):
        return self._executable

    @pyqtProperty(str, notify=changed)
    def status(self):
        return self._status

    @pyqtProperty(bool, notify=changed)
    def ready(self):
        return bool(self._executable)

    @pyqtProperty(bool, notify=changed)
    def checking(self):
        return self._process is not None

    @pyqtSlot(QUrl, result=str)
    def localDirectory(self, url):
        path = url.toLocalFile()
        return str(Path(path)) if path else ''

    @pyqtSlot()
    def invalidate(self):
        process = self._process
        self._process = None
        self._executable = ''
        self._status = 'Not checked'
        self._candidates = []
        if process is not None:
            process.kill()
        self.changed.emit()

    @pyqtSlot(str)
    def check(self, directory):
        directory = directory.strip().strip('"')
        if self.checking and directory == self._directory:
            return
        self.invalidate()
        url = QUrl(directory)
        if url.isLocalFile():
            directory = url.toLocalFile()
        try:
            folder = Path(directory).expanduser().resolve() if directory else None
        except (OSError, ValueError, RuntimeError):
            folder = None
        self._directory = str(folder) if folder is not None else directory
        if not directory:
            self._status = 'Not configured'
        elif folder is None or not folder.is_dir():
            self._status = 'Directory not found'
        else:
            name = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
            pattern = 'ffmpeg*.exe' if os.name == 'nt' else 'ffmpeg*'
            candidates = [path for directory in [folder, folder / 'bin']
                          for path in directory.glob(pattern) if path.is_file()]
            candidates.sort(key=lambda path: (path.name.lower() != name,
                                              path.parent != folder, path.name.lower()))
            self._candidates = [str(path.resolve()) for path in candidates]
            if self._candidates:
                self._startCheck(self._candidates.pop(0))
                return
            self._status = 'FFmpeg executable not found'
        self.changed.emit()

    def _startCheck(self, executable):
        process = QProcess(self)
        self._process = process
        self._status = 'Checking...'
        process.setProcessChannelMode(QProcess.MergedChannels)
        timeout = QTimer(process)
        timeout.setSingleShot(True)
        timeout.timeout.connect(lambda: self._finishCheck(process, 'FFmpeg check timed out'))
        process.finished.connect(timeout.stop)
        process.errorOccurred.connect(timeout.stop)
        process.finished.connect(lambda code, status: self._checked(process, executable, code, status))
        process.errorOccurred.connect(lambda error: self._finishCheck(process, 'Could not start FFmpeg'))
        self.changed.emit()
        timeout.start(5000)
        process.start(executable, ['-version'])
        if process is self._process:
            process.closeWriteChannel()

    def _checked(self, process, executable, code, status):
        if process is not self._process:
            process.deleteLater()
            return
        output = bytes(process.readAllStandardOutput()).decode('utf-8', errors='replace')
        valid = code == 0 and status == QProcess.NormalExit and any(
            line.startswith('ffmpeg version ') for line in output.splitlines())
        self._finishCheck(process, 'FFmpeg detected' if valid else 'FFmpeg check failed',
                          executable if valid else '')

    def _finishCheck(self, process, status, executable=''):
        if process is self._process:
            self._process = None
            if process.state() != QProcess.NotRunning:
                process.kill()
            if not executable and self._candidates:
                self._startCheck(self._candidates.pop(0))
            else:
                self._candidates = []
                self._executable = executable
                self._status = status
                self.changed.emit()
        process.deleteLater()

    def createProcess(self, parent=None):
        """Create a task process using the successfully detected executable."""
        if not self.ready or not Path(self._executable).is_file():
            raise RuntimeError('Configure and detect FFmpeg before starting a task.')
        process = QProcess(parent)
        process.setProgram(self._executable)
        return process
