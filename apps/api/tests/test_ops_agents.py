import pytest
from app.eval.agents.ops_judge import judge_ops
from app.eval.schema import AgentExpect

@pytest.mark.unit
def test_list_beds_icu():
    args = {"need": "icu"}
    expect = AgentExpect(ordered_ids_prefix=["gmch-purnea", "galaxy-heart-purnia", "sadar-purnia"])
    res = judge_ops("list_beds", args, expect)
    assert res["status"] == "pass"

@pytest.mark.unit
def test_list_beds_o2():
    args = {"need": "oxygen"}
    expect = AgentExpect(ordered_ids_prefix=["gmch-purnea", "sadar-purnia", "galaxy-heart-purnia"])
    res = judge_ops("list_beds", args, expect)
    assert res["status"] == "pass"
    
@pytest.mark.unit
def test_pharmacy_dapt():
    args = {"meds": ["DAPT"]}
    # The first id should be pmbjk-khajanchi
    expect = AgentExpect(ordered_ids_prefix=["pmbjk-khajanchi"])
    res = judge_ops("search", args, expect)
    assert res["status"] == "pass"
