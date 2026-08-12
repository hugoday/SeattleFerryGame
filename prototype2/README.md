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

## Committing a leg

R on the map (or RETURN from cargo ops) opens the commit screen: every
option quotes exact ticks, exact fuel, and a stability band for the water
it actually crosses. What is *in* the unstable water is never shown.

## Controls

| Where | Keys |
|---|---|
| Map | arrows pan · -/+ range · A/D port · TAB ship · E open · U upgrade · O observe · R route · X abandon · SPACE tick · RETURN run · F5/F9 save/load · Q quit |
| Cargo | WASD move · SPACE act · F vessel · U upgrade · R repair · RETURN commit leg · Q back |
| Commit | W/S dest · A/D option · SPACE commit · X abandon · Q back |
| Repair | W/S choose · SPACE repair (twice) · Q back |
| Shipyard | TAB section · W/S choose · SPACE act (twice) · R repair · RETURN route · Q back |

## Not yet

The in-hull instrument view and its four verbs, Bad-chart /
Bearings-only / Noise-drawn / Decoherence encounter tiers, agents,
observed-flag reliability upgrades, sound, story. The seams are cut:
encounters land in `sim.step()`, agents ride the order queue, the in-hull
view reads `Ship.components` and the coverage model.
