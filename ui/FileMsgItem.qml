import QtQuick 2.8
import QtQuick.Layouts 1.3

Item {
    id:msgItem

    property alias fileName: fileNameEditText.text

    property real total: 100
    property int  curProgress: 1
    property int  curTime: 0
    property var  curSpeed: 0
    property int  preTime: 0
    property int  preProgress: 0
    property alias state: downState.text

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

    ColumnLayout {
        id: row
        anchors.fill: parent
        spacing: 10

        CProgressBar{
            id:bar
            height:30
            value:curProgress / total * 100
            Layout.fillWidth: true

            TextLoader{
                id:percentage
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignHCenter
                anchors.fill: parent
                text:(bar.value).toFixed(2) + "%"
            }
        }

        Row{
            spacing: 10

            TextLoader{
                text:"下载状态:"
            }

            TextLoader{
                id:downState
                text:state
            }
        }

        Row{
            spacing: 10

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
                id:fileNameTextLoader
                text:"文件名:"
                height:fileNameEditText.height
            }

            CTextEdit{
                id:fileNameEditText
                width:row.width - 20 - fileNameTextLoader.width
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

        Row{
            spacing: 10

            TextLoader{
                text:"下载速度:"
            }

            TextLoader{
                id:downloadSpeed
                text:changeToString(curSpeed) + "/s"
            }
        }
    }


}
