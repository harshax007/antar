import uuid
from app.obs import store
from app.core.settings import settings
from app.services.quickml import quickml_generate_with_logprobs
from app.obs.judge import _JUDGE_SYSTEM, parse_json_response, judge_prompt, clean_scores
from app.services.quickml import quickml_chat_generate
from app.obs.sdar_processor import process_rollout_group

G_ROLLOUTS = 4

async def process_sdar_pending(limit: int = 2):
    """
    Background worker process to generate SDAR GRPO groups.
    Sweeps recent traces that don't have an SDAR group yet.
    """
    if not getattr(settings, "OBS_ENABLED", False):
        return 0
        
    with store.conn() as c:
        # Find traces that have context and a score (so they are valid base traces) 
        # but no sdar group yet.
        rows = c.execute("""
            SELECT t.trace_id, t.session_id, t.question, c.system_sent, c.prompt_sent, c.row_ids_json
            FROM traces t
            JOIN trace_context c ON t.trace_id = c.trace_id
            JOIN scores s ON t.trace_id = s.trace_id
            WHERE t.trace_id NOT IN (SELECT base_trace_id FROM sdar_groups WHERE base_trace_id IS NOT NULL)
            ORDER BY t.ts_start DESC LIMIT ?
        """, (limit,)).fetchall()
        
    done = 0
    for r in rows:
        trace_id = r["trace_id"]
        system_sent = r["system_sent"] or ""
        prompt_sent = r["prompt_sent"] or ""
        
        if not prompt_sent:
            continue
            
        group_id = str(uuid.uuid4())
        
        # 1. Generate G rollouts
        rollouts = []
        for i in range(G_ROLLOUTS):
            try:
                # Generate with high temperature for diversity
                text, logprobs_list = await quickml_generate_with_logprobs(
                    system=system_sent,
                    user=prompt_sent,
                    temperature=0.8,
                    max_tokens=500
                )
                
                # 2. Score the rollout using the Judge
                judge_user = judge_prompt(r["question"], r["row_ids_json"], text)
                raw_score = await quickml_chat_generate(
                    system=_JUDGE_SYSTEM, 
                    user=judge_user,
                    json_mode=True, 
                    max_tokens=200, 
                    temperature=0.0
                )
                score_dict = clean_scores(parse_json_response(raw_score))
                # Combine metrics into a single reward [0, 1]
                reward = (score_dict.get("groundedness", 0) + score_dict.get("answered", 0) + score_dict.get("safety", 0) - score_dict.get("hallucination", 0)) / 3.0
                
                # We save log_P_student. 
                # (log_P_teacher will be evaluated offline by vLLM since Catalyst API lacks echo=True)
                tokens_data = []
                for lp in logprobs_list:
                    tokens_data.append({
                        "token": lp.get("token", ""),
                        "log_p_student": lp.get("logprob", 0.0),
                        "log_p_teacher": 0.0 # Placeholder for offline eval
                    })
                    
                rollouts.append({
                    "reward": reward,
                    "tokens": tokens_data
                })
            except Exception as e:
                # never the exception text on stdout: it can carry the upstream body and URL
                import logging
                from app.core.security import scrub_text
                logging.getLogger("antar.sdar").warning("sdar_rollout_failed %s", scrub_text(e))
                
        # 3. Process the group if we got enough rollouts
        if len(rollouts) == G_ROLLOUTS:
            with store.conn() as c:
                import time
                c.execute("""
                    INSERT INTO sdar_groups (group_id, session_id, question, ts, base_trace_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (group_id, r["session_id"], r["question"], int(time.time()*1000), trace_id))
            
            process_rollout_group(group_id, rollouts)
            done += 1
            
    return done
