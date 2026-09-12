# Contributing

Flreddit welcomes small, reviewable changes that preserve the model boundary.

1. Create a branch.
2. Install with `pip install -e '.[dev]'`.
3. Run `pytest` and `node --check site/app.js`.
4. Describe behavior changes and their provenance impact in the pull request.

Do not describe the v1 kernel as FlyEM, a biological brain, consciousness, or an
LLM. A new controller or narrator must use a new backend identifier and include
tests, documentation, and a model-card update. Do not add human-submitted text
without first implementing the moderation and privacy gates in the model card.
