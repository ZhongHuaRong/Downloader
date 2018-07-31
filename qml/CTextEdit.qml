import QtQuick 2.7
import QtQuick.Layouts 1.3
import QtQuick.Controls.Styles 1.4
import QtQuick.Controls 1.2

Rectangle {
    id:rectangle
    width:150
    height: 30
    border.width: 1
    border.color:"#dfdfe7"

    property bool isPW: false
    property string placeholderText: ""
    property int textMaxNum: 32767
    property color enteredBorderColor: "#2248DD"
    property double leftMargin: 5
    property alias text: textInput.text

    color: "#00000000"

    signal  editingFinished();

    function setPlaceholderText(text){
        rectangle.placeholderText=text;
    }

    states :
        [
        State {
            name: "entered"
            PropertyChanges {
                target: rectangle;
                border.color: rectangle.enteredBorderColor
            }
        },
        State{
            name:"exited";
        }
    ]

    transitions: Transition{
        ColorAnimation{
                target: rectangle.border
                property: "color"
                duration: 250
        }
    }
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true

        onEntered: {
            rectangle.state="entered";
        }

        onExited:{
            rectangle.state="exited";
        }
        z:-1
    }

    TextInput {
        id: textInput
        text: qsTr("")
        anchors.fill: parent
        anchors.leftMargin: leftMargin
        selectionColor: "#2a7ce2"
        passwordCharacter: "*"
        echoMode: rectangle.isPW===true?TextInput.Password:TextInput.Normal
        verticalAlignment:TextInput.AlignVCenter
        font.pixelSize: 14
        font.family: "黑体"
        maximumLength: rectangle.textMaxNum
        selectByMouse:true
        focus: true
        clip: true
        onEditingFinished: rectangle.editingFinished();
        z:1

        Text {
            id: textInput_placeholderText
            color: "#9ca39c"
            text: rectangle.placeholderText
            anchors.fill:parent
            font.pixelSize: 14
            verticalAlignment:TextInput.AlignVCenter
            font.family: "黑体"
            visible: textInput.text.length?false:true
            enabled: false
        }
    }
}
