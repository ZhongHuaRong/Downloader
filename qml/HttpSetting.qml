import QtQuick 2.9

Item {
    id:httpItem

    signal download(string name)

    property alias fileName: targetEdit.text
    property string path: ""

    function setFileName(name,path){
        httpItem.fileName = setting.checkFileName(name,path)
        httpItem.path = path
        if(settingItem.downloadFlag){
            downloadButton.clicked("")
        }
    }

    MyScrollView{
        anchors.fill: parent

        Column{
            spacing: 10
            padding: 5

            Row {
                id: fileNameRow
                height: 40
                spacing: 10

                TextLoader {
                    id: fileNameText
                    text: qsTr("文件名:")
                    height:targetEdit.height
                }

                CTextEdit{
                    id:targetEdit
                    width:httpItem.width - fileNameText.width - 35
                    placeholderText:"输入路劲"
                }
            }

            CCheckBox{
                id:isMultiple
                text:"是否下载多个文件？(用于下载有特定规律的url资源，漫画，动漫下载)"
                checked: false
            }

            CPushButton{
                id:downloadButton
                text:"下载"
                onClicked: httpItem.download(fileName)
            }

        }
    }
}
