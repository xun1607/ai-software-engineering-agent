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
class Skill:
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "General"
    level: Literal["atomic", "composite"] = "atomic"
    tags: List[str] = field(default_factory=list)
    input: Dict[str, Any] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)
    constraints: SkillConstraints = field(default_factory=SkillConstraints)
    sub_skills: List[str] = field(default_factory=list)
    instructions: str = ""
    skill_dir: Optional[Path] = None

    @classmethod
    def from_md_file(cls, skill_md_path: Path) -> "Skill":
        """Parse a SKILL.md file into a Skill object."""
        content = skill_md_path.read_text(encoding="utf-8")

        # Split frontmatter from body
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", content, re.DOTALL)
        if not match:
            raise ValueError(
                f"Invalid SKILL.md (missing YAML frontmatter between ---): {skill_md_path}"
            )
        yaml_str = match.group(1)
        body = match.group(2).strip()
        meta = yaml.safe_load(yaml_str)

        # Parse constraints block
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

        # Extract ## Instructions section from body
        inst_match = re.search(
            r"##\s+(?:🚀\s+)?Instructions?\s*\n(.*?)(?=\n##\s|\Z)",
            body,
            re.DOTALL | re.IGNORECASE,
        )
        instructions = inst_match.group(1).strip() if inst_match else body

        return cls(
            name=meta["name"],
            description=meta["description"],
            version=meta.get("version", "1.0.0"),
            category=meta.get("category", "General"),
            level=meta.get("level", "atomic"),
            tags=meta.get("tags", []),
            input=meta.get("input", {}),
            output=meta.get("output", {}),
            constraints=constraints,
            sub_skills=meta.get("sub_skills", []),
            instructions=instructions,
            skill_dir=skill_md_path.parent,
        )

    def to_dict(self) -> dict:
        """Serialize to JSON-friendly dict (for API/frontend)."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "level": self.level,
            "tags": self.tags,
            "input": self.input,
            "output": self.output,
            "sub_skills": self.sub_skills,
        }
