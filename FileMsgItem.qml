import QtQuick 2.8
import QtQuick.Layouts 1.3
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.4

Item {
    id:msgItem

    property string fileName: ""

    function setProgress(value,max){
        bar.value = value/max * 100
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
        }
    }


}
