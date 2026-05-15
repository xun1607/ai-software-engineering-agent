from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from shared.config import get_skills_dir
from shared.db import Base, ENGINE, SessionLocal
from shared.models import Skill as SkillORM
from shared.skill_markdown import SkillMarkdownError, parse_skill_markdown

REQUIRED = ("name", "version", "category", "level")
CORE = {"name", "version", "category", "level", "tags"}


def split_metadata(metadata: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    missing = [k for k in REQUIRED if not metadata.get(k)]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    tags = metadata.get("tags", [])
    if tags is None:
        tags = []
    if not isinstance(tags, list):
        raise ValueError("tags must be a list")

    core = {
        "name": str(metadata["name"]).strip(),
        "version": str(metadata["version"]).strip(),
        "category": str(metadata["category"]).strip(),
        "level": str(metadata["level"]).strip(),
        "tags": [str(tag).strip() for tag in tags if str(tag).strip()],
    }
    if len(core["name"]) > 255 or not core["name"]:
        raise ValueError("name must be 1..255 characters")
    if len(core["version"]) > 50 or not core["version"]:
        raise ValueError("version must be 1..50 characters")
    if len(core["category"]) > 100 or not core["category"]:
        raise ValueError("category must be 1..100 characters")
    if len(core["level"]) > 15 or not core["level"]:
        raise ValueError("level must be 1..15 characters")

    extras = {k: v for k, v in metadata.items() if k not in CORE}
    return core, extras


def iter_skill_files(skills_dir: Path) -> list[Path]:
    return sorted(skills_dir.rglob("SKILL.md"))


def reset_tables() -> None:
    Base.metadata.drop_all(bind=ENGINE)
    Base.metadata.create_all(bind=ENGINE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reload all SKILL.md files into database")
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not drop/recreate tables before loading",
    )
    args = parser.parse_args()

    skills_dir = get_skills_dir()
    if not skills_dir.exists():
        print(f"[reload-skills] skills dir not found: {skills_dir}")
        return 1

    if not args.no_reset:
        reset_tables()

    files = iter_skill_files(skills_dir)
    loaded = 0
    skipped: list[tuple[Path, str]] = []

    with SessionLocal() as session:
        for md_path in files:
            raw = md_path.read_text(encoding="utf-8")
            try:
                metadata, _ = parse_skill_markdown(raw)
                core, extras = split_metadata(metadata)
            except (SkillMarkdownError, ValueError) as exc:
                skipped.append((md_path, str(exc)))
                continue

            exists = (
                session.query(SkillORM)
                .filter(SkillORM.name == core["name"])
                .first()
            )
            if exists:
                skipped.append((md_path, f"duplicate name '{core['name']}'"))
                continue

            session.add(
                SkillORM(
                    name=core["name"],
                    version=core["version"],
                    category=core["category"],
                    level=core["level"],
                    tags=core["tags"],
                    metadata_json=extras,
                    raw_content=raw.strip() + "\n",
                )
            )
            loaded += 1

        session.commit()

    print(f"[reload-skills] loaded: {loaded}")
    print(f"[reload-skills] skipped: {len(skipped)}")
    for path, reason in skipped:
        print(f"  - {path}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
