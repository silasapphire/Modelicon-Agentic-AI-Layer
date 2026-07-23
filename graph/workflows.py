import uuid

from langgraph.types import Command
from graph.graph import build_graph

graph = build_graph()


def run(user_request: str, auto_approve=None):
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    state = graph.invoke({"user_request": user_request, "log": []}, config)

    while "__interrupt__" in state:
        payload = state["__interrupt__"][0].value
        print("\n[HUMAN APPROVAL NEEDED]")
        print(" ", payload["summary"])
        print(" actions:", payload["actions"])

        if auto_approve is not None:
            decision = "y" if auto_approve else "n"
        else:
            decision = input(" approve? [y/N] ").strip() or "n"

        state = graph.invoke(Command(resume=decision), config)

    print("\n--- execution log ---")
    for line in state.get("log", []):
        print(" ", line)
    print("\nfinal:", state.get("final_response"))
    print("executed:", state.get("execution_result"))
    return state


if __name__ == "__main__":
    run("The east zone feels warm this afternoon, optimise it for comfort and energy.")
