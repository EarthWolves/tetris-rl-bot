# tetris-rl-bot

## Project goal

Train a reinforcement learning agent that plays Tetris on [tetr.io](https://tetr.io/) and, once
trained, runs it live against the real site. Everything is Python. There is no frontend and none
is planned — this is a headless bot, not a product.

The project has two subsystems that must stay decoupled:

1. **Interface layer** — reads game state from tetr.io and injects actions back into it.
2. **Agent layer** — a Deep Q-Network (DQN) that learns to play from that state.

The interface layer's job is to produce a clean `(state, reward, done)` tuple and accept an
`action` — the agent must never know or care that tetr.io, a browser, or a vision model is
involved. Keep the boundary between them a plain data interface (think Gym/Gymnasium `Env`
API: `reset()`, `step(action) -> (obs, reward, done, info)`), so the agent layer could in
principle train against a local simulator with zero changes.

## Interface layer: hybrid extraction

- **Primary path: Playwright + JS/DOM/WebSocket extraction.** Drive a real browser session with
  Playwright and pull board state, current/next/hold piece, and game events directly from the
  page's JS state, DOM, or WebSocket traffic. This is deterministic, fast, and cheap — always
  prefer it.
- **Fallback path: vision model on screenshots.** Only fall back to screenshotting the canvas and
  parsing it (CV or a vision model) if tetr.io's client changes in a way that breaks JS-level
  extraction, or obfuscates state we need. Treat this as a degraded mode: slower, noisier, and
  costs inference calls. Don't build agent logic that assumes vision-path latency/noise
  characteristics as the norm.
- Action injection (moves, rotations, hold, drops) should go through Playwright's input
  simulation (keyboard/mouse events against the page), not through hidden hooks into game
  internals — this keeps the bot's actions equivalent to what a human player could do.
- Isolate all tetr.io-specific scraping/DOM/selector logic behind one module boundary. tetr.io
  will change its client over time; when it does, only that module should need to change.

## Agent layer: Deep Q-Network

- The state space (full board grid × piece queue × hold) is too large for tabular Q-learning.
  Commit to a neural net Q-function (PyTorch) from the start — don't build a tabular/bucketed
  fallback "for now."
- Standard DQN machinery is required, not optional: experience replay buffer, a separate target
  network (periodically synced), and a decaying epsilon-greedy explore/exploit schedule as
  specified in the original project brief.
- Reward shaping, network architecture, and hyperparameters are open design questions — expect
  these to evolve. What is **not** open for debate without discussion: the use of a neural
  Q-function, replay buffer, and target network as the foundation.

## Hard constraints — must not be violated

1. **Single browser session only.** Never drive multiple concurrent sessions against tetr.io
   (no parallel self-play farms, no multi-account training). One logged-in session at a time.
2. **Human-plausible action timing.** Actions injected into the page must be rate-limited to
   timing a human could plausibly produce. Never inject actions faster than real input events
   allow, and never batch/replay actions in a way that bypasses the game's normal input cadence.
3. **No anti-detection or anti-cheat evasion.** Never write code whose purpose is to hide the
   bot's automated nature from tetr.io (fingerprint spoofing, detection-signature evasion, timing
   randomization specifically designed to defeat bot-detection, etc.). If tetr.io's ToS or
   anti-cheat would object to this bot existing, that's a constraint on how/where it's run, not a
   problem to code around.
4. **No modification of game internals.** Only observe state and inject input events. Never
   monkey-patch, hook, or otherwise alter tetr.io's client-side code to change game behavior,
   expose hidden state beyond what a human could infer from the screen, or gain a mechanical
   advantage.
5. **Credentials stay local.** Any tetr.io login credentials/session cookies used for automation
   must be read from local config/environment, never hardcoded or committed.

## Code organization expectations

- Python only, backend/logic only — do not introduce any web server, API, or UI code unless the
  user explicitly asks for one.
- Keep the interface layer (browser/vision/tetr.io-specific code) and the agent layer (DQN,
  replay buffer, training loop) in separate top-level packages/modules. The training loop should
  depend on the interface layer only through the `reset()`/`step()`-style boundary described
  above.
- Use `uv` / `pyproject.toml` for dependency management (already scaffolded) — don't introduce a
  second dependency manager (pip requirements.txt, poetry, conda) alongside it.
