"""FAILURE 3: everything lives in the conversation.

Context fills, the session restarts, and the agent loses the decision it made
twenty turns ago. It then makes the opposite one.

Run:  python3 failures/03_no_persistence.py
"""
CONVERSATION = ["decided: postgres, because we need concurrent writers"]

def restart():
    CONVERSATION.clear()          # context reset. the decision was only ever here.

if __name__ == "__main__":
    print(f"before reset: {CONVERSATION}")
    restart()
    print(f"after reset:  {CONVERSATION}")
    print("\nnew session picks sqlite, because nothing on disk says otherwise.")
    print("The decision was real work and it lived somewhere a reset could reach.")
