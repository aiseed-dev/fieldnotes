# Tasks for Muse Code

Muse Code (Meta's terminal coding agent) runs in a terminal in this repository (`muse`), next to the Claude Code sessions. It has two jobs: to build the part closest to Meta's own API, and to check the code that the other agents wrote. Every commit it makes says so in its message (`Written with Muse Code`), so the README can show which parts it did.

Start it from the repository root:

```bash
cd ~/dev/fieldnotes && muse
```

Then paste one of the tasks below.

## Task 1: voice (WP2)

```
Read docs/implementation.md (rules, and the "Voice (WP2)" section). Implement src/fieldnotes/voice.py:
transcribe(wav, vocabulary=(), language="ja") -> str using Muse Voice Transcribe (muse-voice-transcribe-1.0,
POST https://api.meta.ai/v1/asr/transcribe, multipart: request JSON + WAV, PUSH_TO_TALK, Japanese language bias,
vocabulary biasing), and vocabulary(field, root) -> list[str]. Read the API reference on dev.meta.ai for the exact
request fields; do not guess. Get the key with fieldnotes.llm.api_key(); never print it.
Add offline pytest tests (fake HTTP). Then one real call on a short Japanese WAV to confirm it works.
Commit on a new branch named muse/voice, message ending with "Written with Muse Code". Do not push.
```

## Task 2: check the code (review only)

```
Review src/fieldnotes/pipeline.py, cli.py, app.py, appdata.py, concepts.py and records.py against
docs/implementation.md. Look for real bugs: wrong file paths, lost farmer verdicts on re-run, lines marked
on the wrong record, crashes on empty or missing files, the API key leaking into logs, and blocking calls
in the Flet UI thread. Do not change code. Write the findings, most serious first, each with file:line and a
concrete failing case, to docs/reviews/muse-code-review.md. Commit only that file on a new branch named
muse/review, message ending with "Written with Muse Code". Do not push.
```

When a task is done, the main Claude session merges the branch after the farmer says so, the same as the Sonnet branches.
