STARTS = {
    "r/fermentation": ("The oldest fruit smells the loudest", "Yeast changed the room again", "A sweet edge appeared near the jar"),
    "r/flight": ("The air above the lamp is uneven", "I crossed the chamber without landing", "My left wing corrected first"),
    "r/fruit": ("The pear has become interesting", "A soft grape is still a grape", "I found sugar under the skin"),
    "r/labnotes": ("The glass wall moved closer", "The room reset after the light", "Today the ceiling vibrated twice"),
    "r/light": ("Blue light pulls differently", "The bright square returned", "A shadow crossed all my ommatidia"),
    "r/night": ("The dark has quieter currents", "Nothing moved except the colony", "The lamp went out before the smell did"),
}

ENDINGS = (
    "Did anyone else notice?", "I would sample it again.", "This may be worth following.",
    "I changed direction immediately.", "No conclusion yet.", "The thread should know.",
)

REPLIES = (
    "I crossed the same signal.", "That was not my reading.", "The timing matches my last flight.",
    "Can you describe the odor?", "Upvoted for the careful landing.", "I will check the north wall.",
)


def post(community: str, variant: int) -> tuple[str, str]:
    start = STARTS[community][variant % 3]
    end = ENDINGS[(variant // 3) % len(ENDINGS)]
    title = start
    return title, f"{start}. {end}"


def reply(variant: int, target: str) -> str:
    return f"@{target} {REPLIES[variant % len(REPLIES)]}"
