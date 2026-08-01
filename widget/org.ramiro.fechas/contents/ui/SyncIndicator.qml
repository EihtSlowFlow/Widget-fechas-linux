import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components 3.0 as PlasmaComponents
import org.kde.kirigami as Kirigami

RowLayout {
    id: syncIndicator

    property bool compact: true

    spacing: 4

    function timeAgo(isoString) {
        if (root.syncStatus === "background") return "en 2º plano...";
        if (root.isSyncing) return "sincronizando...";
        if (root.syncStatus === "already_running") return "ya en curso";
        
        if (!isoString) return "nunca";
        try {
            var syncTime = new Date(isoString);
            var now = new Date();
            var diffMs = now.getTime() - syncTime.getTime();
            var diffMin = Math.floor(diffMs / 60000);

            if (diffMin < 1) return "ahora";
            if (diffMin < 60) return diffMin + " min";
            var diffHrs = Math.floor(diffMin / 60);
            if (diffHrs < 24) return diffHrs + "h";
            var diffDays = Math.floor(diffHrs / 24);
            return diffDays + "d";
        } catch (e) {
            return "?";
        }
    }

    function syncIcon() {
        if (root.syncStatus === "background") return "view-refresh";
        if (root.isSyncing) return "view-refresh";
        if (root.syncStatus === "already_running") return "dialog-information";
        if (root.syncStatus === "ok") return "checkmark";
        if (root.syncStatus === "partial") return "dialog-warning";
        if (root.syncStatus === "error") return "dialog-error";
        return "clock";
    }

    function syncColor() {
        if (root.syncStatus === "background" || root.isSyncing) return Kirigami.Theme.highlightColor;
        if (root.syncStatus === "already_running") return "#FFC107"; // Yellow/Orange
        if (root.syncStatus === "ok") return Kirigami.Theme.positiveTextColor;
        if (root.syncStatus === "partial") return "#FFC107";
        if (root.syncStatus === "error") return Kirigami.Theme.negativeTextColor;
        return Kirigami.Theme.textColor;
    }

    Kirigami.Icon {
        source: syncIcon()
        Layout.preferredWidth: compact ? Kirigami.Units.iconSizes.small * 0.7 : Kirigami.Units.iconSizes.small
        Layout.preferredHeight: Layout.preferredWidth
        color: syncColor()

        // Warning animation if sync failed or already running
        SequentialAnimation on opacity {
            running: root.syncStatus === "error" || root.syncStatus === "already_running"
            loops: Animation.Infinite
            NumberAnimation { from: 1.0; to: 0.4; duration: 1000 }
            NumberAnimation { from: 0.4; to: 1.0; duration: 1000 }
        }
        
        // Rotation animation when syncing
        RotationAnimation on rotation {
            loops: Animation.Infinite
            from: 0
            to: 360
            duration: 1000
            running: root.isSyncing || root.syncStatus === "background"
        }
    }

    PlasmaComponents.Label {
        text: compact ? timeAgo(root.lastSync) : ("Sync: hace " + timeAgo(root.lastSync))
        font.pixelSize: Kirigami.Units.gridUnit * (compact ? 0.45 : 0.55)
        opacity: 0.5
        color: syncColor()

        PlasmaComponents.ToolTip {
            text: {
                if (root.syncStatus === "background") return "La sincronización continúa en segundo plano";
                if (root.isSyncing) return "Sincronizando con los servidores...";
                if (root.syncStatus === "already_running") return "Ya hay una sincronización en curso";
                if (root.syncStatus === "ok") return "Sincronización exitosa";
                if (root.syncError && root.syncError.length > 0)
                    return "⚠ " + root.syncError;
                return "Estado: " + root.syncStatus;
            }
        }
    }
}
