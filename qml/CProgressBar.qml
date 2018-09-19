import QtQuick 2.8
import QtQuick.Controls 1.4

ProgressBar{
    maximumValue : 100.0
    minimumValue : 0.0
}

//Item{
//    id:bar
//    property real  value: 50.0
//    property real  max: 100.0
//    property real  min: 0.0
//    property alias backColor: back.color
//    property alias border: back.border
//    property real curWidth: 0
//    state :"first"

//    function stop(){
//        timer.stop()
//    }

//    function changed(){
//        timer.start()
//        curWidth = ( bar.value - bar.min ) / ( bar.max - bar.min ) * ( bar.width - 2 * back.border.width )
//        if(bar.state == "no")
//            bar.state = "first"
//        else if(bar.state = "second")
//            bar.state = "first"
//        else
//            bar.state = "second"
//    }

//    states:[
//        State{
//            name:"first"
//            PropertyChanges {
//                target: front;
//                width:curWidth
//            }
//        },
//        State{
//            name:"second"
//            PropertyChanges {
//                target: front;
//                width:curWidth
//            }
//        },
//        State{
//            name:"no"
//        }
//    ]

//    onValueChanged: {
//        changed()
//    }

//    onWidthChanged: {
//        changed()
//    }

//    Rectangle{
//        id:back
//        color:"#cdcdcd"
//        border.width:2
//        border.color: "#ADADAD"
//        anchors.fill: parent

//    }

//    Rectangle{
//        id:front
//        clip: true
//        anchors.top: parent.top
//        anchors.topMargin: back.border.width
//        anchors.bottom: parent.bottom
//        anchors.bottomMargin: back.border.width
//        anchors.left: parent.left
//        anchors.leftMargin: back.border.width
//        color:"#06B025"


//        CProgressBarAnimation{
//            id:animation
//            x:0
//            y:0
//            width:bar.width - 2 * back.border.width
//            height:bar.height - 2 * back.border.width
//        }
//    }

//    transitions: Transition{
//        NumberAnimation{
//            target: front
//            property: "width"
//            duration: 150
//        }
//    }

//    Timer{
//        id:timer
//        interval: 3000;
//        running: false;
//        repeat: true
//        onTriggered: {
//            animation.changeState()
//            interval = animation.time
//        }
//    }
//}
