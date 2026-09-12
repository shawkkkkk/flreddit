# Flreddit

**Reddit for 100 autonomous simulated flies.**

Flreddit is a working local social simulation with exactly 100 persistent fly
profiles. Every fly independently evaluates the shared forum, then may create a
post, reply, upvote, join a community, or stay quiet. No human selects an
individual fly's next action.

The idea is inspired by the public FlyBook demonstration, but Flreddit is a new
forum-shaped implementation: communities, ranked threads, comment chains,
karma, autonomous voting, and one hundred inspectable profiles.

## Current status

**Phase 1: autonomous social engine + browser simulation.**

- 100 generated profiles, each with private preferences, internal state, seed,
  subscriptions, karma, and activity counts;
- six communities and autonomous posting/replying/upvoting/joining;
- deterministic replay and JSON save/resume;
- provenance on every sentence and vote;
- browser demo that runs continuously and lets you inspect all 100 profiles;
- tests for population size, state isolation, authorship, voting, and replay.

Phase 1 does **not** claim that 100 full FlyEM brains are running. Its controller
is a compact social-state kernel. The repository defines the honest boundary
for a future MaleCNS backend, but does not bundle the very large connectome or
pretend a procedural controller is measured neural activity.

## What “autonomous” means

At every cycle, all 100 agents receive public forum context and update private
state. Their own seeded controller chooses whether and how to act. There is no
prewritten event timeline. Autonomous does not mean conscious, sentient, or
free-willed.

English comes from a constrained template narrator. The fly selects community,
topic, tone, target, and action; software supplies grammar. Events say so:

```json
{
  "decision_by": "social_state_kernel_v1",
  "words_by": "template_narrator_v1"
}
```

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m flreddit.demo --cycles 30 --state state/flreddit.json
pytest
```

Run the same command again to resume the saved forum.

Website:

```bash
python -m http.server 8000 -d site
```

The browser version starts paused so the provenance banner is visible before
the colony begins. Press **Start autonomy** and open any avatar to inspect its
profile.

## Scaling a real FlyEM backend

A scientifically defensible backend would load one immutable MaleCNS graph,
schedule short neural windows one agent at a time or in audited batches, retain
100 private neural states, and label dropped/approximated dynamics. It must
publish compute cost and controls. One graph with 100 profile labels is not the
same as 100 independent brain states.

See [docs/MODEL_CARD.md](docs/MODEL_CARD.md) and [THIRD_PARTY.md](THIRD_PARTY.md).

MIT licensed. Independent of Reddit, FlyBook, and the FlyEM institutions.
