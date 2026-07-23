import sys

from graph.workflows import run

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stdin.encoding and sys.stdin.encoding.lower() != "utf-8":
    sys.stdin.reconfigure(encoding="utf-8")

BANNER = """
ModeliCon Agentic Layer
------------------------
Type a request in plain English, for example:
  - "What is the current temperature and CO2 level in the building?"
  - "Turn down the lights in the east wing, it's too bright."
  - "Is there anything wrong with the HVAC equipment right now?"
  - "There is smoke coming from the server room!"
  - "Optimise the building for energy savings this afternoon."

Type 'exit' or 'quit' to stop.
"""


def main():
    print(BANNER)
    while True:
        try:
            user_request = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_request:
            continue
        if user_request.lower() in ("exit", "quit"):
            break

        run(user_request)
        print()


if __name__ == "__main__":
    main()
