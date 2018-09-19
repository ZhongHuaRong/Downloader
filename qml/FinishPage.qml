import QtQuick 2.8
import Qt.labs.settings 1.0
import QtQuick.Controls 2.3

Item {
    id:page

    property alias count: listView.count
    property string urlList: ""
    property string pathList: ""
    property string nameList: ""
    property string numList: ""
    property string finishList: ""
    property string totalList: ""
    property string progressList: ""

    signal toDownload(string url,string path,string name,string num)
    signal toTrash(string url,string path,string name,string num,
                   string finishFile, string total,string curProgress)
    signal deleteFile(string path,string name)
    signal viewOnExplorer(string path,string name)

    function insertNew(url,path,name,totalFile,
                       finishFile,
                       total,
                       curProgress){
        listModel.append({
                             url:url,
                             path:path,
                             name:name,
                             files:totalFile,
                             finish:finishFile,
                             total:total,
                             progress:curProgress
                         })
        urlAppend(url)
        pathAppend(path)
        nameAppend(name)
        numAppend(totalFile)
        finishAppend(finishFile)
        totalAppend(total)
        progressAppend(curProgress)
    }

    function removeTask(index,toDownload,toRecycleBin,
                        finishFile,total,curProgress){
        var u = listModel.get(index).url
        var p = listModel.get(index).path
        var n = listModel.get(index).name
        var f = listModel.get(index).files
        urlRemove(index)
        pathRemove(index)
        nameRemove(index)
        numRemove(index)
        finishRemove(index)
        totalRemove(index)
        progressRemove(index)
        listModel.remove(index)
        if(toDownload){
            page.toDownload(u,
                            p,
                            n,
                            f)
        }
        else if(toRecycleBin){
            page.toTrash(u,
                         p,
                         n,
                         f,
                         finishFile,total,curProgress)
        }
        else{
            page.deleteFile(p,n)
        }
    }

    function urlAppend(str){
        urlList += "|" + str
    }

    function pathAppend(str){
        pathList += "|" + str
    }

    function nameAppend(str){
        nameList += "|" + str
    }

    function numAppend(str){
        numList += "|" + str
    }

    function finishAppend(str){
        finishList += "|" + str
    }

    function totalAppend(str){
        totalList += "|" + str
    }

    function progressAppend(str){
        progressList += "|" + str
    }

    function urlRemove(index){
        var l = urlList.split('|')
        urlList = ""
        for(var n = 1; n < l.length; n++){
            if(n != index + 1)
                urlAppend(l[n])
        }
    }

    function pathRemove(index){
        var l = pathList.split('|')
        pathList = ""
        for(var n = 1; n < l.length; n++){
            if(n != index + 1)
                pathAppend(l[n])
        }
    }

    function nameRemove(index){
        var l = nameList.split('|')
        nameList = ""
        for(var n = 1; n < l.length; n++){
            if(n != index + 1)
                nameAppend(l[n])
        }
    }

    function numRemove(index){
        var l = numList.split('|')
        numList = ""
        for(var n = 1; n < l.length; n++){
            if(n != index + 1)
                numAppend(l[n])
        }
    }

    function finishRemove(index){
        var l = finishList.split('|')
        finishList = ""
        for(var n = 1; n < l.length; n++){
            if(n != index + 1)
                finishAppend(l[n])
        }
    }

    function totalRemove(index){
        var l = totalList.split('|')
        totalList = ""
        for(var n = 1; n < l.length; n++){
            if(n != index + 1)
                totalAppend(l[n])
        }
    }

    function progressRemove(index){
        var l = progressList.split('|')
        progressList = ""
        for(var n = 1; n < l.length; n++){
            if(n != index + 1)
                progressAppend(l[n])
        }
    }

    function changeToString(value){
        if(value == 0){
            return "0 B"
        }

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

    // 加载历史信息
    Component.onCompleted: {
        var ul = urlList.split('|')
        var pl = pathList.split('|')
        var nl = nameList.split('|')
        var numl = numList.split('|')
        var fl = finishList.split('|')
        var tl = totalList.split('|')
        var prl = progressList.split('|')

        for(var n = 1; n < ul.length; n++){
            listModel.append({
                                 url:ul[n],
                                 path:pl[n],
                                 name:nl[n],
                                 files:numl[n],
                                 finish:fl[n],
                                 total:tl[n],
                                 progress:prl[n]
                             })
        }
    }

    Settings{
        id:settings
        property alias finishUrl: page.urlList
        property alias finishPath: page.pathList
        property alias finishName: page.nameList
        property alias finishNum: page.numList
        property alias finishFiles: page.finishList
        property alias finishTotal: page.totalList
        property alias finishProgress: page.progressList
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
                anchors.left: parent.left
                anchors.leftMargin: 5

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
                    anchors.right: parent.right
                    anchors.rightMargin: 20
                    anchors.left: parent.left
                    anchors.leftMargin: 0
                    height:20
                    value:total!=0?progress / total * 100:100

                    TextLoader{
                        id:percentage
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        anchors.fill: parent
                        text:(bar.value).toFixed(2) + "%"
                    }
                }

                TextLoader{
                    id:fileSize
                    anchors.top: bar.bottom
                    anchors.topMargin: 5
                    anchors.left: parent.left
                    anchors.leftMargin: 0
                    text:"文件大小:" + page.changeToString(total)
                }

                TextLoader{
                    id:down
                    anchors.top: bar.bottom
                    anchors.topMargin: 5
                    anchors.left: fileSize.right
                    anchors.leftMargin: 10
                    text:"已下载:"+page.changeToString(progress)
                }

                TextLoader{
                    id:totalFileText
                    anchors.top: bar.bottom
                    anchors.topMargin: 5
                    anchors.left: down.right
                    anchors.leftMargin: 20
                    anchors.right: parent.right
                    anchors.rightMargin: 0
                    text:"已完成/总数量:"+finish + "/" + files
                }

                MouseArea{
                    anchors.fill: parent
                    z:3
                    acceptedButtons:Qt.RightButton
                    onClicked: {
                        if(mouse.button == Qt.RightButton){
                            popup.x = mouse.x
                            popup.y = mouse.y
                            popup.open()
                        }
                    }
                }

                Menu{
                    id:popup

                    Action{
                        id:startAction
                        text:qsTr("Start Download")
                        checkable: false
                        onTriggered: {
                            popup.close()
                            page.removeTask(index,true,false,finish,total,progress)
                        }
                    }

                    Action{
                        id:viewAction
                        text:qsTr("View on Explorer")
                        checkable: false
                        onTriggered: {
                            popup.close()
                            page.viewOnExplorer(path,name)
                        }
                    }

                    Action{
                        id:removeAction
                        text:qsTr("Remove to trash")
                        checkable: false
                        onTriggered: {
                            popup.close()
                            page.removeTask(index,false,true,finish,total,progress)
                        }
                    }

                    Action{
                        id:deleteAction
                        text:qsTr("Delete permanently")
                        checkable: false
                        onTriggered: {
                            popup.close()
                            page.removeTask(index,false,false,finish,total,progress)
                        }
                    }
                }

            }
        }
    }

}
