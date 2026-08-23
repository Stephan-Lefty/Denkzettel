#!/usr/bin/env python3
"""
Denkzettel: Notizen und Tags in einer SQLite-Datei.

Eine einzige Datei (~/.local/share/denkzettel/notizen.db), die sich
kopieren und sichern lässt. Datum und Uhrzeit stehen als ISO-Text darin -
lesbar, sortierbar, ohne Zeitzonen-Überraschungen, weil durchgehend
Ortszeit ohne Zeitzonenangabe verwendet wird.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS notizen (
    id              INTEGER PRIMARY KEY,
    erstellt        TEXT NOT NULL,
    text            TEXT NOT NULL,
    rohtext         TEXT,
    audio           TEXT,
    faellig         TEXT,
    kalender_status TEXT NOT NULL DEFAULT 'ohne',
    kalender_ziel   TEXT,
    kalender_uid    TEXT,
    erledigt        INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
);
CREATE TABLE IF NOT EXISTS notiz_tags (
    notiz_id INTEGER NOT NULL REFERENCES notizen(id) ON DELETE CASCADE,
    tag_id   INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (notiz_id, tag_id)
);
CREATE INDEX IF NOT EXISTS idx_notizen_faellig ON notizen(faellig);
CREATE INDEX IF NOT EXISTS idx_notizen_erstellt ON notizen(erstellt);
"""

# Zustände der Kalender-Anbindung
OHNE = "ohne"          # keine Wiedervorlage gewünscht
OFFEN = "offen"        # Termin steht aus - Server war nicht erreichbar
CALDAV = "caldav"      # im Kalender auf dem Server
ICS = "ics"            # als Datei abgelegt
FEHLER = "fehler"      # dauerhaft gescheitert, Grund steht in kalender_ziel


@dataclass
class Notiz:
    id: int | None = None
    erstellt: datetime = field(default_factory=datetime.now)
    text: str = ""
    rohtext: str = ""
    audio: str | None = None
    faellig: datetime | None = None
    kalender_status: str = OHNE
    kalender_ziel: str | None = None
    kalender_uid: str | None = None
    erledigt: bool = False
    tags: list[str] = field(default_factory=list)

    @property
    def titel(self) -> str:
        """Erste Zeile bzw. erster Satz - für Kalendereintrag und Liste."""
        text = " ".join(self.text.split())
        for zeichen in (". ", "! ", "? "):
            if zeichen in text[:80]:
                return text[: text.index(zeichen) + 1].strip()
        return text


def _dt(wert: str | None) -> datetime | None:
    return datetime.fromisoformat(wert) if wert else None


def _txt(wert: datetime | None) -> str | None:
    return wert.isoformat(timespec="seconds") if wert else None


class Speicher:
    def __init__(self, pfad: Path | None = None):
        self.pfad = pfad or config.DATENBANK
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.pfad)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        self.db.commit()

    def schliessen(self) -> None:
        self.db.close()

    # -- Tags ---------------------------------------------------------

    def _tag_id(self, name: str) -> int:
        name = name.strip()
        cur = self.db.execute("SELECT id FROM tags WHERE name = ?", (name,))
        zeile = cur.fetchone()
        if zeile:
            return zeile["id"]
        return self.db.execute("INSERT INTO tags (name) VALUES (?)", (name,)).lastrowid

    def _tags_setzen(self, notiz_id: int, tags: list[str]) -> None:
        self.db.execute("DELETE FROM notiz_tags WHERE notiz_id = ?", (notiz_id,))
        for t in dict.fromkeys(t.strip() for t in tags if t.strip()):
            self.db.execute(
                "INSERT OR IGNORE INTO notiz_tags (notiz_id, tag_id) VALUES (?, ?)",
                (notiz_id, self._tag_id(t)))

    def _tags_von(self, notiz_id: int) -> list[str]:
        cur = self.db.execute(
            "SELECT t.name FROM tags t JOIN notiz_tags nt ON nt.tag_id = t.id "
            "WHERE nt.notiz_id = ? ORDER BY t.name COLLATE NOCASE", (notiz_id,))
        return [z["name"] for z in cur]

    def tags(self, auch_leere: bool = False) -> list[tuple[str, int]]:
        """Alle Tags mit Anzahl der Notizen."""
        sql = ("SELECT t.name, COUNT(nt.notiz_id) AS anzahl FROM tags t "
               "LEFT JOIN notiz_tags nt ON nt.tag_id = t.id GROUP BY t.id ")
        if not auch_leere:
            sql += "HAVING anzahl > 0 "
        sql += "ORDER BY t.name COLLATE NOCASE"
        return [(z["name"], z["anzahl"]) for z in self.db.execute(sql)]

    def tag_anlegen(self, name: str) -> bool:
        """Neuen Tag anlegen. False, wenn es ihn schon gibt."""
        name = name.strip()
        if not name:
            return False
        vorher = self.db.execute("SELECT id FROM tags WHERE name = ?",
                                 (name,)).fetchone()
        if vorher:
            return False
        self._tag_id(name)
        self.db.commit()
        return True

    def tag_umbenennen(self, alt: str, neu: str) -> int:
        """Tag umbenennen - überall, wo er hängt.

        Gibt es den neuen Namen schon, werden beide zusammengeführt,
        statt am UNIQUE-Index zu scheitern. Rückgabe: Zahl der Notizen,
        die den Tag jetzt tragen.
        """
        alt, neu = alt.strip(), neu.strip()
        if not neu or alt.lower() == neu.lower():
            # Nur Groß-/Kleinschreibung geändert: direkt umschreiben.
            if neu and alt != neu:
                self.db.execute("UPDATE tags SET name = ? WHERE name = ?", (neu, alt))
                self.db.commit()
            return len(self.liste(tag=neu or alt))
        zeile = self.db.execute("SELECT id FROM tags WHERE name = ?", (alt,)).fetchone()
        if not zeile:
            return 0
        alt_id = zeile["id"]
        ziel = self.db.execute("SELECT id FROM tags WHERE name = ?", (neu,)).fetchone()
        if ziel:
            self.db.execute(
                "UPDATE OR IGNORE notiz_tags SET tag_id = ? WHERE tag_id = ?",
                (ziel["id"], alt_id))
            self.db.execute("DELETE FROM notiz_tags WHERE tag_id = ?", (alt_id,))
            self.db.execute("DELETE FROM tags WHERE id = ?", (alt_id,))
        else:
            self.db.execute("UPDATE tags SET name = ? WHERE id = ?", (neu, alt_id))
        self.db.commit()
        return len(self.liste(tag=neu))

    def tag_loeschen(self, name: str) -> int:
        """Tag entfernen. Die Notizen selbst bleiben - nur die Zuordnung geht.
        Rückgabe: Zahl der Notizen, die ihn getragen haben."""
        zeile = self.db.execute("SELECT id FROM tags WHERE name = ?",
                                (name.strip(),)).fetchone()
        if not zeile:
            return 0
        betroffen = self.db.execute(
            "SELECT COUNT(*) AS n FROM notiz_tags WHERE tag_id = ?",
            (zeile["id"],)).fetchone()["n"]
        self.db.execute("DELETE FROM notiz_tags WHERE tag_id = ?", (zeile["id"],))
        self.db.execute("DELETE FROM tags WHERE id = ?", (zeile["id"],))
        self.db.commit()
        return betroffen

    # -- Notizen ------------------------------------------------------

    def _bauen(self, zeile: sqlite3.Row) -> Notiz:
        return Notiz(
            id=zeile["id"],
            erstellt=_dt(zeile["erstellt"]) or datetime.now(),
            text=zeile["text"],
            rohtext=zeile["rohtext"] or "",
            audio=zeile["audio"],
            faellig=_dt(zeile["faellig"]),
            kalender_status=zeile["kalender_status"],
            kalender_ziel=zeile["kalender_ziel"],
            kalender_uid=zeile["kalender_uid"],
            erledigt=bool(zeile["erledigt"]),
            tags=self._tags_von(zeile["id"]),
        )

    def anlegen(self, notiz: Notiz) -> int:
        cur = self.db.execute(
            "INSERT INTO notizen (erstellt, text, rohtext, audio, faellig, "
            "kalender_status, kalender_ziel, kalender_uid, erledigt) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (_txt(notiz.erstellt), notiz.text, notiz.rohtext, notiz.audio,
             _txt(notiz.faellig), notiz.kalender_status, notiz.kalender_ziel,
             notiz.kalender_uid, int(notiz.erledigt)))
        notiz.id = cur.lastrowid
        self._tags_setzen(notiz.id, notiz.tags)
        self.db.commit()
        return notiz.id

    def aktualisieren(self, notiz: Notiz) -> None:
        if notiz.id is None:
            raise ValueError("Notiz ohne Nummer kann nicht aktualisiert werden")
        self.db.execute(
            "UPDATE notizen SET text = ?, rohtext = ?, audio = ?, faellig = ?, "
            "kalender_status = ?, kalender_ziel = ?, kalender_uid = ?, "
            "erledigt = ? WHERE id = ?",
            (notiz.text, notiz.rohtext, notiz.audio, _txt(notiz.faellig),
             notiz.kalender_status, notiz.kalender_ziel, notiz.kalender_uid,
             int(notiz.erledigt), notiz.id))
        self._tags_setzen(notiz.id, notiz.tags)
        self.db.commit()

    def kalender_setzen(self, notiz_id: int, status: str,
                        ziel: str | None = None, uid: str | None = None) -> None:
        self.db.execute(
            "UPDATE notizen SET kalender_status = ?, kalender_ziel = ?, "
            "kalender_uid = COALESCE(?, kalender_uid) WHERE id = ?",
            (status, ziel, uid, notiz_id))
        self.db.commit()

    def erledigt_setzen(self, notiz_id: int, erledigt: bool) -> None:
        self.db.execute("UPDATE notizen SET erledigt = ? WHERE id = ?",
                        (int(erledigt), notiz_id))
        self.db.commit()

    def loeschen(self, notiz_id: int) -> None:
        self.db.execute("DELETE FROM notizen WHERE id = ?", (notiz_id,))
        self.db.commit()

    def holen(self, notiz_id: int) -> Notiz | None:
        zeile = self.db.execute("SELECT * FROM notizen WHERE id = ?",
                                (notiz_id,)).fetchone()
        return self._bauen(zeile) if zeile else None

    def liste(self, tag: str | None = None, suche: str | None = None,
              nur_wiedervorlage: bool = False, nur_offen: bool = False,
              grenze: int | None = None) -> list[Notiz]:
        sql = "SELECT n.* FROM notizen n"
        werte: list = []
        bedingungen: list[str] = []
        if tag:
            sql += (" JOIN notiz_tags nt ON nt.notiz_id = n.id"
                    " JOIN tags t ON t.id = nt.tag_id")
            bedingungen.append("t.name = ? COLLATE NOCASE")
            werte.append(tag)
        if suche:
            bedingungen.append("n.text LIKE ?")
            werte.append(f"%{suche}%")
        if nur_wiedervorlage:
            bedingungen.append("n.faellig IS NOT NULL")
        if nur_offen:
            bedingungen.append("n.erledigt = 0")
        if bedingungen:
            sql += " WHERE " + " AND ".join(bedingungen)
        sql += (" ORDER BY n.faellig IS NULL, n.faellig ASC, n.erstellt DESC"
                if nur_wiedervorlage else " ORDER BY n.erstellt DESC")
        if grenze:
            sql += f" LIMIT {int(grenze)}"
        return [self._bauen(z) for z in self.db.execute(sql, werte)]

    def offene_kalendereintraege(self) -> list[Notiz]:
        """Notizen, deren Termin noch nicht auf dem Server steht."""
        cur = self.db.execute(
            "SELECT * FROM notizen WHERE faellig IS NOT NULL "
            "AND kalender_status IN (?, ?) ORDER BY erstellt", (OFFEN, ICS))
        return [self._bauen(z) for z in cur]
