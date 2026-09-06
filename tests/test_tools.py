"""Tool tests against a seeded temporary database."""
import pytest

from app.db import init_db
from app.agent.tools import (check_inventory, create_work_order, get_asset_history,
                             known_assets, search_manual)


@pytest.fixture(scope="module", autouse=True)
def db():
    init_db(reset=True)


def test_known_assets_seeded():
    assert {"PMP-4412", "CHL-2201", "CNV-1180"} <= known_assets()


def test_inventory_by_asset_flags_out_of_stock():
    parts = check_inventory(asset_id="PMP-4412")["parts"]
    by_no = {p["part_number"]: p for p in parts}
    assert by_no["BRG-6206"]["status"] == "out of stock"
    assert by_no["SEAL-208"]["status"] == "in stock"


def test_inventory_needs_an_argument():
    assert "error" in check_inventory()


def test_history_returns_asset_and_events():
    out = get_asset_history("PMP-4412")
    assert out["asset"]["name"].startswith("Feedwater")
    assert len(out["history"]) >= 3


def test_history_unknown_asset():
    assert "error" in get_asset_history("PMP-0000")


def test_search_manual_finds_vibration_section():
    hits = search_manual("vibration shutdown limit", top_k=3)["results"]
    assert hits and any("centrifugal-pump" in h["chunk_id"] for h in hits)


def test_create_and_reject_work_order():
    ok = create_work_order("PMP-4412", "Inspect coupling alignment", "high")
    assert ok["wo_id"].startswith("WO-") and ok["status"] == "open"
    assert "error" in create_work_order("PMP-9999", "nope", "low")
