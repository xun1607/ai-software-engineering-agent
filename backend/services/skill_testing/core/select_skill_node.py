import json
import re
from services.skill_testing.core.registry import semantic_registry
from services.skill_testing.state import AgentState
import httpx

# Dữ liệu fallback dự phòng khi không thể kết nối tới Microservice AG1 (Cổng 8001)
MOCK_SKILL_DETAILS = {
    "debug-java-null-pointer": {
        "name": "debug-java-null-pointer",
        "level": "composite",
        "category": "java/debugging",
        "tags": ["java", "debug"],
        "raw_content": """---
name: debug-java-null-pointer
description: Biên dịch code Java và kiểm tra lỗi Null Pointer
---
## Instructions
Sử dụng công cụ debug-java-null-pointer để thực thi biên dịch (javac) trên file code mục tiêu.
Lưu ý: Nếu nhận diện lỗi thiếu lớp (cannot find symbol: class User), kích hoạt cơ chế tạo stub."""
    },
    "suggest-java-fix": {
        "name": "suggest-java-fix",
        "level": "atomic",
        "category": "java/debugging",
        "tags": ["java", "fix"],
        "raw_content": """---
name: suggest-java-fix
description: Ghi bản vá sửa lỗi Java xuống đĩa
---
## Instructions
Vá code lỗi Java."""
    },
    "analyze-stacktrace": {
        "name": "analyze-stacktrace",
        "level": "atomic",
        "category": "universal",
        "tags": ["stacktrace", "analyze"],
        "raw_content": """---
name: analyze-stacktrace
description: Phân tích Stacktrace
---
## Instructions
Phân tích stacktrace lỗi."""
    },
    "read-code-context": {
        "name": "read-code-context",
        "level": "atomic",
        "category": "universal",
        "tags": ["code", "read"],
        "raw_content": """---
name: read-code-context
description: Đọc ngữ cảnh mã nguồn
---
## Instructions
Đọc code."""
    },
    "debug-python-error": {
        "name": "debug-python-error",
        "level": "composite",
        "category": "python/debugging",
        "tags": ["python", "debug"],
        "raw_content": """---
name: debug-python-error
description: Phân tích lỗi Python và sửa
---
## Instructions
Sửa lỗi Python."""
    },
    "suggest-python-fix": {
        "name": "suggest-python-fix",
        "level": "atomic",
        "category": "python/debugging",
        "tags": ["python", "fix"],
        "raw_content":[]
    }
}
            
async def select_skill_node(state: AgentState):
    print("\n--- [Skill Selection Node] Choosing the best skill for the current task ---")
    current_task = state.plan[state.current_step_idx]
    state.current_task = current_task
    print(f"Nhiệm vụ hiện tại: {current_task}")
    
    filename = state.user_context.get("filename") or ""
    stacktrace = state.user_context.get("stacktrace", "")
    baseline_mode = state.user_context.get("baseline_mode", "B3")

    # ── B0: Random Selection ────────────────────────────────────────────────
    if baseline_mode == "B0":
        import random
        random_skill_id = random.choice(list(MOCK_SKILL_DETAILS.keys()))
        state.selected_skill = random_skill_id
        state.user_context["current_skill_metadata"] = MOCK_SKILL_DETAILS[random_skill_id]
        print(f"🎲 [B0 - Random] Selected: {state.selected_skill}")
        return state

    # ── B1: Single Best Solver (SBS) ────────────────────────────────────────
    if baseline_mode == "B1":
        s = "suggest-java-fix" if filename.endswith(".java") else "suggest-python-fix"
        state.selected_skill = s
        state.user_context["current_skill_metadata"] = MOCK_SKILL_DETAILS[s]
        print(f"🎯 [B1 - SBS] Static selection: {state.selected_skill}")
        return state

    # ── B2: Zero-shot Selection ─────────────────────────────────────────────
    if baseline_mode == "B2":
        print("🤖 [B2 - Zero-shot Selection] Asking LLM to select the skill directly...")
        available_skills_text = ""
        for name, detail in MOCK_SKILL_DETAILS.items():
            desc = detail.get("description", "")
            available_skills_text += f"- Name: {name}\n  Description: {desc}\n"
            
        system_prompt = f"""
        You are a Software Engineering Agent Skill Selector.
        Your job is to select the single best skill from the available skills below to solve the user's task.
        
        AVAILABLE SKILLS:
        {available_skills_text}
        
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
        
        from services.skill_testing.core.llm_client import OpenAIClient
        from services.skill_testing.orchestrator import api_key
        llm = OpenAIClient(api_key=api_key)
        
        try:
            llm_response = await llm.call(system_prompt, user_prompt)
            resp_data = json.loads(llm_response)
            selected_name = resp_data.get("selected_skill", "").strip()
            
            matched_id = semantic_registry.get_id_by_name(selected_name) or selected_name
            skill_detail = MOCK_SKILL_DETAILS.get(matched_id)
            if skill_detail:
                state.selected_skill = skill_detail["name"]
                state.user_context["current_skill_metadata"] = skill_detail
                print(f"🏆 [B2 - Zero-shot] LLM selected skill: '{state.selected_skill}'")
                return state
        except Exception as e:
            print(f"⚠️ [B2 - Zero-shot] LLM selection failed: {e}. Falling back to default B3.")

    # ── B4: Metadata Rule-Based ─────────────────────────────────────────────
    if baseline_mode == "B4":
        s = "read-code-context"
        if "NullPointerException" in stacktrace or "NPE" in current_task or "NPE" in stacktrace:
            s = "debug-java-null-pointer"
        elif "import" in current_task.lower() or "missing symbol" in stacktrace.lower():
            s = "suggest-java-fix" if filename.endswith(".java") else "suggest-python-fix"
        elif "explain" in current_task.lower() or "what does" in current_task.lower():
            s = "analyze-stacktrace"
        elif filename.endswith(".py"):
            if "debug" in current_task.lower() or "error" in current_task.lower():
                s = "debug-python-error"
            else:
                s = "suggest-python-fix"
        state.selected_skill = s
        state.user_context["current_skill_metadata"] = MOCK_SKILL_DETAILS[s]
        print(f"📋 [B4 - Rule-Based] Selected: {state.selected_skill}")
        return state

    # ── B3 (Semantic Retrieval) & B5 (Cost-Blind) & B6 (Proposed) ──────────
    hits = semantic_registry.search(current_task, top_k=5)
    if not hits:
        print(f"⚠️ Không tìm thấy ứng viên tương đồng cho: {current_task}")
        state.selected_skill = None
        return state

    print(f"🎯 [ROUTING Quyết Định] Đang đánh giá kỹ năng ứng viên cho tác vụ: '{current_task}'")
    candidates_scores = []
    
    for skill_name, similarity_score in hits:
        skill_id = semantic_registry.get_id_by_name(skill_name)
        if not skill_id:
            continue
            
        # Ưu tiên lấy từ cache metadata của Registry (Tránh gọi HTTP GET /skills/{id} cho top-k)
        skill_detail = semantic_registry._summary_cache.get(skill_name)
        if not skill_detail:
            skill_detail = MOCK_SKILL_DETAILS.get(skill_id) or MOCK_SKILL_DETAILS.get(skill_name)
            
        if not skill_detail:
            continue
            
        sim_val = float(similarity_score)
        context_val = 0.0
        file_ext = filename.split(".")[-1].lower() if "." in filename else "java"
        
        metadata = skill_detail.get("metadata") or {}
        skill_tags = skill_detail.get("tags") or metadata.get("tags") or []
        skill_category = skill_detail.get("category") or metadata.get("category") or ""
        
        if file_ext == "java" and (any("java" in str(t).lower() for t in skill_tags) or "java" in skill_category.lower()):
            context_val += 0.3
        elif file_ext == "py" and (any(any(x in str(t).lower() for x in ("python", "py")) for t in skill_tags) or any(x in skill_category.lower() for x in ("python", "py"))):
            context_val += 0.3
            
        # CostPenalty (B5 bỏ qua Cost Penalty)
        cost_penalty = 0.0
        if baseline_mode != "B5":
            level = skill_detail.get("level") or metadata.get("level") or "atomic"
            if level == "composite":
                cost_penalty += 0.15
            else:
                cost_penalty += 0.05
            
        decision_score = sim_val + context_val - cost_penalty
        
        candidates_scores.append({
            "name": skill_name,
            "id": skill_id,
            "detail": skill_detail,
            "score": decision_score
        })
        
        print(f"   - Kỹ năng '{skill_name}' (ID: {skill_id}):")
        print(f"     + Similarity: {sim_val:.4f}")
        print(f"     + ContextScore: {context_val:.4f}")
        print(f"     + CostPenalty: {cost_penalty:.4f}")
        print(f"     ==> Decision Score = {decision_score:.4f}")

    if candidates_scores:
        best_candidate = max(candidates_scores, key=lambda x: x["score"])
        state.selected_skill = best_candidate["name"]
        
        # Chỉ lazy load chi tiết đầy đủ (gồm instructions) khi skill đã thực sự được chọn
        skill_id = best_candidate["id"]
        skill_detail = await semantic_registry.get_skill_detail(skill_id)
        if not skill_detail:
            skill_detail = best_candidate["detail"]
            
        state.user_context["current_skill_metadata"] = skill_detail
        print(f"🏆 [ROUTING Lựa Chọn] Kỹ năng tốt nhất được chọn: '{best_candidate['name']}' với Score = {best_candidate['score']:.4f}")
        
        skill_name = skill_detail.get('name', 'Unknown')
        raw_content = skill_detail.get('raw_content', '')
        instructions = raw_content
        inst_match = re.search(r"##\s+(?:🚀\s+)?Instructions?\s*\n(.*?)(?=\n##\s|\Z)", raw_content, re.DOTALL | re.IGNORECASE)
        if inst_match:
            instructions = inst_match.group(1).strip()
        
        print(f"\n" + "="*60)
        print(f"🔍 TÊN KỸ NĂNG: {skill_name}")
        print(f"🔑 ID KỸ NĂNG: {best_candidate['id']}")
        print(f"📜 CHỈ THỊ (## Instructions):")
        print("-" * 60)
        print(f"{instructions}")
        print("="*60 + "\n")
    else:
        state.selected_skill = None
        print("⚠️ Không có ứng viên kỹ năng nào thỏa mãn.")
        
    return state
