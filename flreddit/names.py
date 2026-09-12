ADJECTIVES = (
    "amber", "brisk", "cobalt", "dappled", "electric",
    "fuzzy", "gentle", "hollow", "iridescent", "jittery",
)

NOUNS = (
    "antenna", "bristle", "compoundeye", "drifter", "fruit",
    "hover", "lantern", "proboscis", "shadow", "wing",
)

COMMUNITIES = ("r/fermentation", "r/flight", "r/fruit", "r/labnotes", "r/light", "r/night")


def profile_name(index: int) -> tuple[str, str]:
    adjective = ADJECTIVES[index // 10]
    noun = NOUNS[index % 10]
    handle = f"{adjective}_{noun}"
    display = f"{adjective.title()} {noun.title()}"
    return handle, display
