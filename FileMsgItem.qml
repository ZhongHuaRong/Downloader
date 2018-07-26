import QtQuick 2.8
import QtQuick.Layouts 1.3
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.4

Item {
    id:msgItem

    property string fileName: ""

    property real total: 0.0
    property int  curProgress: 0
    property int  curTime: 0
    property var  curSpeed: 0.0

    function setProgress(value,max,timeStamp){
        bar.value = value/max * 100

        if(curProgress ==0){
            total = max
            curProgress = value
            curTime = timeStamp
            curSpeed = 0.0
        }
        else if(curTime == timeStamp){
        }
        else {
            curSpeed = (value - curProgress) / (timeStamp - curTime)
            curProgress = value
            curTime = timeStamp
        }
        setMsg(total,curSpeed,value)
    }

    function setMsg(total,curSpeed,value){
        progressText.text = "总大小:" + changeToString(total) +
                ",已下载" + changeToString(value) +
                ",当前百分比" + (value / total * 100).toFixed(2) + "%" +
                ",当前速度:" + changeToString(curSpeed) + "/s"
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
            m = "M"
            break
        case 3:
            m = "G"
            break
        }

        return value.toFixed(2) + m
    }

    ColumnLayout {
        id: row
        anchors.fill: parent
        spacing: 10

        TextLoader{
            id:fileText
            text:"file name:" + msgItem.fileName
            Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
        }

        ProgressBar{
            id:bar
            minimumValue:0
            maximumValue:100
            value:0
            height:30
            Layout.fillWidth: true
            style:ProgressBarStyle
            {
                background: Rectangle {
                    radius: bar.width/3
                    color: "#E2E2E2"
                    border.width: 0
                }
                progress:  Rectangle {
                    radius: bar.width/3
                    color: "#4dc7e7"
                }
            }

            TextLoader{
                id:progressText
                anchors.fill: parent
            }
        }
    }


}
