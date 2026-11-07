import QtQuick 2.9

Item {
    id:httpItem

    property alias fileName: targetEdit.text
    property alias url: srcEdit.text

    function setFileName(name,path){
        httpItem.url = setting.getThunderUrl(name)
        var list = name.split('//')
        httpItem.fileName = setting.checkFileName(list[list.length - 1] + ".torrent",path)
        downloadButton.enabled = true
        if(settingItem.downloadFlag){
            downloadButtonClick()
        }
    }

    function downloadButtonClick(){
        httpItem.parent.btDownload(url,fileName)
        downloadButton.enabled = false
    }

    MyScrollView{
        id:scroll
        objectName:"btScroll"
        anchors.fill: parent

        Column{
            width:scroll.viewport.width
            spacing: 10
            padding: 5

            Row {
                width:parent.width - 10
                height: 40
                spacing: 10

                TextLoader {
                    id: urlText
                    text: qsTr("解析出来的链接:")
                    height:targetEdit.height
                }

                CTextEdit{
                    id:srcEdit
                    width:parent.width - urlText.width - 10
                    readOnly: true
                }
            }

            Row {
                width:parent.width - 10
                height: 40
                spacing: 10

                TextLoader {
                    id: fileNameText
                    text: qsTr("文件名:")
                    height:targetEdit.height
                }

                CTextEdit{
                    id:targetEdit
                    width:parent.width - fileNameText.width - 10
                    readOnly: true
                }
            }

            CPushButton{
                id:downloadButton
                text:"下载"
                onClicked: {
                    downloadButton.enabled = false
                    httpItem.downloadButtonClick()
                }
            }

        }
    }
}
