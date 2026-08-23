[Deutsch](README.md) | [English](README.en.md) | [Änderungsprotokoll](#änderungsprotokoll) | [TODO](TODO.md)

# Denkzettel

Ein Sprachnotizbuch für Debian- und Arch-basierte Systeme: Gedanken
**sprechen**, sie mit **Tags** einsortieren (privat, beruflich, DialOS …)
und ihnen gleich eine **Wiedervorlage** mitgeben, die im Kalender landet.

Die Spracherkennung läuft **vollständig auf dem eigenen Rechner**. Es geht
kein Ton ins Netz - weder zum Erkennen noch zum Speichern.

Dieses Projekt ist in Zusammenarbeit mit [Claude](https://claude.com)
entstanden und gehört zur [DialOS](https://dialos.org)-Familie - daher
auch das verwandte Symbol: dieselbe Dame, aber statt Schallwellen
schreibt ein Stift mit.

## Wie es sich anfühlt

Tastenkürzel drücken. Sprechen:

> „Angebot für Meier nachrechnen, Tag beruflich,
> Wiedervorlage nächsten Montag um zehn Uhr.“

Leertaste. Denkzettel zeigt:

| | |
|---|---|
| **Notiz** | Angebot für Meier nachrechnen. |
| **Tag** | beruflich ✓ |
| **Wiedervorlage** | Montag, 24.08.2026, 10:00 |

Prüfen, `Strg`+`S`. Der Termin steht im Kalender, die Notiz im Register
„beruflich“.

Die Angaben zu Tag und Wiedervorlage werden aus dem Gesprochenen
herausgelöst und **aus dem Notiztext entfernt** - sie sind Anweisung,
nicht Inhalt. Was nicht sicher erkannt wird, bleibt im Text stehen,
statt zu verschwinden.

## Was verstanden wird

**Tags** nach `Tag`, `Tags`, `Schlagwort`, `Kategorie`, `Stichwort` -
mehrere mit „und“ oder Komma. Ein bekannter Tag wird auch dann
vorgeschlagen, wenn er einfach so im Satz vorkommt. `#DialOS` geht auch.

**Wiedervorlage** nach `Wiedervorlage`, `erinnere mich`, `Erinnerung`,
`nachfassen`, `Termin`:

| Gesprochen | Ergebnis |
|---|---|
| heute · morgen · übermorgen | der jeweilige Tag |
| in drei Tagen · in 14 Tagen · in zwei Wochen · in einem Monat | gerechnet ab heute |
| nächsten Montag · am Freitag · diesen Mittwoch | der nächste passende Tag |
| nächste Woche · nächsten Monat · nächstes Jahr | + 1 Woche / Monat / Jahr |
| am Wochenende | der kommende Samstag |
| am 15. September · am dritten Oktober · 01.09.2026 | festes Datum |
| um zehn Uhr · um 14:30 · um halb neun · viertel nach acht | Uhrzeit |
| morgens · mittags · nachmittags · abends · früh | 8 / 12 / 15 / 18 / 8 Uhr |

Ohne Uhrzeitangabe gilt die eingestellte Standardzeit (ab Werk 9:00).
Reihenfolge egal: „um zehn am Montag“ versteht es genauso.

## Das Notizbuch

Ein Fenster mit **Registern** wie in einem echten Notizbuch: „Alle“,
„Wiedervorlagen“ und je ein Register pro Tag.

**Alles geht mit der Tastatur** - Register anlegen, umbenennen, löschen
und wechseln, Notizen anlegen, bearbeiten, abhaken, löschen. Jeder
Befehl steht zusätzlich im Menü, damit man ihn wiederfindet, ohne ihn
auswendig zu können. Übersicht im Programm mit `F1`.

| Taste | Wirkung |
|---|---|
| `Strg`+`N` | Neue Notiz diktieren |
| `Strg`+`Umschalt`+`N` | Notiz tippen |
| `Eingabe` / `F2` | Notiz bearbeiten |
| `Strg`+`D` | erledigt / wieder offen |
| `Entf` | Notiz löschen |
| `Strg`+`F` | suchen |
| `Strg`+`T` | neues Register (Tag) |
| `Umschalt`+`F2` | Register umbenennen |
| `Strg`+`Umschalt`+`W` | Register löschen |
| `Strg`+`Bild auf/ab`, `Alt`+`1…9` | Register wechseln |

Wird ein Register gelöscht, bleiben die Notizen darin erhalten - nur der
Tag verschwindet. Beim Umbenennen wird der Tag überall mitgeführt; gibt
es den neuen Namen schon, werden beide zusammengelegt.

## Kalender

Zwei Wege, umschaltbar in den Einstellungen:

* **CalDAV** - der Termin geht direkt in den Nextcloud-Kalender und ist
  damit auch auf dem Handy da. Bei Nextcloud ein **App-Passwort**
  benutzen, nicht das Anmelde-Passwort.
* **Termindatei (.ics)** - der Termin wird als Datei abgelegt, die man in
  Thunderbird als lokalen Kalender einbindet. Ohne Server, ohne
  Zugangsdaten.

Ab Werk steht es auf **automatisch**: erst der Server, und wenn der nicht
erreichbar ist, ersatzweise die Datei. Die Notiz merkt sich dann, dass
der Termin noch nicht auf dem Server steht; `Strg`+`R` (oder
`denkzettel nachtragen`) reicht ihn nach, sobald wieder Netz da ist. Ein
Termin darf nicht verloren gehen, nur weil gerade kein Netz war.

Die Adresse des eigenen Kalenders muss man nicht suchen -
„Kalender suchen …“ in den Einstellungen holt die Liste vom Server.

## Beim ersten Start: die Einführung

Beim allerersten Start läuft ein kurzer Assistent - fünf Seiten, eine
Minute: was das Programm tut, **wie man spricht** (mit Beispielsatz und
dem, was daraus wird), **welches Mikrofon** genommen wird, **welche
Tasten** es gibt, und was noch offen ist (Kalender).

Er ist nicht nur Erklärung, sondern auch der Weg, das **Mikrofon zu
wechseln** - deshalb lässt er sich jederzeit wieder aufrufen:

* im Notizbuch über **Hilfe → Einführung**
* im Terminal mit `denkzettel einfuehrung`

## Mikrofon

Viele Rechner haben ein eingebautes Mikrofon **und** das einer Webcam.
Welches gemeint ist, kann kein Programm raten, deshalb fragt die
Einführung danach und zeigt alle gefundenen Geräte an - mit einer
**Probe**, bei der man ein paar Worte spricht und am Pegelbalken sieht,
ob das Gerät wirklich etwas hört. Später ändern: Einführung erneut
aufrufen, **Extras → Einstellungen** oder

```
denkzettel mikrofone --waehlen
```

Zwei Dinge sind dabei bewusst gelöst, weil sie sonst still schiefgehen:

* Beim Aufnehmen zeigt ein **Pegelbalken** die Aussteuerung. Schlägt er
  nicht aus, steht das sofort als Warnung im Fenster - ein stummes
  Mikrofon fällt sonst erst auf, wenn der Gedanke schon weg ist.
* Ist das eingestellte Gerät **nicht angeschlossen** (Webcam abgezogen),
  nimmt Denkzettel über die Standardquelle auf und **sagt das**, statt
  eine leere Datei zu erzeugen.

## Installation

```
git clone https://github.com/Stephan-Lefty/Denkzettel.git
cd Denkzettel
./install.sh
```

Das Skript erkennt Debian- und Arch-basierte Systeme selbst, installiert
die Pakete, übersetzt whisper.cpp, lädt das Spracherkennungs-Modell
(ab Werk `large-v3-turbo`, etwa 574 MB), legt die Menüeinträge an, fragt
nach dem Mikrofon und richtet das Tastenkürzel `Meta`+`N` ein.

Kleineres Modell für schwächere Rechner:

```
./install.sh --modell medium     # 539 MB
./install.sh --modell small      # 190 MB
```

Prüfen, ob alles bereit ist:

```
denkzettel pruefen
```

### Befehle

| Befehl | Wirkung |
|---|---|
| `denkzettel` | Notizbuch öffnen |
| `denkzettel erfassen` | sofort aufnehmen (das Tastenkürzel) |
| `denkzettel einfuehrung` | Einführung erneut zeigen |
| `denkzettel mikrofone --waehlen` | Mikrofon festlegen |
| `denkzettel kalender` | Kalender auf dem Server auflisten |
| `denkzettel nachtragen` | offene Termine nachreichen |
| `denkzettel pruefen` | Einrichtung prüfen |
| `denkzettel einstellungen` | Einstellungen öffnen |

## Wo liegt was

| Was | Wo |
|---|---|
| Einstellungen | `~/.config/denkzettel/config.ini` |
| Notizen (SQLite) | `~/.local/share/denkzettel/notizen.db` |
| Tonaufnahmen | `~/.local/share/denkzettel/aufnahmen/` |
| Termindateien | `~/.local/share/denkzettel/kalender/` |
| Spracherkennung | `~/.local/share/denkzettel/whisper.cpp/`, `…/modelle/` |

Die Notizen liegen in **einer** Datei - kopieren genügt als Sicherung.

## Warum whisper.cpp und nicht Vosk

DialOS erkennt Sprache mit Vosk, und das aus gutem Grund: Dort geht es um
eine feste Liste von Befehlssätzen, und mit eingeschränkter Grammatik ist
Vosk dabei sehr zuverlässig.

Hier ist es umgekehrt - frei gesprochene Gedanken, kein festes
Vokabular. Genau dabei ist Vosk deutlich schwächer, und Nachkorrigieren
kostet mehr Zeit, als das größere Modell an Rechenzeit braucht. Beides
läuft offline, insofern ändert sich am Grundsatz nichts.

## Änderungsprotokoll

### 0.1.0 (2026-08-23)

Erste Fassung.

* **Einführung beim ersten Start** statt einer Frage im
  Installationsskript (Stephans Vorgabe). Fünf Seiten: was das Programm
  tut, wie man spricht, Mikrofon-Auswahl mit Probe, Tastenbefehle,
  Ausblick. Jederzeit wieder aufrufbar über *Hilfe → Einführung* oder
  `denkzettel einfuehrung` - sie ist auch der Weg, das Mikrofon zu
  wechseln. Begründung: Eine Frage, die einmal im Terminal durchläuft,
  sieht man nie wieder, und man beantwortet sie, bevor man das Programm
  kennt.
* **Ein Menüeintrag, unter Dienstprogrammen.** Anfangs standen zwei
  Einträge in zwei Kategorien: `Categories=Office;TextEditor;` bringt
  KDE dazu, das Programm sowohl unter Büroprogramme als auch unter
  Dienstprogramme einzusortieren, und die zweite .desktop-Datei war nur
  als Träger des Tastenkürzels gedacht. Sie steht jetzt auf
  `NoDisplay=true`; „Gedanken aufnehmen“ hängt als Aktion am einen
  Eintrag.
* **Erkennung gegen bekannten Text geprüft** (2026-08-23): vier
  DialOS-Sprachbeispiele mit hinterlegtem Wortlaut durch whisper.cpp
  geschickt. Inhaltlich alle vier richtig; Abweichungen nur bei
  Zeichensetzung und Groß-/Kleinschreibung, ein einziger Wortfehler
  („Sage“ → „Zeige“). Etwa 27 Sekunden je Diktat - das ist im
  Wesentlichen die Ladezeit des Modells, nicht die Länge der Aufnahme.
* Aufnahme über PulseAudio/PipeWire (`parecord`, ersatzweise `arecord`)
  mit Pegelanzeige, Höchstdauer und Warnung bei stummem Mikrofon.
* Mikrofon-Auswahl bei der Installation und jederzeit über
  `denkzettel mikrofone --waehlen`. Geräte, die sich nutzlos beschreiben,
  werden über den Produktnamen aus der Gerätekennung kenntlich gemacht -
  aus „EEM Gadget Mono“ wird „UGREEN AI Camera CM930 4K“.
* Spracherkennung über whisper.cpp, vollständig offline. Die Suche nach
  dem Programm ist bewusst streng: Auf vielen Systemen liegt unter
  `/usr/bin/whisper` das ganz andere **openai-whisper** mit anderen
  Aufrufparametern. Mehrdeutige Namen werden vor der Verwendung geprüft,
  sonst schlüge erst das erste Diktat fehl.
* Deutsche Auswertung des Diktats: Tags und Wiedervorlage werden
  herausgelöst, der Notiztext bleibt sauber. Relative Angaben
  („in drei Tagen“, „nächsten Montag“), feste Daten, Uhrzeiten in Wort
  und Ziffer, Tageszeiten - Datum und Uhrzeit in beliebiger Reihenfolge.
* Notizbuch mit Registern je Tag, vollständig mit der Tastatur bedienbar;
  Register anlegen, umbenennen (mit Zusammenlegen), löschen.
* Kalender über CalDAV mit Rückfall auf Termindateien und Nachreichen,
  sobald der Server wieder erreichbar ist. Kalendersuche per PROPFIND.
* Eigenes Symbol, aus dem DialOS-App-Icon abgeleitet: Die Vorlage wird in
  eine Strichzeichnung mit Transparenz zurückgerechnet, die Schallwellen
  werden entfernt, Schreiblinie und Stift kommen dazu. Das Bauskript
  rechnet nach, dass der Stift den Ring nicht berührt, und bricht sonst
  ab.
