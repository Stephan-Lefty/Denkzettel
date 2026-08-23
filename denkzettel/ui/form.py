#!/usr/bin/env python3
"""
Denkzettel: das Formular für eine Notiz.

Wird an zwei Stellen gebraucht - direkt nach dem Diktieren im
Erfassen-Fenster und später beim Nachbearbeiten im Notizbuch. Deshalb
einmal gebaut und zweimal benutzt.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from PyQt6 import QtCore, QtGui, QtWidgets

from .. import config, store
from . import common


class NotizFormular(QtWidgets.QWidget):
    """Text, Tags und Wiedervorlage - alles korrigierbar."""

    def __init__(self, cfg, eltern=None):
        super().__init__(eltern)
        self.cfg = cfg
        self._kaestchen: dict[str, QtWidgets.QCheckBox] = {}

        aufbau = QtWidgets.QVBoxLayout(self)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.setSpacing(10)

        # -- Notiztext --
        beschriftung = QtWidgets.QLabel("&Notiz")
        self.text = QtWidgets.QTextEdit()
        self.text.setAcceptRichText(False)
        self.text.setPlaceholderText("Der Gedanke …")
        common.schriftgroesse(self.text, 12)
        self.text.setMinimumHeight(120)
        beschriftung.setBuddy(self.text)
        self.text.setAccessibleName("Notiztext")
        aufbau.addWidget(beschriftung)
        aufbau.addWidget(self.text, 1)

        # -- Tags --
        self.tag_kasten = QtWidgets.QGroupBox("Tags")
        self.tag_raster = QtWidgets.QGridLayout(self.tag_kasten)
        aufbau.addWidget(self.tag_kasten)

        weitere_zeile = QtWidgets.QHBoxLayout()
        weitere_beschriftung = QtWidgets.QLabel("&Weitere:")
        self.weitere = QtWidgets.QLineEdit()
        self.weitere.setPlaceholderText("neue Tags, mit Komma getrennt")
        self.weitere.setAccessibleName("Weitere Tags")
        weitere_beschriftung.setBuddy(self.weitere)
        weitere_zeile.addWidget(weitere_beschriftung)
        weitere_zeile.addWidget(self.weitere, 1)
        aufbau.addLayout(weitere_zeile)

        # -- Wiedervorlage --
        self.wiedervorlage = QtWidgets.QCheckBox("&Wiedervorlage im Kalender")
        self.wiedervorlage.setAccessibleName("Wiedervorlage eintragen")
        aufbau.addWidget(self.wiedervorlage)

        termin_zeile = QtWidgets.QHBoxLayout()
        self.termin = QtWidgets.QDateTimeEdit()
        self.termin.setCalendarPopup(True)
        self.termin.setDisplayFormat("dddd, dd.MM.yyyy  HH:mm")
        self.termin.setAccessibleName("Termin der Wiedervorlage")
        common.schriftgroesse(self.termin, 11)
        termin_zeile.addWidget(self.termin, 1)
        for beschriftung_text, tage in (("Morgen", 1), ("In 3 Tagen", 3),
                                        ("Nächste Woche", 7), ("In 4 Wochen", 28)):
            knopf = QtWidgets.QPushButton(beschriftung_text)
            knopf.setAutoDefault(False)
            knopf.clicked.connect(lambda _, t=tage: self._schnell(t))
            termin_zeile.addWidget(knopf)
        aufbau.addLayout(termin_zeile)

        self.wiedervorlage.toggled.connect(self._umschalten)
        self._umschalten(False)
        self._tags_aufbauen([])

    # -- innere Hilfen ------------------------------------------------

    def _umschalten(self, an: bool) -> None:
        self.termin.setEnabled(an)

    def _schnell(self, tage: int) -> None:
        ziel = (datetime.now() + timedelta(days=tage)).replace(
            hour=9, minute=0, second=0, microsecond=0)
        self.termin.setDateTime(common.datetime_zu_qt(ziel))
        self.wiedervorlage.setChecked(True)

    def _tags_aufbauen(self, zusaetzliche: list[str]) -> None:
        while self.tag_raster.count():
            teil = self.tag_raster.takeAt(0)
            if teil.widget():
                teil.widget().deleteLater()
        self._kaestchen.clear()

        namen = config.bekannte_tags(self.cfg)
        vorhanden = {n.lower() for n in namen}
        namen += [t for t in zusaetzliche if t.lower() not in vorhanden]
        if not namen:
            self.tag_kasten.setVisible(False)
            return
        self.tag_kasten.setVisible(True)
        for i, name in enumerate(namen):
            kaestchen = QtWidgets.QCheckBox(name)
            kaestchen.setAccessibleName(f"Tag {name}")
            self.tag_raster.addWidget(kaestchen, i // 3, i % 3)
            self._kaestchen[name.lower()] = kaestchen

    # -- außen benutzt ------------------------------------------------

    def fuellen(self, text: str, tags: list[str],
                faellig: datetime | None) -> None:
        self.text.setPlainText(text)
        self._tags_aufbauen(tags)
        gesetzt = {t.lower() for t in tags}
        for klein, kaestchen in self._kaestchen.items():
            kaestchen.setChecked(klein in gesetzt)
        self.weitere.clear()
        self.wiedervorlage.setChecked(faellig is not None)
        self.termin.setDateTime(common.datetime_zu_qt(
            faellig or (datetime.now() + timedelta(days=1)).replace(
                hour=9, minute=0, second=0, microsecond=0)))

    def aus_notiz(self, notiz: store.Notiz) -> None:
        self.fuellen(notiz.text, notiz.tags, notiz.faellig)

    def gewaehlte_tags(self) -> list[str]:
        tags = [kaestchen.text() for kaestchen in self._kaestchen.values()
                if kaestchen.isChecked()]
        for roh in self.weitere.text().split(","):
            roh = roh.strip()
            if roh and roh.lower() not in {t.lower() for t in tags}:
                tags.append(roh)
        return tags

    def gewaehlter_termin(self) -> datetime | None:
        if not self.wiedervorlage.isChecked():
            return None
        return common.qt_zu_datetime(self.termin.dateTime())

    def notiztext(self) -> str:
        return self.text.toPlainText().strip()

    def in_notiz(self, notiz: store.Notiz) -> store.Notiz:
        notiz.text = self.notiztext()
        notiz.tags = self.gewaehlte_tags()
        notiz.faellig = self.gewaehlter_termin()
        return notiz

    def fokus_auf_text(self) -> None:
        self.text.setFocus()
        zeiger = self.text.textCursor()
        zeiger.movePosition(QtGui.QTextCursor.MoveOperation.End)
        self.text.setTextCursor(zeiger)
