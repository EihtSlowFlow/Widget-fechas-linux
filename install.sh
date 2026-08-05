#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Instalador del Sistema de Fechas Académicas para Kubuntu
# ═══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIDGET_ID="org.ramiro.fechas"
PLASMOIDS_DIR="$HOME/.local/share/plasma/plasmoids"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
DATA_DIR="$HOME/.local/share/fechas-academicas"
CONFIG_DIR="$HOME/.config/fechas-academicas"

echo "═══════════════════════════════════════════════"
echo "  📅 Instalador — Fechas Académicas"
echo "═══════════════════════════════════════════════"
echo ""

# ─── 1. Dependencias Python ──────────────────────────────
echo "📦 [1/6] Instalando dependencias Python..."
if command -v apt-get &> /dev/null; then
    echo "   → Detectado sistema basado en Debian/Ubuntu. Usando apt para instalar paquetes del sistema..."
    sudo apt-get update
    sudo apt-get install -y \
        python3-pyqt6 \
        python3-icalendar \
        python3-recurring-ical-events \
        python3-dateutil \
        python3-bs4 \
        python3-lxml \
        python3-requests
else
    echo "   → Usando pip3 para instalar dependencias..."
    pip3 install --user --break-system-packages \
        icalendar>=6.0.0 \
        recurring-ical-events>=3.0.0 \
        python-dateutil>=2.9.0 \
        beautifulsoup4>=4.12.0 \
        lxml>=5.0.0 \
        2>/dev/null || pip3 install --user \
        icalendar>=6.0.0 \
        recurring-ical-events>=3.0.0 \
        python-dateutil>=2.9.0 \
        beautifulsoup4>=4.12.0 \
        lxml>=5.0.0
fi
echo "   ✓ Dependencias instaladas"

# ─── 2. Directorios de datos ─────────────────────────────
echo "📁 [2/6] Creando directorios de datos..."
mkdir -p "$DATA_DIR"
mkdir -p "$CONFIG_DIR"

# Guardar ruta de instalación para que el widget la descubra
echo "$SCRIPT_DIR" > "$CONFIG_DIR/install_path"

echo "   ✓ $DATA_DIR"
echo "   ✓ $CONFIG_DIR"

# ─── 3. Widget Plasma ────────────────────────────────────
echo "🖥  [3/6] Instalando widget de Plasma..."
mkdir -p "$PLASMOIDS_DIR"

# Remover versión anterior si existe
if [ -d "$PLASMOIDS_DIR/$WIDGET_ID" ]; then
    rm -rf "$PLASMOIDS_DIR/$WIDGET_ID"
    echo "   → Versión anterior eliminada"
fi

# Copiar widget
cp -r "$SCRIPT_DIR/widget/$WIDGET_ID" "$PLASMOIDS_DIR/"
echo "   ✓ Widget instalado en $PLASMOIDS_DIR/$WIDGET_ID"

# ─── 4. Servicios systemd ────────────────────────────────
echo "⚙  [4/6] Configurando servicios systemd..."
mkdir -p "$SYSTEMD_USER_DIR"

# Generar el .service reemplazando el placeholder con la ruta real
sed "s|__INSTALL_DIR__|$SCRIPT_DIR|g" \
    "$SCRIPT_DIR/systemd/fechas-sync.service" \
    > "$SYSTEMD_USER_DIR/fechas-sync.service"

cp "$SCRIPT_DIR/systemd/fechas-sync.timer" "$SYSTEMD_USER_DIR/"
systemctl --user daemon-reload
systemctl --user enable fechas-sync.timer
systemctl --user start fechas-sync.timer
echo "   ✓ Timer habilitado y arrancado"

# ─── 5. Primera sincronización ────────────────────────────
echo "🔄 [5/6] Ejecutando primera sincronización..."
PYTHONPATH="$SCRIPT_DIR" python3 "$SCRIPT_DIR/backend/fechas_sync.py" 2>&1 | tail -5
echo "   ✓ Sincronización completada"

# ─── 6. Verificación ─────────────────────────────────────
echo "✅ [6/6] Verificando instalación..."

# Verificar cache
if [ -f "$DATA_DIR/cache.json" ]; then
    EVENT_COUNT=$(python3 -c "import json; d=json.load(open('$DATA_DIR/cache.json')); print(len(d.get('events',[])))")
    echo "   ✓ Cache creada: $EVENT_COUNT eventos encontrados"
else
    echo "   ⚠ Cache no creada (se creará en la próxima sincronización)"
fi

# Verificar timer
echo "   → Estado del timer:"
systemctl --user list-timers fechas-sync.timer --no-pager 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ ¡Instalación completada!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Próximos pasos:"
echo "  1. Hacé clic derecho en el escritorio → 'Agregar widgets'"
echo "     y buscá 'Fechas Académicas'"
echo "  2. O ejecutá la app principal:"
echo "     python3 $SCRIPT_DIR/app/main.py"
echo ""
echo "  ℹ  El servicio de fondo se ejecuta cada 30 minutos."
echo "  Para ver el estado: systemctl --user status fechas-sync.timer"
echo ""
echo "  ℹ  Para configurar tu feed de Moodle, abrí la app → pestaña Fuentes."
echo ""
