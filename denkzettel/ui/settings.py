#!/usr/bin/env python3
"""
Denkzettel: Einstellungen.

Das Wichtigste steht bewusst zuerst: **welches Mikrofon**. Viele Rechner
haben ein eingebautes und zusätzlich das einer Webcam, und welches davon
brauchbar ist, hört man nur, wenn man es ausprobiert - dafür gibt es hier
die Probe mit Pegelanzeige.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6 import QtCore, QtWidgets

from .. import audio, calendar_sync, config, stt
from . import common

SYSTEMSTANDARD = "__standard__"


class MikrofonSeite(QtWidgets.QWidget):
    def __init__(self, cfg, eltern=None):
        super().__init__(eltern)
        self.cfg = cfg
        self.probe: audio.Aufnahme | None = None
        self._datei: Path | None = None

        aufbau = QtWidgets.QVBoxLayout(self)
        aufbau.addWidget(QtWidgets.QLabel(
            "Über welches Mikrofon soll Denkzettel aufnehmen?"))

        self.liste = QtWidgets.QListWidget()
        self.liste.setAccessibleName("Mikrofone")
        aufbau.addWidget(self.liste, 1)

        knopfzeile = QtWidgets.QHBoxLayout()
        self.knopf_suchen = QtWidgets.QPushButton("Erneut &suchen")
        self.knopf_suchen.clicked.connect(self.suchen)
        self.knopf_probe = QtWidgets.QPushButton("&Probe aufnehmen")
        self.knopf_probe.setCheckable(True)
        self.knopf_probe.toggled.connect(self._probe_umschalten)
        knopfzeile.addWidget(self.knopf_suchen)
        knopfzeile.addWidget(self.knopf_probe)
        knopfzeile.addStretch(1)
        aufbau.addLayout(knopfzeile)

        self.pegel = QtWidgets.QProgressBar()
        self.pegel.setRange(0, 100)
        self.pegel.setTextVisible(False)
        self.pegel.setAccessibleName("Aussteuerung der Probe")
        aufbau.addWidget(self.pegel)

        self.probe_text = QtWidgets.QLabel(
            "Bei der Probe ein paar Worte sprechen – der Balken muss "
            "ausschlagen. Bleibt er leer, hört dieses Mikrofon nichts.")
        self.probe_text.setWordWrap(True)
        self.probe_text.setStyleSheet("color: #444;")
        aufbau.addWidget(self.probe_text)

        self.takt = QtCore.QTimer(self)
        self.takt.setInterval(100)
        self.takt.timeout.connect(self._takt)
        self.suchen()

    def suchen(self) -> None:
        gewaehlt = config.wert(self.cfg, "aufnahme", "geraet")
        self.liste.clear()

        standard = audio.standardquelle()
        eintrag = QtWidgets.QListWidgetItem(
            f"Standardmikrofon des Systems"
            + (f" – zurzeit: {audio.beschreibung_zu(standard)}" if standard else ""))
        eintrag.setData(QtCore.Qt.ItemDataRole.UserRole, SYSTEMSTANDARD)
        self.liste.addItem(eintrag)

        gefunden = audio.quellen()
        for quelle in gefunden:
            eintrag = QtWidgets.QListWidgetItem(quelle.anzeige)
            eintrag.setData(QtCore.Qt.ItemDataRole.UserRole, quelle.name)
            eintrag.setToolTip(quelle.name)
            self.liste.addItem(eintrag)

        if gewaehlt and not any(q.name == gewaehlt for q in gefunden):
            eintrag = QtWidgets.QListWidgetItem(
                f"{audio.produkt_aus_name(gewaehlt) or gewaehlt} "
                f"– zurzeit nicht angeschlossen")
            eintrag.setData(QtCore.Qt.ItemDataRole.UserRole, gewaehlt)
            self.liste.addItem(eintrag)

        ziel = gewaehlt or SYSTEMSTANDARD
        for i in range(self.liste.count()):
            if self.liste.item(i).data(QtCore.Qt.ItemDataRole.UserRole) == ziel:
                self.liste.setCurrentRow(i)
                break
        else:
            self.liste.setCurrentRow(0)

    def gewaehltes_geraet(self) -> str:
        eintrag = self.liste.currentItem()
        if eintrag is None:
            return ""
        wert = eintrag.data(QtCore.Qt.ItemDataRole.UserRole)
        return "" if wert == SYSTEMSTANDARD else wert

    def _probe_umschalten(self, an: bool) -> None:
        if an:
            self._probe_starten()
        else:
            self._probe_beenden()

    def _probe_starten(self) -> None:
        self._datei = Path(tempfile.gettempdir()) / "denkzettel-probe.wav"
        self.probe = audio.Aufnahme(self._datei, geraet=self.gewaehltes_geraet(),
                                    hoechstdauer=15)
        try:
            self.probe.starten()
        except (RuntimeError, OSError) as e:
            self.probe = None
            self.knopf_probe.setChecked(False)
            common.fehler_zeigen(self, "Probe", str(e))
            return
        self.knopf_probe.setText("Probe &beenden")
        self.probe_text.setText("Probe läuft – sprich ein paar Worte.")
        self.takt.start()

    def _probe_beenden(self) -> None:
        self.takt.stop()
        self.knopf_probe.setText("&Probe aufnehmen")
        if self.probe is None:
            return
        self.probe.abbrechen()
        self.probe = None
        self.pegel.setValue(0)
        self.probe_text.setText(
            "Bei der Probe ein paar Worte sprechen – der Balken muss "
            "ausschlagen. Bleibt er leer, hört dieses Mikrofon nichts.")

    def _takt(self) -> None:
        if self.probe is None:
            return
        self.pegel.setValue(int(self.probe.pegel() * 100))
        if not self.probe.laeuft or self.probe.ueberzogen:
            self.knopf_probe.setChecked(False)

    def hideEvent(self, ereignis) -> None:      # noqa: N802 - Qt-Vorgabe
        self.knopf_probe.setChecked(False)
        super().hideEvent(ereignis)


class ErkennungSeite(QtWidgets.QWidget):
    def __init__(self, cfg, eltern=None):
        super().__init__(eltern)
        self.cfg = cfg
        aufbau = QtWidgets.QFormLayout(self)

        prog = stt.programm(cfg)
        mod = stt.modell(cfg)
        zustand = QtWidgets.QLabel(
            f"Programm: {prog or 'nicht gefunden'}\nModell: {mod or 'nicht gefunden'}")
        zustand.setWordWrap(True)
        aufbau.addRow("Gefunden:", zustand)

        self.programm = QtWidgets.QLineEdit(config.wert(cfg, "erkennung", "programm"))
        self.programm.setPlaceholderText("leer = automatisch suchen")
        aufbau.addRow("&whisper.cpp:", self.programm)

        self.modell = QtWidgets.QLineEdit(config.wert(cfg, "erkennung", "modell"))
        self.modell.setPlaceholderText("leer = größtes Modell im Modellordner")
        aufbau.addRow("&Modelldatei:", self.modell)

        self.threads = QtWidgets.QSpinBox()
        self.threads.setRange(0, 64)
        self.threads.setSpecialValueText("automatisch")
        self.threads.setValue(config.zahl(cfg, "erkennung", "threads", 0))
        aufbau.addRow("&Rechenkerne:", self.threads)

        self.dauer = QtWidgets.QSpinBox()
        self.dauer.setRange(30, 3600)
        self.dauer.setSuffix(" Sekunden")
        self.dauer.setValue(config.zahl(cfg, "aufnahme", "hoechstdauer_sekunden", 300))
        aufbau.addRow("&Längste Aufnahme:", self.dauer)

        self.behalten = QtWidgets.QCheckBox(
            "Tonaufnahmen behalten (zum Nachhören, braucht Platz)")
        self.behalten.setChecked(
            config.wert(cfg, "aufnahme", "aufnahmen_behalten", "ja") == "ja")
        aufbau.addRow("", self.behalten)

    def uebernehmen(self) -> None:
        self.cfg.set("erkennung", "programm", self.programm.text().strip())
        self.cfg.set("erkennung", "modell", self.modell.text().strip())
        self.cfg.set("erkennung", "threads", str(self.threads.value()))
        self.cfg.set("aufnahme", "hoechstdauer_sekunden", str(self.dauer.value()))
        self.cfg.set("aufnahme", "aufnahmen_behalten",
                     "ja" if self.behalten.isChecked() else "nein")


class KalenderSeite(QtWidgets.QWidget):
    MODI = (("auto", "Automatisch – erst der Server, sonst als Datei"),
            ("caldav", "Nur CalDAV-Server (Nextcloud)"),
            ("ics", "Nur Termindateien (.ics)"),
            ("aus", "Keine Kalendereinträge"))

    def __init__(self, cfg, eltern=None):
        super().__init__(eltern)
        self.cfg = cfg
        aufbau = QtWidgets.QFormLayout(self)

        self.modus = QtWidgets.QComboBox()
        for schluessel, text in self.MODI:
            self.modus.addItem(text, schluessel)
        jetzt = config.wert(cfg, "kalender", "modus", "auto")
        self.modus.setCurrentIndex(max(0, [m[0] for m in self.MODI].index(jetzt)
                                       if jetzt in [m[0] for m in self.MODI] else 0))
        aufbau.addRow("&Art:", self.modus)

        self.url = QtWidgets.QLineEdit(config.wert(cfg, "caldav", "url"))
        self.url.setPlaceholderText(
            "https://cloud.example.de/remote.php/dav/calendars/benutzer/persoenlich/")
        aufbau.addRow("&Kalenderadresse:", self.url)

        self.benutzer = QtWidgets.QLineEdit(config.wert(cfg, "caldav", "benutzer"))
        aufbau.addRow("&Benutzer:", self.benutzer)

        self.passwort = QtWidgets.QLineEdit(config.wert(cfg, "caldav", "passwort"))
        self.passwort.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.passwort.setPlaceholderText("bei Nextcloud ein App-Passwort")
        aufbau.addRow("&Passwort:", self.passwort)

        knopfzeile = QtWidgets.QHBoxLayout()
        knopf_pruefen = QtWidgets.QPushButton("Verbindung &prüfen")
        knopf_pruefen.clicked.connect(self._pruefen)
        knopf_suchen = QtWidgets.QPushButton("Kalender &suchen …")
        knopf_suchen.clicked.connect(self._kalender_suchen)
        knopfzeile.addWidget(knopf_pruefen)
        knopfzeile.addWidget(knopf_suchen)
        knopfzeile.addStretch(1)
        aufbau.addRow("", self._zeile(knopfzeile))

        self.rueckmeldung = QtWidgets.QLabel("")
        self.rueckmeldung.setWordWrap(True)
        aufbau.addRow("", self.rueckmeldung)

        self.ics = QtWidgets.QLineEdit(config.wert(cfg, "ics", "verzeichnis"))
        self.ics.setPlaceholderText(str(config.ICS_DIR))
        aufbau.addRow("&Ordner für Termindateien:", self.ics)

        self.zeit = QtWidgets.QTimeEdit()
        self.zeit.setDisplayFormat("HH:mm")
        stunde, _, minute = config.wert(cfg, "kalender", "standardzeit",
                                        "09:00").partition(":")
        self.zeit.setTime(QtCore.QTime(int(stunde or 9), int(minute or 0)))
        aufbau.addRow("&Uhrzeit ohne Angabe:", self.zeit)

        self.termindauer = QtWidgets.QSpinBox()
        self.termindauer.setRange(5, 480)
        self.termindauer.setSuffix(" Minuten")
        self.termindauer.setValue(config.zahl(cfg, "kalender", "dauer_minuten", 30))
        aufbau.addRow("&Dauer des Termins:", self.termindauer)

        self.erinnerung = QtWidgets.QSpinBox()
        self.erinnerung.setRange(0, 1440)
        self.erinnerung.setSuffix(" Minuten vorher")
        self.erinnerung.setSpecialValueText("keine Erinnerung")
        self.erinnerung.setValue(config.zahl(cfg, "kalender", "erinnerung_minuten", 10))
        aufbau.addRow("&Erinnerung:", self.erinnerung)

    @staticmethod
    def _zeile(aufbau) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setLayout(aufbau)
        return widget

    def _in_konfiguration(self) -> None:
        self.cfg.set("caldav", "url", self.url.text().strip())
        self.cfg.set("caldav", "benutzer", self.benutzer.text().strip())
        self.cfg.set("caldav", "passwort", self.passwort.text())

    def _pruefen(self) -> None:
        self._in_konfiguration()
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
        try:
            gut, meldung = calendar_sync.verbindung_pruefen(self.cfg)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        self.rueckmeldung.setText(meldung)
        self.rueckmeldung.setStyleSheet(
            "color: #1a7f1a;" if gut else "color: #b30000;")

    def _kalender_suchen(self) -> None:
        """Aus der Sammel-Adresse die einzelnen Kalender holen."""
        adresse = self.url.text().strip()
        if not adresse:
            self.rueckmeldung.setText(
                "Bitte zuerst eine Adresse eintragen – die Sammel-Adresse "
                "genügt, z. B. https://cloud.example.de/remote.php/dav/"
                "calendars/benutzer/")
            return
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
        try:
            gefunden = calendar_sync.kalender_auflisten(
                adresse, self.benutzer.text().strip(), self.passwort.text())
        except Exception as e:                  # noqa: BLE001
            gefunden = []
            self.rueckmeldung.setText(calendar_sync._klartext(e, adresse))
            self.rueckmeldung.setStyleSheet("color: #b30000;")
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        if not gefunden:
            return
        namen = [f"{name}  ({url})" for url, name in gefunden]
        wahl, gut = QtWidgets.QInputDialog.getItem(
            self, "Kalender wählen", "Welcher Kalender?", namen, 0, False)
        if gut and wahl:
            self.url.setText(gefunden[namen.index(wahl)][0])
            self.rueckmeldung.setText("Adresse übernommen.")
            self.rueckmeldung.setStyleSheet("color: #1a7f1a;")

    def uebernehmen(self) -> None:
        self._in_konfiguration()
        self.cfg.set("kalender", "modus", self.modus.currentData())
        self.cfg.set("ics", "verzeichnis", self.ics.text().strip())
        self.cfg.set("kalender", "standardzeit", self.zeit.time().toString("HH:mm"))
        self.cfg.set("kalender", "dauer_minuten", str(self.termindauer.value()))
        self.cfg.set("kalender", "erinnerung_minuten", str(self.erinnerung.value()))


class EinstellungenDialog(QtWidgets.QDialog):
    def __init__(self, cfg, eltern=None):
        super().__init__(eltern)
        self.cfg = cfg
        self.setWindowTitle("Denkzettel – Einstellungen")
        self.resize(680, 520)

        aufbau = QtWidgets.QVBoxLayout(self)
        self.register = QtWidgets.QTabWidget()
        self.mikrofon = MikrofonSeite(cfg)
        self.erkennung = ErkennungSeite(cfg)
        self.kalender = KalenderSeite(cfg)
        self.register.addTab(self.mikrofon, "&Mikrofon")
        self.register.addTab(self.erkennung, "&Spracherkennung")
        self.register.addTab(self.kalender, "&Kalender")
        aufbau.addWidget(self.register, 1)

        knoepfe = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        knoepfe.button(QtWidgets.QDialogButtonBox.StandardButton.Save).setText("&Speichern")
        knoepfe.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText("Abbre&chen")
        knoepfe.accepted.connect(self._speichern)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)

    def _speichern(self) -> None:
        self.mikrofon.knopf_probe.setChecked(False)
        self.cfg.set("aufnahme", "geraet", self.mikrofon.gewaehltes_geraet())
        self.erkennung.uebernehmen()
        self.kalender.uebernehmen()
        config.speichern(self.cfg)
        self.accept()
