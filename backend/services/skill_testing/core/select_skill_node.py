import json
import re
from typing import Dict, Any, List
from services.skill_testing.state import AgentState
from services.skill_testing.core.registry import semantic_registry


def query_skill_success_rate(skill_name: str) -> float:
    """Queries execution logs to compute Bayesian Beta-Binomial success probability."""
    from shared.db import get_session
    from services.skill_testing.models import AgentExecutionLog
    try:
        with get_session() as session:
            logs = session.query(AgentExecutionLog).filter_by(skill_name=skill_name).all()
            if logs:
                successes = sum(1 for log in logs if log.success)
                failures = len(logs) - successes
                return (1.0 + successes) / (2.0 + successes + failures)
    except Exception as e:
        print(f"⚠️ [DB QUERY ERROR] Lỗi khi truy vấn tỷ lệ thành công của skill {skill_name}: {e}")
    
    return 0.5 

def query_skill_performance_profile(skill_name: str) -> dict:
    """Queries execution logs to retrieve average tokens and latency metrics."""
    from shared.db import get_session
    from services.skill_testing.models import AgentExecutionLog
    try:
        with get_session() as session:
            logs = session.query(AgentExecutionLog).filter_by(skill_name=skill_name).all()
            if logs:
                successes = sum(1 for log in logs if log.success)
                failures = len(logs) - successes
                prob = (1.0 + successes) / (2.0 + successes + failures)
                avg_tokens = sum(log.total_tokens for log in logs) / len(logs)
                avg_latency = sum(log.latency_ms for log in logs) / len(logs)
                return {
                    "success_rate": prob,
                    "avg_tokens": avg_tokens,
                    "avg_latency_ms": avg_latency
                }
    except Exception as e:
        print(f"⚠️ [DB QUERY ERROR] Lỗi khi truy vấn hiệu năng của skill {skill_name}: {e}")
    
    # Default Fallback (Cold Start values)
    return {
        "success_rate": 0.5,
        "avg_tokens": 1000.0,
        "avg_latency_ms": 2000.0
    }

SIMILARITY_THRESHOLD = 0.50

# NODE chính: lựa chọn skill theo các baseline khác nhau
async def select_skill_node(state: AgentState, model_client=None) -> AgentState:
    """
    Node lựa chọn kỹ năng (Skill Selector):
    Định tuyến và chọn kỹ năng tối ưu nhất dựa trên 4 cấu hình baselines:
    - B1: Static Agent (Single Best Solver)
    - B2: Modern RAG Agent (Vector search + LLM selection)
    - B3: Cost-Blind Agent (Success rate optimized)
    - B4: Proposed Framework (CASS Multi-Objective Optimizer)
    """
    print("\n--- [Skill Selection Node] Choosing the best skill for the current task ---")
    current_task = state.plan[state.current_step_idx]
    state.current_task = current_task
    print(f"Nhiệm vụ hiện tại: {current_task}")
    
    filename = state.user_context.get("filename") or ""
    stacktrace = state.user_context.get("stacktrace", "")
    baseline_mode = state.user_context.get("baseline_mode", "B4")

    # ── B1: Static Agent (Single Best Solver - SBS) ─────────────────────────
    if baseline_mode == "B1":
        s = "suggest-java-fix" if filename.endswith(".java") else "suggest-python-fix"
        state.selected_skill = s
        state.user_context["current_skill_metadata"] = await semantic_registry.get_skill_detail(s)
        print(f"🎯 [B1 - Static Agent] Static selection: {state.selected_skill}")
        return state

    # ── B2: Modern RAG Agent (Vector Search + LLM Selection) ────────────────
    if baseline_mode == "B2":
        hits = semantic_registry.search(current_task, top_k=3)
        if not hits:
            s = "suggest-java-fix" if filename.endswith(".java") else "suggest-python-fix"
            state.selected_skill = s
            state.user_context["current_skill_metadata"] = await semantic_registry.get_skill_detail(s)
            print(f"🎯 [B2 - RAG] No vector hits. Falling back to default: {state.selected_skill}")
            return state
        
        candidates_text = ""
        compatible_hits = []
        for skill_name, similarity in hits:
            if similarity < SIMILARITY_THRESHOLD:
                continue
            skill_id = semantic_registry.get_id_by_name(skill_name) or skill_name
            detail = await semantic_registry.get_skill_detail(skill_id)
            desc = detail.get("description", "") if detail else ""
            candidates_text += f"- Name: {skill_name}\n  Description: {desc}\n"
            compatible_hits.append((skill_name, similarity))
        
        hits = compatible_hits
        if not hits:
            s = "suggest-java-fix" if filename.endswith(".java") else "suggest-python-fix"
            state.selected_skill = s
            state.user_context["current_skill_metadata"] = await semantic_registry.get_skill_detail(s)
            print(f"🎯 [B2 - RAG] No compatible vector hits after threshold. Falling back to default: {state.selected_skill}")
            return state
            
        system_prompt = f"""
        You are a Software Engineering Agent Tool Selector.
        Your job is to select the single best skill from the filtered candidates below to solve the user's task.
        
        CANDIDATE SKILLS:
        {candidates_text}
        
        INSTRUCTIONS:
        1. Select the most relevant skill based on the task description and code file type (Java vs Python).
        2. Return a flat JSON object with a single key "selected_skill" containing the exact name of the selected skill.
        3. Do NOT add extra conversational text. Output ONLY valid JSON.
        """
        user_prompt = f"""
        TASK: {current_task}
        FILE NAME: {filename}
        ERROR STACKTRACE: {stacktrace}
        """
        
        if model_client is not None:
            llm = model_client
        else:
            from services.skill_testing.core.llm_client import OpenAIClient
            from services.skill_testing.orchestrator import api_key
            llm = OpenAIClient(api_key=api_key)
        
        try:
            llm_response = await llm.call(system_prompt, user_prompt)
            cleaned_response = llm_response.strip()
            if "```" in cleaned_response:
                code_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned_response, re.DOTALL | re.IGNORECASE)
                if code_match:
                    cleaned_response = code_match.group(1).strip()
            
            resp_data = json.loads(cleaned_response)
            selected_name = resp_data.get("selected_skill", "").strip()
            
            matched_id = semantic_registry.get_id_by_name(selected_name) or selected_name
            skill_detail = await semantic_registry.get_skill_detail(matched_id)
            if skill_detail:
                state.selected_skill = skill_detail.get("name") or selected_name
                state.user_context["current_skill_metadata"] = skill_detail
                print(f"🏆 [B2 - RAG Agent] LLM selected skill: '{state.selected_skill}'")
                return state
        except Exception as e:
            print(f"⚠️ [B2 - RAG Agent] LLM selection failed: {e}. Falling back to top-1 vector candidate.")
            top_1_name = hits[0][0]
            matched_id = semantic_registry.get_id_by_name(top_1_name) or top_1_name
            state.selected_skill = top_1_name
            state.user_context["current_skill_metadata"] = await semantic_registry.get_skill_detail(matched_id)
            return state

    # ── B3: Cost-Blind Agent (Success-optimized, ignoring cost/latency) ─────
    if baseline_mode == "B3":
        hits = semantic_registry.search(current_task, top_k=3)
        if not hits:
            print(f"⚠️ Không tìm thấy ứng viên tương đồng cho: {current_task}")
            state.selected_skill = None
            return state
        candidates = []
        for skill_name, similarity in hits:
            if similarity < SIMILARITY_THRESHOLD:
                continue
            skill_id = semantic_registry.get_id_by_name(skill_name) or skill_name
            detail = await semantic_registry.get_skill_detail(skill_id)
            tags = detail.get("metadata", {}).get("tags", []) if detail else []
            category = detail.get("metadata", {}).get("category", "") if detail else ""
                
            success_rate = query_skill_success_rate(skill_name)
            candidates.append({
                "name": skill_name,
                "success_rate": success_rate,
                "similarity": similarity
            })
            print(f"   - Candidate '{skill_name}': Success Rate = {success_rate:.4f} (Similarity = {similarity:.4f})")
            
        if not candidates:
            print(f"⚠️ Không tìm thấy ứng viên tương thích ngôn ngữ cho: {current_task}")
            state.selected_skill = None
            return state
            
        best_candidate = max(candidates, key=lambda x: x["success_rate"])
        matched_id = semantic_registry.get_id_by_name(best_candidate["name"]) or best_candidate["name"]
        skill_detail = await semantic_registry.get_skill_detail(matched_id)
        
        state.selected_skill = best_candidate["name"]
        state.user_context["current_skill_metadata"] = skill_detail
        print(f"🏆 [B3 - Cost-Blind] Selected: {state.selected_skill} (Success Rate = {best_candidate['success_rate']:.4f})")
        return state

    # ── B4: Proposed Framework (CASS Multi-Objective Optimizer) ─────────────
    if baseline_mode == "B4":
        hits = semantic_registry.search(current_task, top_k=3)
        if not hits:
            print(f"⚠️ Không tìm thấy ứng viên tương đồng cho: {current_task}")
            state.selected_skill = None
            return state
        
        candidates = []
        for skill_name, similarity in hits:
            if similarity < SIMILARITY_THRESHOLD:
                continue
            skill_id = semantic_registry.get_id_by_name(skill_name) or skill_name
            detail = await semantic_registry.get_skill_detail(skill_id)
            tags = detail.get("metadata", {}).get("tags", []) if detail else []
            category = detail.get("metadata", {}).get("category", "") if detail else ""
            
                
            profile = query_skill_performance_profile(skill_name)
            candidates.append({
                "name": skill_name,
                "success_rate": profile["success_rate"],
                "avg_tokens": profile["avg_tokens"],
                "avg_latency_ms": profile["avg_latency_ms"],
                "similarity": similarity
            })
            
        if not candidates:
            print(f"⚠️ Không tìm thấy ứng viên tương thích ngôn ngữ cho: {current_task}")
            state.selected_skill = None
            return state
            
        token_values = [c["avg_tokens"] for c in candidates]
        latency_values = [c["avg_latency_ms"] for c in candidates]
        
        min_tokens, max_tokens = min(token_values), max(token_values)
        min_latency, max_latency = min(latency_values), max(latency_values)
        
        # Objectives weights: success_rate = 0.4, similarity = 0.3, tokens = 0.15, latency = 0.15
        best_candidate = None
        max_score = -9999.0
        
        print(f"🎯 [B4 - Proposed Framework] Đang đánh giá tối ưu hóa đa mục tiêu:")
        for c in candidates:
            # Normalize to [0, 1] range
            norm_tokens = (c["avg_tokens"] - min_tokens) / (max_tokens - min_tokens) if max_tokens > min_tokens else 0.5
            norm_latency = (c["avg_latency_ms"] - min_latency) / (max_latency - min_latency) if max_latency > min_latency else 0.5
            
            # Score formula
            score = (0.4 * c["success_rate"]) + (0.3 * c["similarity"]) - (0.15 * norm_tokens) - (0.15 * norm_latency)
            
            print(f"   - Skill: '{c['name']}':")
            print(f"     + Success Probability: {c['success_rate']:.4f}")
            print(f"     + Semantic Similarity: {c['similarity']:.4f}")
            print(f"     + Token Penalty: -{0.15 * norm_tokens:.4f} (avg={c['avg_tokens']:.1f})")
            print(f"     + Latency Penalty: -{0.15 * norm_latency:.4f} (avg={c['avg_latency_ms']:.1f}ms)")
            print(f"     ==> Score: {score:.4f}")
            
            if score > max_score:
                max_score = score
                best_candidate = c
                
        matched_id = semantic_registry.get_id_by_name(best_candidate["name"]) or best_candidate["name"]
        skill_detail = await semantic_registry.get_skill_detail(matched_id)
        
        state.selected_skill = best_candidate["name"]
        state.user_context["current_skill_metadata"] = skill_detail
        print(f"🏆 [B4 - Proposed Framework] Selected: {state.selected_skill} with Score = {max_score:.4f}")
        return state

    state.selected_skill = None
    return state
