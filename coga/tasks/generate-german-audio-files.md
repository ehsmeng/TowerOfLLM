---
slug: generate-german-audio-files
title: Generate German audio files
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

Generate one audio file per word with the chosen TTS service, pilot first and then all words. Output: `german/audio/00001 ich.mp3` … for every entry.

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 5,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed) (count is a parameter; 10k possible later). Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 5k german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Naming (decided): `german/audio/<5-digit zero-padded learning order> <form>.mp3` (same stem as the entry JSON), e.g. `german/audio/00001 ich.mp3`.
- Contents per the decision in select-tts-service. Make reruns idempotent and resumable (skip existing files) to control cost.
- Depends on: produce-first-5k-german-words-pdf (TTS last, by request), select-tts-service.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
