# Implementation notes

The project grew from a themed edge chat into a native CLI interface with a local voice companion and desktop control.

| Area | What we implemented |
| --- | --- |
| Omarchy interface | A bottom-left drawer connected to the screen edge, animated opening/closing, compact text, flat message rows, small controls, and live Omarchy colors, font, and scaling. Closed chat has no persistent visible tab. |
| Everyday chat | Streaming Markdown/code, copy, stop, edit/retry, attachments and clipboard images, saved conversations, history search, drafts, rename/delete, export, and model/reasoning/working-folder settings. |
| Real CLI sessions | Persistent OMP, Pi, Codex, and Claude sessions using their native tools, instructions, and permissions. Agents can edit files and run commands, show tool activity and approval prompts, and hand the same conversation to the configured terminal. New chats follow Omarchy’s default agent. |
| Local speech | Voxtype recognition through a file-backed daemon bridge by default, optional local Parakeet/legacy recognition, streaming Pocket TTS, optional Kokoro output, live captions, microphone/playback indicators, push-to-talk, hands-free listening, and optional upstream “Hey Jarvis” wake/follow-up listening for Peek. |
| Computer control | Native mouse, keyboard, screenshots, window focus, and accessible app controls. Desktop mode opens the visible default Omarchy browser; Browser mode uses isolated headless Chromium. An AI marker shows actions, and physical input can pause desktop control. |
| Companion capabilities | Optional screen/selection context, explicit local memory, fast local commands, mid-task corrections, named routines, timers/process watches, tracked config restore points, and speech personality settings. |
| Peeking character | Peek, an original procedural robot with a rounded ceramic shell, a bent antenna, animated brows, smiling eyes, and articulated fingers gripping the left edge. Its entire palette follows the live Omarchy theme. It leans into view, waves, winks, and reacts to voice and task events. Its vertical position is saved; opening chat moves it to the panel edge. |
| Voice controls and settings | Microphone, stop, conversation, reply mute, Desktop/Browser, settings, standby, and power controls. Advanced settings cover models, devices, threads, streaming, voice, volume, detection timing, echo cancellation, interruption, context, personality, expression strength, and reduced motion. |

The setup used during development has **Oh My Pi** as the default agent, **Voxtype** for recognition, and **Pocket TTS with Javert** for replies. Optional local Parakeet or legacy recognition can be installed later, leaving Peek as the assistant/TTS layer and avoiding a duplicate ASR model in RAM by default. Peek follows Voxtype's microphone and endpointing in the default mode; bundled mode uses the system-default microphone. These are configurable; they do not replace other users’ agent or audio preferences. Speech runs locally without a paid speech service. The chosen CLI/provider keeps its own license, account requirements, and any model costs; see [THIRD_PARTY.md](../THIRD_PARTY.md).

### Recent fixes

- Removed a design preview that restarted after crashing during shutdown and displayed a simulated “Listening” state without a microphone connection. Future previews explicitly say **Preview · no mic**, display an explanation, and disable their microphone control. The real Parakeet worker was reconnected and subsequently completed a voice/agent response.
- Patched the Qt Quick 3D window lifecycle after a crash in `QQuick3DSceneManager::setWindow` during window reattachment. The companion now keeps its native window alive while hiding all content and input regions when off. Repeated toggling and monitor changes still need manual verification.
- Refined message spacing and initial scrolling, reduced the rounded interior styling, retained the companion’s position while saving it, handled push-to-talk release outside the button, and made button/spoken standby honor the wake-word setting.

### Robot update verification

The robot redesign passed the 61-test Python suite and Qt 6 rendering/interaction checks for live events, all 19 expression previews, keyboard preview controls, hidden animation clocks, reduced motion, and palette changes without recreating the robot. Rendered expressions were visually reviewed at enlarged and screen-edge sizes. These UI tests use fixture theme tokens and no microphone or agent connection. See [TEST_PLAN.md](../TEST_PLAN.md) for the remaining desktop/audio checks.
