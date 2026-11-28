---
slug: select-tts-service
title: Select TTS service
status: draft
autonomy: interactive
owner: ehsmeng
human: ehsmeng
agent: claude
assignee: ehsmeng
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Pick the text-to-speech service for German audio. The human wants very high quality, will pay for it, and has a Mac available. Output: sample clips from each candidate, a cost estimate for the full run, and the human's choice.

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 1,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed); a second 1,000 (words 1,001–2,000) may follow later, possibly as its own PDF. `words.json` keeps 5,000 ranked forms so the course can grow without rebuilding the list. Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 1000 german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Candidates: ElevenLabs, Azure Neural TTS, Google Cloud TTS, OpenAI TTS, and the Mac's built-in German voices (`say`).
- Done last by request ("Let's do TTS last"), but it only needs the pilot content, so it can run alongside the full generation.
- Open, settle here: what each mp3 contains (the word alone? word plus sentences? include the English?). This drives the cost estimate.
- Licensing criterion (decided 2026-11-26): course content is published under CC BY 4.0, so the service's terms must allow redistributing the generated audio under that license. Check each candidate's terms and record the result.
- Human makes the final choice and sets up the account/API key (stored in coga.local.toml secrets).
- Depends on: generate-german-content-for-words-1-100 (done; pilot reviewed and approved).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
