"""Skill data model — parses SKILL.md (YAML frontmatter + Markdown body)."""
import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class HostConstraint:
    binaries: List[str] = field(default_factory=list)
    runtimes: List[Dict] = field(default_factory=list)
    os: List[str] = field(default_factory=list)


@dataclass
class ResourceConstraint:
    memory: Optional[str] = None
    cpu_cores: Optional[int] = None
    timeout: str = "60s"
    network: str = "full"


@dataclass
class SafetyConstraint:
    fs_access: str = "full"
    db_access: Optional[str] = None
    requires_approval: bool = False


@dataclass
class SkillConstraints:
    host: HostConstraint = field(default_factory=HostConstraint)
    resources: ResourceConstraint = field(default_factory=ResourceConstraint)
    safety: SafetyConstraint = field(default_factory=SafetyConstraint)


@dataclass
class TestCase:
    """A single test case for a skill (Layer 5 — Skill Evaluation)."""
    id: str
    name: str
    input: Dict[str, Any]
    expected_output: Dict[str, Any]
    acceptance: List[str]          # Python expressions: "output.file == expected.file"
    tags: List[str] = field(default_factory=list)


@dataclass
class Skill:
    # ── Layer 1: Specification ───────────────────────────────────────────────
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "General"
    level: Literal["atomic", "composite"] = "atomic"
    tags: List[str] = field(default_factory=list)
    goal: str = ""                             # [NEW] Specific goal of this skill
    input: Dict[str, Any] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)
    constraints: SkillConstraints = field(default_factory=SkillConstraints)
    acceptance_criteria: List[str] = field(default_factory=list)   # [NEW]
    metrics: Dict[str, Any] = field(default_factory=dict)          # [NEW] targets per metric

    # ── Layer 2: Design ──────────────────────────────────────────────────────
    examples: List[Dict] = field(default_factory=list)  # [NEW] few-shot examples
    instructions: str = ""

    # ── Layer 3: Connecting ──────────────────────────────────────────────────
    tools: List[Dict] = field(default_factory=list)           # [NEW]
    context_schema: List[Dict] = field(default_factory=list)  # [NEW]
    memory_interface: Dict[str, List] = field(default_factory=dict)  # [NEW]

    # ── Composite ────────────────────────────────────────────────────────────
    sub_skills: List[str] = field(default_factory=list)

    # ── Layer 5: Evaluation ──────────────────────────────────────────────────
    test_cases: List[TestCase] = field(default_factory=list)   # [NEW]

    # ── Internal ─────────────────────────────────────────────────────────────
    skill_dir: Optional[Path] = None

    # ─────────────────────────────────────────────────────────────────────────
    @classmethod
    def from_markdown(cls, markdown: str, *, skill_dir: Optional[Path] = None) -> "Skill":
        """Parse a SKILL.md markdown string into a Skill object."""
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", markdown, re.DOTALL)
        if not match:
            raise ValueError("Invalid SKILL.md (missing YAML frontmatter)")
        yaml_str = match.group(1)
        body = match.group(2).strip()
        meta = yaml.safe_load(yaml_str) or {}
        if not isinstance(meta, dict):
            raise ValueError("SKILL.md metadata must be a YAML mapping")

        raw_c = meta.get("constraints", {})
        host_d = raw_c.get("host", {})
        res_d = raw_c.get("resources", {})
        safety_d = raw_c.get("safety", {})

        constraints = SkillConstraints(
            host=HostConstraint(
                binaries=host_d.get("binaries", []),
                runtimes=host_d.get("runtimes", []),
                os=host_d.get("os", []),
            ),
            resources=ResourceConstraint(
                memory=res_d.get("memory"),
                cpu_cores=res_d.get("cpu_cores"),
                timeout=res_d.get("timeout", "60s"),
                network=res_d.get("network", "full"),
            ),
            safety=SafetyConstraint(
                fs_access=safety_d.get("fs_access", "full"),
                db_access=safety_d.get("db_access"),
                requires_approval=safety_d.get("requires_approval", False),
            ),
        )

        inst_match = re.search(
            r"##\s+(?:🚀\s+)?Instructions?\s*\n(.*?)(?=\n##\s|\Z)",
            body,
            re.DOTALL | re.IGNORECASE,
        )
        instructions = inst_match.group(1).strip() if inst_match else body

        raw_tcs = meta.get("test_cases", [])
        test_cases = []
        for tc in (raw_tcs or []):
            test_cases.append(
                TestCase(
                    id=tc.get("id", "TC-???"),
                    name=tc.get("name", ""),
                    input=tc.get("input", {}),
                    expected_output=tc.get("expected_output", {}),
                    acceptance=tc.get("acceptance", []),
                    tags=tc.get("tags", []),
                )
            )

        raw_examples = meta.get("examples", [])

        return cls(
            name=meta["name"],
            description=meta["description"],
            version=meta.get("version", "1.0.0"),
            category=meta.get("category", "General"),
            level=meta.get("level", "atomic"),
            tags=meta.get("tags", []),
            goal=meta.get("goal", ""),
            input=meta.get("input", {}),
            output=meta.get("output", {}),
            constraints=constraints,
            acceptance_criteria=meta.get("acceptance_criteria", []),
            metrics=meta.get("metrics", {}),
            examples=raw_examples or [],
            instructions=instructions,
            tools=meta.get("tools", []),
            context_schema=meta.get("context_schema", []),
            memory_interface=meta.get("memory_interface", {}),
            sub_skills=meta.get("sub_skills", []),
            test_cases=test_cases,
            skill_dir=skill_dir,
        )

    @classmethod
    def from_md_file(cls, skill_md_path: Path) -> "Skill":
        """Parse a SKILL.md file into a Skill object."""
        content = skill_md_path.read_text(encoding="utf-8")
        skill = cls.from_markdown(content, skill_dir=skill_md_path.parent)
        if not skill.skill_dir:
            skill.skill_dir = skill_md_path.parent
        return skill

    def to_dict(self) -> dict:
        """Serialize to JSON-friendly dict (for API/frontend)."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "level": self.level,
            "tags": self.tags,
            "goal": self.goal,
            "input": self.input,
            "output": self.output,
            "sub_skills": self.sub_skills,
            "acceptance_criteria": self.acceptance_criteria,
            "metrics": self.metrics,
            "test_cases_count": len(self.test_cases),
        }
