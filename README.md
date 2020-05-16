# YYGame说明文档
YYGame的项目文档，详细说明各个模块的功能，每个模块之间的联系，配合流程图展示模块的运行过程和一些需要注意的地方.<br>
现在文档只说明了Login的流程，后面会逐步完善(:sweat_smile:项目结构有点庞大，一时半会看不完:sweat:)

## 项目结构
* Modules
    * Libs
        * BundleEvent
        * DataReport
        * DataReportMT
        * HttpReq
        * IPCLib
        * UpdateCommonLib
        * Zip
    * CrashReport
    * DmMain
    * GPBase
    * IPC
    * MuteHock
    * SocketIPC
    * UpdateClient
* outplugins
    * Render
        * GPRender
        * GPRenderProxy
    * GPCamera
    * GPLog
* Plugins
    * [GPLatform](#GPLatform)
* [GPluginMgr](#GPluginMgr)
* [Launcher](#Launcher)
* MountPlayer
* MouseClick
* PWRender
* yygame_sdk

## 模块说明

### GPlatform 
#### 项目说明
该模块由GPluginMgr调用  
该项目入口是GPMain，由GPluginMgr调用，先调用InitPrepare做初始化操作，然后调用InitMain，初始化窗口等  
详细步骤请看项目结构和流程

#### 项目结构
* Core  
    * GPMainimpl  
      继承DMRefNum，窗口初始化和创建的操作都在该类实现  
* Modules  
   资源加载相关  
* UI       
    UI相关的类，各种UI逻辑操作都在这里实现(太多了，就不一一说明了)  
* GPMain   
    用于各种初始化操作

#### 流程图  
* 以后补充

#### 流程说明  
主要的操作都在InitPrepare和InitMain，由GPluginMgr调用，InitPrepare和InitMain具体操作在GPMainimpl文件实现。  

* 主线程  
InitPrepare会初始化日志模块，Dump上报，加载Flash和解析启动参数。如果运行大厅个数达到上限，则会自己退出。如果没有uid参数则启动launcher，自己退出,launcher再拉起yygame.exe,再通过yygame.exe拉起自己（这里会不会造成死循环？需要深入了解GPluginMgr和Launcher），随后初始化DataReport,Oem id写入注册表，初始化UpdateController，初始化loginResultHandler  
InitMain会调用InitMainUI初始化UI，加载GPRes.zip并创建主窗口GPMainWnd，然后发送WM_INITDIALOG消息到GPMainWnd。随后调用RunMainUI重置上次GPMainWnd退出时的大小和位置，创建并初始化系统托盘。然后调用RunWork初始化各种组件(还没研究)。初始化鼠标连点器。调用RunMainUIWork发送事件GSEVT_POP_LOGINWND(该事件关联slotPopLoginWnd），这个事件是基于EventGlobal的，和Win32消息不一样
进入DM消息循环

* 进入消息循环后的流程  
进入GPMainWnd的初始化过程(OnInitDialog),调用InitBind绑定各种事件，然后创建窗口。由GSEVT_POP_LOGINWND事件调用slotPopLoginWnd。  
slotPopLoginWnd判断是否需要弹起登录框，不需要的话会弹出消息框，需要就调用DoLoginGP。  
DoLoginGP函数会创建GPLoginMainWnd并阻塞当前窗口等待返回。  
GPLoginMainWnd创建完成后，调用OnInitDialog初始化，关联UI事件和判断是否需要快速登陆  
qq登录和微信登录则是依靠WebUI实现，具体实现在GPIEWnd  

### GPluginMgr  
#### 项目说明  
该项目生成的文件就是yygame.exe,由Launcher拉起。   
项目启动后先调用GPlatform模块初始化，再去读取一个plugins.cfg配置文件，最后会调用GPlatform模块来初始化和创建窗口等操作，详细步骤看[GPlatform](#GPlatform)

#### 项目结构  
* 以后补充

#### 流程图  
* 以后补充  

#### 流程说明  
* 以后补充  

### Launcher  
#### 项目说明  
该项目为yygame启动项目，主要的逻辑实现都在LaunchMgr.cpp。项目启动后检查启动参数，检查完参数后会检查YYGame进程是否存在，如果存在则发送参数到进程实例，不存在的话就会拉起yygame.exe
#### 项目结构  
* 以后补充 

#### 流程图  
* 以后补充  

#### 流程说明  
* 以后补充  
