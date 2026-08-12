# Seattle Ferry Inc. — text-mode prototype

A fresh pass at the game as a DOS-grammar, cell-grid prototype. The original
game in `../source` is untouched.

## Run

    cd prototype
    python main.py

Requires Python 3.10+ and pygame.

## What's in

- **Cell-buffer renderer** (`screen.py`) — every frame is a grid of
  (glyph, fg, bg). Navy theme for the map, near-black for panel screens.
  No anti-aliasing, no half-cells.
- **World in nautical miles** (`world.py`) — procedural coastline rasterised
  at boot, sampled with CP437 half-blocks at any range scale.
- **An economy with teeth** (`sim.py`) — fuel burns per NM continuously,
  payments scale with distance, empty legs lose money. Jobs rotate every
  8 game-hours whether you were ready or not. The sim never pauses.
- **Overhead map** — pan (arrows), three range scales (-/+), uncertainty
  shading `░▒▓` that collapses near ports/buoys/hulls and flickers where
  the water hasn't decided. Contacts board, live event line.
- **Cargo operations** — apron / staged / hold tables, live voyage estimate
  (revenue, bundle bonus, fuel, net), and the vessel in profile with a
  waterline that sinks as you load her.
- **Destination select** — distance, fuel, revenue and net per port, dock
  availability. Depart from here.
- **Shipyard** — fleet board, plan-view hull, refit (hold/speed/efficiency,
  two-press confirm, only when the hull is physically at the yard), and a
  new-hull market (berth required).
- **Port upgrades** (E from a port) — cargo/stage capacity and docks.
- **Something in the water** — an unresolved contact appears after a few
  hours near the KNG corridor. Radar and sonar disagree about it.
- **Save/load** (F5/F9 from the map) — one JSON snapshot
  (`savegame.json`, git-ignored). Geography is deterministic, so only the
  clock, the books, the manifests and the hulls go to disk — a hull saved
  mid-voyage resumes mid-voyage.

## Controls

| Where | Keys |
|---|---|
| Map | arrows pan · -/+ range · A/D select port · SPACE open · E port upgrade · F5 save · F9 load · Q quit |
| Cargo | WASD move · SPACE act · F cycle vessel · RETURN depart (empty hold allowed) · E upgrade · Q back |
| Destination | W/S choose · SPACE depart · Q back |
| Shipyard | TAB section · W/S choose · SPACE act (twice confirms) · RETURN depart selected hull · Q back |

## Dev

`python devshots.py <outdir>` renders every view headless to PNG.

## Not yet

Sound, the in-hull tactical view, anomaly encounters that
develop, island discovery/repair, story. The skeleton is shaped so those
land in the model layer (`sim.py`) and new views without touching the
renderer.
