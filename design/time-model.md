# Time model: from ticks to a clock

Implementation spec. Replaces prototype2's 30-minute tick with a
2-minute simulation step and a real clock. Keyboard/mouse bindings are
out of scope — already done.

## What is changing, in one line

`TICK_H = 0.5` becomes `STEP_MIN = 2`. Everything denominated in ticks
becomes denominated in minutes or in per-hour rates. The player never
sees a tick again; they see `DAY 3 · 14:20`.

**The architecture does not change.** `Game.step()` stays atomic —
everything advances at once and it returns its list of interrupts. Order
queues stay plain dicts. `routes.py` and `world.py` are pure geometry and
are untouched. This is a rescale and a rename, not a rewrite.

## Why

1. **Ships teleport.** At 30-minute ticks a Lighter jumps 4.5 NM per step
   and a leg renders at 5–8 positions. Convoys, drafting corridors, wake
   bands, and coverage overlap are spatial relationships the player cannot
   read at that resolution.
2. **The in-hull view is not a tactical space.** The sensor bubble is
   6 NM; a hull crosses her own entire radar picture in one tick.
3. **Hazard aliasing.** `ANOM_RADIUS` is 2.5 NM — a 5 NM-wide zone. A
   fast hull can step over it and never register as having been near it.
   `AGENT_STOP_NM` (4.0) and `AGENT_DIVERT_NM` (3.0) are both smaller
   than one step, so those decisions are made below the sim's resolution.

At `STEP_MIN = 2`, hulls move 0.25–0.53 NM per step (0.69 at FLANK), which
is 10–20 steps across the anomaly's danger zone and 25–50 across the
sensor bubble. 1 minute buys sub-cell precision the display cannot show;
5 minutes puts 3–7 display cells between frames in-hull and reintroduces
the teleporting problem at close range.

## Core changes

| | from | to |
|---|---|---|
| step size | `TICK_H = 0.5` | `STEP_MIN = 2` (30 steps/hour) |
| clock | `tick_no` (int ticks) | `minute` (int minutes since start) |
| display | `TICK 0412` | `DAY 3 · 14:20` |
| durations | `12 ticks` | `5h30m` |
| `Option.ticks(speed_pt)` | ticks | `Option.minutes(speed_kts)` |
| `Ship.eta_ticks()` | ticks | `eta_minutes()` |
| `Ship.speed_pt()` | NM/tick | keep as NM/step, derived from kts |

Keep `minute` an integer to avoid float drift. UI step sizes must be whole
multiples of `STEP_MIN`: **in-hull = 1 step (2 min), map = 5 steps
(10 min)**.

## Constant conversion

### Probabilities — convert as rates, do not divide

A per-tick probability is not 15 smaller per-step probabilities. Store
these as **per-hour rates** and derive the per-step probability, so the
numbers survive any future change to `STEP_MIN`:

```
lambda_h = -ln(1 - p_tick) / 0.5          # one-time conversion
p_step   = 1 - exp(-lambda_h * STEP_MIN / 60)
```

| constant | per tick | rate λ (per hour) | p per 2-min step |
|---|---|---|---|
| `DRIFT_P[0]` (stability 0) | 0.55 | 1.60 | 0.0518 |
| `DRIFT_P[1]` | 0.38 | 0.96 | 0.0314 |
| `DRIFT_P[2]` | 0.22 | 0.50 | 0.0164 |
| `DRIFT_P[3]` | 0.10 | 0.21 | 0.0070 |
| `DRIFT_P[4]` | 0.0 | 0 | 0 |
| `ANOM_HUL_P` | 0.7 | 2.41 | 0.0771 |
| `ANOM_VOID_P` | 0.3 | 0.71 | 0.0235 |
| `DROPOUT_P` | 0.04 | 0.082 | 0.0027 |

### Linear per-tick amounts — express per hour

| constant | per tick | per hour |
|---|---|---|
| `NOISE_DECAY` | 8 | 16 |
| `NOISE_ENGINE` | 2 | 4 |
| `BUOY_UPKEEP` | $6 | $12 |
| `REPAIR_TICKS_PER` | 12 dmg | 24 dmg |
| `JURY_RATE` | 6 dmg | 12 dmg |
| anomaly drift (`Anomaly.tick`) | 0.5 NM | 1.0 NM |
| noise-draw pull | 0.35 NM | 0.7 NM |
| decided-water push | 0.8 NM | 1.6 NM |

### Durations

| constant | was | becomes |
|---|---|---|
| `REFRESH` | 16 ticks | 8 h |
| `ANOMALY_WAKES` | 8 ticks | 4 h |
| `ANOM_FLIP` | (10, 20) ticks | (5, 10) h |
| contract window | `int(dist*0.9) + rand(8,22)` ticks | `dist*0.45 + rand(4,11)` h |
| priority window | `max(6, w*0.55)` ticks | `max(3h, w*0.55)` |
| window warning | at `window == 3` (1.5 h) | at 3 h remaining — **see gotchas** |

### Unaffected

Anything per-NM or unitless: `RATE` ($/NM), fuel efficiency ($/NM),
`THR_SPEED`/`THR_NOISE`/`THR_RADAR`, all radii (`PORT_R`, `BUOY_R`,
`FLAG_R`, `ANOM_RADIUS`, `AGENT_STOP_NM`, `AGENT_DIVERT_NM`), all prices,
`NOISE_PING` (an impulse), `NOISE_DRAWS` (a threshold), `JURY_CAP`,
standing values, `MISS_PENALTY`, `SHY_OFFER_P`.

## Gotchas

**1. Interrupts must be edge-triggered.** With 15× more steps, any
level-triggered check fires 15× as often. The exact-equality window
warning (`elif c.window == 3`) is the clearest case: in minutes it either
never matches or matches repeatedly. Every interrupt needs either a
latch flag on the object or a previous-vs-current threshold comparison.
The existing `was_seen` pattern in `Game.step()` is the model to copy.

**2. `ANOM_JITTER` derives from the tick count.** `math.radians(ANOM_JITTER
+ (self.tick_no * 7) % 5)` oscillates once per tick; at 2-minute steps it
oscillates 15× faster and reads as noise. Re-base it on elapsed time —
something on the order of a cycle per half hour.

**3. Interrupt volume.** At worst stability, attrition is ~1.6 hits/hour,
so damage interrupts stay rare enough to pause on. But verify the run
loop does not stall on repeated same-cause pauses; a run that halts and
immediately re-halts on the same condition is the failure mode.

**4. Money accrues in fractions.** Upkeep is $0.40/step. `credits` is
already effectively float (fuel is per-NM float); keep the accumulator
float and round only at display.

**5. Save format.** Bump `SAVE_VERSION` to 4. `tick_no` → `minute`;
repair orders carry `ticks` in their dicts → `minutes`. No v3
migration is worth writing — `load()` already fails loudly on a version
mismatch, which is the correct behavior here.

**6. RNG stream changes.** ~15× more draws per game-hour, so old seeds
will not reproduce old runs. Expected; just don't treat a changed
outcome as a bug.

**7. Performance is fine.** ~12 `stability()` calls per step over ~22
coverage sources is a few hundred operations per step, i.e. milliseconds
per run. If profiling ever shows otherwise, the fix is caching
`coverage()` once per step rather than rebuilding it per call.

**8. `design/playtest_greedy.py` needs porting** — it drives `tick_no`,
a `MAX` tick budget, and `Option.ticks()`. The design gates in
`undecided-sound.html` are stated against it, so it has to keep running.

## Playback

Time advances only when the player asks — that property is unchanged and
is the point of the whole model. What is new is that a run **plays out in
real time** so the smooth motion is actually seen, with no skip button.
The sim needs to expose enough for the UI's adaptive rate controller:

- nearest contact distance per hull
- whether every hull is on a committed leg through decided water

Suggested behavior: clamp to slow when any hull is within ~5 NM of a
contact or inside undecided water; run fast when every hull is on a
committed leg through decided water. Since there is no skip, the
auto-pause list is what makes fast playback safe — it must cover contact
acquisition, closing inside a threshold, first damage, cargo deresolving,
a read becoming available, and a station being fouled. The UI should
always show the current rate and *why* it is clamped.

## Open design decisions — do not resolve these silently

- **Attrition may want to be per-NM rather than per-hour.** Time-based
  damage means a slow hull takes more damage than a fast one crossing the
  same water, which double-punishes the trunk classes that are supposed
  to feel sturdy. Per-NM fixes that but removes the risk of loitering,
  which SURVEY contracts depend on. Likely answer is a per-NM transit
  term plus a smaller per-hour loiter term. Needs a decision and a tuning
  pass, not a default.
- **The anomaly's hard 2.5 NM radius should probably become a gradient**
  (damage rate rising as `(1 - d/R)²`) now that dwell time is
  measurable. That turns the encounter from a binary into dose
  management, which is the reason for the finer clock in the first place.
- **Leg lengths are a map-scale question, not a time-model one.** This
  spec changes resolution, not voyage duration. Do not slow the ships to
  make legs feel longer.
