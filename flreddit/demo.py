import argparse
from pathlib import Path

from .forum import Forum


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=30)
    parser.add_argument("--state", type=Path)
    args = parser.parse_args()
    exists = args.state and args.state.exists() and args.state.stat().st_size > 0
    forum = Forum.load(args.state) if exists else Forum()
    for _ in range(args.cycles):
        forum.step()
    if args.state:
        forum.save(args.state)
    print(f"profiles=100 cycles={forum.cycle} threads={len(forum.threads)} comments={sum(len(t.comments) for t in forum.threads)} upvotes={sum(t.score-1 for t in forum.threads)}")
    for thread in sorted(forum.threads, key=lambda t: (-t.score, -t.id))[:5]:
        print(f"{thread.community} · {thread.score}↑ · @{thread.author} · {thread.title}")


if __name__ == "__main__":
    main()
