#!/usr/bin/env python3
"""
Denkzettel: Mikrofon auswählen und aufnehmen.

Aufgenommen wird über `parecord` (PipeWire/PulseAudio), ersatzweise über
`arecord` (ALSA) - beides ist auf Debian wie auf Arch vorhanden und
braucht keine Python-Audiobibliothek.

Zwei Dinge sind hier bewusst gelöst, weil sie sonst still schiefgehen:

1. **Gerätewahl.** Viele Rechner haben ein eingebautes Mikrofon UND das
   Mikrofon einer Webcam. Welches gemeint ist, kann das Programm nicht
   raten, also wird es ausgewählt und gemerkt.
2. **Verschwundenes Gerät.** Eine Webcam wird abgezogen. Dann ist die
   gemerkte Quelle weg. Denkzettel nimmt dann über die Standardquelle auf
   und **sagt das**, statt eine stumme Datei zu erzeugen.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ABTASTRATE = 16000          # whisper.cpp erwartet 16 kHz mono
KANAELE = 1
BREITE = 2                  # s16le


@dataclass
class Quelle:
    name: str               # technischer Name, kommt in die Konfiguration
    beschreibung: str       # was PulseAudio anzeigt
    art: str                # Webcam / Eingebaut / USB / Bluetooth / Unbekannt

    @property
    def anzeige(self) -> str:
        """Name, an dem man das Gerät auch wiedererkennt.

        Nötig, weil manche Geräte sich nutzlos beschreiben: Stephans
        UGREEN-Webcam meldet sich als „EEM Gadget Mono“. Der Produktname
        steckt dann nur noch in der technischen Kennung.
        """
        produkt = produkt_aus_name(self.name)
        if produkt and produkt.lower() not in self.beschreibung.lower():
            return f"{produkt} – {self.beschreibung} ({self.art})"
        return f"{self.beschreibung} ({self.art})"


def produkt_aus_name(name: str) -> str:
    """Aus `alsa_input.usb-UGREEN_UGREEN_AI_Camera_CM930_4K_2025102215-02...`
    wird `UGREEN AI Camera CM930 4K`."""
    kern = name.split(".", 1)[-1]
    if not kern.startswith("usb-"):
        return ""
    kern = kern[4:].split("-", 1)[0]
    teile = [t for t in kern.split("_") if t]
    while teile and teile[-1].isdigit():      # Seriennummer weg
        teile.pop()
    entdoppelt: list[str] = []                # „UGREEN UGREEN“ -> „UGREEN“
    for t in teile:
        if not entdoppelt or entdoppelt[-1].lower() != t.lower():
            entdoppelt.append(t)
    return " ".join(entdoppelt)


def _pactl(*args: str) -> str:
    """pactl aufrufen - mit LC_ALL=C, sonst heißen die Felder auf einem
    deutschen System anders und die Auswertung findet nichts."""
    umgebung = dict(os.environ, LC_ALL="C")
    try:
        aus = subprocess.run(["pactl", *args], capture_output=True, text=True,
                             timeout=10, env=umgebung)
    except (OSError, subprocess.SubprocessError):
        return ""
    return aus.stdout if aus.returncode == 0 else ""


def _art_raten(name: str, beschreibung: str) -> str:
    n = f"{name} {beschreibung}".lower()
    if "bluez" in n or "bluetooth" in n:
        return "Bluetooth"
    if any(w in n for w in ("camera", "webcam", "cam_", "cm930", "video")):
        return "Webcam"
    if name.startswith("alsa_input.pci") or "internal" in n or "built-in" in n:
        return "Eingebaut"
    if "usb" in n:
        return "USB-Gerät"
    return "Unbekannt"


def quellen() -> list[Quelle]:
    """Alle echten Aufnahmequellen (ohne die Monitor-Quellen der Ausgänge)."""
    text = _pactl("list", "sources")
    gefunden: list[Quelle] = []
    name = beschreibung = ""
    ist_monitor = False
    for zeile in text.splitlines():
        z = zeile.strip()
        if z.startswith("Source #"):
            name = beschreibung = ""
            ist_monitor = False
        elif z.startswith("Name:"):
            name = z[5:].strip()
        elif z.startswith("Description:"):
            beschreibung = z[12:].strip()
        elif z.startswith("Monitor of Sink:"):
            ist_monitor = z[16:].strip() not in ("n/a", "")
            if name and not ist_monitor and beschreibung:
                gefunden.append(Quelle(name, beschreibung, _art_raten(name, beschreibung)))
                name = ""
    return gefunden


def standardquelle() -> str:
    return _pactl("get-default-source").strip()


def vorhanden(name: str) -> bool:
    return any(q.name == name for q in quellen())


def beschreibung_zu(name: str) -> str:
    for q in quellen():
        if q.name == name:
            return q.anzeige
    return name


def _befehl(ziel: Path, geraet: str) -> tuple[list[str], str]:
    if shutil.which("parecord"):
        b = ["parecord", f"--rate={ABTASTRATE}", f"--channels={KANAELE}",
             "--format=s16le", "--file-format=wav"]
        if geraet:
            b.append(f"--device={geraet}")
        return b + [str(ziel)], "parecord"
    if shutil.which("arecord"):
        b = ["arecord", "-q", "-f", "S16_LE", "-r", str(ABTASTRATE),
             "-c", str(KANAELE), "-t", "wav"]
        if geraet:
            b += ["-D", geraet]
        return b + [str(ziel)], "arecord"
    raise RuntimeError("Weder parecord noch arecord gefunden - bitte "
                       "pulseaudio-utils bzw. alsa-utils installieren.")


class Aufnahme:
    """Eine laufende Aufnahme in eine WAV-Datei."""

    def __init__(self, ziel: Path, geraet: str = "", hoechstdauer: int = 300):
        self.ziel = ziel
        self.hoechstdauer = hoechstdauer
        self.hinweis = ""            # sichtbare Meldung, falls etwas abwich
        self._proc: subprocess.Popen | None = None
        self._start = 0.0
        self._ende = 0.0

        self.geraet = geraet
        if geraet and not vorhanden(geraet):
            self.hinweis = (f"Das gewählte Mikrofon ist nicht da "
                            f"(„{geraet}“) - aufgenommen wird über die "
                            f"Standardquelle des Systems.")
            self.geraet = ""

    def starten(self) -> None:
        self.ziel.parent.mkdir(parents=True, exist_ok=True)
        befehl, _ = _befehl(self.ziel, self.geraet)
        self._proc = subprocess.Popen(befehl, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.PIPE)
        self._start = time.monotonic()

    @property
    def laeuft(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @property
    def dauer(self) -> float:
        if not self._start:
            return 0.0
        return (self._ende or time.monotonic()) - self._start

    @property
    def ueberzogen(self) -> bool:
        return self.dauer >= self.hoechstdauer

    def pegel(self) -> float:
        """Aussteuerung 0..1 aus dem zuletzt geschriebenen Stück Datei.

        Dient der Anzeige: Der Nutzer soll SEHEN, dass das Mikrofon etwas
        hört - eine stumme Aufnahme fällt sonst erst nach der Erkennung auf.
        """
        try:
            groesse = self.ziel.stat().st_size
        except OSError:
            return 0.0
        if groesse < 44 + 2048:
            return 0.0
        block = min(8192, groesse - 44) // 2 * 2
        try:
            with self.ziel.open("rb") as f:
                f.seek(groesse - block)
                roh = f.read(block)
        except OSError:
            return 0.0
        if len(roh) < 2:
            return 0.0
        werte = np.frombuffer(roh[: len(roh) // 2 * 2], dtype="<i2").astype(np.float32)
        if werte.size == 0:
            return 0.0
        effektiv = float(np.sqrt(np.mean(werte * werte))) / 32768.0
        if effektiv <= 0.0005:
            return 0.0
        # logarithmisch, damit leise Sprache sichtbar ausschlägt
        db = 20 * np.log10(effektiv)
        return float(min(1.0, max(0.0, (db + 55) / 55)))

    def beenden(self) -> Path:
        """Aufnahme sauber stoppen und die WAV-Datei zurückgeben."""
        if self._proc is not None and self._proc.poll() is None:
            # SIGINT, nicht SIGKILL: nur dann schreibt parecord/arecord die
            # Länge in den WAV-Kopf zurück.
            self._proc.send_signal(signal.SIGINT)
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=5)
        self._ende = time.monotonic()
        wav_reparieren(self.ziel)
        return self.ziel

    def abbrechen(self) -> None:
        self.beenden()
        self.ziel.unlink(missing_ok=True)


def wav_reparieren(pfad: Path) -> None:
    """Kopf einer abgebrochenen WAV-Datei richtigstellen.

    Wird die Aufnahme hart beendet, steht im Kopf noch die Länge 0 - die
    Datei enthält dann Ton, aber jedes Programm liest sie als leer.
    """
    if not pfad.exists() or pfad.stat().st_size <= 44:
        return
    try:
        with wave.open(str(pfad), "rb") as w:
            if w.getnframes() > 0:
                return
    except (wave.Error, EOFError, OSError):
        pass
    daten = pfad.read_bytes()[44:]
    if not daten:
        return
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(KANAELE)
        w.setsampwidth(BREITE)
        w.setframerate(ABTASTRATE)
        w.writeframes(daten)


def laenge_sekunden(pfad: Path) -> float:
    try:
        with wave.open(str(pfad), "rb") as w:
            return w.getnframes() / float(w.getframerate() or ABTASTRATE)
    except (wave.Error, EOFError, OSError):
        return 0.0


def hat_ton(pfad: Path, schwelle: float = 0.004) -> bool:
    """Ist überhaupt etwas drauf? Trennt Stille von echtem Ton."""
    try:
        with wave.open(str(pfad), "rb") as w:
            roh = w.readframes(min(w.getnframes(), ABTASTRATE * 60))
    except (wave.Error, EOFError, OSError):
        return False
    if not roh:
        return False
    werte = np.frombuffer(roh[: len(roh) // 2 * 2], dtype="<i2").astype(np.float32)
    if werte.size == 0:
        return False
    return float(np.sqrt(np.mean(werte * werte))) / 32768.0 > schwelle
