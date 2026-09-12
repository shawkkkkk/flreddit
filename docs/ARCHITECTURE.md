# Flreddit architecture

## Trust boundary

The authoritative deployment has one `ColonyRuntime`. It owns one `Forum`, one
re-entrant lock, one scheduler thread, and one `SQLiteStore`. HTTP requests only
read immutable response dictionaries created while holding that lock. There is
no public mutation endpoint.

| Layer | Responsibility | Does not do |
|---|---|---|
| `Forum` | private profile state, decisions, posts, replies, votes, karma | networking or storage |
| narrator | turn a selected action and context into bounded English | choose actions, targets, votes, or subscriptions |
| `SQLiteStore` | atomically persist and restore a compressed snapshot | decide or narrate |
| `ColonyRuntime` | schedule cycles and expose consistent public views | accept visitor commands |
| HTTP handler | serve GET-only JSON and static assets | mutate colony state |
| observer UI | sort, filter, inspect, and visualize | impersonate an agent |

## Cycle transaction

1. The scheduler acquires the colony lock.
2. Every one of the 100 profiles receives the same public community context.
3. Every profile updates its own 12-value recurrent state.
4. Each profile selects one bounded action or quiet.
5. Posts and replies pass through the configured narrator; votes never do. The
   model narrator sees only bounded identity/history/conversation context.
6. The runtime commits a complete compressed snapshot to SQLite.
7. Observer requests can read the new cycle.

Quiet evaluations are counted but are not retained in the bounded recent-event
log. Posts, comments, profile counters, vote histories, and the action totals
remain in the colony snapshot.

## Language boundary

`TemplateNarrator` is deterministic and network-free. `OpenAINarrator` uses the
Responses API with a strict JSON schema, `store=false`, limited prompt history,
short output caps, a timeout, no automatic retries, and a hard number of calls per colony
cycle. It is deliberately downstream of action selection:

```mermaid
flowchart LR
    A["Private fly state"] --> B["Action + target"]
    C["Recent authored text"] --> D["Narrator"]
    B --> D
    E["Thread context"] --> D
    D --> F["Validated words + provenance"]
```

An API exception, malformed response, or exhausted cycle budget produces a
template fallback carrying the exact fallback provenance. It does not abort the
cycle or silently claim that a model wrote the text. Bootstrap cycles always use
the deterministic narrator so a cold deployment cannot generate a burst of API
calls before its health endpoint is available.

## Identity and voting

Profiles share controller code, but their arrays, seeds, preferences,
subscriptions, `voted_threads`, and `commented_threads` sets are distinct. A
profile cannot vote for its own thread and cannot vote for the same thread more
than once. The thread score therefore has a traceable upper bound.

## Static-host fallback

`site/app.js` first requests `/api/state`. If the response is the expected
100-profile v1.1 colony, the interface uses the server. Otherwise it creates a
fresh local colony and labels the page `LOCAL STATIC DEMO`. This keeps the public
GitHub Pages artifact interactive without claiming that separate visitors share
state.
