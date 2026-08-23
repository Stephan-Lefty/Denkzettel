[Deutsch](TODO.md) | [English](TODO.en.md) | [Changelog](README.en.md#changelog)

# TODO

Running list of open points. Open items on top; finished ones are moved
down rather than deleted, with the date they were completed.

## Open

### Must happen before real use

- [ ] **No dictation through the microphone yet.** Recognition itself is
  proven (see below, verified against known text), but the path webcam
  microphone → recording → whisper.cpp has never run with an actual
  voice. The open question is mainly whether the UGREEN webcam's level
  is good enough. (Lesson from DialOS: the T490's built-in microphone
  was overdriven by 60 dB out of the box, so the recogniser never
  produced a result - without any error message.)
- [ ] **Verify `Meta`+`N` under Plasma.** The .desktop file is now
  `NoDisplay=true`. Whether kglobalaccel still registers the shortcut
  for a hidden entry is untested - if not, write the entry into
  `kglobalshortcutsrc` directly.
- [ ] **Model load time.** Every dictation costs about 27 seconds,
  almost regardless of length - that is loading `large-v3-turbo`. For a
  short thought that is a lot. To try: compare smaller models
  (`medium`, `small`), or keep whisper.cpp running as a service instead
  of starting it fresh each time.
- [ ] **Verify CalDAV against the real Nextcloud.** The code follows
  RFC 5545/4791 and the generated .ics is correct (folding, escaping,
  UTC verified) - but no server has ever accepted it. To check: app
  password, correct calendar URL, umlauts, alarm.
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

### Setup and first check on the machine (2026-08-23)

- [x] **`install.sh` ran through on Stephan's Manjaro.** All
  dependencies were already present (so no sudo needed), whisper.cpp
  1.9.3-dev built, model downloaded, menu entries created.
- [x] **Recognition verified against known text**, using the method from
  DialOS: don't speak into a microphone, feed in existing recordings
  whose transcript is on file. Four DialOS speech samples through
  whisper.cpp - all four correct in substance, deviations only in
  punctuation and capitalisation, one word error.
- [x] **Duplicate menu entry fixed.** Denkzettel appeared twice and in
  two categories. Cause: `Categories=Office;TextEditor;` (KDE also files
  `TextEditor` under Utilities) plus a second .desktop file that was
  only supposed to carry the shortcut. Now one visible entry under
  Utilities, the second file set to `NoDisplay=true`.
- [x] **Microphone selection moved out of the install script into an
  introduction on first start** (Stephan's call), together with an
  explanation of how to speak and which keys exist. Available again via
  *Hilfe → Einführung* or `denkzettel einfuehrung`.

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
