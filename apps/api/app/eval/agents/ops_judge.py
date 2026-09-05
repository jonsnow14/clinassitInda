from typing import Any

from ..schema import AgentExpect

# Lazy load agents to avoid importing them if unnecessary
_FN_MAP = None

def get_fn_map():
    global _FN_MAP
    if _FN_MAP is None:
        from app.agents.ops import list_beds
        from app.agents.ops import list_transport, dispatch_transport, track_transport
        from app.agents.pharmacy import search, dispatch, track_courier
        from app.agents.expert import list_experts, connect
        from app.agents.security import raise_sos
        
        _FN_MAP = {
            "list_beds": list_beds,
            "list_transport": list_transport,
            "dispatch_transport": dispatch_transport,
            "track_transport": track_transport,
            "search": search,
            "dispatch": dispatch,
            "track_courier": track_courier,
            "list_experts": list_experts,
            "connect": connect,
            "raise_sos": raise_sos,
        }
    return _FN_MAP

def judge_ops(call: str, args: dict[str, Any], expect: "AgentExpect") -> dict[str, Any]:
    """Call the agent function and assert expectations."""
    fn_map = get_fn_map()
    if call not in fn_map:
        raise ValueError(f"Unknown agent function {call}")
        
    result = fn_map[call](**args)
    
    # Assertions based on expect
    if expect.ordered_ids_prefix:
        res_ids = [r.get("id") for r in result]
        for i, exp_id in enumerate(expect.ordered_ids_prefix):
            if i >= len(res_ids) or res_ids[i] != exp_id:
                return {"status": "fail", "evidence": f"Expected prefix {expect.ordered_ids_prefix}, got {res_ids[:len(expect.ordered_ids_prefix)]}"}
                
    # Other assertions as needed...
    
    return {"status": "pass", "evidence": {}}
