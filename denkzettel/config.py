#!/usr/bin/env python3
"""
Denkzettel: Einstellungen in ~/.config/denkzettel/config.ini.

Bewusst eine INI-Datei und kein TOML: Sie lässt sich mit Bordmitteln
lesen UND schreiben (das Programm speichert die Mikrofon-Auswahl selbst),
und man kann sie im Zweifel mit jedem Texteditor reparieren.
"""
from __future__ import annotations

import configparser
import os
import shlex
import subprocess
from pathlib import Path

APP = "denkzettel"

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / APP
CONFIG_PATH = CONFIG_DIR / "config.ini"
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / APP

AUFNAHME_DIR = DATA_DIR / "aufnahmen"
MODELL_DIR = DATA_DIR / "modelle"
DATENBANK = DATA_DIR / "notizen.db"
ICS_DIR = DATA_DIR / "kalender"
PROTOKOLL = Path.home() / ".log" / "denkzettel.log"

STANDARD: dict[str, dict[str, str]] = {
    "aufnahme": {
        # Leer = Standardquelle des Systems. Sonst der PulseAudio-/PipeWire-
        # Name der Quelle (siehe `denkzettel mikrofone`).
        "geraet": "",
        "hoechstdauer_sekunden": "300",
        "aufnahmen_behalten": "ja",
    },
    "erkennung": {
        "programm": "",          # leer = suchen (whisper-cli, whisper-cpp, main)
        "modell": "",            # leer = neuestes ggml-Modell in MODELL_DIR
        "sprache": "de",
        "threads": "0",          # 0 = halbe Kernanzahl
    },
    "notizen": {
        "bekannte_tags": "privat, beruflich, DialOS, Idee, Einkauf",
    },
    "kalender": {
        "modus": "auto",         # auto | caldav | ics | aus
        "standardzeit": "09:00",
        "dauer_minuten": "30",
        "erinnerung_minuten": "10",
        "titel_zeichen": "60",
    },
    "caldav": {
        "url": "",
        "benutzer": "",
        "passwort": "",
        "passwort_befehl": "",   # z.B. secret-tool lookup dienst denkzettel
    },
    "ics": {
        "verzeichnis": "",       # leer = DATA_DIR/kalender
    },
}


def verzeichnisse_anlegen() -> None:
    for p in (CONFIG_DIR, DATA_DIR, AUFNAHME_DIR, MODELL_DIR, PROTOKOLL.parent):
        p.mkdir(parents=True, exist_ok=True)


def laden() -> configparser.ConfigParser:
    """Konfiguration lesen, fehlende Werte aus STANDARD ergänzen."""
    # Ohne Interpolation: Passwörter dürfen ein %-Zeichen enthalten.
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read_dict(STANDARD)
    if CONFIG_PATH.exists():
        cfg.read(CONFIG_PATH, encoding="utf-8")
    return cfg


def speichern(cfg: configparser.ConfigParser) -> None:
    verzeichnisse_anlegen()
    tmp = CONFIG_PATH.with_suffix(".ini.neu")
    with tmp.open("w", encoding="utf-8") as f:
        f.write("# Einstellungen für Denkzettel.\n"
                "# Wird auch vom Programm geschrieben - Kommentare können dabei\n"
                "# verloren gehen.\n\n")
        cfg.write(f)
    tmp.replace(CONFIG_PATH)
    # Enthält womöglich ein Klartext-Passwort für den Kalender.
    CONFIG_PATH.chmod(0o600)


def wert(cfg, abschnitt: str, schluessel: str, standard: str = "") -> str:
    return cfg.get(abschnitt, schluessel, fallback=standard).strip()


def zahl(cfg, abschnitt: str, schluessel: str, standard: int) -> int:
    try:
        return int(wert(cfg, abschnitt, schluessel, str(standard)))
    except ValueError:
        return standard


def bekannte_tags(cfg) -> list[str]:
    roh = wert(cfg, "notizen", "bekannte_tags")
    return [t.strip() for t in roh.split(",") if t.strip()]


def tags_merken(cfg, tags: list[str]) -> bool:
    """Neue Tags in die bekannte Liste aufnehmen. Gibt True bei Änderung."""
    vorhanden = bekannte_tags(cfg)
    klein = {t.lower() for t in vorhanden}
    neu = [t for t in tags if t.lower() not in klein]
    if not neu:
        return False
    cfg.set("notizen", "bekannte_tags", ", ".join(vorhanden + neu))
    return True


def ics_verzeichnis(cfg) -> Path:
    roh = wert(cfg, "ics", "verzeichnis")
    return Path(roh).expanduser() if roh else ICS_DIR


def caldav_passwort(cfg) -> str:
    """Passwort direkt aus der Datei oder aus einem Befehl (Schlüsselbund)."""
    befehl = wert(cfg, "caldav", "passwort_befehl")
    if befehl:
        try:
            aus = subprocess.run(shlex.split(befehl), capture_output=True,
                                 text=True, timeout=15, check=True)
            return aus.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            return ""
    return wert(cfg, "caldav", "passwort")


def caldav_eingerichtet(cfg) -> bool:
    return bool(wert(cfg, "caldav", "url") and wert(cfg, "caldav", "benutzer"))
