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

## Interface layer: classical CV over canvas, not JS/DOM extraction

Research spikes (Playwright against the live client) ruled out the JS/DOM extraction path we
originally hoped for:

- `window` exposes no usable game state — broad global scans turn up nothing but ad-tech/analytics
  cruft.
- The client renders through **PixiJS onto two small canvases** (`#pixi`, `#pixi-fg`, 256×256px),
  not DOM nodes — there's nothing per-block to scrape from the DOM.
- The main bootstrap bundle is **deliberately obfuscated** (string-array encoding + control-flow
  flattening, not just minification) — there is no plaintext identifier to grep for, and no
  in-clear reference to other loaded chunks. Pushing further into deobfuscating it to find the
  live engine object would mean actively defeating a protection built to stop exactly this kind of
  automation, which conflicts with hard constraint #3 below. Don't go there.
- tetr.io does run a real-time binary protocol over WebSocket (`wss://*.spool.tetr.io/ribbon/*`,
  1-byte opcode + concatenated MessagePack objects) for lobby/menu/social state, confirmed
  reverse-engineerable — but it was not confirmed to carry solo-mode board/piece state per tick,
  and reverse-engineering it further is likewise low-value relative to the CV path below.

**Chosen approach: classical CV over canvas screenshots, not a vision-language model.** The board
is a fixed-size grid of solid-colored blocks — this is a pixel-grid-sampling / color-thresholding
problem (Pillow/OpenCV/NumPy), not an image-understanding one. Read the canvas via Playwright
screenshot, sample cell-center pixel colors against a known board grid geometry and piece color
palette, and derive the logical board/piece/queue/hold state from that. This must run many times
per second for RL training, so a per-frame LLM vision call is not viable as the primary loop — it
may be useful once for bootstrapping/validating the CV calibration, but the runtime path must be
CV-only.

- Action injection (moves, rotations, hold, drops) should go through Playwright's input
  simulation (`page.keyboard`, which dispatches trusted CDP-level events) against the real page,
  not `dispatchEvent`-style JS injection (untrusted events are often ignored by canvas games) and
  not hooks into game internals — this keeps the bot's actions equivalent to what a human player
  could do.
- Isolate all tetr.io-specific pixel-geometry/calibration/color-palette logic behind one module
  boundary. tetr.io will change its client over time; when it does, only that module (and its
  calibration constants) should need to change.
- Use a **persistent Playwright browser profile** (not a fresh context per run) — a cold profile
  takes tetr.io's client roughly 200s to boot before it's interactive; a warm one boots in ~15s.
  This matters for anything that launches the browser repeatedly (dev iteration, restarts).

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

## Known ToS risk — not resolved by these constraints

Confirmed by reading tetr.io's actual rules page: bots, macros, and automation of any kind on a
normal account are **banned on sight** for both the bot and its operator, with no documented
exception process in the rules themselves. The constraints below (single session, human-plausible
timing, no evasion) are there to keep this project's footprint honest and small — they are risk
*mitigation*, not ToS *compliance*. Automated play against the live service is a ban risk on
whatever account runs it, full stop. Treat that as a standing, accepted tradeoff of this project,
not something to re-litigate per session — but also don't act surprised if the account gets
banned, and don't use a primary/important account to run this.

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
