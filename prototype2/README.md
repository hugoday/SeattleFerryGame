# Seattle Ferry Inc. — tick-world prototype

The observation-economy rebuild. The real-time prototype in `../prototype`
is untouched; this one moves time only when you spend it.

## Run

    cd prototype2
    python main.py

Requires Python 3.10+ and pygame. `python checks.py` runs the headless
behavior suite; `python devshots.py <outdir>` renders every view to PNG;
`python fuzz.py` hammers the model with random dispatch and asserts
invariants (slower — run it after structural model changes).

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

## In-hull (I from the map): the four verbs

The ship's instruments, zoomed to her sensor envelope. No cameras; beyond
sensor range the screen is absent, not black.

**Sense.** The radar sweep is crisp, decays fast, and is blocked by land;
passive sonar is always on but gives smeared bearings and never a range.
An active ping (P) resolves everything at once and adds +30 to the
**emissions ledger**: noise decays 8/tick, engines add 2/tick underway,
and a loud hull in the basin finds that the anomaly's wander bends toward
her. Every act of looking announces.

**Interpret (E).** Radar and sonar disagree about the thing in the basin,
and at any moment exactly one of them is honest — which one flips on its
own schedule. Commit to a read and the overhead map plots its claim as
the working fix (`FIX/RADAR`, `FIX/SONAR`); commit to the wrong one and
you will route around empty water while the real thing waits elsewhere.
A ping in earshot reveals the currently honest instrument — briefly.
There is no confirmation. Up close, the anomaly corrupts hulls and
**deresolves cargo** — the manifest simply stops agreeing it exists.

**Steer (H, then A/D heading, W/S throttle).** Heading and throttle only.
STOP / SLOW / CRUISE / FLANK: flank is 1.3× cruise but three times as
loud and blinds a quarter of the radar. The helm refuses to put her
ashore — breakers ahead means all stop.

**Manage (1/2 power, J rig).** A powered-down system cannot be damaged by
undecided water — and does nothing. The hull is always in the water.
A dark boat (both off) funnels every hit into her frames, in silence.
J jury-rigs the worst component at sea: slow, expensive, never past 60.

## Agents (shipyard refit: T1 $6,000 · T2 $14,000 · T3 $30,000)

Installable sub-AIs that automate labor, **never attention** — an
agent-run hull is as unobserved as any other and no agent may ever hold
the flag. Circuits are standing routes (C in the commit screen; G pauses).
T1 automates the sailing only: she waits for dispatch to load her
(`LADING?` on the board), then runs the rotation and stops dead at
anything unexpected — a fixed rotation over thin aprons can absolutely
run at a loss; that judgment is the labor you didn't pay for. T2 runs
full port operations — loads whatever serves the circuit, best pay
first. T3 diverts around *known* hazards, taking the long way rather
than freezing. When the anomaly itself touches any agent's hull,
judgment returns to dispatch.

## Committing a leg

R on the map (or RETURN from cargo ops) opens the commit screen: every
option quotes exact ticks, exact fuel, and a stability band for the water
it actually crosses. What is *in* the unstable water is never shown.

## Controls

| Where | Keys |
|---|---|
| Map | arrows pan · -/+ range · A/D port · TAB ship · E open · U upgrade · O observe · R route · I in-hull · X abandon · SPACE tick · RETURN run · F5/F9 save/load · Q quit |
| In-hull | P ping · E read · H helm · A/D heading · W/S throttle · 1/2 power · J rig · TAB next hull · SPACE tick · RETURN run · Q back |
| Cargo | WASD move · SPACE act · F vessel · U upgrade · R repair · RETURN commit leg · Q back |
| Commit | W/S dest · A/D option · SPACE commit · C circuit · G pause · X abandon · Q back |
| Repair | W/S choose · SPACE repair (twice) · Q back |
| Shipyard | TAB section · W/S choose · SPACE act (twice) · R repair · RETURN route · Q back |

## Not yet

Bad-chart / Bearings-only / Decoherence encounter tiers, the full
Noise-drawn tier (the anomaly bait and emissions ledger are its
foundations), observed-flag reliability upgrades, sound, story.
