from __future__ import annotations


class SharedRigAdapter:
    def initiate_call(self, phone: str, script_id: str) -> dict:
        return {"ok": True, "provider": "shared_rig", "phone": phone, "script_id": script_id}
