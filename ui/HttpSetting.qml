import QtQuick 2.9

Item {
    id:httpItem

    property alias fileName: targetEdit.text
    property string path: ""
    property string name: ""
    property string url: ""
    property bool videoMode:setting.video.resources.length > 0
    property bool submitted:false

    function setMsg(baseUrl,fileName,path){
        httpItem.url = baseUrl
        httpItem.name = fileName
        httpItem.path = path
        httpItem.fileName = httpItem.name
        submitted = false
        if(settingItem.downloadFlag){
            downloadButtonClick()
        }
    }

    function downloadButtonClick(){
        if(videoMode){
            httpItem.parent.videoDownload(videoResults.selectedTasks())
            return
        }
        httpItem.parent.httpDownload(url,fileName,numEdit.text)
        submitted = true
    }

    MyScrollView{
        id:scroll
        anchors.fill: parent

        Column{
            width:httpItem.width - 15
            spacing: 10
            padding: 5

            Row {
                id: fileNameRow
                visible:!httpItem.videoMode
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

            Row {
                visible:!httpItem.videoMode
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
                            httpItem.fileName = setting.getFolderName(url)
                        }
                        else{
                            httpItem.fileName = httpItem.name
                        }
                    }
                }
            }

            CPushButton{
                id:advanced
                objectName:"videoAdvanced"
                width:120
                checkable:true
                text:(checked ? "▾ " : "▸ ") + "高级选项"
            }

            Row{
                visible:advanced.checked
                spacing:8
                CPushButton{
                    objectName:"recognizeVideo"
                    text:setting.video.busy && setting.video.manual ? "完成识别" : "识别视频"
                    enabled:!setting.video.busy || setting.video.manual
                    onClicked:{
                        if(setting.video.busy)
                            httpItem.parent.finishRecognition()
                        else
                            httpItem.parent.recognizeVideo(httpItem.url,false)
                    }
                }
                CPushButton{
                    width:120
                    text:setting.video.busy ? "取消识别" : "浏览器中识别"
                    onClicked:{
                        if(setting.video.busy)
                            httpItem.parent.stopRecognition()
                        else
                            httpItem.parent.recognizeVideo(httpItem.url,true)
                    }
                }
            }

            TextLoader{
                width:parent.width - 10
                visible:text.length > 0
                wrapMode:Text.Wrap
                text:setting.video.error || setting.video.status
                color:setting.video.error ? "#cc3333" : "#445266"
            }

            WebVideoSetting{
                id:videoResults
                width:parent.width - 10
                visible:httpItem.videoMode
                onPreviewClicked:httpItem.parent.previewVideo(resourceId,force)
            }

            CPushButton{
                id:downloadButton
                objectName:"httpDownload"
                width:httpItem.videoMode ? 150 : 100
                text:httpItem.videoMode ? "下载已选（" + videoResults.selectedCount + "）" : "下载"
                enabled:httpItem.videoMode ? videoResults.selectedCount > 0 : !httpItem.submitted
                onClicked:httpItem.downloadButtonClick()
            }

        }
    }

    Timer{
        id:previewTimer
        interval:150
        onTriggered:{
            if(scroll.flickableItem)
                videoResults.requestVisiblePreviews(scroll.flickableItem.contentY,scroll.height)
        }
    }
    Connections{
        target:setting.video
        function onChanged(){previewTimer.restart()}
    }
    Connections{
        target:scroll.flickableItem
        function onContentYChanged(){previewTimer.restart()}
    }
}
