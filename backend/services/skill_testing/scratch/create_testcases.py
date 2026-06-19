import os
import json

TESTCASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "testcases"))
os.makedirs(TESTCASES_DIR, exist_ok=True)

testcases_data = {
    "TC_001_Petclinic_NPE": {
        "testcase": {
            "testcase_id": "TC_001_Petclinic_NPE",
            "repo_name": "spring-petclinic",
            "repo_root": "services/skill_testing/benchmark_repos/spring-petclinic",
            "language": "java",
            "bug_type": "NullPointerException",
            "entry_file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java",
            "task": "Fix the NullPointerException in OwnerController.java. The parameter lastName can be null, and calling lastName.trim() directly triggers NPE. Restore the null-check block so empty string is assigned to lastName if it is null.",
            "stacktrace": "java.lang.NullPointerException: Cannot invoke \"String.trim()\" because \"lastName\" is null\n\tat org.springframework.samples.petclinic.owner.OwnerController.processFindForm(OwnerController.java:99)",
            "bug_injection": {
                "target_file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java",
                "inject_type": "replace_lines",
                "original_content": "String lastName = owner.getLastName();\n\t\tif (lastName == null) {\n\t\t\tlastName = \"\"; // empty string signifies broadest possible search\n\t\t}",
                "buggy_content": "String lastName = owner.getLastName();\n\t\tString trimmed = lastName.trim();"
            },
            "build_command": ["mvnw.cmd", "clean", "compile"],
            "validation_command": ["mvnw.cmd", "test", "-Dtest=OwnerControllerTests"]
        },
        "expected": {
            "validation_targets": {
                "verify_compilation": True,
                "verify_tests": True,
                "verify_patch": True
            },
            "compilation_assertion": {
                "command": ["mvnw.cmd", "clean", "compile"],
                "expected_exit_code": 0
            },
            "test_assertion": {
                "command": ["mvnw.cmd", "test", "-Dtest=OwnerControllerTests"],
                "expected_exit_code": 0
            },
            "patch_assertion": {
                "modified_files": ["src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java"],
                "prohibited_patterns": ["System.exit"],
                "required_patterns": ["lastName == null"]
            }
        },
        "diff": """diff --git a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
--- a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
@@ -98,4 +98,4 @@
-		String lastName = owner.getLastName();
-		String trimmed = lastName.trim();
+		String lastName = owner.getLastName();
+		if (lastName == null) {
+			lastName = "";
+		}"""
    },
    "TC_002_Petclinic_MissingImport": {
        "testcase": {
            "testcase_id": "TC_002_Petclinic_MissingImport",
            "repo_name": "spring-petclinic",
            "repo_root": "services/skill_testing/benchmark_repos/spring-petclinic",
            "language": "java",
            "bug_type": "MissingImport",
            "entry_file": "src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java",
            "task": "Fix the compilation error in PetTypeFormatter.java. The class ParseException is used but not imported. Import java.text.ParseException to compile successfully.",
            "stacktrace": "src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java:52: error: cannot find symbol\n\tpublic PetType parse(String text, Locale locale) throws ParseException {\n\t                                                        ^\n  symbol:   class ParseException\n  location: class PetTypeFormatter",
            "bug_injection": {
                "target_file": "src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java",
                "inject_type": "replace_lines",
                "original_content": "import java.text.ParseException;",
                "buggy_content": "// Deleted import java.text.ParseException;"
            },
            "build_command": ["mvnw.cmd", "clean", "compile"],
            "validation_command": ["mvnw.cmd", "test", "-Dtest=PetTypeFormatterTests"]
        },
        "expected": {
            "validation_targets": {
                "verify_compilation": True,
                "verify_tests": True,
                "verify_patch": True
            },
            "compilation_assertion": {
                "command": ["mvnw.cmd", "clean", "compile"],
                "expected_exit_code": 0
            },
            "test_assertion": {
                "command": ["mvnw.cmd", "test", "-Dtest=PetTypeFormatterTests"],
                "expected_exit_code": 0
            },
            "patch_assertion": {
                "modified_files": ["src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java"],
                "prohibited_patterns": [],
                "required_patterns": ["import java.text.ParseException;"]
            }
        },
        "diff": """diff --git a/src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java b/src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java
--- a/src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java
@@ -21,1 +21,1 @@
-// Deleted import java.text.ParseException;
+import java.text.ParseException;"""
    },
    "TC_003_Petclinic_SyntaxError": {
        "testcase": {
            "testcase_id": "TC_003_Petclinic_SyntaxError",
            "repo_name": "spring-petclinic",
            "repo_root": "services/skill_testing/benchmark_repos/spring-petclinic",
            "language": "java",
            "bug_type": "CompilationError",
            "entry_file": "src/main/java/org/springframework/samples/petclinic/owner/Pet.java",
            "task": "Fix the syntax error in Pet.java. A field declaration is missing a semicolon. Restore the semicolon at the end of the birthDate field.",
            "stacktrace": "src/main/java/org/springframework/samples/petclinic/owner/Pet.java:50: error: ';' expected\n\tprivate LocalDate birthDate\n\t                           ^",
            "bug_injection": {
                "target_file": "src/main/java/org/springframework/samples/petclinic/owner/Pet.java",
                "inject_type": "replace_lines",
                "original_content": "private LocalDate birthDate;",
                "buggy_content": "private LocalDate birthDate"
            },
            "build_command": ["mvnw.cmd", "clean", "compile"],
            "validation_command": ["mvnw.cmd", "test", "-Dtest=OwnerTests"]
        },
        "expected": {
            "validation_targets": {
                "verify_compilation": True,
                "verify_tests": True,
                "verify_patch": True
            },
            "compilation_assertion": {
                "command": ["mvnw.cmd", "clean", "compile"],
                "expected_exit_code": 0
            },
            "test_assertion": {
                "command": ["mvnw.cmd", "test", "-Dtest=OwnerTests"],
                "expected_exit_code": 0
            },
            "patch_assertion": {
                "modified_files": ["src/main/java/org/springframework/samples/petclinic/owner/Pet.java"],
                "prohibited_patterns": [],
                "required_patterns": ["private LocalDate birthDate;"]
            }
        },
        "diff": """diff --git a/src/main/java/org/springframework/samples/petclinic/owner/Pet.java b/src/main/java/org/springframework/samples/petclinic/owner/Pet.java
--- a/src/main/java/org/springframework/samples/petclinic/owner/Pet.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/Pet.java
@@ -50,1 +50,1 @@
-	private LocalDate birthDate
+	private LocalDate birthDate;"""
    },
    "TC_004_Petclinic_MissingMethod": {
        "testcase": {
            "testcase_id": "TC_004_Petclinic_MissingMethod",
            "repo_name": "spring-petclinic",
            "repo_root": "services/skill_testing/benchmark_repos/spring-petclinic",
            "language": "java",
            "bug_type": "MissingMethod",
            "entry_file": "src/main/java/org/springframework/samples/petclinic/owner/Owner.java",
            "task": "Fix the compilation error in Owner.java. The method getPet(String, boolean) was renamed to getPetLegacy. Restore the name of the method back to getPet.",
            "stacktrace": "src/main/java/org/springframework/samples/petclinic/owner/Owner.java:109: error: cannot find symbol\n\t\treturn getPet(name, false);\n\t\t       ^\n  symbol:   method getPet(String,boolean)\n  location: class Owner",
            "bug_injection": {
                "target_file": "src/main/java/org/springframework/samples/petclinic/owner/Owner.java",
                "inject_type": "replace_lines",
                "original_content": "public Pet getPet(String name, boolean ignoreNew) {",
                "buggy_content": "public Pet getPetLegacy(String name, boolean ignoreNew) {"
            },
            "build_command": ["mvnw.cmd", "clean", "compile"],
            "validation_command": ["mvnw.cmd", "test", "-Dtest=OwnerTests"]
        },
        "expected": {
            "validation_targets": {
                "verify_compilation": True,
                "verify_tests": True,
                "verify_patch": True
            },
            "compilation_assertion": {
                "command": ["mvnw.cmd", "clean", "compile"],
                "expected_exit_code": 0
            },
            "test_assertion": {
                "command": ["mvnw.cmd", "test", "-Dtest=OwnerTests"],
                "expected_exit_code": 0
            },
            "patch_assertion": {
                "modified_files": ["src/main/java/org/springframework/samples/petclinic/owner/Owner.java"],
                "prohibited_patterns": [],
                "required_patterns": ["public Pet getPet(String name, boolean ignoreNew)"]
            }
        },
        "diff": """diff --git a/src/main/java/org/springframework/samples/petclinic/owner/Owner.java b/src/main/java/org/springframework/samples/petclinic/owner/Owner.java
--- a/src/main/java/org/springframework/samples/petclinic/owner/Owner.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/Owner.java
@@ -135,1 +135,1 @@
-	public Pet getPetLegacy(String name, boolean ignoreNew) {
+	public Pet getPet(String name, boolean ignoreNew) {"""
    },
    "TC_005_Petclinic_MissingClass": {
        "testcase": {
            "testcase_id": "TC_005_Petclinic_MissingClass",
            "repo_name": "spring-petclinic",
            "repo_root": "services/skill_testing/benchmark_repos/spring-petclinic",
            "language": "java",
            "bug_type": "MissingClass",
            "entry_file": "src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java",
            "task": "Fix the compilation error in PetController.java. The class PetValidator is instantiated but its name has been changed to PetValidatorOld. Rename it back to PetValidator to allow PetController to compile.",
            "stacktrace": "src/main/java/org/springframework/samples/petclinic/owner/PetController.java:95: error: cannot find symbol\n\t\tdataBinder.setValidator(new PetValidator());\n\t\t                            ^\n  symbol:   class PetValidator\n  location: class PetController",
            "bug_injection": {
                "target_file": "src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java",
                "inject_type": "replace_lines",
                "original_content": "public class PetValidator implements Validator {",
                "buggy_content": "public class PetValidatorOld implements Validator {"
            },
            "build_command": ["mvnw.cmd", "clean", "compile"],
            "validation_command": ["mvnw.cmd", "test", "-Dtest=PetControllerTests"]
        },
        "expected": {
            "validation_targets": {
                "verify_compilation": True,
                "verify_tests": True,
                "verify_patch": True
            },
            "compilation_assertion": {
                "command": ["mvnw.cmd", "clean", "compile"],
                "expected_exit_code": 0
            },
            "test_assertion": {
                "command": ["mvnw.cmd", "test", "-Dtest=PetControllerTests"],
                "expected_exit_code": 0
            },
            "patch_assertion": {
                "modified_files": ["src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java"],
                "prohibited_patterns": [],
                "required_patterns": ["public class PetValidator implements Validator"]
            }
        },
        "diff": """diff --git a/src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java b/src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java
--- a/src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java
@@ -32,1 +32,1 @@
-public class PetValidatorOld implements Validator {
+public class PetValidator implements Validator {"""
    },
    "TC_006_Petclinic_LogicalLoop": {
        "testcase": {
            "testcase_id": "TC_006_Petclinic_LogicalLoop",
            "repo_name": "spring-petclinic",
            "repo_root": "services/skill_testing/benchmark_repos/spring-petclinic",
            "language": "java",
            "bug_type": "LogicalLoop",
            "entry_file": "src/main/java/org/springframework/samples/petclinic/owner/Owner.java",
            "task": "Fix the logical infinite loop / stack overflow in Owner.java. In getPets(), a recursive call to getPets() was incorrectly written instead of returning this.pets. Fix it to return this.pets.",
            "stacktrace": "java.lang.StackOverflowError\n\tat org.springframework.samples.petclinic.owner.Owner.getPets(Owner.java:94)",
            "bug_injection": {
                "target_file": "src/main/java/org/springframework/samples/petclinic/owner/Owner.java",
                "inject_type": "replace_lines",
                "original_content": "public List<Pet> getPets() {\n\t\treturn this.pets;\n\t}",
                "buggy_content": "public List<Pet> getPets() {\n\t\treturn this.getPets();\n\t}"
            },
            "build_command": ["mvnw.cmd", "clean", "compile"],
            "validation_command": ["mvnw.cmd", "test", "-Dtest=OwnerTests"]
        },
        "expected": {
            "validation_targets": {
                "verify_compilation": True,
                "verify_tests": True,
                "verify_patch": True
            },
            "compilation_assertion": {
                "command": ["mvnw.cmd", "clean", "compile"],
                "expected_exit_code": 0
            },
            "test_assertion": {
                "command": ["mvnw.cmd", "test", "-Dtest=OwnerTests"],
                "expected_exit_code": 0
            },
            "patch_assertion": {
                "modified_files": ["src/main/java/org/springframework/samples/petclinic/owner/Owner.java"],
                "prohibited_patterns": ["getPets()"],
                "required_patterns": ["return this.pets;"]
            }
        },
        "diff": """diff --git a/src/main/java/org/springframework/samples/petclinic/owner/Owner.java b/src/main/java/org/springframework/samples/petclinic/owner/Owner.java
--- a/src/main/java/org/springframework/samples/petclinic/owner/Owner.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/Owner.java
@@ -93,3 +93,3 @@
 	public List<Pet> getPets() {
-		return this.getPets();
+		return this.pets;
 	}"""
    },
    "TC_007_Petclinic_BrokenHibernateMapping": {
        "testcase": {
            "testcase_id": "TC_007_Petclinic_BrokenHibernateMapping",
            "repo_name": "spring-petclinic",
            "repo_root": "services/skill_testing/benchmark_repos/spring-petclinic",
            "language": "java",
            "bug_type": "BrokenJPA",
            "entry_file": "src/main/java/org/springframework/samples/petclinic/owner/Pet.java",
            "task": "Fix the database schema constraint error in Pet.java. The @JoinColumn for type links to a non-existent database column invalid_type_id. Rename it back to type_id to match Hibernate entity definitions.",
            "stacktrace": "org.springframework.beans.factory.BeanCreationException: Error creating bean with name 'entityManagerFactory'... Column 'invalid_type_id' not found",
            "bug_injection": {
                "target_file": "src/main/java/org/springframework/samples/petclinic/owner/Pet.java",
                "inject_type": "replace_lines",
                "original_content": "@JoinColumn(name = \"type_id\")",
                "buggy_content": "@JoinColumn(name = \"invalid_type_id\")"
            },
            "build_command": ["mvnw.cmd", "clean", "compile"],
            "validation_command": ["mvnw.cmd", "test", "-Dtest=OwnerTests"]
        },
        "expected": {
            "validation_targets": {
                "verify_compilation": True,
                "verify_tests": True,
                "verify_patch": True
            },
            "compilation_assertion": {
                "command": ["mvnw.cmd", "clean", "compile"],
                "expected_exit_code": 0
            },
            "test_assertion": {
                "command": ["mvnw.cmd", "test", "-Dtest=OwnerTests"],
                "expected_exit_code": 0
            },
            "patch_assertion": {
                "modified_files": ["src/main/java/org/springframework/samples/petclinic/owner/Pet.java"],
                "prohibited_patterns": [],
                "required_patterns": ["@JoinColumn(name = \"type_id\")"]
            }
        },
        "diff": """diff --git a/src/main/java/org/springframework/samples/petclinic/owner/Pet.java b/src/main/java/org/springframework/samples/petclinic/owner/Pet.java
--- a/src/main/java/org/springframework/samples/petclinic/owner/Pet.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/Pet.java
@@ -53,1 +53,1 @@
-	@JoinColumn(name = "invalid_type_id")
+	@JoinColumn(name = "type_id")"""
    },
    "TC_008_Petclinic_CircularDependency": {
        "testcase": {
            "testcase_id": "TC_008_Petclinic_CircularDependency",
            "repo_name": "spring-petclinic",
            "repo_root": "services/skill_testing/benchmark_repos/spring-petclinic",
            "language": "java",
            "bug_type": "CircularDependency",
            "entry_file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java",
            "task": "Fix the circular dependency error in OwnerController.java and PetController.java. The two controllers constructor-inject each other, preventing application bootstrap. Remove the circular fields and injections.",
            "stacktrace": "org.springframework.beans.factory.UnsatisfiedDependencyException: Error creating bean with name 'ownerController'... Circular dependency between beans",
            "bug_injection": {
                "target_file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java",
                "inject_type": "replace_lines",
                "original_content": "\tpublic OwnerController(OwnerRepository clinicService) {\n\t\tthis.owners = clinicService;\n\t}",
                "buggy_content": "\tprivate PetController petController;\n\tpublic OwnerController(OwnerRepository clinicService, PetController petController) {\n\t\tthis.owners = clinicService;\n\t\tthis.petController = petController;\n\t}"
            },
            "build_command": ["mvnw.cmd", "clean", "compile"],
            "validation_command": ["mvnw.cmd", "test", "-Dtest=OwnerControllerTests"]
        },
        "expected": {
            "validation_targets": {
                "verify_compilation": True,
                "verify_tests": True,
                "verify_patch": True
            },
            "compilation_assertion": {
                "command": ["mvnw.cmd", "clean", "compile"],
                "expected_exit_code": 0
            },
            "test_assertion": {
                "command": ["mvnw.cmd", "test", "-Dtest=OwnerControllerTests"],
                "expected_exit_code": 0
            },
            "patch_assertion": {
                "modified_files": ["src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java"],
                "prohibited_patterns": ["PetController petController"],
                "required_patterns": ["public OwnerController(OwnerRepository clinicService)"]
            }
        },
        "diff": """diff --git a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
--- a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
@@ -52,5 +52,3 @@
-	private PetController petController;
-	public OwnerController(OwnerRepository clinicService, PetController petController) {
+	public OwnerController(OwnerRepository clinicService) {
 		this.owners = clinicService;
-		this.petController = petController;
 	}"""
    }
}

for tc_id, data in testcases_data.items():
    tc_dir = os.path.join(TESTCASES_DIR, tc_id)
    os.makedirs(tc_dir, exist_ok=True)
    
    # testcase.json
    with open(os.path.join(tc_dir, "testcase.json"), "w", encoding="utf-8") as f:
        json.dump(data["testcase"], f, ensure_ascii=False, indent=2)
        
    # expected.json
    with open(os.path.join(tc_dir, "expected.json"), "w", encoding="utf-8") as f:
        json.dump(data["expected"], f, ensure_ascii=False, indent=2)
        
    # patch.diff
    with open(os.path.join(tc_dir, "patch.diff"), "w", encoding="utf-8") as f:
        f.write(data["diff"])

print("✅ Successfully generated all 8 testcases under testcases/!")
