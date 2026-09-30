import math
from typing import List, Dict, Any

def calculate_group_advantage(rewards: List[float]) -> List[float]:
    """
    Step 2 of SDAR: Calculate GRPO sequence-level advantage A^(i).
    A^(i) = (R^(i) - \mu_G) / \sigma_G
    """
    G = len(rewards)
    if G <= 1:
        return [0.0] * G

    mu_g = sum(rewards) / G
    variance = sum((r - mu_g) ** 2 for r in rewards) / G
    sigma_g = math.sqrt(variance)
    
    if sigma_g < 1e-6:
        return [0.0] * G

    return [(r - mu_g) / sigma_g for r in rewards]


def calculate_sdar_gate(log_p_teacher: float, log_p_student: float, beta: float = 5.0) -> float:
    """
    Step 4 of SDAR: Token-level Gated Distillation.
    g_t = sigmoid(\beta * \Delta_t)
    where \Delta_t = \log \pi_T(y_t | s^+_t) - \log \pi_S(y_t | s_t)
    """
    delta_t = log_p_teacher - log_p_student
    
    # Sigmoid calculation: 1 / (1 + exp(-x))
    try:
        # Cap the exponent to avoid overflow
        x = max(-50.0, min(50.0, beta * delta_t))
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if delta_t < 0 else 1.0


def process_rollout_group(group_id: str, rollouts: List[Dict[str, Any]]):
    """
    Process a group of rollouts (G).
    rollouts should be a list of dicts, each containing:
    - 'reward': float
    - 'tokens': List[Dict] with 'token', 'log_p_student', 'log_p_teacher'
    """
    from app.obs.store import conn
    import time
    
    if not rollouts:
        return
        
    rewards = [r.get("reward", 0.0) for r in rollouts]
    advantages = calculate_group_advantage(rewards)
    
    ts = int(time.time() * 1000)
    
    # Persist the tokens to the database
    with conn() as c:
        for i, rollout in enumerate(rollouts):
            adv = advantages[i]
            for idx, tk in enumerate(rollout.get("tokens", [])):
                token = tk.get("token", "")
                log_p_s = tk.get("log_p_student", 0.0)
                log_p_t = tk.get("log_p_teacher", 0.0)
                
                gate = calculate_sdar_gate(log_p_t, log_p_s)
                
                c.execute("""
                    INSERT INTO sdar_tokens (group_id, rollout_id, token_idx, token, advantage, log_p_student, log_p_teacher, gate, ts)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (group_id, i+1, idx, token, adv, log_p_s, log_p_t, gate, ts))
