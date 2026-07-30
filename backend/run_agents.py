"""Run one agent cycle from the command line.

Useful for demonstrating the agents without the frontend:

    venv\\Scripts\\python run_agents.py
"""

import json

from agents import run_cycle
from app import app


def main():
    with app.app_context():
        results = run_cycle()

    for result in results:
        agent = result.pop("agent")
        print(f"\n{agent}")
        print("-" * len(agent))
        for key, value in result.items():
            if isinstance(value, (list, dict)) and value:
                print(f"  {key}:")
                print(
                    "\n".join(
                        f"    {line}" for line in json.dumps(value, indent=2).splitlines()
                    )
                )
            else:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
