# Jarvis conversation audit — September 6, 2026

Jarvis should behave like a conversational desktop companion: know when it is being addressed, let the user finish, visibly acknowledge what it heard, explain useful progress, and yield when interrupted. Natural turn-taking matters as much as voice timbre or the time to the first sound.

**What the timing numbers actually mean**

The earlier ~350 ms result measured acknowledgment audio **after a request had been accepted**, following speech recognition. It excluded the user's ending pause and ASR finalization. The new Strong-mode fixtures measured about **0.97–1.24 seconds from the input player's completion to a transcript**, depending on the sample. Recognition finalization accounted for 0.27–0.57 seconds in that run. Player completion is a test reference, not a calibrated last-phoneme measurement. Agent response time and synthesis/playback follow afterward.

The cached acknowledgment makes this wait feel responsive once the request is accepted. Further end-to-end work should instrument last speech → endpoint → transcript → agent first public text → first audible sample. Do not describe a TTS first-chunk number as total conversational latency.

**Findings and changes**

| Area | Problem found | Implemented behavior |
| --- | --- | --- |
| Microphone mute | Stopping capture also canceled the spoken answer and removed its audio route. | Capture stops independently. Current speech finishes; its echo-filter route is released after that sentence drains. |
| False interruptions | A VAD trigger immediately discarded the active answer and queue, even if no words were recognized. | Pause playback first. An empty recognition resumes it; an accepted correction discards obsolete speech. |
| Corrections | `utterance_end` could resume desktop input while asynchronous steering was still waiting for acceptance. | Keep input paused until the correction has been handled and the user has finished speaking. |
| Stale input | Independent submission threads could act on old transcripts after Stop. | One ordered intake consumer and input generations reject superseded speech after Stop, microphone pause, or shutdown. |
| Follow-ups | With interruption disabled, another request overwrote the first pending request. | Preserve pending text in arrival order for the next turn. |
| Room noise | Echo suppression existed, but every speech-like start could interrupt the conversation. | Strong mode adds a stricter speech threshold, sustained onset, and a bounded ambient-level check for faint false starts. |
| Resuming a thought | A stronger onset detector was too slow to notice resumed speech, cutting off part of a word during endpoint waiting. | Separate start-of-request detection from faster continuation detection. Adaptive pauses allow extra time after unfinished phrases. |
| Listening choices | Wake word and hands-free were independent switches with overlapping behavior. | One explicit choice: Hey Jarvis, open microphone, or hold-to-talk. |
| Wake-mode interruptions | Task activity kept the conversation gate open to background speech throughout the task. | An engaged task or spoken answer requires a fresh wake word before an interruption. Idle follow-ups still have a bounded window. |
| Recovery | Empty recognition and the ASR finalization delay were poorly explained; agent failures could be silent. | Distinct “Listening to you” and “Understanding” states, recoverable input notices, and a short spoken failure message. |
| Long requests | Reaching the configured duration limit sent a potentially incomplete instruction. | Reject the oversized request, display a notice, and ignore its remaining speech until a quiet boundary. |
| Settings readability | Numeric controls clipped the leading digits of pause durations and thresholds. | Wider value fields keep complete settings visible. |
| Device routing | Pulse monitor names could be treated as PipeWire node names; a missing selected device could fall back to another microphone. | Explicit monitor routing and disabled device fallback/reconnection. |

**Noise: practical limits and recommended setup**

PipeWire's WebRTC filter already enables high-pass filtering and high noise suppression by default, with automatic gain control disabled. These settings are now explicit in Jarvis's own temporary filter. Its reference signal is Jarvis's output through that filter; unrelated apps' speaker audio is not necessarily part of that reference. [PipeWire implementation](https://github.com/PipeWire/pipewire/blob/1.6.8/spa/plugins/aec/aec-webrtc.cpp), [echo-cancel signal path](https://docs.pipewire.org/page_module_echo_cancel.html).

- For fans and typing: try **Strong** rejection, keep echo cancellation enabled, and speak near the selected microphone. Strong mode can miss soft voices; Balanced remains available.
- For TV and other people: use **Hey Jarvis** or **hold-to-talk**. Ordinary speech detection does not identify who spoke or whether they meant to address the assistant. Noise suppression is not speaker authentication.
- In wake mode, say Hey Jarvis before interrupting a task. The Stop button and Ctrl Alt Esc remain available immediately. Follow-ups after the answer do not require another wake word until the window expires.
- Keep microphone selection explicit when several microphones are connected. No system default devices or global microphone gain were changed by this work.

**Next improvements, in priority order**

1. **Richer turn-end detection.** The new pause handling uses a small English-language heuristic. It cannot understand every unfinished thought, and a meaningful pause after a complete clause can still end a turn. Evaluate an end-of-turn model against real pauses, corrections, short answers, and silence before choosing one.
2. **Continuous audio and synthesis overlap.** Speech still generates and plays in one loop, with a new output process per segment. Separate synthesis from playback with a small bounded buffer; preserve cancellation and pause behavior. This should target sentence gaps and prosody without building a long stale-audio backlog.
3. **Public speech roles.** The controller reads the agent's public Markdown stream, which mixes progress and final answers. Normalize public progress, answer, question, and failure events across adapters. Keep code and private reasoning out of speech. Coalesce adjacent text where doing so preserves natural phrasing.
4. **Acknowledgment quality.** One cached “Got it” can become repetitive, and an arriving answer can cut it short. Compare a small set of brief acknowledgments and sentence-boundary handoffs using listening tests. Faster is not useful if it sounds broken.
5. **Voice quality evaluation.** All nine Pocket voices share one synthesis engine. Adding names does not establish human-like delivery. Compare voices with questions, corrections, hesitation, empathy, numbers, and longer answers. An optional higher-quality engine would require a separate latency, hardware/privacy, and cost decision.
6. **Acoustic validation.** Expand beyond synthetic audio to close/far microphones, actual keyboards, speaker echo, overlapping people, TV, quiet voices, and long sessions. Measure false activations and missed speech as well as latency. The virtual fixtures cannot certify performance in the user's room.

**Validation**

- All 91 backend tests passed in the installed voice runtime, covering input ordering, stop invalidation, noise recovery, correction acknowledgment, listening policies, device routing, and existing agent/session behavior.
- The robot Qt suite passed all 9 checks; the settings Qt suite passed all 7 checks, including mode consistency, hearing/understanding labels, and voice previews.
- `tools/listening_flow_check.py` uses virtual audio to exercise simulated fan/keyboard noise, clean and mixed speech, a 700 ms mid-thought pause, a 1.3 second hold-to-talk pause, speech pause/resume, microphone mute during playback, and an oversized request. No agent or room microphone is used.
- `tools/voice_live_check.py --hands-free --noise-rejection strong` validates synthetic microphone input → Parakeet → the real configured CLI → Pocket speech.
- `tools/wake_live_check.py` checks ignored speech before wake, wake activation, follow-ups, background speech during an engaged task, and return to standby.

Observed fixture results: fan/keyboard noise produced no speech events; clean and noise-mixed requests retained their words; the 700 ms unfinished-phrase pause remained one request; the full CLI round trip spoke its answer; the wake test ignored background speech while engaged and retained idle follow-ups. These are synthetic and virtual-audio results, not a claim of perfect room-noise rejection.

**1.9.1: previous reply replay during interruption**

Reproduced two replay paths: a shorter/empty reply snapshot rewound the speech cursor, and a delayed resume from one utterance could release playback after capture had already detected the next utterance. Shorter prefix snapshots now preserve the consumed cursor. Resume commands carry an utterance number and the worker rejects stale resumes or resumes while input is active. Cancellation during input keeps replacement speech held, including native steering. Playback checks pauses during PCM pacing and immediately before writing audio.

Resume events no longer announce the entire previous sentence as a new caption, and exited/draining players cannot announce a new playback start. Regression tests compare the full PCM byte sequence across interruption, proving that samples are neither repeated nor skipped. The virtual listening fixture additionally verifies stale-resume rejection during actual recognition, cancellation of the previous queued answer, and successful playback of the new reply.
