#!/usr/bin/env python3
"""
Universal Skill Library — Backend Demo Runner

Usage:
  python main.py                          # mock LLM, default query + skill
  python main.py --mock                   # explicitly use mock LLM
  python main.py --api-key sk-xxx         # use DeepSeek (or set DEEPSEEK_API_KEY)
  python main.py --query "java exception" # custom search query
  python main.py --skill analyze-stacktrace --mock  # run a specific skill
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from skill_library.core.registry import SkillRegistry
from skill_library.core.executor import SkillExecutor, LogEvent
from skill_library.adapters.langchain_adapter import LangChainAdapter

# ─────────────────────────────────────────────────────────────────────────────
console = Console()

STEP_ICONS = {
    "identify_skill":  "🔍",
    "validate_input":  "✅",
    "check_constraint": "🔒",
    "call_llm":        "🤖",
    "parse_output":    "📦",
    "compose":         "🔗",
    "safety_approval": "⚠️",
}

STATUS_COLOR = {
    "start":   "bold cyan",
    "success": "bold green",
    "error":   "bold red",
    "info":    "dim white",
}

STEP_ORDER = [
    "identify_skill",
    "validate_input",
    "check_constraint",
    "safety_approval",
    "compose",
    "call_llm",
    "parse_output",
]


def make_log_callback(verbose: bool = True):
    """Returns a callback that pretty-prints each LogEvent to the console."""
    step_counter: dict = {}

    def callback(event: LogEvent):
        icon = STEP_ICONS.get(event.step, "▸")
        color = STATUS_COLOR.get(event.status, "white")
        skill_tag = f"[dim]({event.skill_name})[/dim] " if event.skill_name else ""

        # Indent sub-skill calls a bit
        indent = "    " if event.skill_name and "/" in event.step else "  "

        line = f"{indent}[{color}]{icon} [{event.step.upper()}][/{color}]  {skill_tag}{event.message}"
        console.print(line)

        if verbose and event.data and event.status in ("success", "info"):
            for k, v in event.data.items():
                if isinstance(v, list):
                    v = ", ".join(str(x) for x in v)
                console.print(f"       [dim]↳ {k}: {v}[/dim]")

        # Small pause so it looks like streaming
        time.sleep(0.05)

    return callback


# ─────────────────────────────────────────────────────────────────────────────
# Demo sections
# ─────────────────────────────────────────────────────────────────────────────
def demo_library_overview(registry: SkillRegistry):
    console.print(Rule("[bold yellow]📚 Skill Library Overview"))
    table = Table(show_header=True, header_style="bold magenta", border_style="dim")
    table.add_column("Skill Name", style="cyan", no_wrap=True)
    table.add_column("Level", justify="center")
    table.add_column("Category")
    table.add_column("Tags")
    table.add_column("Sub-skills")

    for skill in registry.all_skills():
        level_color = "yellow" if skill.level == "composite" else "green"
        table.add_row(
            skill.name,
            f"[{level_color}]{skill.level}[/{level_color}]",
            skill.category,
            ", ".join(skill.tags[:3]),
            ", ".join(skill.sub_skills) if skill.sub_skills else "—",
        )
    console.print(table)
    console.print()


def demo_search(registry: SkillRegistry, query: str):
    console.print(Rule("[bold yellow]🔍 Epic 3: Skill Search (TF-IDF Offline)"))
    console.print(f"  Query: [bold cyan]\"{query}\"[/bold cyan]\n")

    results = registry.search(query, top_k=3)
    if not results:
        console.print("  [red]No skills matched.[/red]")
        return None

    table = Table(show_header=True, header_style="bold blue", border_style="dim")
    table.add_column("Rank", style="dim", justify="center")
    table.add_column("Skill Name", style="cyan")
    table.add_column("Level", justify="center")
    table.add_column("Score", justify="right", style="green")

    for i, (skill, score) in enumerate(results, 1):
        table.add_row(str(i), skill.name, skill.level, f"{score:.4f}")
    console.print(table)

    best = results[0][0]
    console.print(
        f"\n  [green]→ Best match:[/green] [bold]{best.name}[/bold] "
        f"(score={results[0][1]:.4f})\n"
    )
    return best


def demo_execute(executor: SkillExecutor, skill_name: str, input_data: dict):
    skill = executor.registry.get(skill_name)
    if skill is None:
        console.print(f"[red]Skill '{skill_name}' not found in registry![/red]")
        return None

    console.print(Rule(f"[bold yellow]⚙️  Epic 4: Executing Skill — '{skill.name}'"))

    # Skill info panel
    sub_info = (
        f"\n  Sub-skills: [yellow]{' → '.join(skill.sub_skills)}[/yellow]"
        if skill.sub_skills else ""
    )
    console.print(Panel(
        f"[bold]{skill.name}[/bold]  v{skill.version}\n"
        f"[dim]{skill.description}[/dim]\n"
        f"Level: [cyan]{skill.level}[/cyan]  |  Category: [green]{skill.category}[/green]"
        f"{sub_info}",
        title="Skill Details", border_style="blue", padding=(0, 2),
    ))

    console.print("\n[bold]Input:[/bold]")
    console.print_json(json.dumps(input_data, ensure_ascii=False))
    console.print()

    # Identify skill step (meta — before executor runs)
    console.print(
        f"  [bold cyan]🔍 [IDENTIFY_SKILL][/bold cyan]  "
        f"Skill found: [bold]{skill.name}[/bold] "
        f"(level={skill.level}, sub_skills={skill.sub_skills})"
    )
    console.print()
    console.print("[bold cyan]──── Execution Log ──────────────────────────────────────[/bold cyan]")

    try:
        t0 = time.time()
        output = executor.run(skill, input_data)
        elapsed = time.time() - t0

        console.print(
            f"\n[bold cyan]──── Output ({elapsed:.2f}s) ────────────────────────────────[/bold cyan]"
        )
        console.print_json(json.dumps(output, indent=2, ensure_ascii=False))
        return output

    except Exception as exc:
        console.print(f"\n[bold red]✗ Execution failed:[/bold red] {exc}")
        return None


def demo_langchain_adapter(executor: SkillExecutor):
    console.print(Rule("[bold yellow]🔌 Framework Adapter: LangChain"))
    adapter = LangChainAdapter(executor)
    try:
        tools = adapter.get_all_tools()
        console.print(
            f"  [green]✓[/green] Converted [bold]{len(tools)}[/bold] skills → LangChain StructuredTools\n"
        )
        table = Table(show_header=True, header_style="bold blue", border_style="dim")
        table.add_column("Tool Name", style="cyan")
        table.add_column("Args Schema", style="dim")
        for t in tools:
            fields = list(t.args_schema.model_fields.keys()) if hasattr(t.args_schema, "model_fields") else ["?"]
            table.add_row(t.name, ", ".join(fields))
        console.print(table)
        console.print(
            "\n  [dim]Note: Constraint checks are embedded inside each tool's wrapper "
            "function — LangChain only calls the skill after all constraints pass.[/dim]\n"
        )
    except Exception as exc:
        console.print(f"  [yellow]LangChain adapter warning: {exc}[/yellow]")


def demo_cycle_detection(registry: SkillRegistry, executor: SkillExecutor):
    """Demonstrate that cyclic skill calls are caught before infinite recursion."""
    console.print(Rule("[bold yellow]🔄 Cycle Detection Demo"))
    console.print(
        "  Simulating: skill-A calls skill-A (circular dependency)\n"
    )
    from skill_library.models.skill import Skill

    # Create a fake self-referential composite skill
    fake_skill = Skill(
        name="skill-a",
        description="Fake skill that calls itself",
        level="composite",
        sub_skills=["skill-a"],
        input={"type": "object", "required": [], "properties": {}},
        output={"type": "object", "properties": {}},
    )
    registry.skills["skill-a"] = fake_skill

    try:
        executor.run(fake_skill, {})
        console.print("  [red]BUG: Cycle was NOT detected![/red]")
    except Exception as exc:
        console.print(f"  [bold green]✓ Cycle caught:[/bold green] {exc}\n")
    finally:
        del registry.skills["skill-a"]  # clean up


# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Universal Skill Library — Backend Demo"
    )
    parser.add_argument("--mock", action="store_true", default=True,
                        help="Use mock LLM (default). Set --no-mock to use DeepSeek.")
    parser.add_argument("--no-mock", dest="mock", action="store_false",
                        help="Use real DeepSeek API (requires DEEPSEEK_API_KEY)")
    parser.add_argument("--api-key", help="DeepSeek API key")
    parser.add_argument("--skill", default="debug-java-null-pointer",
                        help="Name of skill to execute in demo")
    parser.add_argument("--query", default="debug java null pointer exception",
                        help="Search query for skill search demo")
    args = parser.parse_args()

    # ── Header ────────────────────────────────────────────────────────────
    console.print(Panel.fit(
        "[bold cyan]🧠 Universal Skill Library[/bold cyan]\n"
        "[dim]AI Agent Skill Execution Engine — Backend Demo[/dim]\n\n"
        f"  Mode: [{'yellow' if args.mock else 'green'}]"
        f"{'🟡 MOCK (offline)' if args.mock else '🟢 DeepSeek API'}[/]",
        border_style="cyan", padding=(1, 4),
    ))

    # ── Load skill library ────────────────────────────────────────────────
    console.print(Rule("[bold yellow]Loading Skill Library"))
    skills_dir = Path(__file__).parent / "skills"
    registry = SkillRegistry(skills_dir)
    count = registry.load_all()
    console.print(
        f"  [green]✓[/green] Loaded [bold]{count}[/bold] skill(s) from [dim]{skills_dir}[/dim]\n"
    )
    demo_library_overview(registry)

    # ── Create executor ───────────────────────────────────────────────────
    executor = SkillExecutor(
        registry=registry,
        api_key=args.api_key or os.environ.get("DEEPSEEK_API_KEY"),
        mock_mode=args.mock,
        log_callback=make_log_callback(verbose=True),
    )

    # ── Demo 1: Skill Search ──────────────────────────────────────────────
    demo_search(registry, args.query)

    # ── Demo 2: Skill Execution (composite) ──────────────────────────────
    sample_input = {
        "stacktrace": (
            "Exception in thread \"main\" java.lang.NullPointerException\n"
            "\tat com.example.service.UserService.getUsername(UserService.java:42)\n"
            "\tat com.example.controller.UserController.profile(UserController.java:28)\n"
            "\tat sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)\n"
            "\tat org.springframework.web.servlet.FrameworkServlet.service(FrameworkServlet.java:897)"
        ),
        "source_path": "./src/main/java",
    }
    demo_execute(executor, args.skill, sample_input)

    # ── Demo 3: LangChain Adapter ─────────────────────────────────────────
    demo_langchain_adapter(executor)

    # ── Demo 4: Cycle Detection ───────────────────────────────────────────
    demo_cycle_detection(registry, executor)

    console.print(Panel.fit(
        "[bold green]✓ Backend demo complete![/bold green]\n"
        "[dim]Next step: build the web UI that streams these log events in real-time.[/dim]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
