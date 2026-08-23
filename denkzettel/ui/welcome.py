#!/usr/bin/env python3
"""
Denkzettel: die Einführung beim ersten Start.

Vier Seiten: was das Programm tut, wie man spricht, welches Mikrofon,
welche Tasten. Danach kommt sie nicht mehr von selbst - über
„Hilfe → Einführung“ aber jederzeit wieder.

Die Mikrofon-Auswahl steht bewusst **hier** und nicht im
Installationsskript: Eine Frage, die einmal im Terminal durchläuft, sieht
man nie wieder, und man beantwortet sie, bevor man das Programm kennt.
Hier kann man sie mit dem Pegelbalken gleich ausprobieren.
"""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from .. import config
from . import common
from .settings import MikrofonSeite

STIL_BEISPIEL = """
    background: palette(base); border: 1px solid palette(mid);
    border-radius: 6px; padding: 10px;
"""


def _absatz(text: str) -> QtWidgets.QLabel:
    beschriftung = QtWidgets.QLabel(text)
    beschriftung.setWordWrap(True)
    beschriftung.setTextFormat(QtCore.Qt.TextFormat.RichText)
    return beschriftung


class WillkommenSeite(QtWidgets.QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Willkommen bei Denkzettel")
        self.setSubTitle("Ein Notizbuch, dem man seine Gedanken sagt.")

        aufbau = QtWidgets.QVBoxLayout(self)
        symbol = QtWidgets.QLabel()
        bild = common.programmsymbol().pixmap(96, 96)
        if not bild.isNull():
            symbol.setPixmap(bild)
            symbol.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            aufbau.addWidget(symbol)

        aufbau.addWidget(_absatz(
            "Du drückst <b>Meta + N</b> (die Windows-Taste und N), sprichst "
            "deinen Gedanken, und Denkzettel schreibt ihn auf. Dabei kannst "
            "du gleich mitsagen, <b>wohin</b> er gehört und <b>wann</b> er "
            "dich wieder erinnern soll – der Termin landet im Kalender."))
        aufbau.addWidget(_absatz(
            "Im Notizbuch geht auch <b>Strg + N</b>, und im Startmenü steht "
            "Denkzettel unter <i>Dienstprogramme</i>. Sollte <b>Meta + N</b> "
            "einmal nichts tun, hat die Arbeitsumgebung das Kürzel nicht "
            "übernommen – dann hilft der Menüeintrag oder der Befehl "
            "<tt>denkzettel erfassen</tt>."))
        aufbau.addWidget(_absatz(
            "Die Spracherkennung läuft <b>vollständig auf diesem Rechner</b>. "
            "Es geht kein Ton ins Netz – weder zum Erkennen noch zum "
            "Speichern. Auch ohne Internet funktioniert alles, nur der "
            "Kalendereintrag wird dann nachgereicht, sobald wieder Netz da "
            "ist."))
        aufbau.addWidget(_absatz(
            "Diese Einführung dauert eine Minute. Du kannst sie später "
            "jederzeit noch einmal aufrufen unter "
            "<b>Hilfe → Einführung</b>."))
        aufbau.addStretch(1)


class SprechenSeite(QtWidgets.QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("So sprichst du")
        self.setSubTitle("Erst der Gedanke, dann Tag und Wiedervorlage.")

        aufbau = QtWidgets.QVBoxLayout(self)
        aufbau.addWidget(_absatz(
            "Sprich zuerst ganz normal deinen Gedanken. Am Ende hängst du "
            "an, wohin er gehört und wann er wiederkommen soll:"))

        beispiel = _absatz(
            "<i>„Angebot für Meier nachrechnen, "
            "<b>Tag beruflich</b>, "
            "<b>Wiedervorlage nächsten Montag um zehn Uhr</b>.“</i>")
        beispiel.setStyleSheet(STIL_BEISPIEL)
        aufbau.addWidget(beispiel)

        aufbau.addWidget(_absatz("Daraus macht Denkzettel:"))
        ergebnis = _absatz(
            "<b>Notiz:</b> Angebot für Meier nachrechnen.<br>"
            "<b>Tag:</b> beruflich<br>"
            "<b>Wiedervorlage:</b> Montag, 10:00 Uhr – im Kalender")
        ergebnis.setStyleSheet(STIL_BEISPIEL)
        aufbau.addWidget(ergebnis)

        aufbau.addWidget(_absatz(
            "Die Angaben zu Tag und Wiedervorlage werden aus dem Notiztext "
            "<b>herausgenommen</b> – sie sind ja Anweisung und nicht Inhalt. "
            "Was nicht sicher erkannt wird, bleibt im Text stehen, statt zu "
            "verschwinden."))
        aufbau.addWidget(_absatz(
            "Statt „Tag“ geht auch <b>Schlagwort</b>, <b>Kategorie</b> oder "
            "<b>Stichwort</b>; mehrere mit „und“. Statt „Wiedervorlage“ auch "
            "<b>erinnere mich</b> oder <b>nachfassen</b>. Beim Termin "
            "versteht Denkzettel unter anderem: <i>morgen · übermorgen · in "
            "drei Tagen · in zwei Wochen · nächsten Montag · am Freitag · am "
            "Wochenende · am 15. September · um halb neun · abends</i>."))
        aufbau.addWidget(_absatz(
            "<b>Wichtig:</b> Nichts davon wird ungefragt gespeichert. Nach "
            "dem Sprechen zeigt Denkzettel, was es verstanden hat, und du "
            "kannst alles ändern."))
        aufbau.addStretch(1)


class MikrofonWizardSeite(QtWidgets.QWizardPage):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setTitle("Welches Mikrofon?")
        self.setSubTitle("Probier es gleich aus – der Balken muss ausschlagen.")

        aufbau = QtWidgets.QVBoxLayout(self)
        aufbau.addWidget(_absatz(
            "Viele Rechner haben ein eingebautes Mikrofon <b>und</b> das "
            "einer Webcam. Welches gemeint ist, kann kein Programm raten."))
        self.seite = MikrofonSeite(cfg)
        aufbau.addWidget(self.seite, 1)
        aufbau.addWidget(_absatz(
            "Später änderbar unter <b>Extras → Einstellungen</b>."))

    def validatePage(self) -> bool:            # noqa: N802 - Qt-Vorgabe
        self.seite.knopf_probe.setChecked(False)
        self.cfg.set("aufnahme", "geraet", self.seite.gewaehltes_geraet())
        return True


class TastenSeite(QtWidgets.QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Die Tasten")
        self.setSubTitle("Alles geht mit der Tastatur – die Maus braucht "
                         "man nicht.")

        aufbau = QtWidgets.QVBoxLayout(self)
        aufbau.addWidget(_absatz(
            "<b>Aufnehmen – von überall aus:</b>"))
        aufbau.addWidget(self._tabelle([
            ("Meta + N", "Erfassen-Fenster öffnen, Aufnahme läuft sofort"),
            ("Leertaste", "Aufnahme stoppen und auswerten"),
            ("Strg + S", "Notiz speichern"),
            ("Esc", "abbrechen, nichts wird gespeichert"),
        ]))
        aufbau.addWidget(_absatz("<b>Im Notizbuch:</b>"))
        aufbau.addWidget(self._tabelle([
            ("Strg + N", "neue Notiz diktieren"),
            ("Strg + Umschalt + N", "Notiz tippen statt sprechen"),
            ("Eingabe oder F2", "Notiz bearbeiten"),
            ("Strg + D", "erledigt / wieder offen"),
            ("Entf", "Notiz löschen"),
            ("Strg + F", "suchen"),
        ]))
        aufbau.addWidget(_absatz(
            "<b>Register</b> – das Notizbuch hat je ein Register pro Tag:"))
        aufbau.addWidget(self._tabelle([
            ("Strg + T", "neues Register anlegen"),
            ("Umschalt + F2", "Register umbenennen"),
            ("Strg + Umschalt + W", "Register löschen (Notizen bleiben)"),
            ("Alt + 1 … 9", "Register direkt anspringen"),
        ]))
        aufbau.addWidget(_absatz(
            "Jeder Befehl steht auch im Menü, und <b>F1</b> zeigt diese "
            "Liste jederzeit wieder."))
        aufbau.addStretch(1)

    @staticmethod
    def _tabelle(zeilen: list[tuple[str, str]]) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        raster = QtWidgets.QGridLayout(widget)
        raster.setContentsMargins(12, 2, 0, 6)
        raster.setVerticalSpacing(3)
        for i, (taste, was) in enumerate(zeilen):
            beschriftung = QtWidgets.QLabel(f"<b>{taste}</b>")
            beschriftung.setMinimumWidth(160)
            raster.addWidget(beschriftung, i, 0)
            raster.addWidget(QtWidgets.QLabel(was), i, 1)
        raster.setColumnStretch(1, 1)
        return widget


class SchlussSeite(QtWidgets.QWizardPage):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setTitle("Fertig")
        self.setSubTitle("Zwei Dinge noch, dann kann es losgehen.")

        aufbau = QtWidgets.QVBoxLayout(self)
        aufbau.addWidget(_absatz(
            "<b>Kalender.</b> Ohne weitere Einstellung legt Denkzettel jede "
            "Wiedervorlage als Termindatei ab, die man in Thunderbird als "
            "lokalen Kalender einbinden kann. Wenn du sie stattdessen "
            "direkt in deine Nextcloud schreiben lassen willst – und damit "
            "auch aufs Handy bekommst –, richte das unter "
            "<b>Extras → Einstellungen → Kalender</b> ein. Dort findet "
            "„Kalender suchen …“ die richtige Adresse von selbst."))
        aufbau.addWidget(_absatz(
            "<b>Das erste Diktat.</b> Drück <b>Strg + N</b> und sag "
            "einfach:"))
        beispiel = _absatz(
            "<i>„Denkzettel ausprobiert, Tag privat, "
            "Wiedervorlage morgen um zehn Uhr.“</i>")
        beispiel.setStyleSheet(STIL_BEISPIEL)
        aufbau.addWidget(beispiel)
        aufbau.addWidget(_absatz(
            "Das erste Auswerten dauert etwa eine halbe Minute – dabei wird "
            "das Spracherkennungs-Modell geladen. Das ist normal und "
            "passiert bei jedem Diktat einmal, unabhängig davon, wie lang "
            "du gesprochen hast."))
        aufbau.addStretch(1)

    def validatePage(self) -> bool:            # noqa: N802 - Qt-Vorgabe
        self.cfg.set("start", "eingefuehrt", "ja")
        config.speichern(self.cfg)
        return True


class WillkommenAssistent(QtWidgets.QWizard):
    def __init__(self, cfg, eltern=None):
        super().__init__(eltern)
        self.cfg = cfg
        self.setWindowTitle("Denkzettel – Einführung")
        self.setWindowIcon(common.programmsymbol())
        self.setWizardStyle(QtWidgets.QWizard.WizardStyle.ModernStyle)
        self.setOption(QtWidgets.QWizard.WizardOption.NoBackButtonOnStartPage)
        self.resize(720, 640)

        self.addPage(WillkommenSeite())
        self.addPage(SprechenSeite())
        self.addPage(MikrofonWizardSeite(cfg))
        self.addPage(TastenSeite())
        self.addPage(SchlussSeite(cfg))

        knopf = QtWidgets.QWizard.WizardButton
        self.setButtonText(knopf.NextButton, "&Weiter")
        self.setButtonText(knopf.BackButton, "&Zurück")
        self.setButtonText(knopf.FinishButton, "&Los geht's")
        self.setButtonText(knopf.CancelButton, "Ü&berspringen")


def noetig(cfg) -> bool:
    return config.wert(cfg, "start", "eingefuehrt", "nein").lower() != "ja"


def zeigen(cfg, eltern=None) -> None:
    """Einführung anzeigen. Auch beim Überspringen gilt sie als gesehen -
    sonst kommt sie bei jedem Start wieder und wird zur Belästigung."""
    assistent = WillkommenAssistent(cfg, eltern)
    assistent.exec()
    if noetig(cfg):
        cfg.set("start", "eingefuehrt", "ja")
        config.speichern(cfg)
