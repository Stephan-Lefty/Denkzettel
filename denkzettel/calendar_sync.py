#!/usr/bin/env python3
"""
Denkzettel: Wiedervorlagen in den Kalender eintragen.

Zwei Wege, umschaltbar über `[kalender] modus`:

* **caldav** - der Termin wird direkt in den Nextcloud-Kalender
  geschrieben und ist dadurch auch auf dem Handy da.
* **ics**    - alle offenen Termine stehen gesammelt in EINER Datei
  (`denkzettel.ics`), die man einmal in Thunderbird als Kalender
  einbindet. Ohne Server, ohne Zugangsdaten. Eine Datei pro Notiz wäre
  hier die falsche Form gewesen: Thunderbird bindet genau eine feste
  Datei ein, keinen ganzen Ordner - deshalb wird diese eine Datei bei
  jeder Änderung komplett aus der Datenbank neu geschrieben, statt in
  ihr herumzueditieren.

Standard ist **auto**: erst CalDAV, und wenn der Server nicht erreichbar
ist, ersatzweise die Datei. Die Notiz merkt sich dann, dass der Termin
noch nicht auf dem Server steht (Status `ics`), und `denkzettel nachtragen`
reicht ihn beim nächsten Mal nach. Ein Termin darf nicht verloren gehen,
nur weil gerade kein Netz da war.

Absichtlich ohne Fremdbibliothek: urllib aus der Standardbibliothek kann
auch PROPFIND, und eine Abhängigkeit weniger ist eine Fehlerquelle
weniger auf zwei verschiedenen Distributionen.
"""
from __future__ import annotations

import base64
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, store

ZEITLIMIT = 20

PROPFIND_KALENDER = """<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop>
    <d:displayname/>
    <d:resourcetype/>
    <c:supported-calendar-component-set/>
  </d:prop>
</d:propfind>
"""


# -- iCalendar bauen --------------------------------------------------

def _maskieren(wert: str) -> str:
    """Sonderzeichen nach RFC 5545 schützen."""
    return (wert.replace("\\", "\\\\").replace(";", "\\;")
                .replace(",", "\\,").replace("\r\n", "\\n")
                .replace("\n", "\\n").replace("\r", "\\n"))


def _falten(zeile: str) -> str:
    """Zeilen auf 75 Oktett umbrechen - sonst lehnen strenge Server ab."""
    roh = zeile.encode("utf-8")
    if len(roh) <= 75:
        return zeile
    teile, rest = [], roh
    grenze = 73
    while len(rest) > grenze:
        schnitt = grenze
        while schnitt > 0 and (rest[schnitt] & 0xC0) == 0x80:
            schnitt -= 1          # nicht mitten in ein UTF-8-Zeichen schneiden
        teile.append(rest[:schnitt].decode("utf-8"))
        rest = rest[schnitt:]
        grenze = 72
    teile.append(rest.decode("utf-8"))
    return "\r\n ".join(teile)


def _utc(wert: datetime) -> str:
    """Ortszeit in UTC-Stempel. Bewusst UTC statt VTIMEZONE - das ist
    eindeutig und spart einen ganzen Block Zeitzonendefinition."""
    if wert.tzinfo is None:
        wert = wert.astimezone()
    return wert.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _vevent(notiz: store.Notiz, cfg, uid: str | None = None) -> tuple[str, list[str]]:
    """Nur der VEVENT-Block, ohne VCALENDAR-Rahmen.

    Baustein für zwei Verwendungen: `ics_bauen()` verpackt genau einen
    davon für den CalDAV-Server (der will pro Termin eine eigene
    Ablage), `sammelkalender_schreiben()` reiht mehrere davon in eine
    gemeinsame Datei für Thunderbird.
    """
    if notiz.faellig is None:
        raise ValueError("Notiz ohne Wiedervorlage")
    uid = uid or notiz.kalender_uid or f"{uuid.uuid4()}@denkzettel"

    grenze = config.zahl(cfg, "kalender", "titel_zeichen", 60)
    titel = notiz.titel
    if len(titel) > grenze:
        titel = titel[: grenze - 1].rstrip() + "…"

    dauer = config.zahl(cfg, "kalender", "dauer_minuten", 30)
    erinnerung = config.zahl(cfg, "kalender", "erinnerung_minuten", 10)

    zeilen = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_utc(datetime.now())}",
        f"DTSTART:{_utc(notiz.faellig)}",
        f"DTEND:{_utc(notiz.faellig + timedelta(minutes=dauer))}",
        f"SUMMARY:{_maskieren(titel)}",
    ]
    beschreibung = notiz.text
    if notiz.tags:
        beschreibung += "\n\nTags: " + ", ".join(notiz.tags)
    beschreibung += f"\n\nAus Denkzettel, notiert am {notiz.erstellt:%d.%m.%Y um %H:%M}."
    zeilen.append(f"DESCRIPTION:{_maskieren(beschreibung)}")
    if notiz.tags:
        zeilen.append("CATEGORIES:" + ",".join(_maskieren(t) for t in notiz.tags))
    if erinnerung > 0:
        zeilen += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_maskieren(titel)}",
            f"TRIGGER:-PT{erinnerung}M",
            "END:VALARM",
        ]
    zeilen.append("END:VEVENT")
    return uid, zeilen


def ics_bauen(notiz: store.Notiz, cfg, uid: str | None = None) -> tuple[str, str]:
    """Ein vollständiger Kalender mit genau einem Termin - für den
    CalDAV-Server, der pro Termin eine eigene Ablage will."""
    uid, vevent = _vevent(notiz, cfg, uid)
    zeilen = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Denkzettel//DE",
              "CALSCALE:GREGORIAN", *vevent, "END:VCALENDAR"]
    return uid, "\r\n".join(_falten(z) for z in zeilen) + "\r\n"


# -- CalDAV -----------------------------------------------------------

def _kopf(benutzer: str, passwort: str) -> dict[str, str]:
    roh = f"{benutzer}:{passwort}".encode("utf-8")
    return {"Authorization": "Basic " + base64.b64encode(roh).decode("ascii"),
            "User-Agent": "Denkzettel"}


def _anfrage(methode: str, url: str, benutzer: str, passwort: str,
             koerper: bytes | None = None,
             zusatz: dict[str, str] | None = None):
    kopf = _kopf(benutzer, passwort)
    if zusatz:
        kopf.update(zusatz)
    anfrage = urllib.request.Request(url, data=koerper, headers=kopf, method=methode)
    return urllib.request.urlopen(anfrage, timeout=ZEITLIMIT)


def _klartext(fehler: Exception, url: str) -> str:
    """Fehler so beschreiben, dass man weiß, was zu tun ist."""
    if isinstance(fehler, urllib.error.HTTPError):
        if fehler.code == 401:
            return ("Der Kalenderserver hat Benutzer oder Passwort abgelehnt "
                    "(401). Bei Nextcloud ein App-Passwort verwenden, nicht "
                    "das Anmelde-Passwort.")
        if fehler.code == 403:
            return "Keine Schreibrechte auf diesem Kalender (403)."
        if fehler.code == 404:
            return f"Diesen Kalender gibt es nicht: {url} (404)."
        if fehler.code == 405:
            return ("Die Adresse ist kein Kalender, sondern ein Ordner (405). "
                    "`denkzettel kalender` zeigt die richtigen Adressen an.")
        return f"Der Kalenderserver antwortete mit {fehler.code} {fehler.reason}."
    if isinstance(fehler, urllib.error.URLError):
        grund = fehler.reason
        if isinstance(grund, ssl.SSLError):
            return f"Verschlüsselung fehlgeschlagen: {grund}"
        if isinstance(grund, socket.timeout):
            return f"Der Kalenderserver hat nicht innerhalb von {ZEITLIMIT}s geantwortet."
        return f"Kalenderserver nicht erreichbar: {grund}"
    return f"Kalenderserver nicht erreichbar: {fehler}"


def kalender_auflisten(url: str, benutzer: str, passwort: str) -> list[tuple[str, str]]:
    """Kalender unter einer Adresse suchen. Gibt [(Adresse, Name)] zurück.

    Gedacht für `denkzettel kalender`: Man gibt die Sammel-Adresse an
    (…/remote.php/dav/calendars/BENUTZER/) und bekommt die einzelnen
    Kalender mit ihren fertigen Adressen aufgelistet.
    """
    if not url.endswith("/"):
        url += "/"
    antwort = _anfrage("PROPFIND", url, benutzer, passwort,
                       koerper=PROPFIND_KALENDER.encode("utf-8"),
                       zusatz={"Depth": "1",
                               "Content-Type": "application/xml; charset=utf-8"})
    with antwort:
        baum = ET.fromstring(antwort.read())

    dav, caldav = "{DAV:}", "{urn:ietf:params:xml:ns:caldav}"
    gefunden: list[tuple[str, str]] = []
    for antwort_knoten in baum.findall(f"{dav}response"):
        href = antwort_knoten.findtext(f"{dav}href") or ""
        prop = antwort_knoten.find(f"{dav}propstat/{dav}prop")
        if prop is None:
            continue
        if prop.find(f"{dav}resourcetype/{caldav}calendar") is None:
            continue
        komponenten = [k.get("name") for k in
                       prop.findall(f"{caldav}supported-calendar-component-set/"
                                    f"{caldav}comp")]
        if komponenten and "VEVENT" not in komponenten:
            continue          # z.B. reine Aufgaben- oder Adresslisten
        name = prop.findtext(f"{dav}displayname") or href.rstrip("/").rsplit("/", 1)[-1]
        gefunden.append((urllib.parse.urljoin(url, href), name))
    return gefunden


def caldav_senden(cfg, uid: str, ics: str) -> str:
    """VEVENT auf den Server legen. Gibt die Adresse des Termins zurück."""
    url = config.wert(cfg, "caldav", "url")
    if not url.endswith("/"):
        url += "/"
    ziel = urllib.parse.urljoin(url, f"{uid}.ics")
    antwort = _anfrage("PUT", ziel,
                       config.wert(cfg, "caldav", "benutzer"),
                       config.caldav_passwort(cfg),
                       koerper=ics.encode("utf-8"),
                       zusatz={"Content-Type": "text/calendar; charset=utf-8"})
    with antwort:
        antwort.read()
    return ziel


def verbindung_pruefen(cfg) -> tuple[bool, str]:
    """Zugangsdaten testen, ohne etwas einzutragen."""
    if not config.caldav_eingerichtet(cfg):
        return False, "Es ist kein CalDAV-Kalender eingerichtet."
    url = config.wert(cfg, "caldav", "url")
    try:
        antwort = _anfrage("PROPFIND", url,
                           config.wert(cfg, "caldav", "benutzer"),
                           config.caldav_passwort(cfg),
                           koerper=PROPFIND_KALENDER.encode("utf-8"),
                           zusatz={"Depth": "0",
                                   "Content-Type": "application/xml; charset=utf-8"})
        with antwort:
            roh = antwort.read()
    except Exception as e:                      # noqa: BLE001 - Klartext für den Nutzer
        return False, _klartext(e, url)
    if b"calendar" not in roh:
        return False, ("Die Adresse antwortet, ist aber kein Kalender. "
                       "`denkzettel kalender` zeigt die richtigen Adressen an.")
    return True, f"Kalender erreichbar: {url}"


# -- Datei-Weg: eine gemeinsame Sammel-Datei für Thunderbird ----------

SAMMELDATEI = "denkzettel.ics"


def sammelkalender_pfad(cfg) -> Path:
    return config.ics_verzeichnis(cfg) / SAMMELDATEI


def sammelkalender_schreiben(cfg, speicher: store.Speicher) -> Path:
    """Alle noch nicht auf einem Server stehenden Wiedervorlagen in EINE
    Datei schreiben.

    Wird bei jeder Änderung komplett aus der Datenbank neu geschrieben,
    nicht nachträglich in der bestehenden Datei gesucht und ersetzt -
    das ist einfacher und garantiert richtig. Muss vom aufrufenden
    Programmteil (nicht von hier) im selben Thread laufen, der die
    Datenbankverbindung angelegt hat - `sqlite3` erlaubt keine
    Mitbenutzung aus einem Hintergrund-Thread.
    """
    ziel = sammelkalender_pfad(cfg)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    zeilen = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Denkzettel//DE",
              "CALSCALE:GREGORIAN"]
    for notiz in speicher.offene_kalendereintraege():
        _, vevent = _vevent(notiz, cfg, notiz.kalender_uid)
        zeilen += vevent
    zeilen.append("END:VCALENDAR")
    ziel.write_text("\r\n".join(_falten(z) for z in zeilen) + "\r\n", encoding="utf-8")
    return ziel


# -- Steuerung --------------------------------------------------------

def eintragen(cfg, notiz: store.Notiz) -> tuple[str, str]:
    """Termin eintragen. Gibt (Status, Klartext-Meldung) zurück.

    Der Status wandert in die Datenbank: `caldav` ist erledigt, `ics`
    heißt „gehört in die Sammel-Termindatei, steht noch nicht auf dem
    Server“. Schreibt bewusst KEINE Datei selbst - diese Funktion läuft
    bei der Aufnahme im Hintergrund-Thread, und die Sammel-Datei braucht
    Zugriff auf die Datenbank, die nur im Hauptthread sicher ist. Der
    Aufrufer ruft danach im Hauptthread `sammelkalender_schreiben()`.
    """
    if notiz.faellig is None:
        return store.OHNE, ""

    modus = config.wert(cfg, "kalender", "modus", "auto").lower()
    if modus == "aus":
        return store.OHNE, "Kalendereintrag ist abgeschaltet."

    uid, ics = ics_bauen(notiz, cfg, notiz.kalender_uid)
    notiz.kalender_uid = uid

    if modus in ("auto", "caldav") and config.caldav_eingerichtet(cfg):
        try:
            ziel = caldav_senden(cfg, uid, ics)
            notiz.kalender_status = store.CALDAV
            notiz.kalender_ziel = ziel
            return store.CALDAV, "Im Kalender eingetragen."
        except Exception as e:                  # noqa: BLE001
            meldung = _klartext(e, config.wert(cfg, "caldav", "url"))
            if modus == "caldav":
                notiz.kalender_status = store.FEHLER
                notiz.kalender_ziel = meldung
                return store.FEHLER, meldung
            notiz.kalender_status = store.ICS
            notiz.kalender_ziel = str(sammelkalender_pfad(cfg))
            return store.ICS, (f"{meldung}\nDer Termin liegt solange in der "
                               f"Sammel-Termindatei {sammelkalender_pfad(cfg)} "
                               f"und wird beim nächsten Start nachgetragen.")

    if modus == "caldav":
        notiz.kalender_status = store.FEHLER
        notiz.kalender_ziel = "CalDAV ist nicht eingerichtet."
        return store.FEHLER, notiz.kalender_ziel

    notiz.kalender_status = store.ICS
    notiz.kalender_ziel = str(sammelkalender_pfad(cfg))
    return store.ICS, f"In der Sammel-Termindatei eingetragen: {sammelkalender_pfad(cfg)}"


def nachtragen(cfg, speicher: store.Speicher) -> tuple[int, int, list[str]]:
    """Alle Termine nachreichen, die noch nicht auf dem Server stehen."""
    if not config.caldav_eingerichtet(cfg):
        return 0, 0, ["Es ist kein CalDAV-Kalender eingerichtet."]
    if config.wert(cfg, "kalender", "modus", "auto").lower() not in ("auto", "caldav"):
        return 0, 0, ["Der Kalender-Modus steht nicht auf caldav oder auto."]

    gut = schlecht = 0
    meldungen: list[str] = []
    for notiz in speicher.offene_kalendereintraege():
        uid, ics = ics_bauen(notiz, cfg, notiz.kalender_uid)
        try:
            ziel = caldav_senden(cfg, uid, ics)
        except Exception as e:                  # noqa: BLE001
            schlecht += 1
            meldungen.append(f"Notiz {notiz.id}: {_klartext(e, ziel_sicher(cfg))}")
            continue
        speicher.kalender_setzen(notiz.id, store.CALDAV, ziel, uid)
        gut += 1
    if gut:
        # Erfolgreich nachgereichte Termine sollen aus der Sammel-Datei
        # verschwinden - sie stehen jetzt auf dem Server.
        sammelkalender_schreiben(cfg, speicher)
    return gut, schlecht, meldungen


def ziel_sicher(cfg) -> str:
    return config.wert(cfg, "caldav", "url") or "(keine Adresse)"
