#!/usr/bin/env python3
"""
Denkzettel: das Notizbuch.

Sieht aus wie ein Notizbuch mit Registern: „Alle“, „Wiedervorlagen“ und
dann je ein Register pro Tag - privat, beruflich, DialOS und was sonst
noch dazukommt.

**Alles geht mit der Tastatur.** Register anlegen, umbenennen, löschen
und wechseln, ebenso Notizen anlegen, bearbeiten, abhaken und löschen.
Jeder Befehl steht zusätzlich im Menü, damit man ihn wiederfindet, ohne
ihn auswendig zu können. Die Tastenbefehle stehen unter „Hilfe“ (F1).
"""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from .. import calendar_sync, config, store
from . import common
from .form import NotizFormular

ALLE = "alle"
WIEDERVORLAGE = "wiedervorlage"
TAG = "tag"

KALENDER_TEXT = {
    store.OHNE: "",
    store.OFFEN: "wird eingetragen",
    store.CALDAV: "im Kalender",
    store.ICS: "als Datei – noch nicht auf dem Server",
    store.FEHLER: "Fehler",
}


class NotizDialog(QtWidgets.QDialog):
    """Eine Notiz bearbeiten - Text, Tags, Wiedervorlage."""

    def __init__(self, cfg, notiz: store.Notiz, eltern=None):
        super().__init__(eltern)
        self.cfg = cfg
        self.notiz = notiz
        self.setWindowTitle("Notiz bearbeiten")
        self.resize(700, 560)

        aufbau = QtWidgets.QVBoxLayout(self)
        self.formular = NotizFormular(cfg)
        self.formular.aus_notiz(notiz)
        aufbau.addWidget(self.formular, 1)

        if notiz.rohtext and notiz.rohtext != notiz.text:
            roh = QtWidgets.QLabel(f"Diktiert: „{notiz.rohtext}“")
            roh.setWordWrap(True)
            roh.setStyleSheet("color: #666;")
            aufbau.addWidget(roh)

        knoepfe = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        knoepfe.button(QtWidgets.QDialogButtonBox.StandardButton.Save).setText("&Speichern")
        knoepfe.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText("Abbre&chen")
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, self.accept)
        self.formular.fokus_auf_text()

    def uebernehmen(self) -> store.Notiz:
        return self.formular.in_notiz(self.notiz)


class NotizTabelle(QtWidgets.QTableWidget):
    """Liste der Notizen eines Registers."""

    oeffnen = QtCore.pyqtSignal(int)

    SPALTEN = ("Notiz", "Tags", "Wiedervorlage", "Kalender", "Notiert")

    def __init__(self, eltern=None):
        super().__init__(0, len(self.SPALTEN), eltern)
        self.setHorizontalHeaderLabels(self.SPALTEN)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setTextElideMode(QtCore.Qt.TextElideMode.ElideRight)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        kopf = self.horizontalHeader()
        kopf.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(self.SPALTEN)):
            kopf.setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.doubleClicked.connect(self._aktiviert)
        self.setAccessibleName("Notizen")

    def _aktiviert(self, *_) -> None:
        for kennung in self.ausgewaehlte():
            self.oeffnen.emit(kennung)
            return

    def keyPressEvent(self, ereignis) -> None:      # noqa: N802 - Qt-Vorgabe
        if ereignis.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            self._aktiviert()
            return
        super().keyPressEvent(ereignis)

    def setzen(self, notizen: list[store.Notiz]) -> None:
        vorher = self.ausgewaehlte()
        self.setRowCount(len(notizen))
        for zeile, notiz in enumerate(notizen):
            text = " ".join(notiz.text.split())
            felder = (
                text,
                ", ".join(notiz.tags),
                common.datum_deutsch(notiz.faellig) if notiz.faellig else "",
                KALENDER_TEXT.get(notiz.kalender_status, notiz.kalender_status),
                f"{notiz.erstellt:%d.%m.%Y}",
            )
            for spalte, wert in enumerate(felder):
                eintrag = QtWidgets.QTableWidgetItem(wert)
                eintrag.setData(QtCore.Qt.ItemDataRole.UserRole, notiz.id)
                if notiz.erledigt:
                    schrift = eintrag.font()
                    schrift.setStrikeOut(True)
                    eintrag.setFont(schrift)
                    eintrag.setForeground(QtGui.QBrush(QtGui.QColor("#888")))
                if spalte == 0:
                    eintrag.setToolTip(notiz.text)
                self.setItem(zeile, spalte, eintrag)
        if vorher:
            self.auswaehlen(vorher[0])
        elif notizen:
            self.selectRow(0)

    def ausgewaehlte(self) -> list[int]:
        kennungen: list[int] = []
        for zeile in sorted({i.row() for i in self.selectedIndexes()}):
            eintrag = self.item(zeile, 0)
            if eintrag:
                kennungen.append(eintrag.data(QtCore.Qt.ItemDataRole.UserRole))
        return kennungen

    def auswaehlen(self, kennung: int) -> None:
        for zeile in range(self.rowCount()):
            eintrag = self.item(zeile, 0)
            if eintrag and eintrag.data(QtCore.Qt.ItemDataRole.UserRole) == kennung:
                self.selectRow(zeile)
                return


class NotizbuchFenster(QtWidgets.QMainWindow):
    def __init__(self, cfg, speicher: store.Speicher):
        super().__init__()
        self.cfg = cfg
        self.speicher = speicher
        self._register: list[tuple[str, str]] = []     # (Art, Tag-Name)

        self.setWindowTitle("Denkzettel")
        self.setWindowIcon(common.programmsymbol())
        self.resize(980, 640)

        mitte = QtWidgets.QWidget()
        aufbau = QtWidgets.QVBoxLayout(mitte)

        suchzeile = QtWidgets.QHBoxLayout()
        beschriftung = QtWidgets.QLabel("&Suchen:")
        self.suche = QtWidgets.QLineEdit()
        self.suche.setPlaceholderText("im aktuellen Register suchen (Strg+F)")
        self.suche.setClearButtonEnabled(True)
        self.suche.setAccessibleName("Suchen")
        beschriftung.setBuddy(self.suche)
        self.suche.textChanged.connect(self.auffrischen)
        suchzeile.addWidget(beschriftung)
        suchzeile.addWidget(self.suche, 1)
        aufbau.addLayout(suchzeile)

        self.register = QtWidgets.QTabWidget()
        self.register.setDocumentMode(True)
        self.register.setMovable(True)
        self.register.setUsesScrollButtons(True)
        self.register.currentChanged.connect(lambda _: self.auffrischen())
        self.register.tabBarDoubleClicked.connect(lambda _: self.register_umbenennen())
        aufbau.addWidget(self.register, 1)

        self.setCentralWidget(mitte)
        self.setStatusBar(QtWidgets.QStatusBar())

        self._menue_bauen()
        self.register_neu_aufbauen()

    # -- Menü und Tastenbefehle ---------------------------------------

    def _menue_bauen(self) -> None:
        leiste = self.menuBar()

        m_notiz = leiste.addMenu("&Notiz")
        self._aktion(m_notiz, "&Neue Notiz diktieren", "Ctrl+N", self.notiz_diktieren)
        self._aktion(m_notiz, "Notiz &schreiben (ohne Sprache)", "Ctrl+Shift+N",
                     self.notiz_schreiben)
        m_notiz.addSeparator()
        self._aktion(m_notiz, "&Bearbeiten", "F2", self.notiz_bearbeiten)
        self._aktion(m_notiz, "&Erledigt / offen", "Ctrl+D", self.notiz_erledigt)
        self._aktion(m_notiz, "&Löschen", "Del", self.notiz_loeschen)
        m_notiz.addSeparator()
        self._aktion(m_notiz, "S&chließen", "Ctrl+Q", self.close)

        m_reg = leiste.addMenu("&Register")
        self._aktion(m_reg, "&Neues Register (Tag)", "Ctrl+T", self.register_neu)
        self._aktion(m_reg, "&Umbenennen", "Shift+F2", self.register_umbenennen)
        self._aktion(m_reg, "&Löschen", "Ctrl+Shift+W", self.register_loeschen)
        m_reg.addSeparator()
        self._aktion(m_reg, "&Nächstes Register", "Ctrl+PgDown", self.register_weiter)
        self._aktion(m_reg, "&Voriges Register", "Ctrl+PgUp", self.register_zurueck)
        m_reg.addSeparator()
        self._aktion(m_reg, "Tags dieser Notiz &zuweisen", "Ctrl+E",
                     self.notiz_bearbeiten)

        m_extra = leiste.addMenu("&Extras")
        self._aktion(m_extra, "&Suchen", "Ctrl+F", lambda: self.suche.setFocus())
        self._aktion(m_extra, "&Termine nachtragen", "Ctrl+R", self.nachtragen)
        self._aktion(m_extra, "&Einstellungen …", "Ctrl+,", self.einstellungen)

        m_hilfe = leiste.addMenu("&Hilfe")
        self._aktion(m_hilfe, "&Tastenbefehle", "F1", self.tastenbefehle)
        self._aktion(m_hilfe, "Ü&ber Denkzettel", None, self.ueber)

        for nummer in range(1, 10):
            kurz = QtGui.QShortcut(QtGui.QKeySequence(f"Alt+{nummer}"), self)
            kurz.activated.connect(lambda n=nummer: self.register.setCurrentIndex(n - 1))

    def _aktion(self, menue, text: str, taste: str | None, ziel) -> QtGui.QAction:
        aktion = QtGui.QAction(text, self)
        if taste:
            aktion.setShortcut(QtGui.QKeySequence(taste))
            aktion.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        aktion.triggered.connect(ziel)
        menue.addAction(aktion)
        self.addAction(aktion)
        return aktion

    # -- Register -----------------------------------------------------

    def register_neu_aufbauen(self) -> None:
        """Register aus den Tags erzeugen - vorhandene Auswahl merken."""
        vorher = self.aktuelles_register()
        self.register.blockSignals(True)
        while self.register.count():
            self.register.removeTab(0)
        self._register.clear()

        for art, beschriftung in ((ALLE, "Alle"), (WIEDERVORLAGE, "Wiedervorlagen")):
            self.register.addTab(self._neue_tabelle(), beschriftung)
            self._register.append((art, ""))

        gezaehlt = dict(self.speicher.tags(auch_leere=True))
        namen = list(config.bekannte_tags(self.cfg))
        for name in gezaehlt:
            if name.lower() not in {n.lower() for n in namen}:
                namen.append(name)
        for name in namen:
            anzahl = gezaehlt.get(name, 0)
            beschriftung = f"{name} ({anzahl})" if anzahl else name
            self.register.addTab(self._neue_tabelle(), beschriftung)
            self._register.append((TAG, name))

        self.register.blockSignals(False)
        if vorher:
            for i, eintrag in enumerate(self._register):
                if eintrag == vorher:
                    self.register.setCurrentIndex(i)
                    break
        self.auffrischen()

    def _neue_tabelle(self) -> NotizTabelle:
        tabelle = NotizTabelle()
        tabelle.oeffnen.connect(self._notiz_oeffnen)
        return tabelle

    def aktuelles_register(self) -> tuple[str, str] | None:
        i = self.register.currentIndex()
        return self._register[i] if 0 <= i < len(self._register) else None

    def aktuelle_tabelle(self) -> NotizTabelle | None:
        widget = self.register.currentWidget()
        return widget if isinstance(widget, NotizTabelle) else None

    def register_weiter(self) -> None:
        self.register.setCurrentIndex((self.register.currentIndex() + 1)
                                      % max(1, self.register.count()))

    def register_zurueck(self) -> None:
        self.register.setCurrentIndex((self.register.currentIndex() - 1)
                                      % max(1, self.register.count()))

    def register_neu(self) -> None:
        name, gut = QtWidgets.QInputDialog.getText(
            self, "Neues Register", "Name des Registers (Tag):")
        name = name.strip()
        if not gut or not name:
            return
        self.speicher.tag_anlegen(name)
        if config.tags_merken(self.cfg, [name]):
            config.speichern(self.cfg)
        self.register_neu_aufbauen()
        for i, (art, tag) in enumerate(self._register):
            if art == TAG and tag.lower() == name.lower():
                self.register.setCurrentIndex(i)
                break
        self.statusBar().showMessage(f"Register „{name}“ angelegt.", 4000)

    def register_umbenennen(self) -> None:
        aktuell = self.aktuelles_register()
        if not aktuell or aktuell[0] != TAG:
            self.statusBar().showMessage(
                "„Alle“ und „Wiedervorlagen“ lassen sich nicht umbenennen.", 4000)
            return
        alt = aktuell[1]
        neu, gut = QtWidgets.QInputDialog.getText(
            self, "Register umbenennen", "Neuer Name:", text=alt)
        neu = neu.strip()
        if not gut or not neu or neu == alt:
            return
        betroffen = self.speicher.tag_umbenennen(alt, neu)
        namen = [neu if t == alt else t for t in config.bekannte_tags(self.cfg)]
        einmalig: list[str] = []
        for t in namen:
            if t.lower() not in {x.lower() for x in einmalig}:
                einmalig.append(t)
        self.cfg.set("notizen", "bekannte_tags", ", ".join(einmalig))
        config.speichern(self.cfg)
        self.register_neu_aufbauen()
        self.statusBar().showMessage(
            f"„{alt}“ heißt jetzt „{neu}“ – {betroffen} Notizen betroffen.", 5000)

    def register_loeschen(self) -> None:
        aktuell = self.aktuelles_register()
        if not aktuell or aktuell[0] != TAG:
            self.statusBar().showMessage(
                "„Alle“ und „Wiedervorlagen“ lassen sich nicht löschen.", 4000)
            return
        name = aktuell[1]
        anzahl = len(self.speicher.liste(tag=name))
        frage = (f"Register „{name}“ löschen?\n\n"
                 f"Die {anzahl} Notizen darin bleiben erhalten und stehen "
                 f"weiter unter „Alle“ – nur der Tag wird entfernt."
                 if anzahl else f"Register „{name}“ löschen?")
        if QtWidgets.QMessageBox.question(self, "Register löschen", frage) \
                != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self.speicher.tag_loeschen(name)
        namen = [t for t in config.bekannte_tags(self.cfg) if t.lower() != name.lower()]
        self.cfg.set("notizen", "bekannte_tags", ", ".join(namen))
        config.speichern(self.cfg)
        self.register_neu_aufbauen()
        self.statusBar().showMessage(f"Register „{name}“ gelöscht.", 4000)

    # -- Notizen ------------------------------------------------------

    def auffrischen(self) -> None:
        tabelle = self.aktuelle_tabelle()
        aktuell = self.aktuelles_register()
        if tabelle is None or aktuell is None:
            return
        art, tag = aktuell
        suche = self.suche.text().strip() or None
        notizen = self.speicher.liste(
            tag=tag if art == TAG else None,
            suche=suche,
            nur_wiedervorlage=(art == WIEDERVORLAGE))
        tabelle.setzen(notizen)

        gesamt = len(self.speicher.liste())
        offen = len([n for n in self.speicher.liste(nur_wiedervorlage=True,
                                                    nur_offen=True)])
        self.statusBar().showMessage(
            f"{len(notizen)} angezeigt · {gesamt} Notizen insgesamt · "
            f"{offen} offene Wiedervorlagen")

    def _gewaehlte_notiz(self) -> store.Notiz | None:
        tabelle = self.aktuelle_tabelle()
        if tabelle is None:
            return None
        kennungen = tabelle.ausgewaehlte()
        return self.speicher.holen(kennungen[0]) if kennungen else None

    def _notiz_oeffnen(self, kennung: int) -> None:
        notiz = self.speicher.holen(kennung)
        if notiz:
            self._bearbeiten(notiz)

    def notiz_bearbeiten(self) -> None:
        notiz = self._gewaehlte_notiz()
        if notiz is None:
            self.statusBar().showMessage("Keine Notiz ausgewählt.", 3000)
            return
        self._bearbeiten(notiz)

    def _bearbeiten(self, notiz: store.Notiz) -> None:
        vorher_faellig = notiz.faellig
        dialog = NotizDialog(self.cfg, notiz, self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        notiz = dialog.uebernehmen()
        if not notiz.text:
            common.fehler_zeigen(self, "Leere Notiz", "Es steht kein Text in der Notiz.")
            return
        if config.tags_merken(self.cfg, notiz.tags):
            config.speichern(self.cfg)
        if notiz.faellig is None:
            notiz.kalender_status = store.OHNE
        elif notiz.faellig != vorher_faellig:
            notiz.kalender_status = store.OFFEN
        self.speicher.aktualisieren(notiz)

        if notiz.faellig and notiz.kalender_status == store.OFFEN:
            status, meldung = calendar_sync.eintragen(self.cfg, notiz)
            self.speicher.kalender_setzen(notiz.id, status, notiz.kalender_ziel,
                                          notiz.kalender_uid)
            if status not in (store.CALDAV, store.OHNE):
                self.statusBar().showMessage(meldung.replace("\n", " "), 8000)
        self.register_neu_aufbauen()

    def notiz_schreiben(self) -> None:
        notiz = store.Notiz()
        aktuell = self.aktuelles_register()
        if aktuell and aktuell[0] == TAG:
            notiz.tags = [aktuell[1]]
        dialog = NotizDialog(self.cfg, notiz, self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        notiz = dialog.uebernehmen()
        if not notiz.text:
            return
        if notiz.faellig:
            notiz.kalender_status = store.OFFEN
        self.speicher.anlegen(notiz)
        if config.tags_merken(self.cfg, notiz.tags):
            config.speichern(self.cfg)
        if notiz.faellig:
            status, meldung = calendar_sync.eintragen(self.cfg, notiz)
            self.speicher.kalender_setzen(notiz.id, status, notiz.kalender_ziel,
                                          notiz.kalender_uid)
        self.register_neu_aufbauen()

    def notiz_diktieren(self) -> None:
        from .capture import ErfassenFenster
        fenster = ErfassenFenster(self.cfg, self.speicher, self)
        fenster.exec()
        self.register_neu_aufbauen()

    def notiz_erledigt(self) -> None:
        tabelle = self.aktuelle_tabelle()
        if tabelle is None:
            return
        for kennung in tabelle.ausgewaehlte():
            notiz = self.speicher.holen(kennung)
            if notiz:
                self.speicher.erledigt_setzen(kennung, not notiz.erledigt)
        self.auffrischen()

    def notiz_loeschen(self) -> None:
        tabelle = self.aktuelle_tabelle()
        if tabelle is None:
            return
        kennungen = tabelle.ausgewaehlte()
        if not kennungen:
            self.statusBar().showMessage("Keine Notiz ausgewählt.", 3000)
            return
        frage = ("Diese Notiz löschen?" if len(kennungen) == 1
                 else f"{len(kennungen)} Notizen löschen?")
        if QtWidgets.QMessageBox.question(self, "Löschen", frage) \
                != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        for kennung in kennungen:
            self.speicher.loeschen(kennung)
        self.register_neu_aufbauen()

    # -- Extras -------------------------------------------------------

    def nachtragen(self) -> None:
        gut, schlecht, meldungen = calendar_sync.nachtragen(self.cfg, self.speicher)
        if gut and not schlecht:
            text = f"{gut} Termine in den Kalender nachgetragen."
        elif gut or schlecht:
            text = f"{gut} nachgetragen, {schlecht} weiterhin offen."
        else:
            text = meldungen[0] if meldungen else "Es war nichts nachzutragen."
        self.statusBar().showMessage(text, 8000)
        self.auffrischen()

    def einstellungen(self) -> None:
        from .settings import EinstellungenDialog
        if EinstellungenDialog(self.cfg, self).exec() == \
                QtWidgets.QDialog.DialogCode.Accepted:
            self.register_neu_aufbauen()

    def tastenbefehle(self) -> None:
        QtWidgets.QMessageBox.information(self, "Tastenbefehle", """
<h3>Notizen</h3>
<table cellpadding="4">
<tr><td><b>Strg&nbsp;+&nbsp;N</b></td><td>Neue Notiz diktieren</td></tr>
<tr><td><b>Strg&nbsp;+&nbsp;Umschalt&nbsp;+&nbsp;N</b></td><td>Notiz tippen</td></tr>
<tr><td><b>Eingabe</b> oder <b>F2</b></td><td>Notiz bearbeiten</td></tr>
<tr><td><b>Strg&nbsp;+&nbsp;D</b></td><td>Erledigt / wieder offen</td></tr>
<tr><td><b>Entf</b></td><td>Notiz löschen</td></tr>
<tr><td><b>Strg&nbsp;+&nbsp;F</b></td><td>Suchen</td></tr>
</table>
<h3>Register</h3>
<table cellpadding="4">
<tr><td><b>Strg&nbsp;+&nbsp;T</b></td><td>Neues Register (Tag)</td></tr>
<tr><td><b>Umschalt&nbsp;+&nbsp;F2</b></td><td>Register umbenennen</td></tr>
<tr><td><b>Strg&nbsp;+&nbsp;Umschalt&nbsp;+&nbsp;W</b></td><td>Register löschen</td></tr>
<tr><td><b>Strg&nbsp;+&nbsp;Bild&nbsp;auf/ab</b></td><td>Register wechseln</td></tr>
<tr><td><b>Alt&nbsp;+&nbsp;1 … 9</b></td><td>Register direkt anspringen</td></tr>
</table>
<h3>Im Erfassen-Fenster</h3>
<table cellpadding="4">
<tr><td><b>Leertaste</b></td><td>Aufnahme stoppen und auswerten</td></tr>
<tr><td><b>Strg&nbsp;+&nbsp;S</b></td><td>Speichern</td></tr>
<tr><td><b>Esc</b></td><td>Abbrechen</td></tr>
</table>
""")

    def ueber(self) -> None:
        QtWidgets.QMessageBox.about(self, "Über Denkzettel", """
<h3>Denkzettel</h3>
<p>Gedanken sprechen, mit Tags einsortieren und mit einer Wiedervorlage
im Kalender versehen.</p>
<p>Die Spracherkennung läuft vollständig auf diesem Rechner – es geht
kein Ton ins Netz.</p>
<p>Gehört zur DialOS-Familie. Entstanden in Zusammenarbeit mit
<a href="https://claude.com">Claude</a>.</p>
""")
