"""Two independent guards. This is the part most RAG demos leave out.

1. screen_input  — heuristic prompt-injection detector on anything entering
                   the model, including retrieved manual text.
2. authorize     — a deterministic check on every tool call, run *outside*
                   the model. The model can be persuaded; this cannot.

Design note: the model is never the last line of defence. Even a fully
jailbroken model cannot write to the database if `authorize` says no.
"""
import re
from dataclasses import dataclass, field

# Patterns are deliberately shallow and auditable. They are a first filter,
# not a solution — evals/run_redteam.py measures how far they actually get.
INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r"ignore (all |any |the )?(previous|prior|above|earlier)", "override_instructions"),
    (r"disregard (all |any |the )?(previous|prior|above|your)", "override_instructions"),
    (r"forget (everything|all|your) (you|instructions|rules|prompt)", "override_instructions"),
    (r"you are (now|actually) (a|an|no longer)", "persona_switch"),
    (r"(developer|admin|debug|god|maintenance) mode", "privilege_claim"),
    (r"(system|initial) prompt", "prompt_extraction"),
    (r"repeat (everything|the text) above", "prompt_extraction"),
    (r"reveal your (instructions|rules|prompt|tools)", "prompt_extraction"),
    (r"\bdo not (tell|inform|log|record)\b", "audit_evasion"),
    (r"without (asking|confirmation|approval|logging)", "audit_evasion"),
    (r"\ball (work orders|records|assets|rows)\b", "bulk_scope"),
    (r"\b(delete|drop|truncate|wipe|erase) (all|every|the database|table)", "destructive"),
    (r"\b(drop table|delete from|update .* set|;--)", "sql_injection"),
    (r"\bpretend (you|to be|that)\b", "roleplay_bypass"),
    (r"\b(dan|do anything now)\b", "known_jailbreak"),
]

# Tools that change state. Everything else is read-only.
WRITE_TOOLS = {"create_work_order"}

VALID_PRIORITY = {"low", "medium", "high", "emergency"}
MAX_DESCRIPTION_CHARS = 400


@dataclass
class Verdict:
    allowed: bool
    reasons: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.allowed


def screen_input(text: str, source: str = "user") -> Verdict:
    """Flag likely injection. `source` lets us be stricter on retrieved text,
    which the user never typed and should never contain instructions."""
    hits = [label for pattern, label in INJECTION_PATTERNS
            if re.search(pattern, text, flags=re.IGNORECASE)]
    if source == "retrieved" and re.search(r"\b(you must|you should now|instruction)\b",
                                           text, flags=re.IGNORECASE):
        hits.append("instruction_in_document")
    return Verdict(allowed=not hits, reasons=sorted(set(hits)))


def authorize(tool_name: str, args: dict, *, allow_writes: bool,
              known_assets: set[str]) -> Verdict:
    """Deterministic policy check. Runs after the model picks a tool and
    before the tool executes."""
    reasons: list[str] = []

    if tool_name in WRITE_TOOLS and not allow_writes:
        reasons.append("writes_disabled_in_this_session")

    asset_id = args.get("asset_id")
    if asset_id is not None:
        if not isinstance(asset_id, str) or not re.fullmatch(r"[A-Z]{3}-\d{4}", asset_id):
            reasons.append("malformed_asset_id")
        elif asset_id not in known_assets:
            reasons.append("unknown_asset_id")

    if tool_name == "create_work_order":
        desc = args.get("description", "")
        if not isinstance(desc, str) or len(desc.strip()) < 10:
            reasons.append("description_too_short")
        elif len(desc) > MAX_DESCRIPTION_CHARS:
            reasons.append("description_too_long")
        if args.get("priority") not in VALID_PRIORITY:
            reasons.append("invalid_priority")
        # One work order per turn. Blocks "raise a WO for every asset".
        if args.get("_calls_this_turn", 0) >= 1:
            reasons.append("write_rate_limit")

    return Verdict(allowed=not reasons, reasons=reasons)
