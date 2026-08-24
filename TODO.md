[Deutsch](TODO.md) | [English](TODO.en.md) | [Änderungsprotokoll](README.md#änderungsprotokoll)

# TODO

Laufende Liste offener Punkte. Oben steht, was noch offen ist. Erledigtes
wird nicht gelöscht, sondern nach unten verschoben - mit dem Datum, an
dem es fertig wurde.

## Offen

### Muss vor dem ersten echten Einsatz passieren

- [ ] **Tastenkürzel `Meta`+`N` unter Plasma prüfen.** Die
  .desktop-Datei steht jetzt auf `NoDisplay=true`. Ob kglobalaccel das
  Kürzel auch bei einem versteckten Eintrag noch registriert, ist
  ungeprüft - falls nicht, den Eintrag direkt in `kglobalshortcutsrc`
  schreiben.
- [ ] **Ladezeit des Modells.** Jedes Diktat kostet rund 27 Sekunden,
  fast unabhängig von der Länge - das ist das Laden von
  `large-v3-turbo`. Für einen kurzen Gedanken ist das viel. Zu prüfen:
  kleineres Modell (`medium`, `small`) im Vergleich, oder whisper.cpp
  als Dienst mitlaufen lassen, statt es bei jedem Diktat neu zu starten.
- [ ] **CalDAV gegen die echte Nextcloud prüfen.** Der Code ist gegen
  RFC 5545/4791 gebaut und die erzeugte .ics-Datei stimmt (Faltung,
  Maskierung, UTC geprüft) - aber noch nie hat ein Server sie
  angenommen. Zu prüfen: App-Passwort, richtige Kalenderadresse,
  Umlaute, Erinnerung.
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

### Einrichtung und erste Prüfung am Gerät (2026-08-23)

- [x] **`install.sh` ist auf Stephans Manjaro durchgelaufen.** Alle
  Abhängigkeiten waren vorhanden (also kein sudo nötig), whisper.cpp
  1.9.3-dev gebaut, Modell geladen, Menüeinträge gesetzt.
- [x] **Erkennung gegen bekannten Text geprüft**, mit dem Verfahren aus
  DialOS: nicht ins Mikrofon sprechen, sondern vorhandene Aufnahmen mit
  hinterlegtem Wortlaut durchschicken. Vier DialOS-Sprachbeispiele
  (Anna) durch whisper.cpp - inhaltlich alle vier richtig, Abweichungen
  nur bei Zeichensetzung und Groß-/Kleinschreibung, ein Wortfehler
  („Sage“ → „Zeige“).
- [x] **Doppelter Menüeintrag behoben.** Denkzettel stand zweimal und in
  zwei Kategorien im Startmenü. Ursache: `Categories=Office;TextEditor;`
  (KDE sortiert `TextEditor` zusätzlich unter Dienstprogramme) und eine
  zweite .desktop-Datei, die nur das Tastenkürzel tragen sollte. Jetzt
  ein sichtbarer Eintrag unter Dienstprogramme, die zweite Datei auf
  `NoDisplay=true`.
- [x] **Mikrofon-Auswahl aus dem Installationsskript in eine Einführung
  beim ersten Start verlegt** (Stephans Vorgabe), mit Erklärung der
  Sprechweise und der Tastenbefehle. Jederzeit wieder aufrufbar über
  *Hilfe → Einführung* oder `denkzettel einfuehrung`.

### Erstes echtes Diktat über die Webcam (2026-08-24)

- [x] **Erstes Diktat über das Webcam-Mikrofon lief durch - nach zwei
  Korrekturen.** Die Aufnahme selbst war nie das Problem: Der
  Pegelverlauf zeigte von Anfang an ein sauberes Sprachmuster, keine
  Stille, keine Aussetzer. Zwei andere Dinge haben die erste Erkennung
  trotzdem entwertet:
  1. Die Eingangslautstärke der Webcam stand ab Werk auf 76 % statt
     100 % - unnötig leise, jetzt hochgesetzt.
  2. Ein Gerätename außerhalb des Wortschatzes („RabKarcher“) wurde zu
     Kauderwelsch („Rabkascha“). Datum und Uhrzeit im selben Satz waren
     dagegen exakt richtig - das Muster passte zu einem
     Vokabular-Problem, nicht zu schlechter Tonqualität.
- [x] **Eigene Wörter für whisper.cpp** (`[erkennung] wortschatz` in der
  Konfiguration, Feld in Extras → Einstellungen → Spracherkennung).
  Werden zusammen mit den bekannten Tags als `--prompt` mitgegeben.
  Geprüft an genau diesem Fall: ohne Prompt „Rabkascha, Auflagen“, mit
  Prompt „Rabkarcher, Auflagen“ - deutlich näher am tatsächlich
  gesagten „RabKarcher aufladen“. „Auflagen“ statt „aufladen“ blieb
  bestehen - eine akustische Verwechslung zweier ähnlich klingender
  Wörter, kein Vokabular-Problem, also durch einen Prompt nicht zu
  beheben.
- [x] **Kalender-Einrichtung in die Einführung verlegt**, aus demselben
  Grund wie beim Mikrofon (Stephans Vorgabe): Eine neue Seite
  „Wohin mit der Wiedervorlage?“ bindet dieselbe Kalender-Ansicht wie
  die Einstellungen ein, samt „Kalender suchen …“. Die Einführung hat
  jetzt sechs statt fünf Seiten; die Kalender-Erklärung im Schluss-Text
  ist entfallen, weil sie jetzt vorher schon geklärt ist.
  Mikrofon- und Kalenderauswahl werden dabei sofort gespeichert, nicht
  erst am Ende - wer die Einführung nach diesen Seiten über
  „Überspringen“ verlässt, behält die getroffene Wahl trotzdem.

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
