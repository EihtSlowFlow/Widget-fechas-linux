import QtQuick
import QtQuick.Layouts
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components 3.0 as PlasmaComponents
import org.kde.kirigami as Kirigami

Item {
    id: compactRoot

    Layout.preferredWidth: Kirigami.Units.gridUnit * 20
    Layout.preferredHeight: Kirigami.Units.gridUnit * 5

    // ─── Urgency color helper ────────────────────────────────
    function urgencyColor(urgency) {
        switch (urgency) {
            case "red":    return "#F44336";
            case "orange": return "#FF9800";
            case "yellow": return "#FFC107";
            case "green":  return "#4CAF50";
            default:       return Kirigami.Theme.textColor;
        }
    }

    // ─── No events fallback ──────────────────────────────────
    PlasmaComponents.Label {
        anchors.centerIn: parent
        visible: root.eventCount === 0 && (!root.subjectsModel || root.subjectsModel.length === 0)
        text: "📅 Sin eventos próximos"
        opacity: 0.6
        font.pixelSize: Kirigami.Units.gridUnit * 0.9
    }

    // ─── Subjects Banner ─────────────────────────────────────
    Rectangle {
        id: subjectsBanner
        visible: root.subjectsModel && root.subjectsModel.length > 0
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Kirigami.Units.smallSpacing
        anchors.rightMargin: Kirigami.Units.smallSpacing
        anchors.topMargin: Kirigami.Units.smallSpacing
        height: visible ? (Kirigami.Units.gridUnit * 1.2) : 0
        radius: Kirigami.Units.cornerRadius
        color: Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g, Kirigami.Theme.highlightColor.b, 0.2)
        
        PlasmaComponents.Label {
            anchors.centerIn: parent
            text: {
                if (!root.subjectsModel || root.subjectsModel.length === 0) return "";
                var n = root.subjectsModel.length;
                if (n === 1) {
                    var s = root.subjectsModel[0];
                    return "📚 " + s.subject_name + " (Semana " + s.week_number + ")";
                } else {
                    return "📚 " + n + " materias en curso";
                }
            }
            font.pixelSize: Kirigami.Units.gridUnit * 0.6
            font.bold: true
            color: Kirigami.Theme.highlightColor
        }
    }

    // ─── Carousel ────────────────────────────────────────────
    ColumnLayout {
        anchors.top: subjectsBanner.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: Kirigami.Units.smallSpacing
        visible: root.eventCount > 0
        spacing: 2

        ListView {
            id: carouselView
            Layout.fillWidth: true
            Layout.fillHeight: true

            orientation: ListView.Horizontal
            snapMode: ListView.SnapOneItem
            highlightRangeMode: ListView.StrictlyEnforceRange
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            model: root.visibleEventsModel

            onModelChanged: {
                if (count > 0 && currentIndex >= count) {
                    currentIndex = Math.max(0, count - 1);
                }
            }

            delegate: Item {
                width: carouselView.width
                height: carouselView.height

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 2
                    radius: Kirigami.Units.cornerRadius
                    color: Qt.rgba(
                        Kirigami.Theme.backgroundColor.r,
                        Kirigami.Theme.backgroundColor.g,
                        Kirigami.Theme.backgroundColor.b,
                        0.6
                    )
                    border.width: 0

                    // Urgency side bar
                    Rectangle {
                        id: urgencyBar
                        width: 4
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.margins: 0
                        radius: Kirigami.Units.cornerRadius
                        color: urgencyColor(modelData.urgency)
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: urgencyBar.width + Kirigami.Units.smallSpacing * 2
                        anchors.rightMargin: Kirigami.Units.smallSpacing
                        anchors.topMargin: Kirigami.Units.smallSpacing
                        anchors.bottomMargin: Kirigami.Units.smallSpacing
                        spacing: Kirigami.Units.smallSpacing

                        // Days remaining big number
                        ColumnLayout {
                            Layout.alignment: Qt.AlignVCenter
                            Layout.preferredWidth: Kirigami.Units.gridUnit * 3
                            spacing: 0

                            PlasmaComponents.Label {
                                Layout.alignment: Qt.AlignHCenter
                                text: Math.abs(modelData.days_remaining)
                                font.pixelSize: Kirigami.Units.gridUnit * 1.8
                                font.bold: true
                                color: urgencyColor(modelData.urgency)
                            }
                            PlasmaComponents.Label {
                                Layout.alignment: Qt.AlignHCenter
                                text: modelData.days_remaining === 1 ? "día" :
                                      modelData.days_remaining === 0 ? "HOY" :
                                      modelData.days_remaining < 0 ? "vencido" : "días"
                                font.pixelSize: Kirigami.Units.gridUnit * 0.55
                                opacity: 0.7
                            }
                        }

                        // Separator
                        Rectangle {
                            Layout.preferredWidth: 1
                            Layout.fillHeight: true
                            Layout.topMargin: 4
                            Layout.bottomMargin: 4
                            color: Kirigami.Theme.textColor
                            opacity: 0.15
                        }

                        // Event details
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            spacing: 2

                            PlasmaComponents.Label {
                                Layout.fillWidth: true
                                text: modelData.title
                                font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                font.bold: true
                                elide: Text.ElideRight
                                maximumLineCount: 1
                            }

                            PlasmaComponents.Label {
                                Layout.fillWidth: true
                                text: modelData.source_name || ""
                                font.pixelSize: Kirigami.Units.gridUnit * 0.55
                                opacity: 0.6
                                elide: Text.ElideRight
                                maximumLineCount: 1
                            }

                            PlasmaComponents.Label {
                                Layout.fillWidth: true
                                text: {
                                    function fmtDate(iso) {
                                        var d = new Date(iso);
                                        var day = d.getDate();
                                        var months = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
                                        var mon = months[d.getMonth()];
                                        return day + " " + mon;
                                    }
                                    function fmtDateFull(iso) {
                                        var d = new Date(iso);
                                        var day = d.getDate();
                                        var months = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
                                        return day + " " + months[d.getMonth()] + " " + d.getFullYear();
                                    }
                                    try {
                                        if (modelData.start_date && modelData.start_date.length > 0) {
                                            return "📅 " + fmtDate(modelData.start_date) + " → " + fmtDateFull(modelData.due_date);
                                        } else {
                                            return "📅 " + fmtDateFull(modelData.due_date);
                                        }
                                    } catch (e) {
                                        return modelData.due_date || "";
                                    }
                                }
                                font.pixelSize: Kirigami.Units.gridUnit * 0.55
                                opacity: 0.5
                            }
                        }

                        // "Nuevo" badge
                        Rectangle {
                            visible: modelData.is_new === true
                            Layout.alignment: Qt.AlignTop | Qt.AlignRight
                            Layout.preferredWidth: newLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                            Layout.preferredHeight: newLabel.implicitHeight + Kirigami.Units.smallSpacing
                            radius: height / 2
                            color: "#2196F3"

                            PlasmaComponents.Label {
                                id: newLabel
                                anchors.centerIn: parent
                                text: "NUEVO"
                                font.pixelSize: Kirigami.Units.gridUnit * 0.4
                                font.bold: true
                                color: "white"
                            }

                            // Subtle pulse animation
                            SequentialAnimation on opacity {
                                running: modelData.is_new === true && !root.dismissedBadges[modelData.id]
                                loops: 3
                                NumberAnimation { from: 1.0; to: 0.6; duration: 800; easing.type: Easing.InOutQuad }
                                NumberAnimation { from: 0.6; to: 1.0; duration: 800; easing.type: Easing.InOutQuad }
                            }
                        }
                    }

                    HoverHandler {
                        id: hoverHandler
                        enabled: modelData.is_new === true && !root.dismissedBadges[modelData.id]
                        onHoveredChanged: {
                            if (hovered) {
                                hoverTimer.start()
                            } else {
                                hoverTimer.stop()
                            }
                        }
                    }

                    Timer {
                        id: hoverTimer
                        interval: 600
                        onTriggered: {
                            modelData.is_new = false
                            root.markEventSeen(modelData.id)
                        }
                    }
                }
            }
        }

        // ─── Dots indicator + sync status ────────────────────
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: Kirigami.Units.gridUnit * 0.8
            spacing: Kirigami.Units.smallSpacing

            // Carousel dots
            Row {
                Layout.alignment: Qt.AlignHCenter
                spacing: 4

                Repeater {
                    model: Math.min(root.visibleEventsModel ? root.visibleEventsModel.length : 0, 10)
                    Rectangle {
                        width: 6
                        height: 6
                        radius: 3
                        color: index === carouselView.currentIndex ?
                               Kirigami.Theme.highlightColor :
                               Kirigami.Theme.textColor
                        opacity: index === carouselView.currentIndex ? 1.0 : 0.3
                    }
                }
            }

            // Sync indicator (compact)
            SyncIndicator {
                Layout.alignment: Qt.AlignRight
                compact: true
            }
        }

        // ─── Auto-scroll timer ───────────────────────────────
        Timer {
            interval: Math.max(2, plasmoid.configuration.autoScrollIntervalSec || 5) * 1000
            running: root.visibleEventsModel && root.visibleEventsModel.length > 1 && !carouselView.moving
            repeat: true
            onTriggered: {
                if (root.visibleEventsModel.length > 0) {
                    var nextIdx = (carouselView.currentIndex + 1) % root.visibleEventsModel.length;
                    carouselView.positionViewAtIndex(nextIdx, ListView.SnapPosition);
                }
            }
        }
    }

    // ─── Click to expand ─────────────────────────────────────
    TapHandler {
        onTapped: root.expanded = !root.expanded
    }
}
