import QtQuick 2.8
import QtQuick.Controls 1.4

Item {
    id:mainWindow

    function deleteFile(path,name,taskOptions){
        setting.deleteFile(path,name,taskOptions || {})
    }

    function openFolder(path,name){
        Qt.openUrlExternally( path)
    }

    TabView{
        id:tab
        anchors.fill:parent
        Tab {
            id:downloadTab
            title: "正在下载(" + item.count + ")"
            active: true
            DownloadPage{
                onToFinish: {
                    finishPage.item.insertNew(url,path,name,
                                              num,finishFile,total,curProgress,taskOptions)
                }
                onToTrash: {
                    trashTab.item.insertNew(url,path,name,
                                            num,finishFile,total,curProgress,taskOptions)
                }
                onDeleteFiles:setting.deleteFiles(tasks)
                onDeleteFile: {
                    mainWindow.deleteFile(path,name,taskOptions)
                }
                onViewOnExplorer: {
                    mainWindow.openFolder(path,name)
                }
            }
        }
        Tab {
            id:finishPage
            title: "已完成(" + item.count + ")"
            active: true
            FinishPage{
                onToDownload: {
                    downloadTab.item.insertNew(url,path,name,num,taskOptions)
                }
                onToTrash: {
                    trashTab.item.insertNew(url,path,name,
                                            num,finishFile,total,curProgress,taskOptions)
                }
                onDeleteFiles:setting.deleteFiles(tasks)
                onDeleteFile: {
                    mainWindow.deleteFile(path,name,taskOptions)
                }
                onViewOnExplorer: {
                    mainWindow.openFolder(path,name)
                }
            }
        }
        Tab {
            id:trashTab
            title: "已删除(" + item.count + ")"
            active: true
            TrashPage{
                onToDownload: {
                    downloadTab.item.insertNew(url,path,name,num,taskOptions)
                }
                onDeleteFiles:setting.deleteFiles(tasks)
                onDeleteFile: {
                    mainWindow.deleteFile(path,name,taskOptions)
                }
                onViewOnExplorer: {
                    mainWindow.openFolder(path,name)
                }
            }
        }
        Tab {
            id:settingTab
            title: "设置"
            active: true
            SettingPage{
                onProxyButtonClick:setting.setProxy(proxyEnable,proxyHostname,proxyPort,proxyUser,proxyPw)
                onFfmpegButtonClick:setting.ffmpeg.check(ffmpegDirectory)
                onFfmpegDirectoryChanged:setting.ffmpeg.invalidate()
            }
        }
        Tab{
            title:"新任务"
            active: true
            NewUrlPage{
                settingItem: settingTab.item
                onInspectM3u8:setting.video.inspectM3u8(url)
                onCancelVideo:setting.video.reset()
                onRecognizeVideo:setting.video.recognize(url,manual)
                onFinishVideoRecognition:setting.video.finishRecognition()
                onStopVideoRecognition:setting.video.cancel()
                onPreviewVideo:setting.video.preview(resourceId,force)
                onNewVideoTasks: {
                    var ready = setting.prepareVideoTasks(tasks,path,downloadTab.item.activeNames(path))
                    for(var i = 0; i < ready.length; i++){
                        var task = ready[i]
                        downloadTab.item.insertNew(task.url,task.path,task.name,task.files,task.options)
                    }
                }
                onNewOne: {
                    downloadTab.item.insertNew(url,path,fileName,pages)
                }
            }
        }
    }
}
