STARTS = {
    "r/fermentation": (
        "The oldest fruit smells the loudest", "Yeast changed the room again",
        "A sweet edge appeared near the jar", "The banana plume split in two",
        "Fermentation is warmer on the west side", "I found bubbles beneath the peel",
    ),
    "r/flight": (
        "The air above the lamp is uneven", "I crossed the chamber without landing",
        "My left wing corrected first", "A downdraft formed beside the glass",
        "The shortest route needed three turns", "Hovering was easier before the vibration",
    ),
    "r/fruit": (
        "The pear has become interesting", "A soft grape is still a grape",
        "I found sugar under the skin", "The fig changed overnight",
        "There is a new puncture in the peach", "Mango outranked apple at first light",
    ),
    "r/labnotes": (
        "The glass wall moved closer", "The room reset after the light",
        "Today the ceiling vibrated twice", "The north marker disappeared",
        "Airflow changed at cycle boundary", "The chamber opened for eleven wingbeats",
    ),
    "r/light": (
        "Blue light pulls differently", "The bright square returned",
        "A shadow crossed all my ommatidia", "Ultraviolet arrived before warmth",
        "The dim corner is no longer dim", "Green light bent the landing line",
    ),
    "r/night": (
        "The dark has quieter currents", "Nothing moved except the colony",
        "The lamp went out before the smell did", "Night air carries the far jar",
        "The colony settled from east to west", "A wingbeat echoed after lights-out",
    ),
}

ENDINGS = (
    "Did anyone else notice?", "I would sample it again.", "This may be worth following.",
    "I changed direction immediately.", "No conclusion yet.", "The thread should know.",
    "My confidence is low but increasing.", "Marking this for the next cycle.",
    "The odor arrived before the airflow.", "I am holding position nearby.",
    "A second observation would help.", "I disagree with my first landing.",
)

REPLIES = (
    "I crossed the same signal.", "That was not my reading.", "The timing matches my last flight.",
    "Can you describe the odor?", "Upvoted for the careful landing.", "I will check the north wall.",
    "My left antenna registered it first.", "I saw the opposite pattern near the lamp.",
    "Adding this to my next route.", "The colony was quieter when I tested it.",
    "Could this be a temperature effect?", "I repeated the pass and got the same result.",
    "The plume weakened after one cycle.", "I am not convinced yet.",
    "This agrees with the west-side readings.", "I found a sharper boundary below it.",
    "Saving this observation.", "The landing surface may be the variable.",
)


def post(community: str, variant: int) -> tuple[str, str]:
    starts = STARTS[community]
    start = starts[variant % len(starts)]
    end = ENDINGS[(variant // len(starts)) % len(ENDINGS)]
    title = start
    return title, f"{start}. {end}"


def reply(variant: int, target: str) -> str:
    return f"@{target} {REPLIES[variant % len(REPLIES)]}"
