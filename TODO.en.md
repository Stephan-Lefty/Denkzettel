[Deutsch](TODO.md) | [English](TODO.en.md) | [Changelog](README.en.md#changelog)

# TODO

Running list of open points. Open items on top; finished ones are moved
down rather than deleted, with the date they were completed.

## Open

### Must happen before real use

- [ ] **`install.sh` has never run end to end.** Written and partly
  verified (syntax, dependency check in both directions, `--help`), but
  a full run including the whisper.cpp build and the model download is
  still pending. That takes several minutes and downloads 574 MB.
- [ ] **Not a single real dictation yet.** Every building block has been
  tested on its own, but the chain microphone → whisper.cpp → parsing →
  calendar has never run through with an actual voice. Nothing is proven
  until it has. (Lesson from DialOS: a test against an uninstalled
  change tests the old state without saying so.)
- [ ] **Verify CalDAV against the real Nextcloud.** The code follows
  RFC 5545/4791 and the generated .ics is correct (folding, escaping,
  UTC verified) - but no server has ever accepted it. To check: app
  password, correct calendar URL, umlauts, alarm.
- [ ] **Verify the shortcut under KDE.** `X-KDE-Shortcuts=Meta+N` in the
  .desktop file is the intended route, but depending on the Plasma
  version it only takes effect after `kbuildsycoca6` or a re-login. If
  that proves unreliable, write an entry into `kglobalshortcutsrc`.

### After that

- [ ] **Reminders without a calendar.** The follow-up currently depends
  entirely on the calendar. A notification of its own when a note falls
  due would be independent of it - especially for the .ics route, where
  nothing guarantees the file was ever added to a calendar.
- [ ] **Completed note vs. calendar entry.** Ticking off a note leaves
  the appointment in the calendar. Delete it? Mark it done? Decide,
  don't guess.
- [ ] **Clean up recordings.** They are kept by default and nobody
  deletes them. Proposal: remove after X days, and show the space used
  in the settings.
- [ ] **Stop automatically on silence.** Right now you stop with the
  space bar, or the maximum duration applies. Careful: pauses for
  thought while dictating are normal - better to stop too late than
  mid-sentence.
- [ ] **Export notes** (Markdown or plain text) so the thoughts are not
  stuck inside a database.
- [ ] **Hook into DialOS voice control** ("Denkzettel öffnen"). Check
  against the rules in `DialOS/docs/sprachbefehle.md` first: are the
  words even in the Vosk vocabulary? "Denkzettel" is a compound word and
  may well be missing.
- [ ] **Command parsing is German only.** whisper.cpp recognises many
  languages, but "Tag"/"Wiedervorlage" is understood only by the German
  parser. Other languages would need their own word lists in
  `textparser.py`.

### Open questions

- [ ] **How strict should tag detection be?** "Das war ein schöner Tag"
  is correctly not treated as a tag, because a known tag has to follow
  the trigger word. Conversely, a known tag that merely appears in the
  sentence is suggested. Whether that is annoying in daily use will only
  show with use.
- [ ] **"nächsten Montag" on a Sunday** currently yields tomorrow.
  Defensible linguistically, but some people mean the week after. Change
  it when it actually gets in the way - not before.

## Done

### Foundation (2026-08-23)

- [x] Name settled: **Denkzettel** - one word for both languages, like
  DialOS, and pronounceable as a voice command.
- [x] Icon derived from the DialOS app icon (draft B: sound waves out,
  written line and pencil in). The pencil does not touch the ring; the
  build script verifies the distance and aborts otherwise.
- [x] Recording via `parecord`/`arecord` with a level meter and WAV
  header repair after a hard stop.
- [x] Microphone selection during installation and via
  `denkzettel mikrofone --waehlen`; devices with useless names are
  identified by their product name.
- [x] whisper.cpp integration with strict detection - `/usr/bin/whisper`
  on Manjaro is the entirely different openai-whisper and is correctly
  rejected.
- [x] German parsing for tags and follow-up dates, verified against 21
  examples.
- [x] Notebook with one tab per tag, fully keyboard-operable.
- [x] CalDAV with .ics fallback and resubmission.
- [x] Dependencies are checked during installation, only missing ones are
  installed, and the result is verified afterwards.
