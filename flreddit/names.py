ADJECTIVES = (
    "amber", "brisk", "cobalt", "dappled", "electric",
    "fuzzy", "gentle", "hollow", "iridescent", "jittery",
)

NOUNS = (
    "antenna", "bristle", "compoundeye", "drifter", "fruit",
    "hover", "lantern", "proboscis", "shadow", "wing",
)

COMMUNITIES = ("r/fermentation", "r/flight", "r/fruit", "r/labnotes", "r/light", "r/night")

ROLES = (
    "maps fermentation plumes",
    "tests crosswinds near glass",
    "catalogues bruised fruit",
    "records chamber anomalies",
    "tracks spectral changes",
    "patrols the dark edge",
    "follows warm air currents",
    "studies landing surfaces",
    "counts colony rhythms",
    "samples unfamiliar odors",
)

TEMPERAMENTS = (
    "Careful observer",
    "Restless scout",
    "Methodical skeptic",
    "Social forager",
    "Low-light specialist",
    "Patient sampler",
    "Fast responder",
    "Contrarian navigator",
    "Quiet archivist",
    "Curious drifter",
)


def profile_name(index: int) -> tuple[str, str]:
    adjective = ADJECTIVES[index // 10]
    noun = NOUNS[index % 10]
    handle = f"{adjective}_{noun}"
    display = f"{adjective.title()} {noun.title()}"
    return handle, display


def profile_bio(index: int) -> str:
    """Return a stable, unique-ish public biography for one simulated fly."""
    temperament = TEMPERAMENTS[index % len(TEMPERAMENTS)]
    role = ROLES[(index * 7 + index // 10) % len(ROLES)]
    return f"{temperament}. Usually {role}."
