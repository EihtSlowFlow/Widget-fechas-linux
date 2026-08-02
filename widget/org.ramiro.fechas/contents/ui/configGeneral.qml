import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    property alias cfg_refreshIntervalSec: refreshSpin.value
    property alias cfg_autoScrollIntervalSec: autoScrollSpin.value
    property alias cfg_maxVisibleEvents: maxEventsSpin.value

    Kirigami.FormLayout {
        SpinBox {
            id: refreshSpin
            Kirigami.FormData.label: "Intervalo de actualización (segundos):"
            from: 10
            to: 3600
        }
        
        SpinBox {
            id: autoScrollSpin
            Kirigami.FormData.label: "Intervalo de auto-scroll (segundos):"
            from: 2
            to: 60
        }
        
        SpinBox {
            id: maxEventsSpin
            Kirigami.FormData.label: "Eventos visibles (máximo):"
            from: 1
            to: 100
        }
    }
}
