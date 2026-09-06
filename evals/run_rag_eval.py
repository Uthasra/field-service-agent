"""Retrieval evaluation. No LLM needed, so this runs in CI on every push.

If retrieval is wrong, the agent is wrong, and no amount of prompt tuning
fixes it. Measure this layer on its own before blaming the model.

Usage: python -m evals.run_rag_eval
"""
import json
from pathlib import Path

from app.config import TOP_K
from app.rag.retriever import search

OUT = Path(__file__).parent / "results_rag.json"

# (question, substring that must appear in the chunk_id of a correct hit)
GOLDEN = [
    ("What is the vibration alert band for the pump?", "centrifugal-pump::3.1"),
    ("Above what vibration level must the pump be shut down?", "centrifugal-pump::3.1"),
    ("What causes high vibration on a pump?", "centrifugal-pump::3.2"),
    ("What torque for the gland nuts on the mechanical seal?", "centrifugal-pump::4.2"),
    ("How do I replace the mechanical seal?", "centrifugal-pump::4.2"),
    ("What temperature to heat the bearing before fitting?", "centrifugal-pump::4.5"),
    ("How much grease goes in the bearing housing?", "centrifugal-pump::4.5"),
    ("What does cavitation sound like and what causes it?", "centrifugal-pump::6.1"),
    ("What does fault code E02 mean?", "hvac-chiller::2.3"),
    ("What is fault code E11 on the chiller?", "hvac-chiller::2.3"),
    ("How often are the chiller filters changed?", "hvac-chiller::3.4"),
    ("What water pressure for cleaning the condenser coil?", "hvac-chiller::5.2"),
    ("Why does the conveyor belt run to one side?", "belt-conveyor::2.1"),
    ("When should the conveyor belt be replaced?", "belt-conveyor::2.4"),
    ("When do I replace an idler roller?", "belt-conveyor::4.1"),
    ("Do I need to lock out before opening a conveyor guard?", "belt-conveyor::7.2"),
]


def _probe_mode() -> str:
    hits = search(GOLDEN[0][0], top_k=1)
    return hits[0]["mode"] if hits else "unknown"


def main() -> None:
    rows, hits_at_1, hits_at_k, rr_total = [], 0, 0, 0.0

    for question, expect in GOLDEN:
        results = search(question, top_k=TOP_K)
        ids = [r["chunk_id"] for r in results]
        rank = next((i + 1 for i, cid in enumerate(ids) if cid.startswith(expect)), None)
        hits_at_1 += rank == 1
        hits_at_k += rank is not None
        rr_total += 1 / rank if rank else 0.0
        rows.append({"question": question, "expected": expect,
                     "rank": rank, "retrieved": ids})

    n = len(GOLDEN)
    summary = {
        "questions": n,
        "recall@1": round(hits_at_1 / n, 3),
        f"recall@{TOP_K}": round(hits_at_k / n, 3),
        "mrr": round(rr_total / n, 3),
        "mode": _probe_mode(),
    }
    OUT.write_text(json.dumps({"summary": summary, "cases": rows}, indent=2))

    print("-" * 46)
    for k, v in summary.items():
        print(f"{k:<14} {v}")
    misses = [r for r in rows if r["rank"] is None]
    if misses:
        print(f"\n{len(misses)} miss(es):")
        for m in misses:
            print(f"  {m['question']}\n    wanted {m['expected']}, got {m['retrieved'][:2]}")
    print(f"\nwritten to {OUT.name}")


if __name__ == "__main__":
    main()
