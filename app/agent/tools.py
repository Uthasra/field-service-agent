"""The agent's four tools, plus the JSON schemas the model sees.

Tools return plain dicts. They never raise on bad input — they return an
`error` key so the model can recover instead of the request dying.
"""
from app.config import TOP_K
from app.db import connect, next_wo_id, now
from app.rag.retriever import search


def known_assets() -> set[str]:
    conn = connect()
    rows = conn.execute("SELECT asset_id FROM assets").fetchall()
    conn.close()
    return {r["asset_id"] for r in rows}


# --- implementations --------------------------------------------------------

def search_manual(query: str, top_k: int = TOP_K) -> dict:
    hits = search(query, top_k=top_k)
    return {"query": query, "results": [
        {"chunk_id": h["chunk_id"], "manual": h["manual_id"],
         "section": h["section"], "text": h["text"], "score": h["score"]}
        for h in hits
    ]}


def check_inventory(asset_id: str | None = None, part_number: str | None = None) -> dict:
    conn = connect()
    try:
        if part_number:
            rows = conn.execute(
                "SELECT * FROM parts WHERE part_number = ?", (part_number,)).fetchall()
        elif asset_id:
            rows = conn.execute(
                "SELECT p.* FROM parts p JOIN asset_parts ap"
                " ON ap.part_number = p.part_number WHERE ap.asset_id = ?",
                (asset_id,)).fetchall()
        else:
            return {"error": "give either asset_id or part_number"}
        return {"parts": [
            {"part_number": r["part_number"], "description": r["description"],
             "on_hand": r["on_hand"], "reorder_at": r["reorder_at"],
             "warehouse": r["warehouse"],
             "status": "out of stock" if r["on_hand"] == 0
                       else "low" if r["on_hand"] <= r["reorder_at"] else "in stock"}
            for r in rows]}
    finally:
        conn.close()


def get_asset_history(asset_id: str, limit: int = 10) -> dict:
    conn = connect()
    try:
        asset = conn.execute(
            "SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
        if not asset:
            return {"error": f"no asset {asset_id}"}
        rows = conn.execute(
            "SELECT event_on, event, technician FROM asset_history"
            " WHERE asset_id = ? ORDER BY event_on DESC LIMIT ?",
            (asset_id, min(limit, 25))).fetchall()
        return {
            "asset": {"asset_id": asset["asset_id"], "name": asset["name"],
                      "location": asset["location"], "manual": asset["manual_id"],
                      "criticality": asset["criticality"]},
            "history": [dict(r) for r in rows],
        }
    finally:
        conn.close()


def create_work_order(asset_id: str, description: str, priority: str = "medium") -> dict:
    conn = connect()
    try:
        if not conn.execute("SELECT 1 FROM assets WHERE asset_id = ?",
                            (asset_id,)).fetchone():
            return {"error": f"no asset {asset_id}"}
        with conn:
            wo_id = next_wo_id(conn)
            conn.execute(
                "INSERT INTO work_orders VALUES (?,?,?,?,?,?)",
                (wo_id, asset_id, description.strip(), priority, "open", now()))
        return {"wo_id": wo_id, "asset_id": asset_id, "priority": priority,
                "status": "open", "created_at": now()}
    finally:
        conn.close()


REGISTRY = {
    "search_manual": search_manual,
    "check_inventory": check_inventory,
    "get_asset_history": get_asset_history,
    "create_work_order": create_work_order,
}


# --- schemas the model sees -------------------------------------------------

SCHEMAS = [
    {"type": "function", "function": {
        "name": "search_manual",
        "description": "Search equipment service manuals for procedures, limits, "
                       "fault codes and torque values. Use this before answering "
                       "any question about how to do something.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "What to look for, in plain words"},
            "top_k": {"type": "integer", "description": "How many passages, 1-8"},
        }, "required": ["query"]}}},

    {"type": "function", "function": {
        "name": "check_inventory",
        "description": "Check spare part stock, either for one part number or for "
                       "every part fitted to an asset.",
        "parameters": {"type": "object", "properties": {
            "asset_id": {"type": "string", "description": "e.g. PMP-4412"},
            "part_number": {"type": "string", "description": "e.g. SEAL-208"},
        }}}},

    {"type": "function", "function": {
        "name": "get_asset_history",
        "description": "Past maintenance events for one asset, newest first.",
        "parameters": {"type": "object", "properties": {
            "asset_id": {"type": "string", "description": "e.g. PMP-4412"},
            "limit": {"type": "integer"},
        }, "required": ["asset_id"]}}},

    {"type": "function", "function": {
        "name": "create_work_order",
        "description": "Raise a maintenance work order. This changes records, so "
                       "only call it when the technician has clearly asked for it.",
        "parameters": {"type": "object", "properties": {
            "asset_id": {"type": "string"},
            "description": {"type": "string", "description": "What needs doing and why"},
            "priority": {"type": "string", "enum": ["low", "medium", "high", "emergency"]},
        }, "required": ["asset_id", "description"]}}},
]
