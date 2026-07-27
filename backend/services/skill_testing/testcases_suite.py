from typing import List, Dict, Any, Optional

TESTCASES_SUITE: List[Dict[str, Any]] = [
    {
        "id": "tc_long_context_spring",
        "name": "Heavy Stack Trace & Multi-File Spring Boot Context Fix",
        "category": "java",
        "repo_dir": "benchmark_repos/spring-petclinic",
        "task_desc": (
            "Dưới đây là đoạn nhật ký khởi chạy ứng dụng (Long Application Stack Trace Context) được hệ thống ghi nhận:\n\n"
            "[2026-07-25 15:30:12.102] [main] INFO  o.s.b.w.embedded.tomcat.TomcatWebServer - Tomcat initialized with port(s): 8080 (http)\n"
            "[2026-07-25 15:30:12.215] [main] INFO  o.s.b.w.servlet.context.ServletWebServerApplicationContext - Root WebApplicationContext: initialization completed in 1432 ms\n"
            "[2026-07-25 15:30:12.388] [main] WARN  o.s.b.a.m.MustacheAutoConfiguration - Cannot find template loader path: classpath:/templates/\n"
            "[2026-07-25 15:30:12.412] [main] ERROR o.s.boot.SpringApplication - Application run failed\n"
            "org.springframework.beans.factory.BeanCreationException: Error creating bean with name 'petController' defined in file [/app/target/classes/org/springframework/samples/petclinic/owner/PetController.class]: Initialization of bean failed; nested exception is java.lang.Error: Unresolved compilation problem\n"
            "\tat org.springframework.beans.factory.support.AbstractAutowireCapableBeanFactory.doCreateBean(AbstractAutowireCapableBeanFactory.java:603)\n"
            "\tat org.springframework.beans.factory.support.AbstractAutowireCapableBeanFactory.createBean(AbstractAutowireCapableBeanFactory.java:522)\n"
            "\tat org.springframework.beans.factory.support.AbstractBeanFactory.lambda$doGetBean$0(AbstractBeanFactory.java:337)\n"
            "\tat org.springframework.beans.factory.support.DefaultSingletonBeanRegistry.getSingleton(DefaultSingletonBeanRegistry.java:234)\n"
            "\tat org.springframework.beans.factory.support.AbstractBeanFactory.doGetBean(AbstractBeanFactory.java:335)\n"
            "\tat org.springframework.beans.factory.support.AbstractBeanFactory.getBean(AbstractBeanFactory.java:200)\n"
            "\tat org.springframework.beans.factory.support.DefaultListableBeanFactory.preInstantiateSingletons(DefaultListableBeanFactory.java:975)\n"
            "\tat org.springframework.context.support.AbstractApplicationContext.finishBeanFactoryInitialization(AbstractApplicationContext.java:915)\n"
            "\tat org.springframework.context.support.AbstractApplicationContext.refresh(AbstractApplicationContext.java:584)\n"
            "\tat org.springframework.boot.web.servlet.context.ServletWebServerApplicationContext.refresh(ServletWebServerApplicationContext.java:146)\n"
            "\tat org.springframework.boot.SpringApplication.refresh(SpringApplication.java:732)\n"
            "\tat org.springframework.boot.SpringApplication.refreshContext(SpringApplication.java:434)\n"
            "\tat org.springframework.boot.SpringApplication.run(SpringApplication.java:310)\n"
            "\tat org.springframework.boot.SpringApplication.run(SpringApplication.java:1303)\n"
            "\tat org.springframework.boot.SpringApplication.run(SpringApplication.java:1292)\n"
            "\tat org.springframework.samples.petclinic.PetClinicApplication.main(PetClinicApplication.java:32)\n"
            "Caused by: java.lang.Error: Unresolved compilation problem: Syntax error on token in PetValidator.java\n"
            "\tat org.springframework.samples.petclinic.owner.PetValidator.validate(PetValidator.java:38)\n"
            "\tat org.springframework.samples.petclinic.owner.PetController.initCreationForm(PetController.java:60)\n\n"
            "Yêu cầu: Hãy phân tích đoạn log trên, kiểm tra file 'src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java' trong repo, sửa lỗi cú pháp biên dịch tại dòng 38 và đảm bảo file biên dịch thành công."
        ),
        "test_cmd": "javac src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java"
    },
    {
        "id": "tc_repo_petclinic_java",
        "name": "Spring PetClinic Java Syntax Fix",
        "category": "java",
        "repo_dir": "benchmark_repos/spring-petclinic",
        "task_desc": "Trong dự án Spring PetClinic, file 'src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java' đang bị lỗi cú pháp Java khi biên dịch. Hãy tìm và sửa lỗi cú pháp để file biên dịch thành công.",
        "test_cmd": "javac src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java"
    },
    {
        "id": "tc_repo_flask_api",
        "name": "Flask API Repo Fix (ZeroDivision & KeyError)",
        "category": "python",
        "repo_dir": "benchmark_repos/repo_flask_api",
        "task_desc": "Hãy chạy bộ unit test trong thư mục 'tests/' để tìm các lỗi ZeroDivisionError và KeyError trong file 'app.py', sau đó sửa lại mã nguồn trong 'app.py' sao cho toàn bộ unit test đều PASS.",
        "test_cmd": "python -m unittest discover -s tests"
    },
    {
        "id": "tc_repo_data_processor",
        "name": "Data Processor Repo Fix (KeyError Default ID)",
        "category": "python",
        "repo_dir": "benchmark_repos/repo_data_processor",
        "task_desc": "Chạy thử bộ unit test trong thư mục 'tests/' và sửa lỗi KeyError khi trường 'id' bị thiếu trong dữ liệu JSON tại file 'src/data_parser.py'.",
        "test_cmd": "python -m unittest discover -s tests"
    },
    {
        "id": "tc_python_syntax",
        "name": "Python Syntax Error Fix",
        "category": "python",
        "task_desc": "Hãy kiểm tra và sửa lỗi cú pháp trong file 'calculator.py' để hàm add(a, b) hoạt động bình thường.",
        "files": {
            "calculator.py": "def add(a, b)\n    return a + b\n\nif __name__ == '__main__':\n    print(add(2, 3))"
        },
        "test_cmd": "python calculator.py"
    },
    {
        "id": "tc_python_import",
        "name": "Python Missing Import Fix",
        "category": "python",
        "task_desc": "Sửa lỗi NameError trong file 'math_utils.py' do dùng hàm math.sqrt mà chưa import thư viện math.",
        "files": {
            "math_utils.py": "def calculate_root(val):\n    return math.sqrt(val)\n\nif __name__ == '__main__':\n    print(calculate_root(16))"
        },
        "test_cmd": "python math_utils.py"
    },
    {
        "id": "tc_java_npe",
        "name": "Java NullPointer Safety Check",
        "category": "java",
        "task_desc": "Bổ sung kiểm tra null cho biến user trong file 'UserService.java' để tránh lỗi NullPointerException khi gọi getName().",
        "files": {
            "src/main/java/UserService.java": "public class UserService {\n    public static String getUserName(User user) {\n        return user.getName();\n    }\n}"
        },
        "test_cmd": "javac src/main/java/UserService.java"
    },
    {
        "id": "tc_git_conflict",
        "name": "Git Conflict Markers Resolver",
        "category": "git",
        "task_desc": "Dọn dẹp các ký hiệu xung đột Git (<<<<<<<, =======, >>>>>>>) trong file 'config.py' và giữ lại giá trị PORT = 8080.",
        "files": {
            "config.py": "<<<<<<< HEAD\nPORT = 8080\n=======\nPORT = 3000\n>>>>>>> feature/new-port\n"
        },
        "test_cmd": "python -c \"import config; print('OK')\""
    },
    {
        "id": "tc_system_log_scan",
        "name": "System Log Error Scanner",
        "category": "system",
        "task_desc": "Quét file nhật ký 'server.log' tìm các dòng chứa chữ 'ERROR' và lưu kết quả tổng hợp.",
        "files": {
            "server.log": "INFO: Server started\nERROR: Failed to connect to database at localhost:5432\nINFO: Retrying connection\nERROR: Timeout connection to Redis\n"
        },
        "test_cmd": "python -c \"print('OK')\""
    }
]

# Auto-load SWE-bench Lite testcases if swe_lite_testcases.json exists
import os, json
json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "swe_lite_testcases.json"))
if os.path.exists(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            swe_items = json.load(f)
            existing_ids = {tc["id"] for tc in TESTCASES_SUITE}
            for item in swe_items:
                if item["id"] not in existing_ids:
                    TESTCASES_SUITE.append(item)
    except Exception as e:
        print(f"Warning loading swe_lite_testcases.json: {e}")

def get_testcases(
    selected_ids: Optional[List[str]] = None, 
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Hàm bộ lọc khống chế danh sách Testcases cần chạy.
    """
    suite = list(TESTCASES_SUITE)
    if selected_ids:
        suite = [tc for tc in suite if tc["id"] in selected_ids]
    if category:
        suite = [tc for tc in suite if tc["category"].lower() == category.lower()]
    return suite
