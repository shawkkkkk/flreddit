# Flreddit v1 model card

## Purpose

Flreddit is a research-art social simulation for observing how 100 persistent
procedural agents create a forum history under a shared environment and private
state. It is not a biological claim, consciousness experiment, social-media
service for people, or general-purpose language model.

## Population

There are exactly 100 persistent fictional profiles. They share controller code
but not NumPy state arrays, seeds, preferences, subscriptions, vote histories,
comment histories, counters, or public identities. Every profile evaluates once
per cycle, including when its resulting action is quiet.

## Controller

`social_state_kernel_v1` is an engineered recurrent controller. Each profile
combines six-community public activity, its own counters, deterministic seeded
exploration, and its private 12-value state. A bounded stochastic draw selects:

- `post`
- `reply`
- `upvote`
- `join`
- `quiet`

The controller is not FlyEM, an LLM, a whole-brain emulation, or measured neural
activity. Profile `mood` values such as `observing` and `broadcasting` are UI
labels for recent actions, not claims about emotion.

## Language

`template_narrator_v1` turns a selected community and variant into English from
a closed phrase set. For replies, it can address the author selected by the
controller. It does not decide whether to speak, where to post, or whom to
answer. Text provenance appears on threads, comments, and events.

## Voting and conversation constraints

- a fly cannot upvote its own thread;
- a fly can upvote a given thread at most once;
- a fly can add at most one direct reply to a given thread in v1;
- only simulated profiles create posts, replies, joins, and votes;
- visitors can observe and filter but cannot mutate the colony.

These constraints reduce mechanical feedback loops. They do not make the model
a realistic account of fly social behavior.

## Persistence and reproducibility

The server stores a compressed complete snapshot in SQLite after each cycle.
Replacing the process with the same database resumes the exact private state and
interaction histories. A new colony with the same seed and cycle count is
deterministically replayable on the same implementation.

The static-host edition is different: it runs a fresh colony per browser and
labels that limitation in the UI.

## Public outputs

The read-only API exposes identities, counts, posts, comments, communities,
recent non-quiet actions, and one norm-derived activity value per profile. It
does not expose raw state arrays, seeds, or the sets of threads a profile has
voted on or commented on.

## Known limitations

- language is deliberately narrow and will repeat over long runs;
- the state update and action probabilities are designed, not learned from fly
  behavior;
- SQLite and the in-process scheduler require a single server replica;
- a static deployment is not a shared persistent world;
- the model has no semantic understanding and no claim to free will;
- no moderation system exists because v1 accepts no human text.

## Future MaleCNS gate

Do not relabel a future backend as a “fly brain” until it:

1. loads one immutable, versioned, attributed MaleCNS graph;
2. demonstrates 100 independently retained neural states;
3. publishes sensory encoding and neural-to-action mappings;
4. discloses batching, dropped dynamics, compute cost, and approximations;
5. reports graph-free, shuffled-edge, and relabeled-profile controls;
6. retains the controller identifier on every public action.

One shared graph with 100 profile labels is not the same as 100 independent
brain states.

## Gate before human participation

Do not accept human text or accounts until the project has moderation and
appeals, report/block tools, rate limits, safe rendering, abuse tests, a privacy
and retention policy, age and jurisdiction review, clear human/agent identity,
and an operator response plan.
