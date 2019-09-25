import QtQuick 2.0

Rectangle {
    id: rect
    height: 30
    width: 100
    color:"#00000000"

    property color pressedColor: "#CCE4F7"
    property color pressedBorderColor: "#00559B"
    property color enteredColor: "#E5F1FB"
    property color enteredBorderColor: "#0078D7"
    property color exitedColor: "#E1E1E1"
    property color exitedBorderColor: "#ADADAD"
    property color unClickedColor: "#808080"
    property int borderWidth: 1
    property bool isPressed: false
    property string text: "按钮"
    property int pixelSize: 14
    property var enabled: true

    //让子组件button暴露在接口
    property var buttonObject: button

    //checkButton property
    property bool checkable: false
    property bool checked: false
    property var group: 0

    signal clicked(var sender);

    onGroupChanged: {
        rect.group.addedChild(rect);
    }

    function reset(){
        if(!rect.checkable)
            return;
        rect.state="exited";
        rect.checked=false;
    }

    function setChecked(){
        if(!rect.checkable)
            return;
        rect.state="checked";
        rect.checked=true;
    }

    onEnabledChanged: {
        if(enabled)
            rect.state = "exited"
        else
            rect.state = "unClicked"
    }

    states :
        [
        State {
            name: "entered"
            PropertyChanges {
                target: button;
                color:rect.enteredColor
                border.color: rect.enteredBorderColor
                border.width: 2
            }
        },
        State{
            name:"pressed";
            PropertyChanges {
                target: button;
                color:rect.pressedBorderColor
                border.color: rect.pressedBorderColor
                width:rect.width - rect.width*0.1
                height:rect.height - rect.height*0.1
            }
        },
        State{
            name:"exited";
        },
        State{
            name:"released";
            PropertyChanges {
                target: button;
                color:{
                    if(mouseArea.containsMouse)
                        rect.enteredColor;
                    else
                        rect.exitedColor;
                }
                border.color: {
                    if(mouseArea.containsMouse)
                        rect.enteredBorderColor;
                    else
                        rect.exitedBorderColor;
                }
                border.width: {
                    if(mouseArea.containsMouse)
                        2;
                    else
                        0;
                }
            }
        },
        State{
            name:"checked";
            PropertyChanges {
                target: button;
                color:{
                    if(mouseArea.containsMouse)
                        rect.enteredColor;
                    else
                        rect.exitedColor;
                }
                border.color: rect.enteredBorderColor;
                border.width: 3
                width:rect.width - rect.width*0.05;
                height:rect.height - rect.height*0.05;
            }
        },
        State{
            name:"unClicked";
            PropertyChanges {
                target: text1;
                color:rect.unClickedColor
            }
        }

    ]

    transitions: Transition{
        ColorAnimation{
                target: button
                property: "color"
                duration: 250
        }

        ColorAnimation{
            target:button.border
            property: "color"
            duration:250
        }

        NumberAnimation {
            target: button;
            property: "width"
            duration:100
        }

        NumberAnimation {
            target: button;
            property: "height"
            duration:100
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true

        onEntered: {
            if(!rect.enabled){
                return;
            }

            if(!rect.isPressed)
                rect.state="entered";
            else
                rect.state="pressed";
        }

        onExited:{
            if(!rect.enabled){
                return;
            }
            if(rect.checkable){
                if(rect.checked)
                    rect.state="checked";
                else
                    rect.state="exited";
            }
            else
                rect.state="exited";
        }

        onPressed: {
            if(!rect.enabled){
                return;
            }
            rect.state="pressed";
            isPressed = true;
        }

        onReleased: {
            if(!rect.enabled){
                return;
            }
            //松开在点击之前，所以checked反着判断
            if(rect.checkable){
                if(rect.checked){
                    if(rect.group)
                        rect.state="checked";
                    else if(mouseArea.containsMouse)
                        rect.state="released";
                    else
                        rect.state="checked";
                }
                else{
                    if(mouseArea.containsMouse)
                        rect.state="checked";
                    else
                        rect.state="released";
                }
            }
            else
                rect.state="released";
            isPressed = false;
        }

        onClicked: {
            if(!rect.enabled){
                rect.state="unClicked";
                return;
            }
            if(rect.checkable){
                if(rect.group){
                    if(!rect.checked){
                        rect.checked=!rect.checked
                        rect.clicked(rect);
                    }
                }
                else{
                    rect.checked=!rect.checked
                    rect.clicked(rect);
                }
            }
            else
                rect.clicked(rect);
        }
    }

    Rectangle{
        id:button
        width:parent.width
        height:parent.height
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        color:rect.exitedColor
        border.width: rect.borderWidth
        border.color: rect.exitedBorderColor

        Text {
            id: text1
            text: rect.text
            anchors.fill:parent
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: rect.pixelSize
            font.family: "微软雅黑"
        }
    }
}
