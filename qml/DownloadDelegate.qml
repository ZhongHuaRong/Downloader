import QtQuick 2.8
import QtQuick.Layouts 1.3
import zm.pyqt.Downloader 1.0

Item {
    id:delegate

    property real total: 100
    property int  curProgress: attributes?attributes.curProgress:0
    property int  curTime: attributes?attributes.curTime:0
    property var  curSpeed: 0
    property int  preTime: 0
    property int  preProgress: attributes?attributes.preProgress:0
    property string state: attributes?attributes.state:0
    property var attributes: 0

    Component.onCompleted: {
        downloaderManager.setFileTotal(1)
        downloaderManager.setPath(path)
        downloaderManager.setUrl(url)
        downloaderManager.setFileName(name)
        delegate.attributes = downloaderManager.downloadFile()
    }

    DownloaderManager{
        id:downloaderManager
    }

    onCurTimeChanged: {
        if(preTime == curTime)
            return
        curSpeed = (curProgress - preProgress) / (curTime - preTime)
        preTime = curTime
        preProgress = curProgress
    }

    function stop(){
        bar.stop()
    }

    function reset(){
        total = 0.0
        curProgress = 0.0
        curTime = 0
        curSpeed  = 0.0
    }

    function changeToString(value){
        var n = 0
        while(value>1024){
            value /= 1024.0
            n++
        }

        var m
        switch(n){
        case 0:
            m = "B"
            break
        case 1:
            m = "KB"
            break
        case 2:
            m = "MB"
            break
        case 3:
            m = "GB"
            break
        }

        return value.toFixed(2) + " " + m
    }

    Column {
        id: row
        anchors.fill: parent
        spacing: 5

        TextLoader{
            id:fileNameText
            text:name
        }

        Row{
            spacing : 5
            Layout.fillWidth: true

            CProgressBar{
                id:bar
                height:20
                value:curProgress / total * 100
                width:row.width - downloadSpeed.width - 20

                TextLoader{
                    id:percentage
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignHCenter
                    anchors.fill: parent
                    text:(bar.value).toFixed(2) + "%"
                }
            }

            TextLoader{
                id:downloadSpeed
                text:changeToString(curSpeed) + "/s"
            }
        }

        Row{
            spacing: 5

            TextLoader{
                text:"下载状态:"
            }

            TextLoader{
                id:downState
                text:state
            }
        }

        Row{
            spacing: 5

            TextLoader{
                text:"文件大小:"
            }

            TextLoader{
                id:fileSize
                text:changeToString(total)
            }
        }

        Row{
            spacing: 10

            TextLoader{
                text:"已下载:"
            }

            TextLoader{
                id:down
                text:changeToString(curProgress)
            }
        }
    }
}
