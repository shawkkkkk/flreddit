import numpy as np

from flreddit import Forum


def test_exactly_one_hundred_unique_profiles_with_private_states():
    forum = Forum()
    assert len(forum.profiles) == 100
    assert len(set(forum.profiles)) == 100
    states = [profile.state for profile in forum.profiles.values()]
    assert len({id(state) for state in states}) == 100
    states[0][0] = 1
    assert all(state[0] == 0 for state in states[1:])


def test_seeded_forums_are_replayable():
    left, right = Forum(seed=42), Forum(seed=42)
    for _ in range(5):
        left.step(); right.step()
    assert left.snapshot() == right.snapshot()


def test_forum_generates_posts_replies_and_votes():
    forum = Forum()
    for _ in range(35):
        forum.step()
    assert forum.threads
    assert any(thread.comments for thread in forum.threads)
    assert any(thread.score > 1 for thread in forum.threads)


def test_language_and_vote_provenance():
    forum = Forum()
    for _ in range(20):
        forum.step()
    assert all(t.words_by == "template_narrator_v1" for t in forum.threads)
    assert all(e.decision_by == "social_state_kernel_v1" for e in forum.events)
    vote_events = [e for e in forum.events if e.action == "upvote"]
    assert vote_events and all(e.words_by is None for e in vote_events)


def test_save_round_trip(tmp_path):
    forum = Forum(seed=7)
    forum.step()
    path = tmp_path / "forum.json"
    forum.save(path)
    assert Forum.load(path).snapshot() == forum.snapshot()
