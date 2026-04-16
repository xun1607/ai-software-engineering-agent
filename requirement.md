Topic: AI agent (agentic) trong Software engineering

AI agent là một dạng “phần mềm” được hỗ trợ bởi các mô hình ngôn ngữ lớn (LLM). Agent có tính tự chủ với khả năng hoạt động độc lập, không cần hoặc chỉ cần một phần sự giám sát của con người cho từng bước. Các agent này thường được thiết kế hướng mục tiêu (goal oriented), tức là xác định mục tiêu, lập kế hoạch hành động và thực hiện theo kế hoạch. Các hành động này không chỉ bao gồm sự tương tác với mô hình LLM nền tảng mà còn có thể sử dụng công cụ bên thứ ba (ví dụ như truy cập web, gọi API, truy vấn CSDL, chạy lệnh terminal,…).

AI agent thường bao gồm các thành phần sau:


AI agent giúp tự động hóa hoạt động trong các quy trình. Ví dụ trong công nghệ phần mềm: tự động hóa lập trình, kiểm thử tự động (tự tạo testcase, tự chạy test, tự phân tích lỗi và tổng hợp báo cáo,…), tự động phản hồi sự cố,…

Các framework để phát triển AI agent: LangChain / LangGraph, AutoGPT / BabyAGI, CrewAI, Microsoft Semantic Kernel, Botpress, OpenAI agents SDK,…

Một xu hướng tiếp cận trong xây dựng hệ thống AI agent hiện nay là “skill-first”: xây dựng các “kỹ năng” trước khi phát triển AI agent. Khái niệm agent skill vẫn chưa được định hình một cách rõ ràng và nhất quán. Các tài liệu nghiên cứu

hiện nay có thể dùng các thuật ngữ như capability, function hoặc behavior. Tuy nhiên có một tiêu chuẩn mở (open standard) cho agent skill: https://agentskills.io/home

Tiêu chuẩn này hình thành một định dạng mở (open format) nhằm giúp xây dựng skill cho các agent có thể hoạt động trên các mô hình LLM khác nhau.

Các bước tổng quát để xây dựng AI agent skill như sau:

1. Xác định mục tiêu & Quy trình (SOP):

o Xác định rõ ràng "kỹ năng" này giải quyết vấn đề gì (ví dụ: gỡ lỗi, gửi email, phân tích báo cáo).

o Phác thảo quy trình các bước (step-by-step) mà AI cần thực hiện, giống như hướng dẫn cho một nhân viên mới.

2. Định nghĩa Hành động (Actions/Tools):

o Tạo các công cụ (tools) hoặc hàm (functions) cụ thể mà AI có thể gọi để tương tác với thế giới bên ngoài (API, cơ sở dữ liệu, công cụ tìm kiếm).

o Ví dụ: Hàm search_database(query) hoặc send_email(to, body).

3. Tạo Skill với AI (LLM) (Sử dụng prompt):

o Sử dụng câu lệnh /create-skill trong các môi trường hỗ trợ (như Visual Studio Code) và mô tả kỹ năng muốn tạo.

o AI sẽ tự động tạo tệp SKILL.md bao gồm: Cấu trúc thư mục, hướng dẫn, phần mở đầu (introduction) và các bước thực hiện.

4. Tích hợp Ngữ cảnh (Context) & Kết nối (Connectors):

o Cung cấp dữ liệu nền cần thiết để kỹ năng hoạt động chính xác.

o Sử dụng các công cụ kết nối (Connectors) để liên kết kỹ năng với hệ thống nội bộ.

5. Kiểm tra và Tinh chỉnh (Testing):

o Chạy thử kỹ năng trong môi trường giả lập.

o Dựa trên phản hồi để tinh chỉnh câu lệnh, quy trình và dữ liệu đầu vào.

Các bước tổng quát này cho thấy việc xây dựng agent skill vẫn tồn tại nhiều thách thức.

· Việc xác định mục tiêu và xây dựng quy trình (SOP) vừa đòi hỏi ở mức độ trừu tượng hóa nhất định (để skill tổng quát và có thể tái sử dụng thuận tiện) vừa phải cân nhắc đến ngữ cảnh khi sử dụng. Thường một skill tốt nên chỉ giải quyết một nhóm vấn đề rõ ràng.

· Khi tạo skill thông qua prompt với LLM, chất lượng đầu ra phụ thuộc nhiều vào cách diễn đạt và cấu trúc prompt, vẫn mang tính kinh nghiệm và khó kiểm soát một cách hệ thống.

· Việc tích hợp ngữ cảnh và kết nối dữ liệu đặt ra các vấn đề về tính nhất quán, độ tin cậy và bảo mật thông tin, đặc biệt trong các hệ thống doanh nghiệp.

Một số hướng nghiên cứu về hệ thống AI agent dựa trên LLM như sau:

AG1. Xây dựng mô hình biểu diễn và phân loại (taxonomy) cho AI agent skill
trong Software Engineering
Bối cảnh
Sự phát triển của các hệ thống AI agent dựa trên mô hình ngôn ngữ lớn (LLM)
đang mở ra khả năng tự động hóa nhiều hoạt động trong quy trình phát triển
phần mềm. Tuy nhiên, khái niệm “agent skill” hiện vẫn chưa có một chuẩn biểu
diễn thống nhất, gây khó khăn cho việc tái sử dụng, chia sẻ và kết hợp các kỹ
năng giữa các hệ thống.
Ý tưởng:
Mô tả này bao gồm các thông tin về sự phân loại (taxonomy) cho skill, cơ chế
biểu diễn phù hợp, cấu trúc phân cấp giúp hình thành kỹ năng tổng hợp từ các
kỹ năng đơn lẻ,…
Mô tả có thể giúp lựa chọn để sử dụng lại những skill có sẵn cho việc tự động
hóa các hoạt động trong quy trình phát triển phần mềm. Hoặc thực hiện chuyển
giao kỹ năng giữa các nhiệm vụ phát triển phần mềm.
Mục tiêu
• Xây dựng một mô hình biểu diễn chính thức (formal representation) cho
AI agent skill
• Đề xuất hệ thống phân loại (taxonomy) cho các skill trong Software
Engineering
• Hỗ trợ khả năng tái sử dụng và kết hợp skill giữa các bài toán khác nhau
Nội dung thực hiện
• Khảo sát các cách tiếp cận hiện có về agent skill và capability
• Phân tích các thành phần cấu thành skill (goal, action, context,
constraint,…)
• Thiết kế mô hình biểu diễn (có thể dưới dạng ontology hoặc schema)
• Xây dựng taxonomy phân cấp cho các skill trong quy trình phát triển phần
mềm
• Thử nghiệm áp dụng trên một số bài toán (ví dụ: debug, testing, CI/CD
automation)
o Epic 1: Chuẩn hóa format skill: Goal, Input/Output, Actions,
Constraints. Ví dụ:
▪ skill: debug_null_pointer
▪ input: stacktrace
▪ output: root_cause
o Epic 2: Xây dựng taxonomy để nhóm skill theo các tiêu chí lập sẵn
(Debugging, Testing, DevOps). Phân cấp được atomic vs composite
skill
o Epic 3: Tìm skill theo keyword, context (task description) và
Ranking skill phù hợp
o Epic 4: Skill composition, cho phép: nối skill thành pipeline, reuse
skill giữa project
Kết quả kỳ vọng
• Một mô hình biểu diễn skill có tính tổng quát và khả năng mở rộng
• Một taxonomy có cấu trúc rõ ràng cho agent skill
• Minh chứng khả năng tái sử dụng và kết hợp skill trong các bài toán thực
tế
• Một “Skill Library” cho Software Engineering:
• Có thể tìm kiếm: “skill debug Java exception”
• Có thể ghép skill: debug → fix → test → commit
• Có file chuẩn kiểu SKILL.md + metadata có cấu trúc
Kịch bản ứng dụng
Scenario: Developer Assistant trong IDE
Một lập trình viên gặp lỗi: “NullPointerException trong service A”
Hệ thống:
1. Tìm trong thư viện skill:
o analyze_stacktrace
o locate_null_source
o suggest_fix_pattern
2. Ghép thành pipeline xử lý lỗi
3. Trả về:
o nguyên nhân
o đề xuất fix
o code patch
Điểm mấu chốt: Skill không viết lại → tái sử dụng từ thư viện
AG2. Kết hợp và điều phối các AI agent skill trong Software engineering
theo ngữ cảnh
Bối cảnh
AI agent đã cho thấy khả năng tự động hóa một phần các hoạt động trong quy
trình phát triển phần mềm. Các agent này cũng trở thành một loại tài nguyên
(nguồn lực) cần quản lý và phân phối. Trong nhiều tình huống, AI agent có thể
thực hiện tốt các tác vụ đơn lẻ. Nhưng lại gặp khó khăn khi phải xử lý các hoạt
động nhiều bước hoặc các yêu cầu phối hợp nhiều kỹ năng (kết quả thực hiện
thường không đáp ứng theo mong đợi). Thông thường, kỹ năng của con người
gắn liền với trí nhớ (kiến thức) và trải nghiệm (ngữ cảnh, kinh nghiệm,…). AI
agent bị giới hạn ở thành phần bộ nhớ (rời rạc, mang tính tình huống), khó xây
dựng bộ nhớ dài hạn. Ngoài ra, phần lớn các kỹ năng hiện nay chưa tính đến yếu
tố chi phí và tài nguyên. Các agent thường không có khả năng cân nhắc giữa độ
chính xác và chi phí tính toán, dẫn đến việc sử dụng tài nguyên không hiệu quả.
Ý tưởng
Hướng tiếp cận này liên quan đến việc lựa chọn kỹ năng phù hợp theo ngữ cảnh
và lập kế hoạch dự án phần mềm.
Mục tiêu
• Xây dựng cơ chế lựa chọn skill phù hợp với từng ngữ cảnh cụ thể
• Đề xuất phương pháp điều phối nhiều agent/skill trong các tác vụ nhiều
bước
• Xem xét yếu tố chi phí và hiệu năng trong quá trình thực thi
Nội dung thực hiện
• Phân tích các phương pháp lập kế hoạch (planning) cho AI agent
• Xây dựng mô hình phân rã nhiệm vụ (task decomposition)
• Thiết kế thuật toán lựa chọn skill dựa trên ngữ cảnh
• Xây dựng cơ chế điều phối multi-agent hoặc multi-skill
• Thực nghiệm trên các bài toán như: tự động kiểm thử, sửa lỗi, xử lý sự cố.
Kịch bản ứng dụng
Ví dụ: Scenario: Automated Bug Fixing Pipeline
o Input: “Bug: API trả sai dữ liệu khi input null”
o Hệ thống tự làm:
▪ Phân rã task (analyze bug, reproduce, fix, test)
▪ Chọn skill: bug_analysis_skill, unit_test_generation,
code_fixing
▪ Lập kế hoạch execution
▪ Chạy tuần tự + kiểm tra kết quả. Nếu fail:tự retry với skill khác
hoặc đổi chiến lược
Kết quả kỳ vọng
• Một framework điều phối agent skill
• Thuật toán lựa chọn skill hiệu quả
• Đánh giá về hiệu năng, chi phí và độ ổn định so với các phương pháp cơ
bản
• Một AI Software Engineer Agent có thể:
o Nhận task: “fix bug + viết test + deploy”
o Tự chia nhỏ task
o Tự chọn skill phù hợp
o Tối ưu chi phí (không gọi LLM vô tội vạ)
Hướng triển khai
• Sử dụng các framework multi-agent (LangGraph, CrewAI, AutoGPT)
• Áp dụng các kỹ thuật planning (rule-based, LLM-based, hoặc hybrid)
• Đánh giá thông qua các chỉ số: success rate, latency, chi phí tính toán…