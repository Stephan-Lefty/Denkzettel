#!/usr/bin/env python3
"""
Denkzettel: das Erfassen-Fenster.

Öffnet sich auf Tastendruck und nimmt **sofort** auf - man soll sprechen
können, ohne vorher irgendwo hinklicken zu müssen. Danach zeigt es, was
verstanden wurde, und lässt es korrigieren, bevor gespeichert wird.

Die Anzeige des Aussteuerungspegels ist kein Zierrat: Ein stummes
Mikrofon fällt sonst erst auf, wenn der Gedanke schon weg ist.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

from .. import audio, calendar_sync, config, store, stt, textparser
from . import common
from .form import NotizFormular

AUFNAHME = "aufnahme"
ERKENNUNG = "erkennung"
BEARBEITEN = "bearbeiten"

STIL_WARNUNG = "color: #b35c00; font-weight: bold;"
STIL_HINWEIS = "color: #444;"


class ErfassenFenster(QtWidgets.QDialog):
    def __init__(self, cfg, speicher: store.Speicher, eltern=None):
        super().__init__(eltern)
        self.cfg = cfg
        self.speicher = speicher
        self.phase = AUFNAHME
        self.aufnahme: audio.Aufnahme | None = None
        self.wav: Path | None = None
        self._arbeit: common.Arbeit | None = None
        self._hoechster_pegel = 0.0
        self._anhaengen = False
        self._rohtext = ""

        self.setWindowTitle("Denkzettel – Aufnahme läuft")
        self.setWindowIcon(common.programmsymbol())
        self.resize(720, 600)
        self._aufbauen()

        bereit, meldung = stt.bereit(cfg)
        if not bereit:
            QtCore.QTimer.singleShot(0, lambda: self._abbruch_mit_meldung(meldung))
            return
        QtCore.QTimer.singleShot(0, self._aufnahme_starten)

    # -- Aufbau -------------------------------------------------------

    def _aufbauen(self) -> None:
        aufbau = QtWidgets.QVBoxLayout(self)
        aufbau.setSpacing(12)

        self.status = QtWidgets.QLabel("Aufnahme wird gestartet …")
        common.schriftgroesse(self.status, 16, fett=True)
        self.status.setAccessibleName("Zustand")
        aufbau.addWidget(self.status)

        self.hinweis = QtWidgets.QLabel(common.mikrofon_text(self.cfg))
        self.hinweis.setStyleSheet(STIL_HINWEIS)
        self.hinweis.setWordWrap(True)
        aufbau.addWidget(self.hinweis)

        pegel_zeile = QtWidgets.QHBoxLayout()
        self.pegel = QtWidgets.QProgressBar()
        self.pegel.setRange(0, 100)
        self.pegel.setTextVisible(False)
        self.pegel.setFixedHeight(22)
        self.pegel.setAccessibleName("Aussteuerung")
        self.uhr = QtWidgets.QLabel("0:00")
        common.schriftgroesse(self.uhr, 14)
        pegel_zeile.addWidget(self.pegel, 1)
        pegel_zeile.addWidget(self.uhr)
        self.pegel_zeile_widget = QtWidgets.QWidget()
        self.pegel_zeile_widget.setLayout(pegel_zeile)
        aufbau.addWidget(self.pegel_zeile_widget)

        self.formular = NotizFormular(self.cfg)
        self.formular.setVisible(False)
        aufbau.addWidget(self.formular, 1)

        knoepfe = QtWidgets.QHBoxLayout()
        self.knopf_weiter = QtWidgets.QPushButton("&Weiter diktieren")
        self.knopf_weiter.setVisible(False)
        self.knopf_weiter.setAutoDefault(False)
        self.knopf_weiter.clicked.connect(self._weiter_diktieren)

        self.knopf_abbruch = QtWidgets.QPushButton("Abbre&chen")
        self.knopf_abbruch.setAutoDefault(False)
        self.knopf_abbruch.clicked.connect(self.reject)

        self.knopf_haupt = QtWidgets.QPushButton("&Stopp und auswerten")
        self.knopf_haupt.setDefault(True)
        common.schriftgroesse(self.knopf_haupt, 12, fett=True)
        self.knopf_haupt.setMinimumHeight(44)
        self.knopf_haupt.clicked.connect(self._hauptknopf)

        knoepfe.addWidget(self.knopf_weiter)
        knoepfe.addStretch(1)
        knoepfe.addWidget(self.knopf_abbruch)
        knoepfe.addWidget(self.knopf_haupt)
        aufbau.addLayout(knoepfe)

        self.takt = QtCore.QTimer(self)
        self.takt.setInterval(100)
        self.takt.timeout.connect(self._takt)

        # Leertaste stoppt die Aufnahme - ohne die Maus zu suchen.
        self._taste_leer = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Space), self)
        self._taste_leer.activated.connect(self._leertaste)
        self._taste_speichern = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self._taste_speichern.activated.connect(self._hauptknopf)

    # -- Aufnahme -----------------------------------------------------

    def _aufnahme_starten(self) -> None:
        stempel = datetime.now().strftime("%Y%m%d-%H%M%S")
        ziel = config.AUFNAHME_DIR / f"denkzettel-{stempel}.wav"
        self.aufnahme = audio.Aufnahme(
            ziel,
            geraet=config.wert(self.cfg, "aufnahme", "geraet"),
            hoechstdauer=config.zahl(self.cfg, "aufnahme", "hoechstdauer_sekunden", 300))
        try:
            self.aufnahme.starten()
        except (RuntimeError, OSError) as e:
            self._abbruch_mit_meldung(str(e))
            return

        self._hoechster_pegel = 0.0
        self.phase = AUFNAHME
        self.status.setText("Sprich jetzt.")
        self.hinweis.setText(self.aufnahme.hinweis or common.mikrofon_text(self.cfg))
        self.hinweis.setStyleSheet(STIL_WARNUNG if self.aufnahme.hinweis else STIL_HINWEIS)
        self.knopf_haupt.setText("&Stopp und auswerten")
        self.knopf_haupt.setEnabled(True)
        self.pegel_zeile_widget.setVisible(True)
        self.formular.setVisible(False)
        self.knopf_weiter.setVisible(False)
        self.setWindowTitle("Denkzettel – Aufnahme läuft")
        self.takt.start()

    def _takt(self) -> None:
        if self.aufnahme is None:
            return
        pegel = self.aufnahme.pegel()
        self._hoechster_pegel = max(self._hoechster_pegel, pegel)
        self.pegel.setValue(int(pegel * 100))
        dauer = self.aufnahme.dauer
        self.uhr.setText(f"{int(dauer) // 60}:{int(dauer) % 60:02d}")

        if dauer > 3 and self._hoechster_pegel <= 0.01:
            self.hinweis.setText("Vom Mikrofon kommt kein Ton. Stimmt die "
                                 "Auswahl unter Einstellungen?")
            self.hinweis.setStyleSheet(STIL_WARNUNG)

        if not self.aufnahme.laeuft:
            self.hinweis.setText("Die Aufnahme wurde vom System beendet.")
            self.hinweis.setStyleSheet(STIL_WARNUNG)
            self._stoppen()
        elif self.aufnahme.ueberzogen:
            self.hinweis.setText(
                f"Höchstdauer von "
                f"{config.zahl(self.cfg, 'aufnahme', 'hoechstdauer_sekunden', 300) // 60} "
                f"Minuten erreicht - Aufnahme beendet.")
            self.hinweis.setStyleSheet(STIL_WARNUNG)
            self._stoppen()

    def _stoppen(self) -> None:
        if self.aufnahme is None or self.phase != AUFNAHME:
            return
        self.takt.stop()
        self.wav = self.aufnahme.beenden()
        self.phase = ERKENNUNG
        self.pegel.setRange(0, 0)            # unbestimmter Fortschritt
        self.status.setText("Wird ausgewertet …")
        self.setWindowTitle("Denkzettel – wird ausgewertet")
        self.knopf_haupt.setEnabled(False)

        if not audio.hat_ton(self.wav):
            self._nichts_gehoert()
            return

        wav = self.wav
        self._arbeit = common.Arbeit(lambda: stt.transkribieren(wav, self.cfg), self)
        self._arbeit.fertig.connect(self._erkannt)
        self._arbeit.fehler.connect(self._erkennung_fehlgeschlagen)
        self._arbeit.start()

    def _nichts_gehoert(self) -> None:
        self.pegel.setRange(0, 100)
        self.pegel.setValue(0)
        self.status.setText("Es war nichts zu hören.")
        self.hinweis.setText(
            f"Die Aufnahme ist stumm. Aufgenommen wurde über: "
            f"{common.mikrofon_text(self.cfg)}. Mit „Weiter diktieren“ noch "
            f"einmal versuchen oder unter „Einstellungen“ ein anderes "
            f"Mikrofon wählen.")
        self.hinweis.setStyleSheet(STIL_WARNUNG)
        self._in_bearbeiten("", behalten=True)

    def _erkennung_fehlgeschlagen(self, meldung: str) -> None:
        self.pegel.setRange(0, 100)
        self.pegel.setValue(0)
        self.status.setText("Die Spracherkennung ist gescheitert.")
        self.hinweis.setText(meldung)
        self.hinweis.setStyleSheet(STIL_WARNUNG)
        self._in_bearbeiten("", behalten=True)

    def _erkannt(self, text: object) -> None:
        rohtext = str(text).strip()
        self.pegel.setRange(0, 100)
        if not rohtext:
            self._nichts_gehoert()
            return
        self.status.setText("Verstanden – bitte prüfen.")
        self.hinweis.setText(common.mikrofon_text(self.cfg))
        self.hinweis.setStyleSheet(STIL_HINWEIS)
        self._in_bearbeiten(rohtext)

    def _in_bearbeiten(self, rohtext: str, behalten: bool = False) -> None:
        """Erkannten Text auswerten und ins Formular übernehmen."""
        self.phase = BEARBEITEN
        self.setWindowTitle("Denkzettel – prüfen und speichern")
        self.pegel_zeile_widget.setVisible(False)
        self.formular.setVisible(True)
        self.knopf_weiter.setVisible(True)
        self.knopf_haupt.setText("&Speichern")
        self.knopf_haupt.setEnabled(True)

        if rohtext:
            ausgewertet = textparser.auswerten(
                rohtext, config.bekannte_tags(self.cfg),
                standardzeit=config.wert(self.cfg, "kalender", "standardzeit", "09:00"))
        else:
            ausgewertet = textparser.Auswertung(text="")

        # Beim Weiterdiktieren bleibt stehen, was schon da ist - sonst wäre
        # der erste Teil des Gedankens weg.
        if self._anhaengen:
            alt_text = self.formular.notiztext()
            alt_tags = self.formular.gewaehlte_tags()
            alt_termin = self.formular.gewaehlter_termin()
        else:
            alt_text, alt_tags, alt_termin = "", [], None

        neuer_text = " ".join(t for t in (alt_text, ausgewertet.text) if t).strip()
        tags = alt_tags + [t for t in ausgewertet.tags
                           if t.lower() not in {a.lower() for a in alt_tags}]
        self._rohtext = " ".join(t for t in (self._rohtext, rohtext) if t).strip()
        self.formular.fuellen(neuer_text, tags, ausgewertet.faellig or alt_termin)
        self._anhaengen = False
        self.formular.fokus_auf_text()

        if ausgewertet.entfernt:
            self.hinweis.setText("Aus dem Diktat übernommen: "
                                 + " | ".join(ausgewertet.entfernt))
            self.hinweis.setStyleSheet(STIL_HINWEIS)

    # -- Knöpfe -------------------------------------------------------

    def _leertaste(self) -> None:
        # Nur während der Aufnahme - danach schreibt man ja Text.
        if self.phase == AUFNAHME:
            self._stoppen()

    def _hauptknopf(self) -> None:
        if self.phase == AUFNAHME:
            self._stoppen()
        elif self.phase == BEARBEITEN:
            self._speichern()

    def _weiter_diktieren(self) -> None:
        if self.phase != BEARBEITEN:
            return
        self._anhaengen = True
        self._aufnahme_starten()

    def _speichern(self) -> None:
        text = self.formular.notiztext()
        if not text:
            common.fehler_zeigen(self, "Leere Notiz",
                                 "Es steht kein Text in der Notiz.")
            return

        behalten = config.wert(self.cfg, "aufnahme", "aufnahmen_behalten", "ja") == "ja"
        if not behalten and self.wav:
            self.wav.unlink(missing_ok=True)

        notiz = store.Notiz(text=text, rohtext=self._rohtext,
                            audio=str(self.wav) if (self.wav and behalten) else None,
                            tags=self.formular.gewaehlte_tags(),
                            faellig=self.formular.gewaehlter_termin())
        if notiz.faellig:
            notiz.kalender_status = store.OFFEN
        self.speicher.anlegen(notiz)

        if config.tags_merken(self.cfg, notiz.tags):
            config.speichern(self.cfg)

        if notiz.faellig is None:
            self.accept()
            return

        self.knopf_haupt.setEnabled(False)
        self.knopf_weiter.setEnabled(False)
        self.status.setText("Gespeichert. Termin wird eingetragen …")
        self._arbeit = common.Arbeit(
            lambda: calendar_sync.eintragen(self.cfg, notiz), self)
        self._arbeit.fertig.connect(lambda e: self._kalender_fertig(notiz, e))
        self._arbeit.fehler.connect(lambda m: self._kalender_fertig(
            notiz, (store.FEHLER, m)))
        self._arbeit.start()

    def _kalender_fertig(self, notiz: store.Notiz, ergebnis) -> None:
        # Läuft im Hauptthread (Qt-Signal), deshalb hier und nicht im
        # Hintergrund-Thread: die Sammel-Datei braucht die Datenbank, und
        # sqlite3-Verbindungen dürfen nicht threadübergreifend benutzt werden.
        status, meldung = ergebnis
        self.speicher.kalender_setzen(notiz.id, status, notiz.kalender_ziel,
                                      notiz.kalender_uid)
        if status == store.ICS:
            calendar_sync.sammelkalender_schreiben(self.cfg, self.speicher)
        if status == store.CALDAV:
            self.status.setText("Gespeichert und im Kalender eingetragen.")
            QtCore.QTimer.singleShot(900, self.accept)
            return
        # Die Notiz ist sicher gespeichert - nur der Termin hakt. Das muss
        # man sehen, sonst wartet man auf eine Erinnerung, die nie kommt.
        common.fehler_zeigen(self, "Termin nicht im Kalender", meldung)
        self.accept()

    # -- Fenster ------------------------------------------------------

    def _abbruch_mit_meldung(self, meldung: str) -> None:
        common.fehler_zeigen(self, "Denkzettel", meldung)
        self.reject()

    def reject(self) -> None:                 # noqa: D102 - Qt-Vorgabe
        self.takt.stop()
        if self.aufnahme is not None and self.aufnahme.laeuft:
            self.aufnahme.abbrechen()
        super().reject()

    def closeEvent(self, ereignis) -> None:   # noqa: N802 - Qt-Vorgabe
        self.takt.stop()
        if self._arbeit is not None and self._arbeit.isRunning():
            self._arbeit.wait(2000)
        super().closeEvent(ereignis)
