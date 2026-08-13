# Your first hour on the Sound

Read the README for what the game *is*. This is what to press.

## The one rule

**Time only moves when you spend it.** Nothing happens while you sit on a
screen reading it. Two keys spend time, and they work from the map and
from the in-hull view:

- `SPACE` — one tick (half an hour).
- `RETURN` — run ticks until something on the interrupt list happens
  (an arrival, a new contact, damage, a derelict, a window at 3 ticks, a
  flag dropout). Any key halts a run.

Everything else — loading cargo, choosing routes, buying buoys — is free.
You are never in a hurry inside a screen. You are only ever in a hurry
across ticks.

## Where you are

The **map** is home. Every other screen is opened from it and `Q` comes
back. You never navigate between two sub-screens except where noted.

    map ──E──> cargo (a port)      ──RETURN──> commit leg
     │  ──E──> shipyard (SHY only) ──RETURN──> commit leg
     │  ──R──> commit leg
     │  ──I──> in-hull             ──R──────> commit leg
     │  ──U──> port upgrades

Two selections live on the map at once, and they are independent:

- `A` / `D` select a **port** (what `E` and `U` open).
- `TAB` selects a **hull** (what `R`, `I`, `O` and `X` act on).

Most early confusion is these two drifting apart: you press `E` and get a
port your ship isn't in. Check the header of the screen that opens — it
names the port and the vessel.

## The loop, once through

Start: $10,000, ENDURANCE at Mercer Island, DISCOVERY at Edmonds.

1. **Open a port.** On the map, `A`/`D` until the selected port is Mercer
   Island, then `E`. You get the cargo screen: APRON (offers on the
   dock), STAGED (offers you're holding for later), HOLD (what's on the
   ship).
2. **Load.** `W`/`S` moves the cursor, `A`/`D` picks which button is
   armed, `SPACE` presses it. On an apron row with `[ LOAD ]` armed,
   `SPACE` puts it in the hold. Each row shows destination code, contents,
   pay, and the window in ticks. Take two or three bound for the same
   port — same-destination items pay a 5% stacking bonus per extra item.
3. **Commit a leg.** `RETURN` from the cargo screen. Now you're on the
   commit screen: destinations on the left, route offers on the right.
   `W`/`S` picks the destination, `A`/`D` picks LANE or DIRECT,
   `SPACE` commits. Left column boxes off how many items aboard are owed
   to each port; HOLD MANIFEST at bottom right lists them.
4. **Spend the time.** Back on the map, `RETURN`. She sails. The run
   stops when she docks.
5. **Get paid.** Docking pays automatically for everything bound there.
   `E` at that port to load the next lot.

That's the whole economy. Everything else is what goes wrong.

## "She's at sea and HOLDING. How do I get her to a port?"

A hull with an empty order queue sits still forever — she is not drifting
home. Give her an order:

- From the **map**: `TAB` until she's the selected hull (bottom-left
  contacts panel shows her highlighted), then `R`, pick a destination
  with `W`/`S`, `SPACE`. Then `RETURN` to run.
- From the **in-hull view**: `R` does the same thing without going back
  to the map.

This works from open water exactly as it does from a berth — the commit
screen quotes a route from wherever she is. If she was under manual helm,
committing a leg secures the helm and takes over.

Manual helm (`H` in the in-hull view) is **not** how you travel. It is
for the last mile in bad water — creeping, running dark, standing off
something. She will steer that heading until you tell her otherwise or
she meets breakers. `H` again drops it.

## The in-hull view, and when to bother

`I` from the map. This is the ship's own instruments — a 6 NM bubble, not
a camera. Most legs never need it. Open it when you want to *look* at
something rather than move past it.

- `P` **ping** — resolves everything at once, and adds 30 to the noise
  ledger. The basin listens: loud hulls attract the anomaly's wander.
- `E` **read** — radar and sonar disagree about the anomaly. Exactly one
  is honest at any moment, and which one flips on its own schedule.
  Committing a read plots that instrument's claim as the working fix on
  the overhead map. There is no confirmation you were right.
- `H` **helm**, then `A`/`D` heading, `W`/`S` throttle (STOP / SLOW /
  CRUISE / FLANK). FLANK is 1.3× cruise, three times as loud, and blinds
  a quarter of the radar.
- `1` / `2` **power** ENG and RDR. A powered-down system can't be damaged
  by undecided water — and does nothing. Both off is a dark boat: silent,
  shielded, going nowhere, and every hit lands on her frames instead.
- `J` **rig** — jury-rig the worst component at sea. Needs open water and
  an empty queue, never gets past 60. The CON panel's RIG row tells you
  whether it's available and why not.

The CON panel is status, not commands you must issue. The HELM row always
reads her present compass heading — `106 E  auto` means she is on that
heading sailing a committed leg, which is the normal state and is fine;
`106 E  CRUISE` means you have the helm. Headings and contact bearings
both read from north.

Under the status line at the bottom of that column is her condition:
`ENG 100  RDR 100  HUL 62`, green above 60, amber down to 30, magenta
below. The same three numbers appear per hull in the map's contacts
panel, so you can watch the whole fleet without opening anything.

## Reading the water

Every route offer quotes a stability band 0–4 for the water it actually
crosses — the worst sample on the path decides the rating, so one bad
patch caps the whole leg. 4 is decided and safe; 0–2 gnaws at ENG, RDR
and HUL every tick you spend in it.

Coverage comes from ports (9 NM), lit buoy stations (7.5 NM), each hull's
own radar, and the observed flag (`O` on the map — exactly one hull can
hold it, 9 NM, occasional dropout).

**LANE and DIRECT often quote the same stability.** That is not a bug and
usually not something you fix by choosing differently: both paths cross
the same undecided patch, so both are capped by it.

Working out *which* patch is chart work. Every station is named on the
map — `○` in cyan is lit, `·` in dim is dark — so a run that quotes 2/4
is telling you there is a dark station somewhere along it. Light it and
the LANE offer separates from DIRECT, because the lane snaps to stations
and the direct line doesn't.

At start, the northern lane (B1–B5) is lit and the yard corridor (J6, J7)
and the southern basin (S1–S3) are not. That's why every Shipyard run
quotes 2/4. Buoys are bought at the Shipyard: `E` there, `TAB` to the
BUOY TENDER section. $2,500 to light, $6/tick forever — certainty is a
subscription, and the upkeep bills whether or not you sail that water.

## What actually kills you

- **Windows.** Contracts age everywhere, including in your hold. Expire
  on the apron and the offer just evaporates. Expire in your custody and
  you eat a penalty, lose standing, and the cargo decoheres to a VOID
  slot that rides along until you next dock. There is no partial credit.
  The commit screen warns `WINDOW n < t TICKS -- WILL MISS` before you
  commit; believe it and `X` out instead.
- **Attrition.** Damage is persistent and repair costs *ticks in a
  berth* — the same currency the windows are denominated in. At HUL 0 she
  goes derelict and another hull has to tow her in.
- **Buoy upkeep in arrears.** Negative credits stop you buying.

## Cheat sheet

| Where | Keys |
|---|---|
| Map | arrows pan · -/+ range · A/D port · TAB ship · E open · U upgrade · O observe · R route · I in-hull · X abandon · SPACE tick · RETURN run · F5/F9 save/load · Q quit |
| Cargo | WASD move · SPACE act · F vessel · U upgrade · R repair · RETURN commit leg · Q back |
| Commit | W/S dest · A/D option · SPACE commit · C circuit · G pause · X abandon · Q back |
| In-hull | P ping · E read · H helm · A/D heading · W/S throttle · 1/2 power · J rig · R route · TAB next hull · SPACE tick · RETURN run · Q back |
| Repair | W/S choose · SPACE repair (twice) · Q back |
| Shipyard | TAB section · W/S choose · SPACE act (twice) · R repair · RETURN route · Q back |
