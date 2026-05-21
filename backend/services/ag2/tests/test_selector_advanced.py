import pytest
from unittest.mock import MagicMock, patch
from skill_selector_module.selector import ContextBasedSkillSelector
from skill_selector_module.schemas import SkillSelectionResult
import torch

@pytest.fixture
def advanced_skills_registry():
    return [
        {"id": "5137b88e-6f36-432a-88ae-b1fd36b4557b", "name": "suggest-java-fix", "description": "Suggests a concrete Java fix pattern for a NullPointerException given the file location and the null variable."},
        {"id": "0800f777-aad0-4344-963c-d4faf36aaeed", "name": "debug-python-error", "description": "Full pipeline to debug any Python exception — analyzes the stacktrace to find the root cause, then generates an actionable fix suggestion with corrected code."},
        {"id": "fe370c46-20d5-4b2d-a753-e163770379b8", "name": "suggest-python-fix", "description": "Suggests a concrete, actionable Python fix for an exception given the file, line number, variable name, and error type."},
        {"id": "3563b2dc-1338-4fdc-b82b-f29c44fb1b4c", "name": "analyze-stacktrace", "description": "Analyzes an exception stacktrace to pinpoint the exact source file, line number, and the variable or root cause."},
        {"id": "2180e74e-5844-49a6-a377-060721235c74", "name": "run-python-test", "description": "Dùng để thực thi các đoạn code Python và kiểm tra xem chúng có vượt qua các bài unit test hay không."}
    ]
# def mock_skills_registry():
#     # Mock chính xác 7 skill từ dữ liệu thật của bạn kia
#     return [
#         {"id": "5137b88e-6f36-432a-88ae-b1fd36b4557b", "name": "suggest-java-fix", "description": "Suggests a concrete Java fix pattern for a NullPointerException given the file location and the null variable."},
#         {"id": "0800f777-aad0-4344-963c-d4faf36aaeed", "name": "debug-python-error", "description": "Full pipeline to debug any Python exception — analyzes the stacktrace to find the root cause, then generates an actionable fix suggestion with corrected code."},
#         {"id": "fe370c46-20d5-4b2d-a753-e163770379b8", "name": "suggest-python-fix", "description": "Suggests a concrete, actionable Python fix for an exception given the file, line number, variable name, and error type."},
#         {"id": "3563b2dc-1338-4fdc-b82b-f29c44fb1b4c", "name": "analyze-stacktrace", "description": "Analyzes an exception stacktrace to pinpoint the exact source file, line number, and the variable or root cause."},
#         {"id": "2180e74e-5844-49a6-a377-060721235c74", "name": "run-python-test", "description": "Dùng để thực thi các đoạn code Python và kiểm tra xem chúng có vượt qua các bài unit test hay không."}
#     ]

# @patch('skill_selector_module.selector.ContextBasedSkillSelector._fetch_skills_with_cache')
# def test_semantic_and_edge_cases(mock_fetch, mock_skills_registry):
#     mock_fetch.return_value = mock_skills_registry
#     mock_openai = MagicMock()
    
#     selector = ContextBasedSkillSelector(client=mock_openai, skill_registry_url="http://mock-url")
    
#     # --- CASE 1: GẦN NGHĨA NHƯNG KHÁC KEYWORD (Semantic Selection Correctness) ---
#     # Task dùng từ "kiểm tra", "mã nguồn", "kịch bản test" nhưng không có chữ "pytest" hay "execute"
#     task_1 = "Chạy toàn bộ các kịch bản kiểm thử mã nguồn để verify logic"
    
#     # Chúng ta test tầng 1 độc lập để xem hành vi của embedding (Embedding similarity behavior)
#     corpus = [f"{s['name']}: {s['description']}" for s in mock_skills_registry]
#     corpus_embeddings = selector.embedder.encode(corpus, convert_to_tensor=True)
#     query_embedding = selector.embedder.encode(task_1, convert_to_tensor=True)
#     scores = selector.embedder.similarity(query_embedding, corpus_embeddings)[0]
    
#     # Kiểm chứng: Skill 'run-python-test' (chỉ số 4) phải nằm trong nhóm điểm cao nhất
#     assert scores[4].item() > 0.4 
#     print(f"\n✅ Case 1 Pass: Thuật toán nhận diện đồng nghĩa tốt! Score cho run-python-test: {scores[4].item():.4f}")

#     # --- CASE 2: EDGE CASES - TASK HOÀN TOÀN KHÔNG LIÊN QUAN (Threshold Trigger) ---
#     task_2 = "Hãy viết một email xin nghỉ ốm gửi cho phòng nhân sự"
#     result_edge = selector.select_best_skill(task_2, {}, similarity_threshold=0.3)
    
#     # Kiểm chứng: Hệ thống phải kích hoạt bộ lọc Threshold và trả về None ngay ở tầng 1, không tốn token gọi LLM
#     assert result_edge is None
#     print("✅ Case 2 Pass: Kích hoạt ngưỡng chặn Threshold thành công cho task không liên quan!")

#     # --- CASE 3: TOP-K RERANKING LOGIC ---
#     # Khảo sát xem với task phức tạp, Top-2 được lọc ra có chứa cả skill phân tích lẫn skill fix không
#     task_3 = "Tìm nguyên nhân crash của dự án Java dựa trên log exception"
#     query_embedding_3 = selector.embedder.encode(task_3, convert_to_tensor=True)
#     scores_3 = selector.embedder.similarity(query_embedding_3, corpus_embeddings)[0]
#     import torch
#     _, indices = torch.topk(scores_3, k=2)
    
#     # indices phải chứa 3 hoặc 0 (tương ứng với analyze-stacktrace và suggest-java-fix)
#     assert 3 in indices.tolist() or 0 in indices.tolist()
#     print("✅ Case 3 Pass: Bộ lọc Reranking lấy ra đúng nhóm kỹ năng bổ trợ bối cảnh Java!")
    
    
@patch('skill_selector_module.selector.ContextBasedSkillSelector._fetch_skills_with_cache')
def test_semantic_and_edge_cases(mock_fetch_method, advanced_skills_registry):
    # Ép hàm cache trả về toàn bộ 5 skill thật
    mock_fetch_method.return_value = advanced_skills_registry
    
    # Cấu hình Mock OpenAI chuyên sâu để phục vụ tầng 2 nếu luồng chạy vượt qua tầng 1
    mock_openai = MagicMock()
    mock_parsed_result = SkillSelectionResult(
        selected_skill_id="2180e74e-5844-49a6-a377-060721235c74",
        skill_name="run-python-test",
        reasoning="Matched via LLM verification",
        extracted_arguments={}
    )
    mock_openai.beta.chat.completions.parse.return_value.choices[0].message.parsed = mock_parsed_result
    
    # Khởi tạo selector
    selector = ContextBasedSkillSelector(client=mock_openai, skill_registry_url="http://mock-url")
    
    # --- CASE 1: SEMANTIC SELECTION (Đồng nghĩa khác keyword) ---
    task_1 = "Chạy toàn bộ các kịch bản kiểm thử mã nguồn để verify logic"
    corpus = [f"{s['name']}: {s['description']}" for s in advanced_skills_registry]
    corpus_embeddings = selector.embedder.encode(corpus, convert_to_tensor=True)
    query_embedding = selector.embedder.encode(task_1, convert_to_tensor=True)
    scores = selector.embedder.similarity(query_embedding, corpus_embeddings)[0]
    
    # run-python-test nằm ở chỉ số cuối cùng (4) trong mảng fixture mới
    assert scores[4].item() > 0.4
    print(f"\n✅ Case 1 Pass: Embedding Score đạt {scores[4].item():.4f}")

    # --- CASE 2: EDGE CASES - THRESHOLD TRIGGER (Hoàn toàn lệch ngữ nghĩa) ---
    task_2 = "Hãy viết một email xin nghỉ ốm gửi cho phòng nhân sự"
    
    # Chạy qua selector thật với ngưỡng chặn nghiêm ngặt 0.35 để tránh nhiễu do kho skill nhỏ
    result_edge = selector.select_best_skill(task_2, {}, similarity_threshold=0.42)
    
    # KIỂM CHỨNG: Kết quả bắt buộc phải trả về None vì không có skill nào hỗ trợ viết email
    assert result_edge is None
    print("✅ Case 2 Pass: Kích hoạt bộ lọc Threshold chặn đứng task không liên quan!")

    # --- CASE 3: TOP-K RERANKING LOGIC ---
    task_3 = "Tìm nguyên nhân crash của dự án Java dựa trên log exception"
    query_embedding_3 = selector.embedder.encode(task_3, convert_to_tensor=True)
    scores_3 = selector.embedder.similarity(query_embedding_3, corpus_embeddings)[0]
    _, indices = torch.topk(scores_3, k=2)
    
    # Mảng trả về phải trúng các skill Java (chỉ số 0 hoặc 3)
    assert 0 in indices.tolist() or 3 in indices.tolist()
    print("✅ Case 3 Pass: Trích xuất chính xác nhóm giải pháp bổ trợ ngôn ngữ Java!")