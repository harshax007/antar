from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.obs import store
from app.core.settings import settings

router = APIRouter()

@router.get("/export/sdar", response_class=JSONResponse)
def export_sdar_training_data():
    """
    Exports the Self-Distilled Agentic Reinforcement Learning (SDAR) dataset.
    This generates a JSON payload ready for offline vLLM / TRL training.
    Format:
    [
      {
        "prompt": "...",
        "group_id": "...",
        "rollouts": [
           {
             "reward": 0.8,
             "tokens": [{"text": "Hello", "adv": 0.5, "log_p_s": -0.1, "gate": 0.9}, ...]
           },
           ...
        ]
      }
    ]
    """
    if not getattr(settings, "OBS_ENABLED", False):
        return {"error": "Observability disabled"}
        
    with store.conn() as c:
        # Get groups
        groups = c.execute("SELECT group_id, question FROM sdar_groups").fetchall()
        
        result = []
        for g in groups:
            g_id = g["group_id"]
            
            # Get tokens for this group
            tokens = c.execute("""
                SELECT rollout_id, token_idx, token, advantage, log_p_student, log_p_teacher, gate
                FROM sdar_tokens
                WHERE group_id = ?
                ORDER BY rollout_id, token_idx
            """, (g_id,)).fetchall()
            
            # Organize tokens by rollout
            rollouts_dict = {}
            for t in tokens:
                rid = t["rollout_id"]
                if rid not in rollouts_dict:
                    rollouts_dict[rid] = []
                rollouts_dict[rid].append({
                    "token": t["token"],
                    "advantage": t["advantage"],
                    "log_p_student": t["log_p_student"],
                    "log_p_teacher": t["log_p_teacher"],
                    "gate": t["gate"]
                })
                
            rollouts_list = [{"rollout_id": k, "tokens": v} for k, v in rollouts_dict.items()]
            
            result.append({
                "group_id": g_id,
                "prompt": g["question"],
                "rollouts": rollouts_list
            })
            
    return result
