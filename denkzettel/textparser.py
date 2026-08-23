#!/usr/bin/env python3
"""
Denkzettel: aus dem Diktat Tags und Wiedervorlage heraushören.

Man spricht einen Gedanken und hängt hinten an, wohin er gehört und wann
er wieder auftauchen soll:

    „Angebot für Meier nachrechnen, Tag beruflich,
     Wiedervorlage nächsten Montag um zehn Uhr.“

Daraus wird die Notiz „Angebot für Meier nachrechnen.“, der Tag
„beruflich“ und ein Termin. Die erkannten Teile werden aus dem Notiztext
entfernt - sie sind Anweisung, nicht Inhalt.

Wichtig: Diese Auswertung darf sich irren. Deshalb landet alles im
Erfassen-Fenster zur Bestätigung, statt still gespeichert zu werden. Was
nicht sicher erkannt wird, bleibt lieber im Text stehen, als dass ein
Stück Gedanke verschwindet.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# -- Wortlisten -------------------------------------------------------

WOCHENTAGE = {
    "montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3,
    "freitag": 4, "samstag": 5, "sonnabend": 5, "sonntag": 6,
}

MONATE = {
    "januar": 1, "jänner": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
    "oktober": 10, "november": 11, "dezember": 12,
}

ZAHLWORTE = {
    "ein": 1, "eine": 1, "einem": 1, "einen": 1, "einer": 1, "eins": 1,
    "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "fuenf": 5, "sechs": 6,
    "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12,
    "zwoelf": 12, "dreizehn": 13, "vierzehn": 14, "fünfzehn": 15,
    "sechzehn": 16, "siebzehn": 17, "achtzehn": 18, "neunzehn": 19,
    "zwanzig": 20, "einundzwanzig": 21, "dreißig": 30, "dreissig": 30,
}


def _ordnungszahlen() -> dict[str, int]:
    """„ersten“ bis „einunddreißigsten“ - erzeugt statt abgetippt."""
    grund = ["", "ersten", "zweiten", "dritten", "vierten", "fünften",
             "sechsten", "siebten", "achten", "neunten", "zehnten", "elften",
             "zwölften", "dreizehnten", "vierzehnten", "fünfzehnten",
             "sechzehnten", "siebzehnten", "achtzehnten", "neunzehnten",
             "zwanzigsten"]
    einer = ["", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben",
             "acht", "neun"]
    d = {w: i for i, w in enumerate(grund) if w}
    d["siebenten"] = 7
    for i in range(1, 10):
        d[f"{einer[i]}undzwanzigsten"] = 20 + i
    d["dreißigsten"] = 30
    d["dreissigsten"] = 30
    d["einunddreißigsten"] = 31
    d["einunddreissigsten"] = 31
    return d


ORDNUNGSZAHLEN = _ordnungszahlen()

TAGESZEITEN = {
    "morgens": (8, 0), "früh": (8, 0), "frueh": (8, 0), "vormittags": (10, 0),
    "mittags": (12, 0), "nachmittags": (15, 0), "abends": (18, 0),
    "nachts": (20, 0),
}

# -- Auslöser ---------------------------------------------------------

WIEDERVORLAGE = re.compile(
    r"\b(?:wiedervorlage|wieder\s+vorlage|wiedervorlagen|erinnere\s+mich|"
    r"erinner\s+mich|erinnerung|nachfassen|termin|wiederauflage)\b", re.I)

TAG_AUSLOESER = re.compile(
    r"\b(schlagwörter|schlagworte|schlagwort|kategorien|kategorie|"
    r"stichwörter|stichworte|stichwort|tags|tag)\b\s*:?\s*", re.I)

# Auslöser, nach denen auch ein unbekanntes Wort als neuer Tag gilt.
TAG_AUSDRUECKLICH = re.compile(r"^(schlagw|kategorie|stichw)", re.I)

HASHTAG = re.compile(r"#([A-Za-zÄÖÜäöüß][\wÄÖÜäöüß-]*)")

# Füllwörter zwischen Auslöser und Datum („Wiedervorlage bitte am …“).
FUELLWORT = re.compile(
    r"^(?:\s*(?:bitte|dann|doch|mal|auf|am|an|den|dem|der|für|fuer|zum|zur|"
    r"ist|wäre|waere|setzen|setz|machen|mach)\b)+", re.I)

MONATSMUSTER = "|".join(MONATE)
WOCHENTAGSMUSTER = "|".join(WOCHENTAGE)
ORDNUNGSMUSTER = "|".join(sorted(ORDNUNGSZAHLEN, key=len, reverse=True))
ZAHLMUSTER = "|".join(sorted(ZAHLWORTE, key=len, reverse=True))
TAGESZEITMUSTER = "|".join(TAGESZEITEN)


@dataclass
class Auswertung:
    text: str                                   # bereinigter Notiztext
    tags: list[str] = field(default_factory=list)
    faellig: datetime | None = None
    entfernt: list[str] = field(default_factory=list)   # was rausgelöst wurde


# -- Datum und Uhrzeit ------------------------------------------------

def _zahl(wort: str) -> int | None:
    wort = wort.strip().lower()
    if wort.isdigit():
        return int(wort)
    return ZAHLWORTE.get(wort)


def _naechster_wochentag(jetzt: datetime, ziel: int, naechste_woche: bool,
                         diese_woche: bool) -> datetime:
    abstand = (ziel - jetzt.weekday()) % 7
    if diese_woche:
        pass                       # „diesen Freitag“ - auch heute erlaubt
    elif abstand == 0:
        abstand = 7                # „am Montag“ am Montag meint den nächsten
    if naechste_woche and abstand < 7:
        # „nächsten Montag“ meint die kommende Woche, nicht in zwei Tagen -
        # außer der Tag liegt ohnehin schon in der nächsten Kalenderwoche.
        if jetzt.weekday() + abstand < 7:
            abstand += 7
    return jetzt + timedelta(days=abstand)


def _monate_dazu(d: datetime, anzahl: int) -> datetime:
    monat = d.month - 1 + anzahl
    jahr = d.year + monat // 12
    monat = monat % 12 + 1
    letzter = [31, 29 if (jahr % 4 == 0 and jahr % 100 != 0) or jahr % 400 == 0
               else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][monat - 1]
    return d.replace(year=jahr, month=monat, day=min(d.day, letzter))


def _datum_versuchen(rest: str, jetzt: datetime) -> tuple[datetime | None, int]:
    """Ein Datum am Anfang von `rest` lesen. Gibt Datum und Länge zurück."""
    m = re.match(r"^heute\b", rest, re.I)
    if m:
        return jetzt, m.end()

    m = re.match(r"^übermorgen\b|^uebermorgen\b", rest, re.I)
    if m:
        return jetzt + timedelta(days=2), m.end()

    m = re.match(r"^morgen\b", rest, re.I)
    if m:
        return jetzt + timedelta(days=1), m.end()

    m = re.match(rf"^in\s+(\d+|{ZAHLMUSTER})\s+"
                 r"(tagen?|wochen?|monaten?|monat|jahren?|jahr)\b", rest, re.I)
    if m:
        n = _zahl(m.group(1))
        if n is not None:
            einheit = m.group(2).lower()
            if einheit.startswith("tag"):
                return jetzt + timedelta(days=n), m.end()
            if einheit.startswith("woch"):
                return jetzt + timedelta(weeks=n), m.end()
            if einheit.startswith("monat"):
                return _monate_dazu(jetzt, n), m.end()
            return _monate_dazu(jetzt, n * 12), m.end()

    m = re.match(r"^(nächste[nrs]?|naechste[nrs]?|kommende[nrs]?)\s+"
                 r"(woche|monat|jahr)\b", rest, re.I)
    if m:
        einheit = m.group(2).lower()
        if einheit == "woche":
            return jetzt + timedelta(weeks=1), m.end()
        if einheit == "monat":
            return _monate_dazu(jetzt, 1), m.end()
        return _monate_dazu(jetzt, 12), m.end()

    m = re.match(rf"^(nächste[nrs]?|naechste[nrs]?|kommende[nrs]?|"
                 rf"diese[nrs]?)?\s*({WOCHENTAGSMUSTER})\b", rest, re.I)
    if m:
        vorsatz = (m.group(1) or "").lower()
        return _naechster_wochentag(
            jetzt, WOCHENTAGE[m.group(2).lower()],
            naechste_woche=vorsatz.startswith(("näch", "naech", "komm")),
            diese_woche=vorsatz.startswith("dies")), m.end()

    m = re.match(r"^(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{2,4})?", rest)
    if m:
        tag, monat = int(m.group(1)), int(m.group(2))
        jahr = int(m.group(3)) if m.group(3) else None
        d = _zusammensetzen(jetzt, tag, monat, jahr)
        if d:
            return d, m.end()

    m = re.match(rf"^(?:(\d{{1,2}})\.?|({ORDNUNGSMUSTER}))\s*"
                 rf"({MONATSMUSTER})\b\s*(\d{{4}})?", rest, re.I)
    if m:
        tag = int(m.group(1)) if m.group(1) else ORDNUNGSZAHLEN[m.group(2).lower()]
        monat = MONATE[m.group(3).lower()]
        jahr = int(m.group(4)) if m.group(4) else None
        d = _zusammensetzen(jetzt, tag, monat, jahr)
        if d:
            return d, m.end()

    m = re.match(r"^(?:am\s+)?wochenende\b", rest, re.I)
    if m:
        return _naechster_wochentag(jetzt, 5, False, False), m.end()

    return None, 0


def _zusammensetzen(jetzt: datetime, tag: int, monat: int,
                    jahr: int | None) -> datetime | None:
    if not (1 <= monat <= 12 and 1 <= tag <= 31):
        return None
    if jahr is not None and jahr < 100:
        jahr += 2000
    for versuch in ([jahr] if jahr else [jetzt.year, jetzt.year + 1]):
        try:
            d = jetzt.replace(year=versuch, month=monat, day=tag,
                              hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            continue
        # Ohne Jahresangabe ist ein bereits vergangenes Datum das nächste Jahr.
        if jahr or d.date() >= jetzt.date():
            return d
    return None


def _uhrzeit_versuchen(rest: str) -> tuple[tuple[int, int] | None, int]:
    m = re.match(r"^(?:um\s+)?(\d{1,2})[:.](\d{2})\s*(?:uhr)?\b", rest, re.I)
    if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
        return (int(m.group(1)), int(m.group(2))), m.end()

    m = re.match(rf"^(?:um\s+)?(\d{{1,2}}|{ZAHLMUSTER})\s*uhr"
                 rf"(?:\s*(\d{{1,2}}|{ZAHLMUSTER}))?\b", rest, re.I)
    if m:
        stunde = _zahl(m.group(1))
        minute = _zahl(m.group(2)) if m.group(2) else 0
        if stunde is not None and stunde < 24 and (minute or 0) < 60:
            return (stunde, minute or 0), m.end()

    m = re.match(rf"^(?:um\s+)?halb\s+(\d{{1,2}}|{ZAHLMUSTER})\b", rest, re.I)
    if m:
        stunde = _zahl(m.group(1))
        if stunde is not None:
            return ((stunde - 1) % 24, 30), m.end()

    m = re.match(rf"^(?:um\s+)?(?:viertel\s+vor|dreiviertel)\s+"
                 rf"(\d{{1,2}}|{ZAHLMUSTER})\b", rest, re.I)
    if m:
        stunde = _zahl(m.group(1))
        if stunde is not None:
            return ((stunde - 1) % 24, 45), m.end()

    m = re.match(rf"^(?:um\s+)?viertel\s+nach\s+(\d{{1,2}}|{ZAHLMUSTER})\b",
                 rest, re.I)
    if m:
        stunde = _zahl(m.group(1))
        if stunde is not None:
            return (stunde % 24, 15), m.end()

    m = re.match(rf"^({TAGESZEITMUSTER})\b", rest, re.I)
    if m:
        return TAGESZEITEN[m.group(1).lower()], m.end()

    return None, 0


def _termin_lesen(rest: str, jetzt: datetime,
                  standardzeit: tuple[int, int]) -> tuple[datetime | None, int]:
    """Datum und Uhrzeit in beliebiger Reihenfolge lesen.

    „nächsten Montag um zehn“ und „um zehn am Montag“ sollen beide gehen,
    deshalb wird abwechselnd probiert, bis nichts mehr passt.
    """
    pos = 0
    datum: datetime | None = None
    uhrzeit: tuple[int, int] | None = None
    while True:
        fuell = FUELLWORT.match(rest[pos:])
        if fuell and fuell.end():
            probe = pos + fuell.end()
            leer = re.match(r"^\s*", rest[probe:])
            probe += leer.end() if leer else 0
        else:
            leer = re.match(r"^\s*", rest[pos:])
            probe = pos + (leer.end() if leer else 0)

        if datum is None:
            d, laenge = _datum_versuchen(rest[probe:], jetzt)
            if d is not None:
                datum, pos = d, probe + laenge
                continue
        if uhrzeit is None:
            z, laenge = _uhrzeit_versuchen(rest[probe:])
            if z is not None:
                uhrzeit, pos = z, probe + laenge
                continue
        break

    if datum is None:
        return None, 0
    stunde, minute = uhrzeit if uhrzeit else standardzeit
    return datum.replace(hour=stunde, minute=minute, second=0,
                         microsecond=0), pos


# -- Tags -------------------------------------------------------------

def _tags_lesen(text: str, bekannt: list[str]) -> tuple[list[str], list[tuple[int, int]]]:
    bekannt_klein = {t.lower(): t for t in bekannt}
    gefunden: list[str] = []
    spannen: list[tuple[int, int]] = []

    for m in HASHTAG.finditer(text):
        gefunden.append(bekannt_klein.get(m.group(1).lower(), m.group(1)))
        spannen.append((m.start(), m.end()))

    for m in TAG_AUSLOESER.finditer(text):
        if any(a <= m.start() < b for a, b in spannen):
            continue
        ausdruecklich = bool(TAG_AUSDRUECKLICH.match(m.group(1)))
        pos = m.end()
        hier: list[str] = []
        ende = m.start()
        while True:
            w = re.match(r"^([A-Za-zÄÖÜäöüß][\wÄÖÜäöüß-]*)", text[pos:])
            if not w:
                break
            wort = w.group(1)
            treffer = bekannt_klein.get(wort.lower())
            if treffer is None:
                # Ein unbekanntes Wort wird nur nach einem eindeutigen
                # Auslöser zum neuen Tag. Sonst wäre „ein schöner Tag“
                # sofort ein Tag „schöner“.
                if not (ausdruecklich and not hier):
                    break
                treffer = wort[0].upper() + wort[1:]
            hier.append(treffer)
            pos += w.end()
            ende = pos
            trenner = re.match(r"^\s*(?:,|und|sowie|/)\s*", text[pos:], re.I)
            if not trenner:
                break
            pos += trenner.end()
        if hier:
            gefunden.extend(hier)
            spannen.append((m.start(), ende))

    # Bekannte Tags, die einfach so im Text vorkommen, werden vorgeschlagen -
    # aber nicht aus dem Text entfernt, sie gehören ja zum Gedanken.
    for klein, echt in bekannt_klein.items():
        if re.search(rf"\b{re.escape(klein)}\b", text, re.I):
            gefunden.append(echt)

    einmalig: list[str] = []
    for t in gefunden:
        if t.lower() not in {x.lower() for x in einmalig}:
            einmalig.append(t)
    return einmalig, spannen


# -- Aufräumen --------------------------------------------------------

def _saeubern(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,;:])\s*([.!?])", r"\2", text)
    # Zwei Satzzeichen hintereinander entstehen beim Herauslösen („notiert:,“)
    text = re.sub(r"([,;:])(?:\s*[,;:])+", r"\1", text)
    text = re.sub(r"^[\s,;:.\-–]+", "", text)
    text = re.sub(r"\b(und|sowie|außerdem|ausserdem|dann|noch)\s*([.!?]?)\s*$",
                  r"\2", text, flags=re.I)
    text = re.sub(r"[\s,;:\-–]+$", "", text)
    text = text.strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    # Stand die Wiedervorlage am Satzende, ist der Schlusspunkt mit ihr
    # verschwunden - er gehört aber zum Gedanken, nicht zur Anweisung.
    if text and text[-1] not in ".!?…:)\"”":
        text += "."
    return text


def auswerten(rohtext: str, bekannte_tags: list[str] | None = None,
              jetzt: datetime | None = None,
              standardzeit: str = "09:00") -> Auswertung:
    """Diktat in Notiztext, Tags und Wiedervorlage zerlegen."""
    jetzt = (jetzt or datetime.now()).replace(second=0, microsecond=0)
    bekannte_tags = bekannte_tags or []
    try:
        stunde, minute = (int(x) for x in standardzeit.split(":", 1))
    except ValueError:
        stunde, minute = 9, 0

    text = rohtext.strip()
    zu_entfernen: list[tuple[int, int]] = []
    entfernt: list[str] = []
    faellig: datetime | None = None

    for m in WIEDERVORLAGE.finditer(text):
        termin, laenge = _termin_lesen(text[m.end():], jetzt, (stunde, minute))
        if termin is None:
            continue          # Auslöser ohne Datum - Text bleibt, wie er ist
        faellig = termin
        ende = m.end() + laenge
        # ein angehängtes Satzzeichen gleich mitnehmen
        nach = re.match(r"^\s*[,.;]", text[ende:])
        if nach:
            ende += nach.end()
        zu_entfernen.append((m.start(), ende))
        entfernt.append(text[m.start():ende].strip())
        break

    rest = text
    tags, tag_spannen = _tags_lesen(rest, bekannte_tags)
    for a, b in tag_spannen:
        if not any(x <= a < y for x, y in zu_entfernen):
            zu_entfernen.append((a, b))
            entfernt.append(text[a:b].strip())

    behalten: list[str] = []
    letzte = 0
    for a, b in sorted(zu_entfernen):
        if a < letzte:
            continue
        behalten.append(text[letzte:a])
        letzte = b
    behalten.append(text[letzte:])

    return Auswertung(text=_saeubern("".join(behalten)), tags=tags,
                      faellig=faellig, entfernt=[e for e in entfernt if e])
