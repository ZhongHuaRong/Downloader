import QtQuick 2.8
import QtQuick.Controls 1.4

Item {
    id:mainWindow

    function deleteFile(path,name){
        setting.deleteFile(path,name)
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
                                              num,finishFile,total,curProgress)
                }
                onToTrash: {
                    trashTab.item.insertNew(url,path,name,
                                            num,finishFile,total,curProgress)
                }
                onDeleteFile: {
                    mainWindow.deleteFile(path,name)
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
                    downloadTab.item.insertNew(url,path,name,num)
                }
                onToTrash: {
                    trashTab.item.insertNew(url,path,name,
                                            num,finishFile,total,curProgress)
                }
                onDeleteFile: {
                    mainWindow.deleteFile(path,name)
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
                    downloadTab.item.insertNew(url,path,name,num)
                }
                onDeleteFile: {
                    mainWindow.deleteFile(path,name)
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
            }
        }
        Tab{
            title:"新任务"
            active: true
            NewUrlPage{
                settingItem: settingTab.item
                onNewOne: {
                    downloadTab.item.insertNew(url,path,fileName,pages)
                }
            }
        }
    }
}
