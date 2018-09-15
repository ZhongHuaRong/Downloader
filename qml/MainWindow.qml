import QtQuick 2.8
import QtQuick.Controls 1.4

Item {
    id:mainWindow

    TabView{
        id:tab
        anchors.fill:parent
        Tab {
            id:downloadTab
            title: "正在下载(" + item.count + ")"
            active: true
            DownloadPage{
            }
        }
        Tab {
            title: "已完成(" + 0 + ")"
            active: true
            Rectangle{}
        }
        Tab {
            title: "已删除(" + 0 + ")"
            active: true
            Rectangle{}
        }
        Tab {
            id:settingTab
            title: "设置"
            active: true
            SettingPage{
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
