import QtQuick 2.8
import zm.pyqt.Downloader 1.0

Item {
    id:page

    property alias count: listView.count

    function insertNew(url,path,name){
        path += "/"
        console.debug(url,path,name)
        listModel.append({
                             url:url,
                             path:path,
                             name:name
                         })
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

    ListView{
        id:listView
        anchors.fill: parent
        clip:true
        model: ListModel{
            id:listModel
        }
        delegate: contactsDelegate

        Component{
            id:contactsDelegate
            Rectangle{
                id:delegateItem
                width:listView.width - 10
                height:80
                color:index == listView.currentIndex ? "#98F5FF" : "white"
                anchors.left: parent.left
                anchors.leftMargin: 5

                property real total: attributes?attributes.total:0
                property int  curProgress: attributes?attributes.curProgress:0
                property int  curTime: attributes?attributes.curTime:0
                property var  curSpeed: 0
                property int  preTime: 0
                property int  preProgress: attributes?attributes.preProgress:0
                property string state: attributes?attributes.state:""
                property int finishFile: attributes?attributes.finishFile:0
                property int totalFile: attributes?attributes.totalFile:0
                property var attributes: 0

                Component.onCompleted: {
                    downloaderManager.setFileTotal(1)
                    downloaderManager.setPath(path)
                    downloaderManager.setUrl(url)
                    downloaderManager.setFileName(name)
                    attributes = downloaderManager.downloadFile()
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


                TextLoader{
                    id:fileNameText
                    text:name
                    anchors.top: parent.top
                    anchors.topMargin: 10
                }

                CProgressBar{
                    id:bar
                    anchors.top: fileNameText.bottom
                    anchors.topMargin: 5
                    anchors.right: downState.left
                    anchors.rightMargin: 20
                    anchors.left: parent.left
                    anchors.leftMargin: 0
                    height:30
                    value:curProgress / total * 100
                    width:parent.width - downloadSpeed.width - 20

                    TextLoader{
                        id:percentage
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        anchors.fill: parent
                        text:(bar.value).toFixed(2) + "%"
                    }
                }

                TextLoader{
                    id:downState
                    text:state
                    anchors.top: fileNameText.bottom
                    anchors.topMargin: 5
                    anchors.right: downloadSpeed.left
                    anchors.rightMargin: 20
                }

                TextLoader{
                    id:downloadSpeed
                    text:page.changeToString(curSpeed) + "/s"
                    anchors.top: fileNameText.bottom
                    anchors.topMargin: 5
                    anchors.right: stateButton.left
                    anchors.rightMargin: 20
                }

                CPushButton{
                    id:stateButton
                    text:delegateItem.state
                    width:50
                    height:30
                    anchors.top: fileNameText.bottom
                    anchors.topMargin: 5
                    anchors.right: parent.right
                    anchors.rightMargin: 0
                    onClicked: {
                        //
                    }
                }

                TextLoader{
                    id:fileSize
                    anchors.top: stateButton.bottom
                    anchors.topMargin: 5
                    anchors.left: parent.left
                    anchors.leftMargin: 0
                    text:"文件大小:" + page.changeToString(total)
                }

                TextLoader{
                    id:down
                    anchors.top: stateButton.bottom
                    anchors.topMargin: 5
                    anchors.left: fileSize.right
                    anchors.leftMargin: 10
                    text:"已下载:"+page.changeToString(curProgress)
                }

                TextLoader{
                    id:totalFileText
                    anchors.top: stateButton.bottom
                    anchors.topMargin: 5
                    anchors.left: down.right
                    anchors.leftMargin: 20
                    anchors.right: parent.right
                    anchors.rightMargin: 0
                    text:"已完成/总数量:"+finishFile + "/" + totalFile
                }

            }
        }
    }

}
