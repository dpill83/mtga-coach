# 🧠 MTGA Arena AI Coach (Project Plan for Cursor Plan Mode)

A desktop assistant that reads MTGA log files (like Arena Tutor or MTGA Assistant), reconstructs game state, and provides heuristic or search-based recommendations for optimal lines of play (similar to a chess engine coach).

**Important:** This is a *coach*, not a bot. It does *not* click or play for the user. It provides suggestions only.

---

## 🎯 MVP Objective

✅ Parse MTGA log (`output_log.txt`) in real time  
✅ Reconstruct basic game state (your life, hand, battlefield, mana, opponent commander, etc.)  
✅ Display a readable UI that mirrors parsed state  
✅ Suggest a single heuristic-based “best play” (simple logic based on available mana, board value, and safe actions)

---

## 📦 Project Architecture

```

/project-root
├─ /parser          # MTGA log tailer + event normalizer
├─ /state           # Current game state representation
├─ /rules           # Play legality + known card metadata
├─ /engine          # Heuristics + (later) search/MCTS
├─ /ui-overlay      # Electron-based overlay UI
├─ /data            # Scryfall cache, deck role tags, priors
└─ PROJECT_PLAN.md  # This file (loaded into Cursor Plan Mode)

```

---

## 📍 Phase 0: Setup + Research

- [ ] Create Python environment for backend
- [ ] Identify local MTGA log path
- [ ] Log sample several full matches for analysis
- [ ] Build Scryfall bulk cache (local JSON)

---

## 📍 Phase 1: Log Parser (Python)

✅ Goal: Continuously read new MTGA log events and emit structured JSON events

- [ ] Tail the file at `%AppData%/LocalLow/WOTC/MTGA/output_log.txt`
- [ ] Parse 'payload' lines that contain gameplay (draws, plays, combat, life changes)
- [ ] Normalize events into a consistent schema
- [ ] Emit parsed events to a local event bus (WebSocket or internal queue)

🛠 Suggested libraries:
- `watchdog` or `tailer`
- `pydantic` or dataclasses
- `orjson` for speed

---

## 📍 Phase 2: Game State Manager

✅ Goal: Convert parsed events into an in-memory state object.

State should track:
- [ ] Player + Opponent life totals
- [ ] Player hand (only what is revealed; primarily your own)
- [ ] Player battlefield (creatures, power/toughness, counters, keywords)
- [ ] Stack (optional MVP)
- [ ] Mana available
- [ ] Current phase/step

Card data is fetched from:
- [ ] Local cached Scryfall metadata
- [ ] Your decklist (with roles)

---

## 📍 Phase 3: Action Legality Layer

✅ Goal: Determine which actions are legal right now on your turn.

MVP handles only:
- [ ] Casting spells from hand when mana is sufficient and timing legal
- [ ] Playing a land (once per turn)
- [ ] Declaring attacks (basic: all creatures vs no attacks)
- [ ] Simple activated abilities from known cards (Rhys, etc.)

---

## 📍 Phase 4: Heuristic Evaluator (First AI Layer)

✅ Goal: Score board states + recommend a best action sequence (one-ply)

Suggested heuristics:
- [ ] Reward board presence (tokens, big creatures)
- [ ] Penalize leaving mana unused
- [ ] Reward playing token engines early (in token decks)
- [ ] Reward casting ramp in early turns
- [ ] Reward removing high-threat opposing creatures
- [ ] Penalize playing into obvious blowouts (if opponent has open mana in relevant colors)
- [ ] Detect lethal opportunities and suggest them as top priority

Output:
- ✅ "Best Line" (e.g. Play Land → Cast Torens → Attack with creatures)
- ✅ Short explanation list ("Uses all mana", "Sets up token engines", etc.)

---

## 📍 Phase 5: UI Overlay (Electron App)

✅ Goal: Show live suggestions without interacting with MTGA

- [ ] Electron overlay in transparent click-through mode
- [ ] WebSocket listener from Python backend
- [ ] Display:
  - Current game state snapshot
  - Suggestions (primary and alternative)
  - Explanation of heuristics
- [ ] Hotkey to toggle display

---

## 📍 Phase 6: (Optional) Monte Carlo Tree Search (MCTS)

✅ Goal: Upgrade heuristic engine into shallow search engine

- [ ] Enumerate legal lines (main + combat only)
- [ ] Simulate opponent responses using probabilistic priors
- [ ] Run 200-500 rollouts
- [ ] Return line with highest evaluated score

---

## 📍 Phase 7: Deck-Specific Knowledge Profiles (like Ghalta/Mavren)

✅ Each deck includes:
- Tags: token-engine, finisher, pump, tutor, lifegain-engine
- Known best sequencing (go-wide then pump)
- MCTS heuristics tuned per deck

---

## ✅ Initial Tech Stack

| Component     | Language / Tools            |
|--------------|-----------------------------|
| Parser       | Python                      |
| State Engine | Python (dataclasses)         |
| Heuristics   | Python                       |
| UI Overlay   | Electron (TypeScript/React?) |
| Search (opt) | Python (possibly Cython later) |

---

## 🚦 Milestone Acceptance: MVP = ✅

✅ Live state output in console  
✅ "Best Action: Cast X" message when it’s your main phase  
✅ Reloads when next phase begins  
✅ Reads decklist and uses simple rules to suggest plays

---

## 📌 Future Ideas

- Opponent hand probability model
- Risk profiles: “Aggro”, “Midrange”, “Safe Ramp”
- Voice command/response ("Suggest line", "Next best", "Explain")
- Training mode: UI compares your move vs engine’s move