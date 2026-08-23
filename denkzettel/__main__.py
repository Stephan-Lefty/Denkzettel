#!/usr/bin/env python3
"""
Denkzettel: Einstiegspunkt.

    denkzettel                  Notizbuch öffnen
    denkzettel erfassen         sofort aufnehmen (das Tastenkürzel)
    denkzettel mikrofone        Mikrofone anzeigen, --waehlen zum Festlegen
    denkzettel kalender         Kalender auf dem Server auflisten
    denkzettel nachtragen       offene Termine in den Kalender nachreichen
    denkzettel pruefen          Einrichtung prüfen
    denkzettel einstellungen    Einstellungen öffnen
"""
from __future__ import annotations

import argparse
import sys

from . import __version__, audio, config, store


def _speicher() -> store.Speicher:
    config.verzeichnisse_anlegen()
    return store.Speicher()


def befehl_erfassen(cfg) -> int:
    from .ui import common
    from .ui.capture import ErfassenFenster
    app = common.anwendung(sys.argv)
    speicher = _speicher()
    fenster = ErfassenFenster(cfg, speicher)
    fenster.show()
    fenster.raise_()
    fenster.activateWindow()
    ergebnis = fenster.exec()
    speicher.schliessen()
    del app
    return 0 if ergebnis else 1


def befehl_notizbuch(cfg) -> int:
    from .ui import common
    from .ui.notebook import NotizbuchFenster
    app = common.anwendung(sys.argv)
    speicher = _speicher()
    fenster = NotizbuchFenster(cfg, speicher)
    fenster.show()
    ergebnis = app.exec()
    speicher.schliessen()
    return ergebnis


def befehl_einstellungen(cfg) -> int:
    from .ui import common
    from .ui.settings import EinstellungenDialog
    app = common.anwendung(sys.argv)
    dialog = EinstellungenDialog(cfg)
    ergebnis = dialog.exec()
    del app
    return 0 if ergebnis else 1


def befehl_mikrofone(cfg, waehlen: bool) -> int:
    gefunden = audio.quellen()
    gewaehlt = config.wert(cfg, "aufnahme", "geraet")
    standard = audio.standardquelle()

    if not gefunden:
        print("Kein Mikrofon gefunden.")
        print("Ist eines angeschlossen? `pactl list sources` zeigt alle Quellen.")
        return 1

    print("Gefundene Mikrofone:\n")
    print(f"  0) Standardmikrofon des Systems"
          + (f" – zurzeit: {audio.beschreibung_zu(standard)}" if standard else ""))
    for i, quelle in enumerate(gefunden, start=1):
        marke = " *" if quelle.name == gewaehlt else "  "
        print(f" {marke}{i}) {quelle.anzeige}")
    print()
    if gewaehlt:
        print(f"Eingestellt (*): {audio.beschreibung_zu(gewaehlt)}")
    else:
        print("Eingestellt: Standardmikrofon des Systems")

    if not waehlen:
        return 0

    print("\nWelches Mikrofon soll Denkzettel benutzen?")
    print("Nummer eingeben, Eingabetaste für unverändert.")
    try:
        eingabe = input("Nummer: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return 1
    if not eingabe:
        print("Unverändert.")
        return 0
    if not eingabe.isdigit() or int(eingabe) > len(gefunden):
        print("Das ist keine der angebotenen Nummern - unverändert.")
        return 1

    nummer = int(eingabe)
    neu = "" if nummer == 0 else gefunden[nummer - 1].name
    cfg.set("aufnahme", "geraet", neu)
    config.speichern(cfg)
    print(f"Gemerkt: {audio.beschreibung_zu(neu) if neu else 'Standardmikrofon des Systems'}")
    return 0


def befehl_kalender(cfg) -> int:
    from . import calendar_sync
    adresse = config.wert(cfg, "caldav", "url")
    if not adresse:
        print("Es ist keine Kalenderadresse eingetragen.")
        print("Trag die Sammel-Adresse ein, z. B.")
        print("  https://cloud.example.de/remote.php/dav/calendars/BENUTZER/")
        print(f"in {config.CONFIG_PATH} unter [caldav] url,")
        print("oder benutze `denkzettel einstellungen`.")
        return 1
    try:
        gefunden = calendar_sync.kalender_auflisten(
            adresse, config.wert(cfg, "caldav", "benutzer"),
            config.caldav_passwort(cfg))
    except Exception as e:                      # noqa: BLE001
        print(calendar_sync._klartext(e, adresse))
        return 1
    if not gefunden:
        print("Unter dieser Adresse liegt kein Kalender.")
        return 1
    print("Kalender auf dem Server:\n")
    for url, name in gefunden:
        print(f"  {name}\n    {url}\n")
    print("Die gewünschte Adresse unter [caldav] url eintragen.")
    return 0


def befehl_nachtragen(cfg) -> int:
    from . import calendar_sync
    speicher = _speicher()
    gut, schlecht, meldungen = calendar_sync.nachtragen(cfg, speicher)
    speicher.schliessen()
    for m in meldungen:
        print(m)
    print(f"{gut} nachgetragen, {schlecht} weiterhin offen.")
    return 0 if schlecht == 0 else 1


def befehl_pruefen(cfg) -> int:
    from . import calendar_sync, stt
    fehlt = 0

    print("Denkzettel – Einrichtung prüfen\n")

    prog = stt.programm(cfg)
    print(f"  whisper.cpp : {prog or 'FEHLT'}")
    mod = stt.modell(cfg)
    if mod:
        print(f"  Modell      : {mod.name} "
              f"({mod.stat().st_size / 1024 / 1024:.0f} MB)")
    else:
        print("  Modell      : FEHLT")
    fehlt += (prog is None) + (mod is None)

    gewaehlt = config.wert(cfg, "aufnahme", "geraet")
    if not gewaehlt:
        print(f"  Mikrofon    : Standard des Systems "
              f"({audio.beschreibung_zu(audio.standardquelle()) or 'keines'})")
    elif audio.vorhanden(gewaehlt):
        print(f"  Mikrofon    : {audio.beschreibung_zu(gewaehlt)}")
    else:
        print(f"  Mikrofon    : eingestellt, aber NICHT angeschlossen "
              f"({gewaehlt})")
        fehlt += 1

    modus = config.wert(cfg, "kalender", "modus", "auto")
    print(f"  Kalender    : Modus {modus}")
    if modus in ("auto", "caldav") and config.caldav_eingerichtet(cfg):
        gut, meldung = calendar_sync.verbindung_pruefen(cfg)
        print(f"                {meldung}")
        if not gut and modus == "caldav":
            fehlt += 1
    elif modus in ("auto", "caldav"):
        print("                kein CalDAV eingerichtet – "
              "Termine werden als Datei abgelegt")
    print(f"  Termindateien: {config.ics_verzeichnis(cfg)}")

    speicher = _speicher()
    print(f"\n  Notizen     : {len(speicher.liste())}")
    print(f"  Datenbank   : {speicher.pfad}")
    print(f"  Einstellungen: {config.CONFIG_PATH}")
    speicher.schliessen()

    print("\nAlles bereit." if fehlt == 0 else
          f"\n{fehlt} Punkt(e) offen – siehe oben.")
    return 0 if fehlt == 0 else 1


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        prog="denkzettel",
        description="Gedanken sprechen, mit Tags einsortieren und mit einer "
                    "Wiedervorlage im Kalender versehen.")
    zerleger.add_argument("--version", action="version",
                          version=f"Denkzettel {__version__}")
    unter = zerleger.add_subparsers(dest="befehl")
    unter.add_parser("erfassen", help="sofort aufnehmen")
    unter.add_parser("notizbuch", help="Notizbuch öffnen")
    unter.add_parser("einstellungen", help="Einstellungen öffnen")
    mikro = unter.add_parser("mikrofone", help="Mikrofone anzeigen")
    mikro.add_argument("--waehlen", action="store_true",
                       help="eines davon als Standard festlegen")
    unter.add_parser("kalender", help="Kalender auf dem Server auflisten")
    unter.add_parser("nachtragen", help="offene Termine nachreichen")
    unter.add_parser("pruefen", help="Einrichtung prüfen")

    args = zerleger.parse_args(argv)
    config.verzeichnisse_anlegen()
    cfg = config.laden()
    if not config.CONFIG_PATH.exists():
        config.speichern(cfg)

    if args.befehl == "erfassen":
        return befehl_erfassen(cfg)
    if args.befehl == "einstellungen":
        return befehl_einstellungen(cfg)
    if args.befehl == "mikrofone":
        return befehl_mikrofone(cfg, args.waehlen)
    if args.befehl == "kalender":
        return befehl_kalender(cfg)
    if args.befehl == "nachtragen":
        return befehl_nachtragen(cfg)
    if args.befehl == "pruefen":
        return befehl_pruefen(cfg)
    return befehl_notizbuch(cfg)


if __name__ == "__main__":
    sys.exit(main())
