#!/usr/bin/env python3
"""
Acciones rápidas sobre eventos ejecutadas desde la interfaz de usuario.
"""
import sys
import argparse
import logging
from pathlib import Path

# Agregar el directorio padre al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.cache import mark_event_seen

def main():
    parser = argparse.ArgumentParser(description="Acciones sobre eventos")
    subparsers = parser.add_subparsers(dest="action", required=True)
    
    parser_seen = subparsers.add_parser("mark-seen")
    parser_seen.add_argument("event_id", type=str, help="ID del evento a marcar como visto")
    
    args = parser.parse_args()
    
    if args.action == "mark-seen":
        event_id = args.event_id
        # Validar caracteres para mayor seguridad
        if not event_id.replace("-", "").replace("_", "").isalnum():
            print("ID inválido", file=sys.stderr)
            sys.exit(1)
            
        try:
            mark_event_seen(event_id)
            print(f"Evento {event_id} marcado como visto")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
