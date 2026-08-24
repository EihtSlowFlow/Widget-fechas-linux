import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components 3.0 as PlasmaComponents
import org.kde.kirigami as Kirigami

Item {
    id: root
    property var classesModel: []
    property string copiedSubjectId: ""
    property var copyLink: null

    function validUrl(url) {
        return typeof url === "string"
            && /^https?:\/\/[^\s/?#]+(?:[/?#][^\s]*)?$/i.test(url);
    }

    function platformLabel(platform) {
        const labels = {
            "google_meet": "Google Meet",
            "zoom": "Zoom",
            "microsoft_teams": "Microsoft Teams",
            "other": "Otra plataforma"
        };
        return labels[platform] || "Clase virtual";
    }

    ListView {
        anchors.fill: parent
        clip: true
        spacing: Kirigami.Units.smallSpacing
        model: root.classesModel || []

        delegate: Rectangle {
            width: ListView.view.width
            height: content.implicitHeight + Kirigami.Units.smallSpacing * 2
            radius: Kirigami.Units.cornerRadius
            color: modelData.has_class_today
                ? Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g,
                          Kirigami.Theme.highlightColor.b, 0.14)
                : Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                          Kirigami.Theme.backgroundColor.b, 0.4)

            ColumnLayout {
                id: content
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.smallSpacing

                RowLayout {
                    Layout.fillWidth: true
                    PlasmaComponents.Label {
                        text: modelData.subject_name
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    PlasmaComponents.Label {
                        visible: modelData.has_class_today
                        text: "Hoy" + (modelData.today_times.length
                            ? " · " + modelData.today_times.join(", ") : "")
                        color: Kirigami.Theme.highlightColor
                        font.bold: true
                    }
                }

                PlasmaComponents.Label {
                    text: root.platformLabel(modelData.virtual_class_platform)
                    opacity: 0.65
                    font.pixelSize: Kirigami.Units.gridUnit * 0.6
                }

                RowLayout {
                    PlasmaComponents.Button {
                        text: "🔗 Entrar a clase"
                        enabled: root.validUrl(modelData.virtual_class_url)
                        onClicked: Qt.openUrlExternally(modelData.virtual_class_url)
                    }
                    PlasmaComponents.Button {
                        text: "📋 Copiar enlace"
                        enabled: root.validUrl(modelData.virtual_class_url)
                        onClicked: {
                            if (root.copyLink) root.copyLink(modelData.subject_id);
                        }
                    }
                }
                PlasmaComponents.Label {
                    visible: root.copiedSubjectId === modelData.subject_id
                    text: "✓ Enlace copiado"
                    color: "#4CAF50"
                    font.pixelSize: Kirigami.Units.gridUnit * 0.55
                }
            }
        }

        PlasmaComponents.Label {
            anchors.centerIn: parent
            visible: !root.classesModel || root.classesModel.length === 0
            text: "Sin clases virtuales configuradas"
            opacity: 0.5
        }
    }
}
