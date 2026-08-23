#!/usr/bin/env python3
"""Gemeinsames für alle Denkzettel-Fenster."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from PyQt6 import QtCore, QtGui, QtWidgets

from .. import config

WOCHENTAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag",
              "Samstag", "Sonntag")


class Arbeit(QtCore.QThread):
    """Eine Aufgabe im Hintergrund, damit das Fenster nicht einfriert.

    Spracherkennung und Kalenderzugriff dauern Sekunden bis Minuten. Ein
    eingefrorenes Fenster sieht aus wie ein Absturz - gerade wenn man
    gerade erst gesprochen hat und wissen will, ob es geklappt hat.
    """

    fertig = QtCore.pyqtSignal(object)
    fehler = QtCore.pyqtSignal(str)

    def __init__(self, aufgabe: Callable[[], object], eltern=None):
        super().__init__(eltern)
        self._aufgabe = aufgabe

    def run(self) -> None:            # noqa: D102 - Qt-Vorgabe
        try:
            self.fertig.emit(self._aufgabe())
        except Exception as e:        # noqa: BLE001 - Klartext ans Fenster
            self.fehler.emit(str(e))


def anwendung(argv: list[str] | None = None) -> QtWidgets.QApplication:
    """QApplication mit deutschen Datumsformaten und dem Denkzettel-Icon."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(argv or [])
    app.setApplicationName("Denkzettel")
    app.setApplicationDisplayName("Denkzettel")
    app.setDesktopFileName("denkzettel")
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.Language.German,
                                             QtCore.QLocale.Country.Germany))
    symbol = programmsymbol()
    if not symbol.isNull():
        app.setWindowIcon(symbol)
    return app


def programmsymbol() -> QtGui.QIcon:
    symbol = QtGui.QIcon.fromTheme("denkzettel")
    if not symbol.isNull():
        return symbol
    symbol = QtGui.QIcon()
    mitgeliefert = Path(__file__).resolve().parent.parent.parent / "assets"
    for groesse in (512, 256, 128, 64, 48, 32):
        datei = mitgeliefert / f"icon-{groesse}.png"
        if datei.exists():
            symbol.addFile(str(datei))
    return symbol


def datum_deutsch(wert: datetime | None, mit_uhrzeit: bool = True) -> str:
    """„Morgen, 10:00“ statt „24.08.2026 10:00“, wo es hilft."""
    if wert is None:
        return "–"
    heute = datetime.now().date()
    abstand = (wert.date() - heute).days
    if abstand == 0:
        tag = "Heute"
    elif abstand == 1:
        tag = "Morgen"
    elif abstand == -1:
        tag = "Gestern"
    elif 0 < abstand < 7:
        tag = WOCHENTAGE[wert.weekday()]
    else:
        tag = f"{WOCHENTAGE[wert.weekday()][:2]}, {wert:%d.%m.%Y}"
    return f"{tag}, {wert:%H:%M}" if mit_uhrzeit else tag


def qt_zu_datetime(wert: QtCore.QDateTime) -> datetime:
    return wert.toPyDateTime().replace(second=0, microsecond=0)


def datetime_zu_qt(wert: datetime) -> QtCore.QDateTime:
    return QtCore.QDateTime(wert.year, wert.month, wert.day,
                            wert.hour, wert.minute)


def naechster_werktag_neun(tage: int = 1) -> datetime:
    ziel = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    return ziel + timedelta(days=tage)


def fehler_zeigen(eltern, titel: str, text: str) -> None:
    kasten = QtWidgets.QMessageBox(eltern)
    kasten.setIcon(QtWidgets.QMessageBox.Icon.Warning)
    kasten.setWindowTitle(titel)
    kasten.setText(text)
    kasten.exec()


def schriftgroesse(widget: QtWidgets.QWidget, punkte: int,
                   fett: bool = False) -> None:
    schrift = widget.font()
    schrift.setPointSize(punkte)
    schrift.setBold(fett)
    widget.setFont(schrift)


def mikrofon_text(cfg) -> str:
    """Welches Mikrofon ist eingestellt - in Worten."""
    from .. import audio
    gewaehlt = config.wert(cfg, "aufnahme", "geraet")
    if not gewaehlt:
        standard = audio.standardquelle()
        return f"Standardmikrofon des Systems ({audio.beschreibung_zu(standard)})" \
            if standard else "Standardmikrofon des Systems"
    if not audio.vorhanden(gewaehlt):
        return f"{audio.beschreibung_zu(gewaehlt)} – zurzeit NICHT angeschlossen"
    return audio.beschreibung_zu(gewaehlt)
