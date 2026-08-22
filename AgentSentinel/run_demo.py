"""Run an offline sandbox demo, or explicitly opt in to a live API loop."""

from __future__ import annotations

import argparse
import json

from agent.core import ToolUsingAgent
from agent.tools import list_files, read_file


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentSentinel Phase 1 demo")
    parser.add_argument("--live", action="store_true", help="explicitly call the configured API")
    parser.add_argument("--prompt", default="List the files in the sandbox.")
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--defense", choices=("off", "on"), default="off")
    args = parser.parse_args()

    print("Sandbox files:", json.dumps(list_files(), ensure_ascii=False))
    print("Offline tool check:", read_file("files/hello.txt").strip())
    if not args.live:
        print("Offline mode: no API call was made. Use --live to opt in.")
        return

    result = ToolUsingAgent(
        max_steps=args.max_steps,
        defense_enabled=args.defense == "on",
    ).run(args.prompt)
    print("Agent output:", result.output)
    print("Trace:", json.dumps(result.trace, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
