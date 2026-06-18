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
        "raw_content": """---
name: suggest-python-fix
description: Vá lỗi Python
---
## Instructions
Vá code lỗi Python."""
    }
}

async def select_skill_node(state: AgentState):
    print("\n--- [Skill Selection Node] Choosing the best skill for the current task ---")
    current_task = state.plan[state.current_step_idx]
    state.current_task = current_task
    print(f"Nhiệm vụ hiện tại: {current_task}")
    
    # 1. Tìm các ứng viên bằng Semantic Search (top 5)
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
            
        # Tải chi tiết kỹ năng (từ cổng 8001 hoặc lấy từ mock)
        AG1_DETAIL_URL = f"http://127.0.0.1:8001/skills/{skill_id}"
        skill_detail = None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(AG1_DETAIL_URL, timeout=2.0)
                if response.status_code == 200:
                    skill_detail = response.json()
        except Exception:
            pass
            
        if not skill_detail:
            skill_detail = MOCK_SKILL_DETAILS.get(skill_id) or MOCK_SKILL_DETAILS.get(skill_name)
            
        if not skill_detail:
            continue
            
        # Công thức: Score = Similarity + ContextScore - CostPenalty
        sim_val = float(similarity_score)
        
        context_val = 0.0
        filename = state.user_context.get("filename") or ""
        # if not filename:
        #     if "class " in state.user_context.get("code", ""):
        #         filename = "LoginService.java"
        #     else:
        #         filename = "data_sync.py"
                
        file_ext = filename.split(".")[-1].lower() if "." in filename else "java"
        
        metadata = skill_detail.get("metadata") or {}
        skill_tags = skill_detail.get("tags") or metadata.get("tags") or []
        skill_category = skill_detail.get("category") or metadata.get("category") or ""
        
        # ngôn ngữ lập trình tương thích
        if file_ext == "java" and (any("java" in str(t).lower() for t in skill_tags) or "java" in skill_category.lower()):
            context_val += 0.3
        elif file_ext == "py" and (any(any(x in str(t).lower() for x in ("python", "py")) for t in skill_tags) or any(x in skill_category.lower() for x in ("python", "py"))):
            context_val += 0.3
            
        # loại lỗi tương thích
        stacktrace = state.user_context.get("stacktrace", "")
        # if "NullPointerException" in stacktrace and "null-pointer" in skill_name.lower():
        #     context_val += 0.2
        # elif "ModuleNotFoundError" in stacktrace and "python" in skill_name.lower():
        #     context_val += 0.2
            
        # CostPenalty
        cost_penalty = 0.0
        level = skill_detail.get("level") or metadata.get("level") or "atomic"
        if level == "composite":
            cost_penalty += 0.15 # Composite tools are heavy
        else:
            cost_penalty += 0.05 # Atomic tools are cheap
            
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
        state.user_context["current_skill_metadata"] = best_candidate["detail"]
        print(f"🏆 [ROUTING Lựa Chọn] Kỹ năng tốt nhất được chọn: '{best_candidate['name']}' với Score = {best_candidate['score']:.4f}")
        
        skill_name = best_candidate["detail"].get('name', 'Unknown')
        raw_content = best_candidate["detail"].get('raw_content', '')
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
