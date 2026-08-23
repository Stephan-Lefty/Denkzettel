[Deutsch](README.md) | [English](README.en.md) | [Changelog](#changelog) | [TODO](TODO.en.md)

# Denkzettel

*Denkzettel* is German for a note you write yourself so you remember -
literally "thought slip". The name stays untranslated, like DialOS.

A voice notebook for Debian- and Arch-based systems: **speak** a thought,
file it under **tags** (private, work, DialOS …) and give it a
**follow-up date** that goes straight into your calendar.

Speech recognition runs **entirely on your own machine**. No audio leaves
the computer - neither for recognition nor for storage.

Built together with [Claude](https://claude.com). Part of the
[DialOS](https://dialos.org) family - hence the related icon: the same
lady, but instead of sound waves, a pencil writes along.

## How it feels

Press the shortcut. Speak (in German):

> „Angebot für Meier nachrechnen, Tag beruflich,
> Wiedervorlage nächsten Montag um zehn Uhr.“
> *(Recalculate the quote for Meier, tag work, follow up next Monday at ten.)*

Press space. Denkzettel shows:

| | |
|---|---|
| **Note** | Angebot für Meier nachrechnen. |
| **Tag** | beruflich ✓ |
| **Follow-up** | Monday, 24 Aug 2026, 10:00 |

Check it, press `Ctrl`+`S`. The appointment is in the calendar, the note
is in the "beruflich" tab.

Tag and follow-up instructions are lifted out of the spoken text and
**removed from the note** - they are instructions, not content. Anything
not recognised with confidence stays in the text rather than vanishing.

**Note on language:** the spoken-command parsing is German only. The
program is usable with any language whisper.cpp supports (see
`[erkennung] sprache` in the config file), but then tags and follow-up
dates have to be set in the window rather than dictated.

## What it understands

**Tags** after `Tag`, `Tags`, `Schlagwort`, `Kategorie`, `Stichwort` -
several joined by "und" or commas. A known tag is suggested even when it
merely appears in the sentence. `#DialOS` works too.

**Follow-up** after `Wiedervorlage`, `erinnere mich`, `Erinnerung`,
`nachfassen`, `Termin`:

| Spoken | Result |
|---|---|
| heute · morgen · übermorgen | today / tomorrow / day after |
| in drei Tagen · in 14 Tagen · in zwei Wochen · in einem Monat | relative to today |
| nächsten Montag · am Freitag · diesen Mittwoch | next matching weekday |
| nächste Woche · nächsten Monat · nächstes Jahr | + 1 week / month / year |
| am Wochenende | the coming Saturday |
| am 15. September · am dritten Oktober · 01.09.2026 | fixed date |
| um zehn Uhr · um 14:30 · um halb neun · viertel nach acht | time of day |
| morgens · mittags · nachmittags · abends · früh | 8 / 12 / 15 / 18 / 8 o'clock |

Without a time, the configured default applies (9:00 by default). Order
does not matter: "um zehn am Montag" works just as well.

## The notebook

One window with **tabs**, like a real notebook: "Alle" (all),
"Wiedervorlagen" (follow-ups) and one tab per tag.

**Everything works from the keyboard** - creating, renaming, deleting and
switching tabs, as well as creating, editing, ticking off and deleting
notes. Every command is also in the menu, so you can find it without
knowing it by heart. Press `F1` for the list.

| Key | Action |
|---|---|
| `Ctrl`+`N` | dictate a new note |
| `Ctrl`+`Shift`+`N` | type a note |
| `Enter` / `F2` | edit note |
| `Ctrl`+`D` | done / open again |
| `Del` | delete note |
| `Ctrl`+`F` | search |
| `Ctrl`+`T` | new tab (tag) |
| `Shift`+`F2` | rename tab |
| `Ctrl`+`Shift`+`W` | delete tab |
| `Ctrl`+`PgUp/PgDn`, `Alt`+`1…9` | switch tabs |

Deleting a tab keeps the notes - only the tag goes. Renaming carries the
tag everywhere; if the new name already exists, both are merged.

## Calendar

Two routes, switchable in the settings:

* **CalDAV** - the appointment goes straight into your Nextcloud calendar
  and is therefore on your phone as well. With Nextcloud, use an **app
  password**, not your login password.
* **iCalendar file (.ics)** - written to a folder you can add to
  Thunderbird as a local calendar. No server, no credentials.

The default is **automatic**: server first, file as a fallback. The note
then remembers that the appointment is not on the server yet; `Ctrl`+`R`
(or `denkzettel nachtragen`) submits it once the network is back. An
appointment must not get lost just because there was no connection.

You do not have to hunt for your calendar's address - "Kalender suchen …"
in the settings fetches the list from the server.

## Microphone

Many machines have a built-in microphone **and** the one in a webcam. No
program can guess which one you mean, so the installer asks and lists
every device it found. To change it later, use the settings dialog or:

```
denkzettel mikrofone --waehlen
```

Two things are handled deliberately here, because they fail silently
otherwise:

* While recording, a **level meter** shows the input. If it does not
  move, a warning appears in the window straight away - a dead microphone
  otherwise only becomes apparent once the thought is gone.
* If the configured device is **not connected** (webcam unplugged),
  Denkzettel records via the system default and **says so**, instead of
  producing an empty file.

## Installation

```
git clone https://github.com/Stephan-Lefty/Denkzettel.git
cd Denkzettel
./install.sh
```

The script detects Debian- and Arch-based systems, installs the packages,
builds whisper.cpp, downloads the model (`large-v3-turbo` by default,
about 574 MB), creates the menu entries, asks about the microphone and
sets up the `Meta`+`N` shortcut.

Smaller model for weaker machines:

```
./install.sh --modell medium     # 539 MB
./install.sh --modell small      # 190 MB
```

Check the setup:

```
denkzettel pruefen
```

### Commands

| Command | Action |
|---|---|
| `denkzettel` | open the notebook |
| `denkzettel erfassen` | record right away (the shortcut) |
| `denkzettel mikrofone --waehlen` | choose the microphone |
| `denkzettel kalender` | list calendars on the server |
| `denkzettel nachtragen` | submit pending appointments |
| `denkzettel pruefen` | check the setup |
| `denkzettel einstellungen` | open the settings |

## Where things live

| What | Where |
|---|---|
| Settings | `~/.config/denkzettel/config.ini` |
| Notes (SQLite) | `~/.local/share/denkzettel/notizen.db` |
| Recordings | `~/.local/share/denkzettel/aufnahmen/` |
| Calendar files | `~/.local/share/denkzettel/kalender/` |
| Speech recognition | `~/.local/share/denkzettel/whisper.cpp/`, `…/modelle/` |

The notes live in **one** file - copying it is a complete backup.

## Why whisper.cpp and not Vosk

DialOS recognises speech with Vosk, and for good reason: there it is a
fixed list of command sentences, and with a restricted grammar Vosk is
very reliable at that.

Here it is the opposite - freely spoken thoughts, no fixed vocabulary.
That is exactly where Vosk is noticeably weaker, and correcting the
result afterwards costs more time than the larger model costs in compute.
Both run offline, so the principle is unchanged.

## Changelog

### 0.1.0 (2026-08-23)

First release.

* Recording via PulseAudio/PipeWire (`parecord`, falling back to
  `arecord`) with a level meter, a maximum duration and a warning when
  the microphone is silent.
* Microphone selection during installation and at any time via
  `denkzettel mikrofone --waehlen`. Devices that describe themselves
  uselessly are identified by the product name taken from the device id -
  "EEM Gadget Mono" becomes "UGREEN AI Camera CM930 4K".
* Speech recognition via whisper.cpp, fully offline. Detection is
  deliberately strict: on many systems `/usr/bin/whisper` is the entirely
  different **openai-whisper** with different arguments. Ambiguous names
  are verified before use, otherwise only the first dictation would fail.
* German parsing of the dictation: tags and follow-up dates are lifted
  out, the note text stays clean. Relative dates, fixed dates, times in
  words and digits, times of day - date and time in any order.
* Notebook with one tab per tag, fully keyboard-operable; tabs can be
  created, renamed (merging on collision) and deleted.
* Calendar via CalDAV with a fallback to iCalendar files and automatic
  resubmission once the server is reachable. Calendar discovery via
  PROPFIND.
* Its own icon, derived from the DialOS app icon: the original is
  converted back into a line drawing with transparency, the sound waves
  are removed, a written line and a pencil are added. The build script
  verifies that the pencil does not touch the ring and aborts otherwise.
