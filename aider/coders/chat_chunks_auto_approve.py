from dataclasses import dataclass
from typing import List
from .chat_chunks import ChatChunks

@dataclass
class AutoApproveChatChunks(ChatChunks):
    def add_plan(self, plan: List[dict]):
        self.cur.append({
            "role": "assistant",
            "content": json.dumps(plan),
            "type": "plan"
        })

    def get_current_plan(self):
        for msg in reversed(self.cur):
            if msg.get("type") == "plan":
                try:
                    return json.loads(msg["content"])
                except:
                    return None
        return None

    def get_current_step(self):
        plan = self.get_current_plan()
        if not plan:
            return None
        executed = sum(1 for msg in self.cur if msg.get("type") == "step_execution")
        return plan[executed] if executed < len(plan) else None

    def add_step_result(self, step: dict, result: str, success: bool):
        self.cur.append({
            "role": "assistant",
            "content": result,
            "type": "step_execution",
            "metadata": {
                "step": step,
                "success": success
            }
        })