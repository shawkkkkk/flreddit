import json
from types import SimpleNamespace

from flreddit import Forum
from flreddit.narrator import OpenAINarrator


class FakeResponses:
    def __init__(self, outputs=None, error=None):
        self.outputs = list(outputs or [])
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(output_text=json.dumps(self.outputs.pop(0)))


class FakeClient:
    def __init__(self, outputs=None, error=None):
        self.responses = FakeResponses(outputs=outputs, error=error)


PROFILE = {
    "handle": "amber_antenna",
    "display_name": "Amber Antenna",
    "bio": "Careful plume mapper.",
    "favorite_community": "r/fruit",
    "subscriptions": ["r/fruit"],
    "karma": 4,
    "previous_mood": "observing",
    "voice_signals": ["skeptical:high", "patient:high"],
}


def test_openai_post_uses_structured_stateless_response_and_context():
    client = FakeClient([{"title": "The grape remembers dusk", "body": "Its skin cooled before the glass did."}])
    narrator = OpenAINarrator(client, model="test-model", max_calls_per_cycle=2)
    narrator.begin_cycle(9)
    result = narrator.post(
        community="r/fruit", variant=4, profile=PROFILE,
        recent_writing=["A prior observation."],
        recent_forum=[{"title": "Another thread"}], cycle=9,
    )

    assert result.words_by == "openai_responses_v1:test-model"
    assert result.title == "The grape remembers dusk"
    call = client.responses.calls[0]
    assert call["store"] is False
    assert call["reasoning"] == {"effort": "none"}
    assert call["text"]["format"]["strict"] is True
    payload = json.loads(call["input"][1]["content"])
    assert payload["profile"]["handle"] == "amber_antenna"
    assert payload["recent_writing"] == ["A prior observation."]


def test_openai_reply_receives_conversation_and_addresses_target():
    client = FakeClient([{"text": "The cooler edge may explain your landing."}])
    narrator = OpenAINarrator(client, model="test-model")
    narrator.begin_cycle(10)
    thread = {
        "id": 7, "community": "r/night", "author": "cobalt_hover",
        "title": "The lamp went quiet", "body": "I followed the last warm current.",
        "score": 3,
        "recent_replies": [{"author": "gentle_wing", "text": "I heard it too."}],
    }
    result = narrator.reply(
        variant=2, profile=PROFILE, thread=thread,
        recent_writing=["Night air bends east."], cycle=10,
    )

    assert result.text == "@cobalt_hover The cooler edge may explain your landing."
    payload = json.loads(client.responses.calls[0]["input"][1]["content"])
    assert payload["thread"]["recent_replies"][0]["author"] == "gentle_wing"


def test_api_failure_is_disclosed_and_does_not_stop_language():
    narrator = OpenAINarrator(FakeClient(error=TimeoutError("slow")), model="test-model")
    narrator.begin_cycle(11)
    result = narrator.post(
        community="r/fruit", variant=0, profile=PROFILE,
        recent_writing=[], recent_forum=[], cycle=11,
    )

    assert result.title
    assert result.words_by == "template_narrator_v1:error_fallback"
    assert narrator.status()["fallbacks"] == 1
    assert narrator.status()["last_error"] == "TimeoutError"


def test_forum_enforces_model_call_budget_per_cycle():
    outputs = [
        {"title": "First novel thread", "body": "A new observation."},
        {"title": "Second novel thread", "body": "Another observation."},
    ]
    client = FakeClient(outputs)
    narrator = OpenAINarrator(client, model="test-model", max_calls_per_cycle=2)
    forum = Forum(narrator=narrator)
    forum._update = lambda profile, context: ("post", "r/fruit")

    forum.step()

    assert len(client.responses.calls) == 2
    assert sum(thread.words_by == narrator.backend for thread in forum.threads) == 2
    assert sum("budget_fallback" in thread.words_by for thread in forum.threads) == 98
