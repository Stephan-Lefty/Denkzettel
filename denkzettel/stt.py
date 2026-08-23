#!/usr/bin/env python3
"""
Denkzettel: Spracherkennung über whisper.cpp.

Alles läuft offline auf dem eigenen Rechner - es geht kein Ton ins Netz.
whisper.cpp statt Vosk, weil hier frei gesprochene Gedanken diktiert
werden und nicht ein fester Satz Befehle: Vosk ist bei freier Rede
deutlich schwächer, und Nachkorrigieren kostet mehr Zeit, als das
größere Modell an Rechenzeit braucht.

Aufgerufen wird das fertige Programm als Unterprozess. Eine Python-
Anbindung würde nur eine weitere Abhängigkeit einführen, die auf Debian
und Arch unterschiedlich heißt.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import config

# Eindeutige Namen von whisper.cpp - die dürfen ungeprüft genommen werden.
PROGRAMME = ("whisper-cli", "whisper-cpp")

# Mehrdeutige Namen. `whisper` ist auf vielen Systemen das ganz andere
# openai-whisper (Python/torch) mit anderen Aufrufparametern - auf Stephans
# Manjaro liegt genau das unter /usr/bin/whisper. Würde Denkzettel das
# blind nehmen, schlüge erst das erste Diktat fehl. `main` heißt das
# Programm in älteren selbst gebauten whisper.cpp-Versionen und könnte
# irgendetwas sein. Beide werden deshalb vorher überprüft.
PROGRAMME_UNSICHER = ("whisper", "main")

EIGENER_BAU = config.DATA_DIR / "whisper.cpp"

MODELL_QUELLE = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"

MODELLE = {
    "turbo": ("ggml-large-v3-turbo-q5_0.bin", "574 MB",
              "beste deutsche Erkennung, ab etwa 4 GB Arbeitsspeicher"),
    "medium": ("ggml-medium-q5_0.bin", "539 MB",
               "sehr gut, etwas langsamer als turbo"),
    "small": ("ggml-small-q5_1.bin", "190 MB",
              "brauchbar, für ältere Rechner"),
    "base": ("ggml-base-q5_1.bin", "60 MB",
             "nur für Notfälle - macht bei freier Rede viele Fehler"),
}

# Was whisper bei Stille oder Geräuschen ausgibt und was keine Notiz ist.
LEERMARKEN = re.compile(
    r"[\[\(](?:BLANK_AUDIO|SILENCE|INAUDIBLE|Musik|Music|MUSIK|Applaus|"
    r"Applause|Gelächter|Laughter|Untertitel[^\]\)]*|Untertitelung[^\]\)]*)"
    r"[\]\)]", re.IGNORECASE)


def ist_whisper_cpp(pfad: Path) -> bool:
    """Ist das wirklich whisper.cpp? Die Hilfeseite verrät es.

    whisper.cpp kennt `-otxt/--output-txt`, openai-whisper dagegen
    `--output_format` mit Unterstrich. Der Aufruf kostet einen Moment,
    passiert aber nur bei mehrdeutigen Namen - und der gefundene Pfad
    wird von install.sh fest eingetragen.
    """
    try:
        lauf = subprocess.run([str(pfad), "-h"], capture_output=True,
                              text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    hilfe = f"{lauf.stdout}{lauf.stderr}".lower()
    return "output-txt" in hilfe or "whisper.cpp" in hilfe


def programm(cfg) -> Path | None:
    """whisper.cpp finden: Konfiguration, eigener Bau, PATH."""
    gesetzt = config.wert(cfg, "erkennung", "programm")
    if gesetzt:
        p = Path(gesetzt).expanduser()
        return p if p.exists() else None

    # Der eigene Bau zuerst - der ist mit Sicherheit der richtige.
    for unter in ("build/bin", "build", "."):
        for name in (*PROGRAMME, *PROGRAMME_UNSICHER):
            p = EIGENER_BAU / unter / name
            if p.exists() and os.access(p, os.X_OK):
                return p

    for name in PROGRAMME:
        gefunden = shutil.which(name)
        if gefunden:
            return Path(gefunden)

    for name in PROGRAMME_UNSICHER:
        gefunden = shutil.which(name)
        if gefunden and ist_whisper_cpp(Path(gefunden)):
            return Path(gefunden)
    return None


def modell(cfg) -> Path | None:
    """Modelldatei finden: Konfiguration, sonst die größte im Modellordner."""
    gesetzt = config.wert(cfg, "erkennung", "modell")
    if gesetzt:
        p = Path(gesetzt).expanduser()
        return p if p.exists() else None
    if not config.MODELL_DIR.exists():
        return None
    kandidaten = sorted(config.MODELL_DIR.glob("ggml-*.bin"),
                        key=lambda p: p.stat().st_size, reverse=True)
    return kandidaten[0] if kandidaten else None


def bereit(cfg) -> tuple[bool, str]:
    """Kann erkannt werden? Sonst mit einem Satz sagen, was fehlt."""
    if programm(cfg) is None:
        return False, ("whisper.cpp ist nicht installiert. Einmalig "
                       "`./install.sh` im Denkzettel-Ordner ausführen.")
    if modell(cfg) is None:
        return False, (f"Kein Spracherkennungs-Modell in {config.MODELL_DIR}. "
                       f"Einmalig `./install.sh --nur-modell` ausführen.")
    return True, ""


def _threads(cfg) -> int:
    gewuenscht = config.zahl(cfg, "erkennung", "threads", 0)
    if gewuenscht > 0:
        return gewuenscht
    return max(1, (os.cpu_count() or 2) // 2)


def saeubern(text: str) -> str:
    """Ausgabe zu einem Fließtext machen."""
    text = LEERMARKEN.sub(" ", text)
    zeilen = [z.strip() for z in text.splitlines()]
    text = " ".join(z for z in zeilen if z)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text


def transkribieren(wav: Path, cfg, zeitlimit: int = 600) -> str:
    """WAV-Datei in Text verwandeln. Wirft RuntimeError mit Klartext."""
    prog = programm(cfg)
    mod = modell(cfg)
    if prog is None or mod is None:
        raise RuntimeError(bereit(cfg)[1])

    with tempfile.TemporaryDirectory(prefix="denkzettel-") as tmp:
        ziel = Path(tmp) / "ergebnis"
        befehl = [
            str(prog),
            "-m", str(mod),
            "-f", str(wav),
            "-l", config.wert(cfg, "erkennung", "sprache", "de"),
            "-t", str(_threads(cfg)),
            "-nt",                      # ohne Zeitmarken
            "-otxt",
            "-of", str(ziel),
        ]
        try:
            lauf = subprocess.run(befehl, capture_output=True, text=True,
                                  timeout=zeitlimit)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Die Spracherkennung hat länger als "
                               f"{zeitlimit // 60} Minuten gebraucht und wurde "
                               f"abgebrochen.") from None
        except OSError as e:
            raise RuntimeError(f"whisper.cpp ließ sich nicht starten: {e}") from None

        if lauf.returncode != 0:
            letzte = (lauf.stderr or lauf.stdout or "").strip().splitlines()
            grund = letzte[-1] if letzte else f"Rückgabewert {lauf.returncode}"
            raise RuntimeError(f"Die Spracherkennung ist fehlgeschlagen: {grund}")

        ergebnis = ziel.with_suffix(".txt")
        if not ergebnis.exists():
            raise RuntimeError("Die Spracherkennung hat keine Textdatei "
                               "geschrieben - vermutlich ist die Aufnahme leer.")
        return saeubern(ergebnis.read_text(encoding="utf-8", errors="replace"))
