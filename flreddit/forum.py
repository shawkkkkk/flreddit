from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from .names import COMMUNITIES, profile_name
from .narrator import post as narrate_post, reply as narrate_reply


@dataclass
class Profile:
    handle: str
    display_name: str
    seed: int
    color: str
    preferences: np.ndarray = field(repr=False)
    state: np.ndarray = field(default_factory=lambda: np.zeros(12, np.float32), repr=False)
    subscriptions: set[str] = field(default_factory=set)
    karma: int = 0
    posts: int = 0
    comments: int = 0
    votes: int = 0

    def public(self) -> dict:
        return {
            "handle": self.handle, "display_name": self.display_name, "color": self.color,
            "subscriptions": sorted(self.subscriptions), "karma": self.karma,
            "posts": self.posts, "comments": self.comments, "votes": self.votes,
        }


@dataclass
class Thread:
    id: int
    author: str
    community: str
    title: str
    body: str
    cycle: int
    score: int = 1
    comments: list[dict] = field(default_factory=list)
    decision_by: str = "social_state_kernel_v1"
    words_by: str = "template_narrator_v1"


@dataclass
class Event:
    cycle: int
    actor: str
    action: str
    thread_id: int | None = None
    target: str | None = None
    decision_by: str = "social_state_kernel_v1"
    words_by: str | None = None


class Forum:
    def __init__(self, seed: int = 100):
        self.seed = seed
        self.cycle = 0
        self.rng = np.random.default_rng(seed)
        self.profiles: dict[str, Profile] = {}
        for i in range(100):
            handle, display = profile_name(i)
            local = np.random.default_rng(seed + i * 1009)
            preferences = local.dirichlet(np.ones(len(COMMUNITIES))).astype(np.float32)
            color = f"hsl({int((i * 137.508) % 360)} 62% 68%)"
            subscriptions = {COMMUNITIES[int(np.argmax(preferences))]}
            self.profiles[handle] = Profile(handle, display, seed + i * 1009, color, preferences, subscriptions=subscriptions)
        self.threads: list[Thread] = []
        self.events: list[Event] = []

    def _context(self) -> np.ndarray:
        counts = np.ones(len(COMMUNITIES), np.float32)
        for thread in self.threads[-80:]:
            counts[COMMUNITIES.index(thread.community)] += max(1, thread.score)
        return counts / counts.sum()

    def _update(self, profile: Profile, context: np.ndarray) -> tuple[str, str]:
        local = np.random.default_rng(profile.seed + self.cycle * 65537)
        signal = np.concatenate(
            (
                context,
                np.asarray([len(self.threads) / 100, profile.karma / 100]),
                local.random(4),
            )
        )[:12]
        profile.state = np.tanh(.76 * profile.state + .58 * (signal - .2) + local.normal(0, .08, 12)).astype(np.float32)
        community_score = profile.preferences * (context + .08) + local.random(6) * .03
        community = COMMUNITIES[int(np.argmax(community_score))]
        # Every profile evaluates every cycle, but most elect to stay quiet.
        # Internal state modulates bounded action probabilities; seeded
        # exploration prevents one channel's raw scale from dominating forever.
        tendency = 1 / (1 + np.exp(-profile.state[:4]))
        probabilities = np.array([
            .045 + .10 * tendency[0],
            (.035 + .09 * tendency[1]) if self.threads else 0,
            (.05 + .12 * tendency[2]) if self.threads else 0,
            .012 + .025 * tendency[3],
        ])
        draw = local.random()
        cumulative = np.cumsum(probabilities)
        if draw < cumulative[0]:
            action = "post"
        elif draw < cumulative[1]:
            action = "reply"
        elif draw < cumulative[2]:
            action = "upvote"
        elif draw < cumulative[3]:
            action = "join"
        else:
            action = "quiet"
        return action, community

    def step(self) -> list[Event]:
        self.cycle += 1
        context = self._context()
        new: list[Event] = []
        for profile in self.profiles.values():
            action, community = self._update(profile, context)
            local = np.random.default_rng(profile.seed + self.cycle * 31337)
            event = Event(self.cycle, profile.handle, action)
            candidates = [t for t in self.threads[-60:] if t.author != profile.handle]
            if action == "post":
                title, body = narrate_post(community, int(local.integers(1000)))
                thread = Thread(len(self.threads) + 1, profile.handle, community, title, body, self.cycle)
                self.threads.append(thread)
                profile.posts += 1
                event.thread_id = thread.id
                event.words_by = "template_narrator_v1"
            elif action == "reply" and candidates:
                thread = candidates[int(local.integers(len(candidates)))]
                text = narrate_reply(int(local.integers(1000)), thread.author)
                thread.comments.append({
                    "author": profile.handle, "text": text, "cycle": self.cycle,
                    "decision_by": "social_state_kernel_v1", "words_by": "template_narrator_v1",
                })
                profile.comments += 1
                event.thread_id, event.target = thread.id, thread.author
                event.words_by = "template_narrator_v1"
            elif action == "upvote" and candidates:
                thread = candidates[int(local.integers(len(candidates)))]
                thread.score += 1
                self.profiles[thread.author].karma += 1
                profile.votes += 1
                event.thread_id, event.target = thread.id, thread.author
            elif action == "join":
                profile.subscriptions.add(community)
                event.target = community
            else:
                event.action = "quiet"
            new.append(event)
        self.events.extend(new)
        return new

    def snapshot(self) -> dict:
        return {
            "format": 1, "backend": "social_state_kernel_v1", "seed": self.seed,
            "cycle": self.cycle, "profiles": [p.public() for p in self.profiles.values()],
            "preferences": {h: p.preferences.tolist() for h, p in self.profiles.items()},
            "states": {h: p.state.tolist() for h, p in self.profiles.items()},
            "threads": [asdict(t) for t in self.threads], "events": [asdict(e) for e in self.events],
        }

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.snapshot(), indent=2) + "\n")

    @classmethod
    def load(cls, path: str | Path) -> "Forum":
        raw = json.loads(Path(path).read_text())
        if raw.get("format") != 1 or len(raw.get("profiles", [])) != 100:
            raise ValueError("Unsupported or incomplete Flreddit state.")
        forum = cls(seed=int(raw["seed"]))
        forum.cycle = int(raw["cycle"])
        public = {p["handle"]: p for p in raw["profiles"]}
        for handle, profile in forum.profiles.items():
            saved = public[handle]
            profile.preferences = np.asarray(raw["preferences"][handle], np.float32)
            profile.state = np.asarray(raw["states"][handle], np.float32)
            profile.subscriptions = set(saved["subscriptions"])
            profile.karma = int(saved["karma"])
            profile.posts = int(saved["posts"])
            profile.comments = int(saved["comments"])
            profile.votes = int(saved["votes"])
        forum.threads = [Thread(**thread) for thread in raw["threads"]]
        forum.events = [Event(**event) for event in raw["events"]]
        return forum
