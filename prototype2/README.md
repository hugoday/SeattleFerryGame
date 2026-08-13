# Seattle Ferry Inc. — tick-world prototype

The observation-economy rebuild. The real-time prototype in `../prototype`
is untouched; this one moves time only when you spend it.

## Run

    cd prototype2
    python main.py

Requires Python 3.10+ and pygame. `python checks.py` runs the headless
behavior suite; `python devshots.py <outdir>` renders every view to PNG.

## The tick

One tick is half an hour of array time. **Nothing advances until you ask:**
SPACE steps one tick, RETURN runs until something on the interrupt list
happens. The interrupt list is fixed and small — arrival/idle, a new
contact in coverage, component damage, a derelict, a contract window at 3
ticks, an observed-flag dropout. Nothing else stops a run.

## Observation

Reality resolves where attention is spent. Stability is one scale, 0–4,
and the water wears it: 4 holds still, 3 is a settled `░`, 0–2 flicker
`░▒▓`. Coverage comes from port arrays, powered buoy stations ($2,500 to
light, $6/tick to keep lit — certainty is a subscription), each hull's own
radar (partial: +1 to its own water, lost if the radar is wrecked), and
the **observed flag** (O on the map): exactly one hull, strongest
collapse, occasional dropout. The anomaly is only reported where coverage
reaches; elsewhere the board shows a stale last-known.

## Attrition

Undecided water damages components — ENG (speed), RDR (sensor reach),
HUL (integrity). Damage is persistent; repair costs **ticks in a berth**
(plus parts), the same currency contract windows are denominated in. At
HUL 0 a hull goes derelict: dead in the water, contracts void, until
another hull tows her to the yard (R on the map → WRECK entry).

## Contracts

Offers carry windows in ticks and age everywhere. Expire on the apron:
evaporates. Expire in your custody: penalty, standing loss, and the cargo
decoheres to a VOID slot until next docking. Abandon (X) any time —
standing cost grows with route progress. Standing gates priority
contracts (1.6× pay, tight windows) and starves chronic latecomers.
There is no banking and no partial value: void is void.

## In-hull (I from the map)

The ship's instruments, zoomed to her sensor envelope. No cameras; beyond
sensor range the screen is absent, not black. The radar sweep is crisp,
decays fast, and is blocked by land; passive sonar is always on but gives
smeared bearings and never a range. The two instruments do not agree
about the thing in the basin — radar claims a position (DISPUTED),
sonar claims a different bearing. An active ping (P) resolves everything
at once and adds +30 to the **emissions ledger**: noise decays 8/tick,
engines add 2/tick underway, and a loud hull in the basin finds that the
anomaly's wander bends toward her. Every act of looking announces.

## Committing a leg

R on the map (or RETURN from cargo ops) opens the commit screen: every
option quotes exact ticks, exact fuel, and a stability band for the water
it actually crosses. What is *in* the unstable water is never shown.

## Controls

| Where | Keys |
|---|---|
| Map | arrows pan · -/+ range · A/D port · TAB ship · E open · U upgrade · O observe · R route · I in-hull · X abandon · SPACE tick · RETURN run · F5/F9 save/load · Q quit |
| In-hull | P ping · TAB next hull · SPACE tick · RETURN run · Q back |
| Cargo | WASD move · SPACE act · F vessel · U upgrade · R repair · RETURN commit leg · Q back |
| Commit | W/S dest · A/D option · SPACE commit · X abandon · Q back |
| Repair | W/S choose · SPACE repair (twice) · Q back |
| Shipyard | TAB section · W/S choose · SPACE act (twice) · R repair · RETURN route · Q back |

## Not yet

The in-hull verbs beyond Sense (Interpret, Steer, Manage), Bad-chart /
Bearings-only / Decoherence encounter tiers, the full Noise-drawn tier
(the current anomaly bait is its precursor), agents, observed-flag
reliability upgrades, sound, story. The seams are cut: encounters land
in `sim.step()`, agents ride the order queue, Interpret gets its
committing-to-a-read moment from the already-disagreeing instruments.
