from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from .names import COMMUNITIES, profile_bio, profile_name
from .narrator import TEMPLATE_BACKEND, TemplateNarrator


STATE_FORMAT = 2
DECISION_BACKEND = "social_state_kernel_v1"
NARRATOR_BACKEND = TEMPLATE_BACKEND
MAX_RECENT_EVENTS = 5000


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
    bio: str = ""
    mood: str = "observing"
    last_active_cycle: int = 0
    voted_threads: set[int] = field(default_factory=set, repr=False)
    commented_threads: set[int] = field(default_factory=set, repr=False)

    def public(self) -> dict:
        return {
            "handle": self.handle, "display_name": self.display_name, "color": self.color,
            "subscriptions": sorted(self.subscriptions), "karma": self.karma,
            "posts": self.posts, "comments": self.comments, "votes": self.votes,
            "bio": self.bio, "mood": self.mood,
            "last_active_cycle": self.last_active_cycle,
            "favorite_community": COMMUNITIES[int(np.argmax(self.preferences))],
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
    decision_by: str = DECISION_BACKEND
    words_by: str = NARRATOR_BACKEND


@dataclass
class Event:
    cycle: int
    actor: str
    action: str
    thread_id: int | None = None
    comment_id: int | None = None
    target: str | None = None
    decision_by: str = DECISION_BACKEND
    words_by: str | None = None


class Forum:
    def __init__(self, seed: int = 100, narrator=None):
        self.seed = seed
        self.cycle = 0
        self.rng = np.random.default_rng(seed)
        self.narrator = narrator or TemplateNarrator()
        self.profiles: dict[str, Profile] = {}
        for i in range(100):
            handle, display = profile_name(i)
            local = np.random.default_rng(seed + i * 1009)
            preferences = local.dirichlet(np.ones(len(COMMUNITIES))).astype(np.float32)
            color = f"hsl({int((i * 137.508) % 360)} 62% 68%)"
            subscriptions = {COMMUNITIES[int(np.argmax(preferences))]}
            self.profiles[handle] = Profile(
                handle, display, seed + i * 1009, color, preferences,
                subscriptions=subscriptions, bio=profile_bio(i),
            )
        self.threads: list[Thread] = []
        self.events: list[Event] = []
        self.next_thread_id = 1
        self.next_comment_id = 1
        self.evaluations = 0
        self.action_counts = {action: 0 for action in ("post", "reply", "upvote", "join", "quiet")}

    def _narration_profile(self, profile: Profile) -> dict:
        axes = (
            "novelty-seeking", "social", "skeptical", "methodical",
            "restless", "patient", "playful", "literal",
            "collective", "solitary", "bold", "cautious",
        )
        strongest = np.argsort(np.abs(profile.state))[-3:][::-1]
        voice = [
            f"{axes[int(index)]}:{'high' if profile.state[index] >= 0 else 'low'}"
            for index in strongest
        ]
        return {
            "handle": profile.handle,
            "display_name": profile.display_name,
            "bio": profile.bio,
            "favorite_community": COMMUNITIES[int(np.argmax(profile.preferences))],
            "subscriptions": sorted(profile.subscriptions),
            "karma": profile.karma,
            "previous_mood": profile.mood,
            "voice_signals": voice,
        }

    def _recent_writing(self, handle: str, limit: int = 5) -> list[str]:
        writing: list[str] = []
        for thread in reversed(self.threads):
            for comment in reversed(thread.comments):
                if comment["author"] == handle:
                    writing.append(comment["text"])
                    if len(writing) >= limit:
                        return writing
            if thread.author == handle:
                writing.append(f"{thread.title} — {thread.body}")
                if len(writing) >= limit:
                    return writing
        return writing

    def _recent_forum(self, limit: int = 6) -> list[dict]:
        return [
            {
                "community": thread.community,
                "author": thread.author,
                "title": thread.title,
                "body": thread.body,
                "score": thread.score,
                "reply_count": len(thread.comments),
            }
            for thread in self.threads[-limit:]
        ]

    @staticmethod
    def _thread_context(thread: Thread) -> dict:
        return {
            "id": thread.id,
            "community": thread.community,
            "author": thread.author,
            "title": thread.title,
            "body": thread.body,
            "score": thread.score,
            "recent_replies": [
                {"author": comment["author"], "text": comment["text"]}
                for comment in thread.comments[-8:]
            ],
        }

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
            .002 + .006 * tendency[0],
            (.003 + .008 * tendency[1]) if self.threads else 0,
            (.012 + .025 * tendency[2]) if self.threads else 0,
            .0007 + .002 * tendency[3],
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
        self.narrator.begin_cycle(self.cycle)
        context = self._context()
        new: list[Event] = []
        for profile in self.profiles.values():
            self.evaluations += 1
            action, community = self._update(profile, context)
            local = np.random.default_rng(profile.seed + self.cycle * 31337)
            event = Event(self.cycle, profile.handle, action)
            candidates = [t for t in self.threads[-60:] if t.author != profile.handle]
            if action == "post":
                copy = self.narrator.post(
                    community=community,
                    variant=int(local.integers(1000)),
                    profile=self._narration_profile(profile),
                    recent_writing=self._recent_writing(profile.handle),
                    recent_forum=self._recent_forum(),
                    cycle=self.cycle,
                )
                thread = Thread(
                    self.next_thread_id, profile.handle, community,
                    copy.title, copy.body, self.cycle, words_by=copy.words_by,
                )
                self.next_thread_id += 1
                self.threads.append(thread)
                profile.posts += 1
                event.thread_id = thread.id
                event.words_by = copy.words_by
            elif action == "reply" and candidates:
                reply_candidates = [t for t in candidates if t.id not in profile.commented_threads]
                if not reply_candidates:
                    event.action = "quiet"
                    reply_candidates = []
                if reply_candidates:
                    thread = reply_candidates[int(local.integers(len(reply_candidates)))]
                    copy = self.narrator.reply(
                        variant=int(local.integers(1000)),
                        profile=self._narration_profile(profile),
                        thread=self._thread_context(thread),
                        recent_writing=self._recent_writing(profile.handle),
                        cycle=self.cycle,
                    )
                    comment_id = self.next_comment_id
                    self.next_comment_id += 1
                    thread.comments.append({
                        "id": comment_id, "author": profile.handle, "text": copy.text,
                        "cycle": self.cycle, "target": thread.author,
                        "decision_by": DECISION_BACKEND, "words_by": copy.words_by,
                    })
                    profile.comments += 1
                    profile.commented_threads.add(thread.id)
                    event.thread_id, event.comment_id, event.target = thread.id, comment_id, thread.author
                    event.words_by = copy.words_by
            elif action == "upvote" and candidates:
                vote_candidates = [t for t in candidates if t.id not in profile.voted_threads]
                if vote_candidates:
                    thread = vote_candidates[int(local.integers(len(vote_candidates)))]
                    thread.score += 1
                    self.profiles[thread.author].karma += 1
                    profile.votes += 1
                    profile.voted_threads.add(thread.id)
                    event.thread_id, event.target = thread.id, thread.author
                else:
                    event.action = "quiet"
            elif action == "join":
                unjoined = [name for name in COMMUNITIES if name not in profile.subscriptions]
                if unjoined:
                    joined = max(unjoined, key=lambda name: float(profile.preferences[COMMUNITIES.index(name)]))
                    profile.subscriptions.add(joined)
                    event.target = joined
                else:
                    event.action = "quiet"
            else:
                event.action = "quiet"
            profile.mood = {
                "post": "broadcasting", "reply": "conversing", "upvote": "endorsing",
                "join": "exploring", "quiet": "observing",
            }[event.action]
            if event.action != "quiet":
                profile.last_active_cycle = self.cycle
            self.action_counts[event.action] += 1
            new.append(event)
        self.events.extend(event for event in new if event.action != "quiet")
        if len(self.events) > MAX_RECENT_EVENTS:
            self.events = self.events[-MAX_RECENT_EVENTS:]
        return new

    def snapshot(self) -> dict:
        return {
            "format": STATE_FORMAT, "backend": DECISION_BACKEND, "seed": self.seed,
            "cycle": self.cycle, "profiles": [p.public() for p in self.profiles.values()],
            "preferences": {h: p.preferences.tolist() for h, p in self.profiles.items()},
            "states": {h: p.state.tolist() for h, p in self.profiles.items()},
            "histories": {
                h: {
                    "voted_threads": sorted(p.voted_threads),
                    "commented_threads": sorted(p.commented_threads),
                }
                for h, p in self.profiles.items()
            },
            "next_thread_id": self.next_thread_id,
            "next_comment_id": self.next_comment_id,
            "evaluations": self.evaluations,
            "action_counts": self.action_counts,
            "threads": [asdict(t) for t in self.threads], "events": [asdict(e) for e in self.events],
        }

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(self.snapshot(), indent=2) + "\n")
        os.replace(temporary, target)

    @classmethod
    def load(cls, path: str | Path, narrator=None) -> "Forum":
        raw = json.loads(Path(path).read_text())
        return cls.from_snapshot(raw, narrator=narrator)

    @classmethod
    def from_snapshot(cls, raw: dict, narrator=None) -> "Forum":
        if raw.get("format") not in {1, STATE_FORMAT} or len(raw.get("profiles", [])) != 100:
            raise ValueError("Unsupported or incomplete Flreddit state.")
        forum = cls(seed=int(raw["seed"]), narrator=narrator)
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
            profile.bio = saved.get("bio", profile.bio)
            profile.mood = saved.get("mood", "observing")
            profile.last_active_cycle = int(saved.get("last_active_cycle", 0))
            history = raw.get("histories", {}).get(handle, {})
            profile.voted_threads = {int(value) for value in history.get("voted_threads", [])}
            profile.commented_threads = {int(value) for value in history.get("commented_threads", [])}
        forum.threads = []
        inferred_comment_id = 1
        for thread_data in raw["threads"]:
            comments = []
            for comment in thread_data.get("comments", []):
                normalized = dict(comment)
                normalized.setdefault("id", inferred_comment_id)
                normalized.setdefault("target", thread_data["author"])
                inferred_comment_id = max(inferred_comment_id, int(normalized["id"]) + 1)
                comments.append(normalized)
            normalized_thread = dict(thread_data)
            normalized_thread["comments"] = comments
            forum.threads.append(Thread(**normalized_thread))
        forum.events = [Event(**event) for event in raw.get("events", [])]
        if not raw.get("histories"):
            for event in forum.events:
                if event.thread_id is None or event.actor not in forum.profiles:
                    continue
                if event.action == "upvote":
                    forum.profiles[event.actor].voted_threads.add(event.thread_id)
                elif event.action == "reply":
                    forum.profiles[event.actor].commented_threads.add(event.thread_id)
        forum.next_thread_id = int(raw.get("next_thread_id", max((t.id for t in forum.threads), default=0) + 1))
        forum.next_comment_id = int(raw.get("next_comment_id", inferred_comment_id))
        forum.evaluations = int(raw.get("evaluations", forum.cycle * 100))
        if raw.get("action_counts"):
            forum.action_counts.update({key: int(value) for key, value in raw["action_counts"].items()})
        else:
            for event in forum.events:
                forum.action_counts[event.action] += 1
        return forum
