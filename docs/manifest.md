# Submission manifest - FIN 43900 Project 2 (Shrey Goyal)

> **AI disclosure:** built with Anthropic Claude (Opus 5.5); see [validation-and-ai-use.md](validation-and-ai-use.md). The analysis and the decision are mine. **Education, not investment advice.**

Repository: **https://github.com/shreyofficial2006-art/FIN43900-Project2-Fall2026** (public; the instructional team can open it logged out). Frozen at commit `<<commit hash of the final push>>`.

| # | Part | Location | Notes |
|---:|---|---|---|
| 1 | GitHub repository | https://github.com/shreyofficial2006-art/FIN43900-Project2-Fall2026 | README opens with the two statements; one command reproduces the result |
| 2 | Research evolution (Editions A/B) | Not required for Project 2 (owner ruling 2026-10-14 / 2026-11-10) | How the system changed is in Video 1 and the memo |
| 3 | Decision memo | https://github.com/shreyofficial2006-art/FIN43900-Project2-Fall2026/blob/main/docs/decision-memo.md | Also attached to Brightspace |
| 4 | Validation and AI use, with the Locked Changed-Input Record | https://github.com/shreyofficial2006-art/FIN43900-Project2-Fall2026/blob/main/docs/validation-and-ai-use.md | Also attached; prediction commit: https://github.com/shreyofficial2006-art/FIN43900-Project2-Fall2026/commits/main/docs/lcir/prediction.md |
| 5 | Visible executed output | https://github.com/shreyofficial2006-art/FIN43900-Project2-Fall2026/blob/main/output/results.md | Inputs, as-of dates and decision without running code; app screenshots in `output/` |
| 6 | Video 1 - how the system and my thinking changed + one AI output I checked | https://youtu.be/HkuK93My9rc | Unlisted · about 2:15 (max 3:00) |
| 7 | Transcript, Video 1 | https://github.com/shreyofficial2006-art/FIN43900-Project2-Fall2026/blob/main/docs/transcript-video-1.txt | Speaking script (captions not ready at submission); the video's captions are the exact words |
| 8 | Video 2 - code walkthrough | https://youtu.be/r1jxDpjz_gY | Unlisted · about 4:52 (max 5:00) |
| 9 | Transcript, Video 2 | https://github.com/shreyofficial2006-art/FIN43900-Project2-Fall2026/blob/main/docs/transcript-video-2.txt | Speaking script (captions not ready at submission); the video's captions are the exact words |
| 10 | Video 3 - committee presentation, opening with the app live | https://youtu.be/uI3rXDd8bzU | Unlisted · about 4:53 (max 5:00) |
| 11 | Transcript, Video 3 | https://github.com/shreyofficial2006-art/FIN43900-Project2-Fall2026/blob/main/docs/transcript-video-3.txt | Speaking script (captions not ready at submission); the video's captions are the exact words |
| 12 | Deployed app (optional) | Not deployed - runs locally from the README | |

## Evidence index (where each required element is in each video)

| Video | Required element | Time |
|---|---|---|
| 1 | AI statement + "education, not investment advice" | 0:00 |
| 1 | How the system changed (Lab 15 → Lab 20 → Project 2) | 0:16 (Lab 15 and Lab 20), 0:35 (the three Project 2 changes) |
| 1 | How my thinking changed (objective vs loss limit) | 0:59 |
| 1 | One AI output and the check I ran on it; accepted / qualified / corrected / rejected | 1:26 - 2:06 (Gemini's two points; qualified and accepted/corrected) |
| 2 | AI statement + "education, not investment advice" | 0:00 |
| 2 | Architecture and data flow (README diagram, `engine.py`) | 0:14 |
| 2 | Point-in-time signal code (`gs2_as_known`) and the loss screen (`search`) | 1:03 (`gs2_as_known`), 1:43 (`search`) |
| 2 | Reproduce: `python run_analysis.py`, `python -m pytest -q` | 2:33 |
| 2 | Test of the highest-risk claim (full-crisis vs fund-only screen) and the Locked Changed-Input Record | 3:17 (full-crisis vs fund-only screen), 3:48 (Locked Changed-Input Record) |
| 2 | One failure mode / limitation | 4:29 |
| 3 | AI statement + "education, not investment advice" | 0:00 |
| 3 | App running live | 0:00 - 1:35 |
| 3 | Decision, range, evidence, assumptions | 1:35 - 3:47 |
| 3 | Risks, triggers, what reverses it | 3:47 |
| 3 | Committee ask | 4:19 |

## Checks before submitting

- [ ] Every link above opens in a private/incognito window (logged out), videos included.
- [ ] YouTube captions are on for all three videos; the .txt transcripts are corrected and pushed.
- [x] Memo, output, videos and validation record use the same numbers (75/25, 6.04%, 4.22%, 18.5%, 1 of 13).
- [x] No `<<` blanks left anywhere in `docs/`.
- [x] No password, key, token or `.env` in the repository.
- [ ] Brightspace: this manifest's links pasted, plus `decision-memo.md`, `validation-and-ai-use.md` and the three transcripts attached.
