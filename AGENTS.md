# AGENTS.md

Windows 桌面下载器，使用 Python、PyQt5 和 QML。从仓库根目录运行 `python.exe .\src\main.pyw`。

## 项目结构

- `src/main.pyw`：程序入口，注册 Python 类型并加载 QML。
- `src/Network/`：下载管理、网络请求、进度和续传。
- `src/Core/`：设置、URL 解析、文件命名及解压。
- `ui/`：QML 页面和公共控件。
- `tools/`：独立验证工具，保留 `tools/probe_video.py` 用于媒体识别和预览测试。
- `docs/`：功能设计和实施方案；视频下载见 `docs/video-download-plan.md`。
- `sdk/`：7-Zip 工具。
- `Downloader.pro`、`src/main.cpp`、`qml.qrc`：遗留 Qt/C++ 工程。

## 编码约定

- 默认使用中文沟通；新增界面文案使用英文。
- 扩展功能前先查看项目内的同类实现，遵循现有代码风格、目录职责和架构，优先复用已有组件与机制；不要为局部需求另起一套实现。
- Python 使用 4 空格缩进，其余风格跟随现有代码；避免无关格式化。
- 修改 Python/QML 接口时，保持属性、信号和槽函数一致。
- GUI 主线程不执行阻塞网络请求或耗时操作。
- 保持 Windows 兼容，保留原文件编码和换行格式。
- 仅修改任务相关内容，保留用户已有的未提交修改。
- 不访问父目录中的 `../run/` 和 `../finish/`。
