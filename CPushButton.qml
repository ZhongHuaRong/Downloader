import QtQuick 2.7
import QtQuick.Layouts 1.3
import QtQuick.Controls.Styles 1.4
import QtQuick.Controls 1.2

Button {
    id: button

    property color color: "#4c677c"
    property color textColor: "#ffffff"
    property var fontSize: 16


    onHoveredChanged: {
        if(!enabled){
            state = "unenabled"
            return;
        }
        if(hovered)
            state = "entered"
        else
            state = "exited"
    }

    onPressedChanged: {
        if(!enabled){
            state = "unenabled"
            return;
        }
        if(pressed)
            state = "pressed"
        else if(hovered)
            state = "entered"
    }

    onEnabledChanged: {
        if(!enabled)
            state = "unenabled"
        else if(hovered)
            state = "entered"
        else
            state = "exited"
    }

    states :
        [
        State {
            name: "entered"
            PropertyChanges {
                target: button;
                color:"#87CEFA"
            }
        },
        State{
            name:"pressed";
            PropertyChanges {
                target: button;
                color:"#4682B4"
            }
        },
        State{
            name:"exited";
        },
        State{
            name:"unenabled"
            PropertyChanges {
                target: button;
                color:"#DCDCDC"
            }
            PropertyChanges {
                target: button;
                textColor:"#4c677c"
            }
        }

    ]

//    transitions: Transition{
//        ColorAnimation{
//            target: button
//            property: "color"
//            duration: 150
//        }

//        ColorAnimation{
//            target:button
//            property: "textColor"
//            duration:150
//        }
//    }

    style:ButtonStyle{
        background :Rectangle{
            border.width: 0
            radius: 5
            color: button.color
        }
        label:Text{
            color: button.textColor
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            text:button.text
            font.pixelSize: fontSize
            font.family: "黑体"
        }
    }
}
