[Deutsch](TODO.md) | [English](TODO.en.md) | [Änderungsprotokoll](README.md#änderungsprotokoll)

# TODO

Laufende Liste offener Punkte. Oben steht, was noch offen ist. Erledigtes
wird nicht gelöscht, sondern nach unten verschoben - mit dem Datum, an
dem es fertig wurde.

## Offen

### Muss vor dem ersten echten Einsatz passieren

- [ ] **`install.sh` ist noch nie durchgelaufen.** Geschrieben und in
  Teilen geprüft (Syntax, Abhängigkeitsprüfung in beiden Richtungen,
  `--help`), aber der komplette Durchlauf mit whisper.cpp-Bau und
  Modell-Download steht aus. Das dauert einige Minuten und lädt 574 MB.
- [ ] **Noch kein einziges echtes Diktat.** Alle Bausteine sind einzeln
  geprüft, die Kette Mikrofon → whisper.cpp → Auswertung → Kalender aber
  noch nicht am Stück mit echter Stimme. Erst danach ist irgendetwas
  belegt. (Lehre aus DialOS: Ein Test gegen eine nicht installierte
  Änderung testet den alten Stand, ohne es zu sagen.)
- [ ] **CalDAV gegen die echte Nextcloud prüfen.** Der Code ist gegen
  RFC 5545/4791 gebaut und die erzeugte .ics-Datei stimmt (Faltung,
  Maskierung, UTC geprüft) - aber noch nie hat ein Server sie
  angenommen. Zu prüfen: App-Passwort, richtige Kalenderadresse,
  Umlaute, Erinnerung.
- [ ] **Tastenkürzel unter KDE prüfen.** `X-KDE-Shortcuts=Meta+N` in der
  .desktop-Datei ist der vorgesehene Weg, greift aber je nach
  Plasma-Fassung erst nach `kbuildsycoca6` oder einer Neuanmeldung. Wenn
  es nicht zuverlässig ist: eigenen Eintrag in `kglobalshortcutsrc`
  schreiben.

### Danach

- [ ] **Erinnerung auch ohne Kalender.** Zurzeit hängt die Wiedervorlage
  ganz am Kalender. Eine eigene Benachrichtigung beim Fälligwerden wäre
  unabhängig davon - besonders für den .ics-Weg, wo niemand garantiert,
  dass die Datei auch eingebunden wurde.
- [ ] **Erledigte Notiz und Kalendertermin.** Hakt man eine Notiz ab,
  bleibt der Termin im Kalender stehen. Löschen? Auf „erledigt“ setzen?
  Entscheiden, nicht raten.
- [ ] **Aufnahmen aufräumen.** Sie werden ab Werk behalten und niemand
  löscht sie. Vorschlag: nach X Tagen weg, mit Angabe des belegten
  Platzes in den Einstellungen.
- [ ] **Automatisch stoppen, wenn es still wird.** Zurzeit stoppt man mit
  der Leertaste oder es greift die Höchstdauer. Vorsicht: Denkpausen
  beim Diktieren sind normal - lieber zu spät stoppen als mitten im Satz.
- [ ] **Notizen ausgeben** (Markdown oder Textdatei), damit die Gedanken
  nicht in einer Datenbank festsitzen.
- [ ] **Anbindung an die DialOS-Sprachsteuerung** („Denkzettel öffnen“,
  „Gedanken aufnehmen“). Vorher gegen die Regeln in
  `DialOS/docs/sprachbefehle.md` prüfen: Stehen die Wörter überhaupt im
  Vosk-Wortschatz? „Denkzettel“ ist ein zusammengesetztes Wort und
  könnte fehlen.
- [ ] **Sprachauswertung ist nur deutsch.** whisper.cpp erkennt viele
  Sprachen, aber „Tag“/„Wiedervorlage“ versteht nur die deutsche
  Auswertung. Für andere Sprachen müsste `textparser.py` eigene
  Wortlisten bekommen.

### Offene Fragen

- [ ] **Wie streng darf die Tag-Erkennung sein?** „Das war ein schöner
  Tag“ wird richtig nicht als Tag gewertet, weil nach „Tag“ ein bekannter
  Tag folgen muss. Umgekehrt wird ein bekannter Tag, der nur so im Satz
  vorkommt, vorgeschlagen. Ob das im Alltag nervt, zeigt erst der
  Gebrauch.
- [ ] **„nächsten Montag“ am Sonntag** ergibt zurzeit den morgigen Tag.
  Sprachlich vertretbar, aber manche meinen die übernächste Woche. Erst
  ändern, wenn es im Gebrauch stört - nicht vorher wegdiskutieren.

## Erledigt

### Grundgerüst (2026-08-23)

- [x] Name gefunden: **Denkzettel** - ein Wort für beide Sprachen, wie
  DialOS, und als Sprachbefehl aussprechbar.
- [x] Symbol aus dem DialOS-App-Icon abgeleitet (Entwurf B: Schallwellen
  raus, Schreiblinie und Stift rein). Der Stift berührt den Ring nicht;
  das Bauskript rechnet den Abstand nach und bricht sonst ab.
- [x] Aufnahme über `parecord`/`arecord` mit Pegelanzeige und
  WAV-Reparatur bei hartem Abbruch.
- [x] Mikrofon-Auswahl bei der Installation und über
  `denkzettel mikrofone --waehlen`; Geräte mit nutzlosem Namen werden
  über den Produktnamen kenntlich gemacht.
- [x] whisper.cpp-Anbindung mit strenger Erkennung - `/usr/bin/whisper`
  ist auf Manjaro das ganz andere openai-whisper und wird richtig
  abgelehnt.
- [x] Deutsche Auswertung für Tags und Wiedervorlage, an 21 Beispielen
  geprüft.
- [x] Notizbuch mit Registern je Tag, vollständig mit der Tastatur
  bedienbar.
- [x] CalDAV mit Rückfall auf .ics und Nachreichen.
- [x] Abhängigkeiten werden bei der Installation geprüft, nur Fehlendes
  wird nachinstalliert, danach wird nachkontrolliert.
