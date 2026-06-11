# Fechas Académicas — Widget de Cuenta Regresiva para KDE Plasma

Sistema integral de seguimiento temporal y cuenta regresiva para el escritorio KDE Plasma 6, diseñado para estudiantes universitarios. Compatible con Moodle y el calendario académico de la UNRN.

## 🏗 Arquitectura

```
┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  Moodle iCal     │────▶│  Servicio de Fondo   │────▶│   cache.json     │
│  UNRN Web        │     │  (systemd timer)     │     │   (lectura rápida│
│  Eventos Manual  │     │  cada 30 min         │     │    por widget)   │
└──────────────────┘     └─────────────────────┘     └────────┬─────────┘
                                                              │
                              ┌────────────────────────┐      │
                              │   Widget KDE Plasma 6  │◀─────┘
                              │   (QML nativo)         │
                              └───────────┬────────────┘
                                          │ click
                              ┌───────────▼────────────┐
                              │   App PyQt6            │
                              │   (Centro de Gestión)  │
                              └────────────────────────┘
```

## 📦 Componentes

### 1. Backend (Python)
- **`backend/fechas_sync.py`**: Motor de sincronización ejecutado por systemd
- **`backend/parsers/ical_parser.py`**: Parser de feeds iCalendar (Moodle)
- **`backend/parsers/unrn_scraper.py`**: Scraper del calendario académico UNRN
- **`backend/cache.py`**: Escritura atómica de JSON + detección de novedades
- **`backend/config.py`**: Configuración central (URLs, umbrales, paths)

### 2. Widget KDE Plasma 6 (QML)
- Carrusel horizontal de eventos con auto-scroll
- Semáforo de urgencia (🟢🟡🟠🔴)
- Badge "NUEVO" para eventos descubiertos hoy
- Indicador de última sincronización
- Funciona en panel y escritorio

### 3. Aplicación PyQt6
- Vista Timeline con tarjetas filtables
- Vista Calendario con días resaltados por urgencia
- Gestión de fuentes de datos
- Creación de eventos manuales
- Tema oscuro estilo Breeze

## 🚀 Instalación

### Requisitos
- **KDE Plasma 6** (Kubuntu 24.04+, KDE Neon, etc.)
- **Python 3.10+**
- **PyQt6** (`sudo apt install python3-pyqt6` o `pip3 install PyQt6`)
- Conexión a internet para sincronización

### Instalar

```bash
git clone https://github.com/tu-usuario/fechas-academicas.git
cd fechas-academicas
chmod +x install.sh
./install.sh
```

El instalador:
1. Instala dependencias Python
2. Copia el widget a `~/.local/share/plasma/plasmoids/`
3. Configura el timer de systemd (sincronización cada 30 min)
4. Ejecuta la primera sincronización

## ⚙ Configuración Inicial

### Configurar Moodle (opcional pero recomendado)

Para recibir tus entregas y exámenes de Moodle, necesitás configurar tu feed personal:

1. Ingresá a **Moodle** → **Calendario** → **Importar/Exportar**
2. Seleccioná **"Exportar"** → **"Todos los eventos"** → **"Mes actual"**
3. Hacé clic en **"Obtener URL del calendario"** y copiá la URL completa
4. Abrí la app: `python3 app/main.py`
5. Pestaña **"⚙ Fuentes"** → **"+ Agregar Fuente"**
6. Pegá la URL de Moodle como fuente tipo **iCalendar**

> ⚠ **IMPORTANTE**: La URL de Moodle contiene un token personal de autenticación.
> **No compartas esta URL con nadie** ni la subas a repositorios públicos.

### Calendario UNRN

El scraper del calendario académico UNRN viene habilitado por defecto.
Funciona con la página pública [calendario-academico](https://www.unrn.edu.ar/section/47/calendario-academico.html).

## 📅 Uso

### Widget
- Clic derecho en el escritorio → "Agregar widgets" → buscar "Fechas Académicas"
- El widget muestra un carrusel con las próximas entregas/exámenes
- Clic en el widget abre la vista expandida con todos los eventos

### Aplicación
```bash
python3 app/main.py           # Abrir la app
python3 app/main.py --add-event  # Crear evento directamente
```

### Sincronización manual
```bash
python3 backend/fechas_sync.py          # Sync normal
python3 backend/fechas_sync.py --dry-run # Solo mostrar sin escribir
```

## 📡 Fuentes de datos

| Fuente | Tipo | Descripción |
|--------|------|-------------|
| Moodle | iCal | Entregas, exámenes, eventos de curso (requiere URL personal) |
| Calendario Académico UNRN | Web scraping | Fechas institucionales (turnos, inscripciones) |
| Eventos Manuales | Local | Eventos creados por el usuario |

## 🎨 Semáforo de Urgencia

| Color | Rango | Significado |
|-------|-------|-------------|
| 🟢 `#4CAF50` | +7 días | Tranquilo |
| 🟡 `#FFC107` | 3-7 días | Atención |
| 🟠 `#FF9800` | 1-2 días | Próximo |
| 🔴 `#F44336` | Hoy/vencido | ¡Urgente! |

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Si querés agregar soporte para otra universidad
o mejorar algún aspecto del widget:

1. Hacé un fork del repositorio
2. Creá una rama para tu feature (`git checkout -b feature/mi-mejora`)
3. Hacé commit de tus cambios (`git commit -m 'Agregar mi mejora'`)
4. Hacé push a la rama (`git push origin feature/mi-mejora`)
5. Abrí un Pull Request

## 📄 Licencia

Este proyecto está licenciado bajo la [GNU General Public License v3.0](LICENSE).
