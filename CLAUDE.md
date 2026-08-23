# Hinweise für Claude

Dieses Repository ist **Denkzettel** - ein Sprachnotizbuch für Debian-
und Arch-basierte Systeme: Gedanken sprechen, mit Tags einsortieren, mit
einer Wiedervorlage im Kalender versehen. Stephan arbeitet allein daran
(kein Team) - bitte durchgehend "du" statt "ihr/euch" verwenden, und
Stephan darf dich gerne "ClaudIA" nennen.

**Lies zuerst [README.md](README.md)** für den vollständigen Zusammenhang
und [TODO.md](TODO.md) für den Stand. Diese Datei hier ist nur eine kurze
Landkarte, keine Doppelung.

Denkzettel gehört zur **DialOS-Familie** (`../DialOS`) und übernimmt von
dort Optik (abgeleitetes Symbol) und Haltung, aber **nicht** die
Spracherkennung: DialOS benutzt Vosk mit fester Befehlsgrammatik,
Denkzettel whisper.cpp für freie Rede. Begründung steht im README.

## Landkarte

| Datei | Zweck |
|---|---|
| `denkzettel/config.py` | Einstellungen (`~/.config/denkzettel/config.ini`) |
| `denkzettel/audio.py` | Mikrofone finden, aufnehmen, Pegel messen |
| `denkzettel/stt.py` | whisper.cpp aufrufen |
| `denkzettel/textparser.py` | **das Herzstück**: Tags und Wiedervorlage aus dem Diktat |
| `denkzettel/store.py` | SQLite (Notizen, Tags) |
| `denkzettel/calendar_sync.py` | iCalendar bauen, CalDAV, .ics-Rückfall |
| `denkzettel/ui/capture.py` | Erfassen-Fenster (Aufnahme → prüfen → speichern) |
| `denkzettel/ui/notebook.py` | Notizbuch mit Registern je Tag |
| `denkzettel/ui/settings.py` | Einstellungen, u.a. Mikrofon mit Probe |
| `denkzettel/ui/form.py` | Notizformular, von beiden Fenstern benutzt |
| `assets/icon-bauen.py` | erzeugt das Symbol aus dem DialOS-Icon |
| `install.sh` | Einrichtung für Debian und Arch |

Bezeichner im Quelltext sind englisch, Kommentare und Oberfläche deutsch -
wie in Stephans anderen Projekten.

## Regeln, die aus Fehlern stammen

1. **Nichts still fehlschlagen lassen.** Die Regel kommt aus DialOS und
   gilt hier genauso. Umgesetzt an drei Stellen: Pegelanzeige beim
   Aufnehmen (stummes Mikrofon), Meldung bei abgezogenem Gerät (statt
   leerer Datei), sichtbare Meldung wenn der Kalendereintrag hakt (die
   Notiz ist gespeichert, nur der Termin nicht).
2. **Programmnamen prüfen, nicht raten.** `/usr/bin/whisper` ist auf
   Manjaro **openai-whisper**, nicht whisper.cpp - andere Parameter.
   `stt.ist_whisper_cpp()` prüft mehrdeutige Namen vor der Verwendung.
   Wäre das nicht drin, schlüge erst das erste Diktat fehl.
3. **Die Auswertung darf sich irren, aber nichts verschlucken.** Was
   `textparser.py` nicht sicher erkennt, bleibt im Notiztext stehen. Ein
   falsch gesetzter Tag ist ärgerlich, ein verlorener Halbsatz ist
   schlimmer. Deshalb landet auch alles im Fenster zur Bestätigung.
4. **Ein Termin darf nicht am Netz scheitern.** Kein Server erreichbar →
   .ics-Datei → Status „offen“ → `denkzettel nachtragen` reicht nach.
   Die Ersatzdatei wird erst gelöscht, wenn der Server sie hat.
5. **Alles mit der Tastatur bedienbar** (Stephans Vorgabe), und jeder
   Befehl steht zusätzlich im Menü - man soll ihn wiederfinden können,
   ohne ihn auswendig zu wissen.

## Was noch niemand belegt hat

Stand 2026-08-23 ist **kein einziges echtes Diktat** durchgelaufen und
`install.sh` ist nie vollständig ausgeführt worden. Geprüft sind die
Bausteine einzeln (Auswertung an 21 Beispielen, .ics-Erzeugung,
Mikrofon-Erkennung am echten Gerät, Oberfläche im Rauchtest). Die
vollständige Liste steht in [TODO.md](TODO.md) unter „Muss vor dem ersten
echten Einsatz passieren“ - nicht überspringen und nicht als erledigt
behandeln, bevor es am Gerät lief.
