import QtQuick 2.9

Item {
    id:httpItem

    property alias fileName: targetEdit.text
    property string path: ""
    property string name: ""
    property string url: ""

    function setMsg(baseUrl,fileName,path){
        httpItem.url = baseUrl
        httpItem.name = fileName
        httpItem.path = path
        httpItem.fileName = httpItem.name
        downloadButton.enabled = true
        if(settingItem.downloadFlag){
            downloadButtonClick()
        }
    }

    function downloadButtonClick(){
        httpItem.parent.httpDownload(url,fileName,numEdit.text)
        downloadButton.enabled = false
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

//            CCheckBox{
//                id:isMultiple
//                text:"是否下载多个文件？(用于下载有特定规律的url资源，漫画，动漫下载)"
//                checked: false
//            }


            Row {
                spacing: 10

                TextLoader {
                    text: qsTr("数量:")
                    height:numEdit.height
                }

                CTextEdit{
                    id:numEdit
                    width:100
                    placeholderText:"输入页数"
                    text:"1"
                    onTextChanged: {
                        if(text != "1"){
                            //页数不是1的时候会处理文件名
                            httpItem.fileName = setting.getFolderName(url,path)
                        }
                        else{
                            httpItem.fileName = httpItem.name
                        }
                    }
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
