# Design

Campaign design for the game prototype2 is becoming.

- **`undecided-sound.html`** — *The Undecided Sound*: the full campaign
  design. The reclamation premise, the certainty loop, hub-and-spoke
  freight (trunk/spoke classes, draft, staging as transshipment), convoys
  and the moving lighthouse, the expedition that opens a basin, the
  five-basin campaign, the complexity budget, and the design gates.
  Open it in a browser.

- **`playtest_greedy.py`** — the headless bot the gates are written
  against: a player who works the freight economy competently and ignores
  the observation economy completely. Run it with `python
  design/playtest_greedy.py` (needs pygame, since it imports the
  prototype2 model). It currently turns $10,000 into ~$80,000 over 400
  ticks without once observing, pinging, reading an instrument, or
  lighting a buoy — which is the problem the design exists to fix. Under
  the campaign design, this bot should go broke.
