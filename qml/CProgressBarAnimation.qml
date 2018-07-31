import QtQuick 2.8
import QtGraphicalEffects 1.0

Item {
    id:animation
    width:500
    height: 30
    state:"start"

    property int  time : 3000

    function changeState(){
        if(animation.state == "start"){
            time = 3000
            animation.visible = true
            animation.state = "end"
        }
        else{
            time = 500
            animation.visible = false
            animation.state = "start"
        }

    }

    states:[
        State{
            name:"start"
            PropertyChanges {
                target: rect
                x: - rect.height
            }
        },
        State{
            name:"end"
            PropertyChanges {
                target: rect
                x:animation.width
            }
        },
        State{
            name:"no"
        }
    ]

    Rectangle{
        id:rect
        width:parent.height
        height: 60
        y:width
        x: - rect.height
        opacity:0.7

        gradient: Gradient{
            GradientStop { position: 0.0; color: "#eaf7fa" }
            GradientStop { position: 0.5; color: "white" }
            GradientStop { position: 1.0; color: "#eaf7fa" }
        }
        rotation: -90
        transformOrigin: "TopLeft"

    }


    transitions: Transition{
        NumberAnimation{
            target: rect
            property: "x"
            duration: time
        }
    }

}
