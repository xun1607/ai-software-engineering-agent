import os
import json
import dotenv
import sys
import time
import sqlite3
import requests
import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
import streamlit as st
from typing import List, Dict, Any

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# Add sys.path for service imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "swe_agent")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from langchain_community.callbacks import get_openai_callback
from langchain_core.messages import HumanMessage

from swe_agent.core.brain import OpenAIBrain
from swe_agent.core.sandbox import LocalSandbox
from swe_agent.factory import create_swe_agent
from swe_agent.skills.markdown_skill import DynamicMarkdownSkill
from swe_agent.skills.registry import SkillRegistry
from swe_agent.tools import (
    ReadFileTool, WriteFileTool, EditFileTool, ListFilesTool,
    FindFileTool, SearchCodeTool, TerminalShellTool, RunTestsTool,
    CompileProjectTool, GitDiffTool
)
from swe_agent.cass_bridge import CASSBridge
from legacy_skills import LegacySuggestFixSkill, LegacyReadContextSkill
from testcases_suite import TESTCASES_SUITE, get_testcases

# Streamlit Page Config with Collapsed Sidebar by Default for 100% Screen Width
st.set_page_config(
    page_title="CASS Control Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling for Commercial-Grade Responsive UI
st.markdown("""
<style>
    .main-title {
        font-size: 2.4rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 0.1rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.0rem;
    }
    .env-card {
        background-color: #F1F5F9;
        border-left: 4px solid #3B82F6;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 15px;
    }
    .badge-dropped {
        background-color: #FEF2F2;
        border: 1px solid #FCA5A5;
        color: #991B1B;
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 8px;
        font-size: 0.88rem;
    }
    .badge-selected {
        background-color: #ECFDF5;
        border: 1px solid #6EE7B7;
        color: #065F46;
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 8px;
        font-size: 0.88rem;
    }
    code, pre {
        white-space: pre-wrap !important;
        word-break: break-word !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🛡️ CASS Control Center</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Candidate Agent Skill Selection & Real-time Execution Dashboard</div>', unsafe_allow_html=True)

DB_PATH = "benchmark_cass.db"
CSV_PATH = "benchmark_results.csv"

# Quick Configuration Expander on Main Page
with st.expander("⚙️ Quick Configuration & LLM Settings", expanded=False):
    col_c1, col_c2, col_c3 = st.columns(3)
    model_choice = col_c1.selectbox("LLM Brain Model", ["gpt-4o", "gpt-4o-mini"], index=0)
    top_k_skills = col_c2.slider("CASS Top-K Skills Limit", min_value=1, max_value=10, value=3)
    sandbox_root = col_c3.text_input("Sandbox Working Root", value="./workspace_streamlit")

# Helper function to plot Beta PDF curve
def plot_beta_pdf(alpha: float, beta_param: float, skill_name: str):
    x = np.linspace(0.001, 0.999, 200)
    y = stats.beta.pdf(x, alpha, beta_param)
    mean_val = alpha / (alpha + beta_param)
    
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(x, y, color="#10B981", linewidth=2.5, label=f"Beta(α={alpha}, β={beta_param})")
    ax.fill_between(x, 0, y, color="#10B981", alpha=0.25)
    ax.axvline(mean_val, color="#EF4444", linestyle="--", linewidth=1.5, label=f"Expected E[θ] = {mean_val:.2f}")
    
    ax.set_title(f"Thompson Sampling Probability Density - '{skill_name}'", fontsize=10, fontweight="bold")
    ax.set_xlabel("Success Probability (θ)", fontsize=9)
    ax.set_ylabel("Probability Density PDF", fontsize=9)
    ax.legend(fontsize=8.5, loc="upper left")
    ax.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    return fig

# Main Navigation Tabs
tab_live, tab_analytics, tab_import = st.tabs([
    "🕹️ Live Control & Execution", 
    "📈 Benchmark Analytics & Savings",
    "📥 Skill Store & Online Import"
])

# Shared Skill Registration Setup
cass_bridge = CASSBridge(DB_PATH)

registry = SkillRegistry()
brain = OpenAIBrain(model_name=model_choice)
tools = [
    ReadFileTool(), WriteFileTool(), EditFileTool(), ListFilesTool(),
    FindFileTool(), SearchCodeTool(), TerminalShellTool(), RunTestsTool(),
    CompileProjectTool(), GitDiffTool()
]

skills_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "skills"))
if os.path.exists(skills_dir):
    for folder in os.listdir(skills_dir):
        folder_path = os.path.join(skills_dir, folder)
        if os.path.isdir(folder_path):
            md_path = os.path.join(folder_path, "SKILL.md")
            if os.path.exists(md_path):
                try:
                    skill = DynamicMarkdownSkill(md_path, brain, tools)
                    registry.register(skill)
                except Exception as ex:
                    print(f"Warning: Could not parse skill in '{folder}': {ex}")
registry.register(LegacySuggestFixSkill())
registry.register(LegacyReadContextSkill())
all_skills = registry.get_all_skills()

# ==========================================
# TAB 1: LIVE CONTROL CENTER (4-ZONE VISUALIZATION)
# ==========================================
with tab_live:
    all_testcases = get_testcases()
    
    # ------------------------------------------
    # KHU VỰC 1: INPUT & HOST CONTEXT
    # ------------------------------------------
    st.subheader("🎯 1: Input Task & Host Context")
    
    env_context = cass_bridge.cass.context_manager.get_full_context("session_ui", "subtask")
    env_info = env_context.get("environment", {})
    host_os = env_info.get('os_name', sys.platform)
    host_ram = env_info.get('available_ram_mb', 4096)
    host_cpu = env_info.get('cpu_cores', 4)
    
    col_tc_select, col_env_card = st.columns([1.3, 1.0], gap="medium")
    
    with col_tc_select:
        selected_tc_id = st.selectbox("🎯 Select Testcase to Run", [tc["id"] for tc in all_testcases], index=0)
        selected_tc = next(tc for tc in all_testcases if tc["id"] == selected_tc_id)
        
        st.markdown(f"**Testcase**: `{selected_tc['name']}` | **Category**: `{selected_tc['category'].upper()}`")
        st.caption(f"**Task Prompt**: {selected_tc['task_desc'][:250]}...")
        
    with col_env_card:
        st.markdown(f"""
        <div class="env-card">
            <b>💻 Current Host Environment Profile</b><br>
            • <b>Operating System</b>: <code>{host_os.upper()}</code> | 
            • <b>Available RAM</b>: <code>{host_ram} MB</code> | 
            • <b>CPU Cores</b>: <code>{host_cpu} Cores</code><br>
            • <b>Total Skills in Registry</b>: <code>{len(all_skills)} Registered Skills</code>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ------------------------------------------
    # KHU VỰC 2: CASS INTELLIGENCE & FILTERING REASONER
    # ------------------------------------------
    st.subheader("🛡️ 2: CASS Intelligence & Skills Filtering Logic")
    
    cass_details = cass_bridge.get_optimized_skills_with_details(
        all_skills, "session_ui", selected_tc["task_desc"], top_k=top_k_skills
    )
    dropped_skills = cass_details.get("dropped_skills", [])
    selected_skills = cass_details.get("selected_skills", [])
    
    col_cass_sel, col_cass_drop = st.columns(2, gap="medium")
    
    with col_cass_sel:
        st.markdown(f"**Selected Top-{len(selected_skills)} Skills (High Semantic Match & Bayesian Reputation):**")
        for s in selected_skills:
            st.markdown(f"""<div class="badge-selected">✅ <b>{s.name}</b> — <i>{s.description[:80]}...</i></div>""", unsafe_allow_html=True)
            
    with col_cass_drop:
        st.markdown(f"**CASS Rejected ({len(dropped_skills)}) Skills (OS Mismatch / Low Reputation):**")
        with st.container(height=160):
            if dropped_skills:
                for s in dropped_skills:
                    os_req = s.constraints.get("host", {}).get("os", ["Any"])
                    is_os_rejected = host_os not in os_req and "Any" not in os_req
                    reason = f"OS Mismatch (Req: {os_req}, Current: {host_os})" if is_os_rejected else "Lower Bayesian Reputation / Semantic Score"
                    st.markdown(f"""<div class="badge-dropped">❌ <b>{s.name}</b> — <i>REJECTED ({reason})</i></div>""", unsafe_allow_html=True)
            else:
                st.success("No skills rejected for this task.")

    st.markdown("---")

    # ------------------------------------------
    # KHU VỰC 3: AGENT EXECUTION (THOUGHT TRACE vs VIRTUAL TERMINAL)
    # ------------------------------------------
    st.subheader("⚡ 3: Agent Sandbox Execution & Real-time Console")
    
    col_btn1, col_btn2 = st.columns(2)
    run_cass = col_btn1.button("🚀 Run Agent (CASS Enabled)", type="primary", use_container_width=True)
    run_baseline = col_btn2.button("⚡ Run Agent (Baseline)", use_container_width=True)
    
    if run_cass or run_baseline:
        is_cass = True if run_cass else False
        mode_name = "CASS-Enabled" if is_cass else "Baseline"
        
        # 1. Auto-Setup Repository (Shallow Clone if repository missing)
        if "repo_url" in selected_tc:
            repo_url = selected_tc["repo_url"]
            repo_target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), selected_tc.get("repo_dir", f"benchmark_repos/{selected_tc['id']}")))
            if not os.path.exists(repo_target_dir):
                with st.spinner(f"📥 Auto-cloning repository from {repo_url}..."):
                    import subprocess
                    os.makedirs(os.path.dirname(repo_target_dir), exist_ok=True)
                    subprocess.run(["git", "clone", "--depth", "1", repo_url, repo_target_dir], check=False)
        
        with st.status(f"🚀 Running Agent in `{mode_name}` Mode...", expanded=True) as status:
            st.write("🧠 **ReasoningNode**: Analyzing query & binding tools...")
            
            ws_path = f"{sandbox_root}_{mode_name.lower()}"
            if os.path.exists(ws_path):
                import shutil, stat
                def remove_readonly(func, path, exc_info):
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                shutil.rmtree(ws_path, onerror=remove_readonly)
            sandbox = LocalSandbox(ws_path)
            
            if "repo_dir" in selected_tc and os.path.exists(selected_tc["repo_dir"]):
                import shutil
                shutil.copytree(os.path.abspath(selected_tc["repo_dir"]), sandbox.workspace_path, dirs_exist_ok=True)
            if "files" in selected_tc:
                for path, content in selected_tc["files"].items():
                    sandbox.write_file(path, content)
                    
            bridge_to_pass = cass_bridge if is_cass else None
            agent = create_swe_agent(brain, sandbox, all_skills, cass_bridge=bridge_to_pass)
            
            initial_state = {
                "messages": [HumanMessage(content=selected_tc["task_desc"])],
                "iteration_count": 0,
                "is_valid": False,
                "feedback": None,
                "session_id": "session_ui",
                "test_command": selected_tc.get("test_cmd", ""),
                "execution_logs": []
            }
            
            st.write("⚡ **ActionNode**: Executing tool actions inside Sandbox workspace...")
            start_t = time.time()
            final_state = None
            with get_openai_callback() as cb:
                try:
                    final_state = agent.invoke(initial_state, {"recursion_limit": 15})
                    success = final_state.get("is_valid", False) if final_state else False
                except Exception as e:
                    st.error(f"Execution Error: {e}")
                    success = False
            lat = (time.time() - start_t) * 1000
            
            if success:
                status.update(label=f"✅ Mission Accomplished in {lat:.0f}ms! Tokens: {cb.total_tokens}", state="complete", expanded=True)
                st.success(f"**Execution Summary**: Total Tokens: `{cb.total_tokens}` | Latency: `{lat:.2f}ms` | Cost: `${cb.total_cost:.5f}`")
            else:
                status.update(label="❌ Execution Failed", state="error", expanded=True)
                
            # 💾 Telemetry Persistence
            try:
                cass_details_run = cass_bridge.get_optimized_skills_with_details(
                    all_skills, "session_ui", selected_tc["task_desc"], top_k=top_k_skills
                )
                run_skills = cass_details_run.get("selected_skills", [])
                if is_cass and run_skills:
                    for s in run_skills:
                        cass_bridge.cass.db_manager.update_metrics(s.name, success=success)
                        
                row_data = {
                    "Testcase_ID": selected_tc["id"],
                    "Scenario": mode_name,
                    "Total Skills Bound": top_k_skills if is_cass else len(all_skills),
                    "Prompt Tokens": cb.prompt_tokens,
                    "Completion Tokens": cb.completion_tokens,
                    "Total Tokens": cb.total_tokens,
                    "Cost": round(cb.total_cost, 6),
                    "Latency (ms)": round(lat, 2),
                    "Success": 1 if success else 0
                }
                df_row = pd.DataFrame([row_data])
                if os.path.exists(CSV_PATH):
                    df_row.to_csv(CSV_PATH, mode='a', header=False, index=False)
                else:
                    df_row.to_csv(CSV_PATH, mode='w', header=True, index=False)
                    
                st.toast("💾 Telemetry persisted to benchmark_cass.db & benchmark_results.csv!", icon="✅")
            except Exception as save_err:
                print(f"Telemetry save error: {save_err}")

        # --- DUAL VIEW DISPLAY: THOUGHT TRACE vs VIRTUAL TERMINAL ---
        col_thought, col_terminal = st.columns([1.1, 1.1], gap="medium")
        
        with col_thought:
            st.markdown("### 🧠 Agent Thought Trace (Đang suy nghĩ gì)")
            with st.container(height=400):
                if final_state and "messages" in final_state:
                    for msg in final_state["messages"]:
                        role = msg.__class__.__name__
                        if role == "AIMessage" and msg.content:
                            st.markdown("💬 **Agent Reasoning Step:**")
                            st.info(msg.content)
                        elif role == "HumanMessage":
                            st.markdown("👤 **User Prompt Task:**")
                            st.caption(msg.content[:200] + "...")
                else:
                    st.warning("No thought trace recorded.")
                    
        with col_terminal:
            st.markdown("### 🖥️ Virtual Terminal (Stderr / Stdout thực tế từ Sandbox)")
            with st.container(height=400):
                # Build lookup map from AIMessage tool_calls to resolve exact skill names & args
                tool_call_map = {}
                if final_state and "messages" in final_state:
                    for msg in final_state["messages"]:
                        if msg.__class__.__name__ == "AIMessage" and hasattr(msg, "tool_calls"):
                            for tc in getattr(msg, "tool_calls", []):
                                if isinstance(tc, dict) and "id" in tc:
                                    tool_call_map[tc["id"]] = tc

                exec_logs = list(final_state.get("execution_logs", [])) if final_state else []
                if not exec_logs and final_state and "messages" in final_state:
                    for msg in final_state["messages"]:
                        if msg.__class__.__name__ == "ToolMessage":
                            tc_id = getattr(msg, "tool_call_id", "call")
                            tc_info = tool_call_map.get(tc_id, {})
                            tool_name = tc_info.get("name", "sandbox_tool")
                            tool_args = tc_info.get("args", {})
                            exec_logs.append({
                                "tool": tool_name,
                                "args": tool_args,
                                "output": msg.content
                            })
                            
                if exec_logs:
                    terminal_output = ""
                    for idx, log_item in enumerate(exec_logs, 1):
                        tool_name = log_item.get("tool", "shell")
                        tool_args = log_item.get("args", {})
                        
                        # If tool is generic fallback, attempt lookup by tool_call_id
                        if tool_name == "sandbox_tool" and "tool_call_id" in tool_args:
                            tc_info = tool_call_map.get(tool_args["tool_call_id"], {})
                            if "name" in tc_info:
                                tool_name = tc_info["name"]
                                tool_args = tc_info.get("args", {})

                        args_str = json.dumps(tool_args, ensure_ascii=False)
                        out_str = log_item.get("output", "")
                        terminal_output += f"$ [{idx}] Executing Skill: {tool_name}({args_str})\n"
                        terminal_output += f"{out_str}\n"
                        terminal_output += "-" * 50 + "\n"
                    st.code(terminal_output, language="bash")
                else:
                    st.code("$ No commands executed in virtual terminal yet.", language="bash")

        # ------------------------------------------
        # KHU VỰC 4: FINAL CODE PATCH & GIT DIFF VIEW
        # ------------------------------------------
        st.markdown("---")
        st.subheader("📝 4: Final Patch & Git Diff Code Review")
        
        import subprocess
        try:
            diff_res = subprocess.run(["git", "diff"], cwd=sandbox.workspace_path, capture_output=True, encoding="utf-8", errors="replace")
            patch_diff = diff_res.stdout
        except Exception:
            patch_diff = ""
            
        if patch_diff and patch_diff.strip():
            st.markdown("**Modified Code Patch (`git diff` Red/Green):**")
            st.code(patch_diff, language="diff")
        else:
            st.info("No git diff detected in workspace (or files were edited directly). Checking workspace files...")
            modified_file = final_state.get("current_file") if final_state else None
            if modified_file:
                file_path = os.path.join(sandbox.workspace_path, modified_file)
                if os.path.exists(file_path):
                    st.markdown(f"**Current Content of Modified File `{modified_file}`:**")
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        st.code(f.read(), language="python")

# ==========================================
# TAB 2: BENCHMARK ANALYTICS & FINANCIAL SAVINGS
# ==========================================
with tab_analytics:
    st.subheader("📈 CASS vs Baseline Financial Impact & Performance Savings")
    
    if os.path.exists(CSV_PATH):
        df_bench = pd.read_csv(CSV_PATH)
        
        # Ensure numeric columns are cast safely to numeric dtypes
        for num_col in ["Total Tokens", "Prompt Tokens", "Completion Tokens", "Latency (ms)", "Cost ($)"]:
            if num_col in df_bench.columns:
                df_bench[num_col] = pd.to_numeric(df_bench[num_col], errors="coerce").fillna(0)
                
        st.dataframe(df_bench, use_container_width=True)
        
        baseline_df = df_bench[df_bench["Scenario"] == "Baseline"]
        cass_df = df_bench[df_bench["Scenario"] == "CASS-Enabled"]
        
        avg_base_tokens = float(baseline_df["Total Tokens"].mean()) if not baseline_df.empty else 0.0
        avg_cass_tokens = float(cass_df["Total Tokens"].mean()) if not cass_df.empty else 0.0
        
        avg_base_lat = float(baseline_df["Latency (ms)"].mean()) if not baseline_df.empty else 0.0
        avg_cass_lat = float(cass_df["Latency (ms)"].mean()) if not cass_df.empty else 0.0
        
        token_savings_pct = ((avg_base_tokens - avg_cass_tokens) / avg_base_tokens * 100) if avg_base_tokens > 0 else 0
        speedup = (avg_base_lat / avg_cass_lat) if avg_cass_lat > 0 else 1.0
        
        st.markdown("### 💰 Financial & Efficiency Savings Summary")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        
        col_m1.metric("Avg Baseline Tokens", f"{avg_base_tokens:.0f} tokens")
        col_m2.metric("Avg CASS Tokens", f"{avg_cass_tokens:.0f} tokens")
        col_m3.metric("🎯 Token Reduction", f"{token_savings_pct:.1f}%", delta=f"-{token_savings_pct:.1f}%")
        col_m4.metric("⚡ Execution Speedup", f"{speedup:.1f}x Faster", delta=f"{speedup:.1f}x")
        
        st.markdown("---")
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            fig_donut, ax_d = plt.subplots(figsize=(4, 3))
            ax_d.pie(
                [avg_cass_tokens, max(0, avg_base_tokens - avg_cass_tokens)],
                labels=["CASS Tokens", "Saved Tokens"],
                colors=["#10B981", "#3B82F6"],
                autopct="%1.1f%%",
                startangle=90,
                wedgeprops=dict(width=0.4, edgecolor="w")
            )
            ax_d.set_title("Token Savings Distribution", fontsize=10, fontweight="bold")
            st.pyplot(fig_donut, use_container_width=True)
            
        with col_chart2:
            chart_file = "benchmark_comparison.png"
            if os.path.exists(chart_file):
                st.image(chart_file, caption="Benchmark Latency & Token Comparison Chart", use_container_width=True)
    else:
        st.info("No benchmark_results.csv found. Run benchmark_cass.py to generate analytics.")

# ==========================================
# TAB 3: SKILL STORE & ONLINE IMPORT TOOL
# ==========================================
with tab_import:
    st.subheader("📥 Skill Store & Dynamic Online Import")
    st.markdown("Easily inspect all registered skills, their **Formatted Scores**, and **import new SKILL.md files** directly from GitHub or web URLs.")
    
    col_store_left, col_store_right = st.columns([1.3, 1.0], gap="medium")
    
    with col_store_left:
        st.markdown("### 📚 Registered Skills & Formatted Metrics")
        
        # Build skill details dataframe
        skill_rows = []
        for s in all_skills:
            constraints_os = s.constraints.get("host", {}).get("os", ["Any"])
            skill_rows.append({
                "Skill Name": s.name,
                "Description": s.description[:80] + "...",
                "OS Constraints": ", ".join(constraints_os),
                "Category": getattr(s, "category", "universal/generic"),
                "Type": "Dynamic Markdown" if isinstance(s, DynamicMarkdownSkill) else "Legacy Static"
            })
        df_store = pd.DataFrame(skill_rows)
        st.dataframe(df_store, use_container_width=True, hide_index=True)
        
    with col_store_right:
        st.markdown("### 🌐 Import New Skill from Web / GitHub")
        st.caption("Provide a URL to a `SKILL.md` file or paste Markdown content directly below.")
        
        import_mode = st.radio("Import Source Mode", ["Import via URL", "Paste Markdown Text"], horizontal=True)
        
        if import_mode == "Import via URL":
            skill_url = st.text_input("GitHub / Web SKILL.md URL", placeholder="https://raw.githubusercontent.com/.../SKILL.md or https://github.com/.../SKILL.md")
            new_skill_folder = st.text_input("Target Folder Name", value="custom_imported_skill")
            
            if st.button("📥 Download & Register Skill", type="primary", use_container_width=True):
                if skill_url:
                    try:
                        clean_url = skill_url.strip()
                        # Auto-convert standard GitHub blob URLs to raw usercontent URLs
                        if "github.com" in clean_url and "/blob/" in clean_url:
                            clean_url = clean_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                            
                        resp = requests.get(clean_url, timeout=10)
                        resp.raise_for_status()
                        md_content = resp.text
                        
                        target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "skills", new_skill_folder.lower().replace("-", "_")))
                        os.makedirs(target_dir, exist_ok=True)
                        target_file = os.path.join(target_dir, "SKILL.md")
                        
                        with open(target_file, "w", encoding="utf-8") as f:
                            f.write(md_content)
                            
                        # Try parsing immediately to confirm validity
                        try:
                            temp_skill = DynamicMarkdownSkill(target_file, brain, tools)
                            st.success(f"✅ Skill '{temp_skill.name}' successfully imported & validated!")
                        except Exception as parse_ex:
                            st.warning(f"⚠️ Saved file to `skills/{new_skill_folder}/SKILL.md`, but metadata parsing fell back with warning: {parse_ex}")
                    except Exception as ex:
                        st.error(f"Failed to fetch skill from URL: {ex}")
                else:
                    st.warning("Please provide a valid URL.")
        else:
            pasted_name = st.text_input("Skill Directory Name", value="custom_pasted_skill")
            pasted_md = st.text_area("SKILL.md Content (YAML Frontmatter + Instructions)", height=220, value="""---
name: custom-pasted-skill
description: Custom dynamic skill imported via CASS Control Center UI.
version: 1.0.0
category: custom/demo
level: atomic
constraints:
  host:
    os:
    - windows
    - linux
    - darwin
---

## Instructions
1. Read the input files using `read_file`.
2. Apply changes using `edit_file`.
""")
            if st.button("📥 Save & Register Skill", type="primary", use_container_width=True):
                if pasted_md and pasted_name:
                    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "skills", pasted_name.lower().replace("-", "_")))
                    os.makedirs(target_dir, exist_ok=True)
                    target_file = os.path.join(target_dir, "SKILL.md")
                    
                    with open(target_file, "w", encoding="utf-8") as f:
                        f.write(pasted_md)
                        
                    st.success(f"✅ Skill saved to `skills/{pasted_name}/SKILL.md`!")
                    st.info("Reload page to index the new skill in CASS Vector Registry.")

    # 📜 SKILL SCRIPT & SOURCE CODE INSPECTOR
    st.markdown("---")
    st.subheader("📜 Skill Script & Source Code Inspector")
    st.caption("Select any registered skill below to inspect its full `SKILL.md` script, YAML frontmatter, and instructions.")
    
    inspect_skill_names = [s.name for s in all_skills]
    inspect_skill_name = st.selectbox("🔍 Select Skill to Inspect Code & Instructions", inspect_skill_names, index=0)
    inspect_skill = next((s for s in all_skills if s.name == inspect_skill_name), None)
    
    if inspect_skill:
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.markdown(f"**Skill Name**: `{inspect_skill.name}`")
        col_s2.markdown(f"**Category**: `{getattr(inspect_skill, 'category', 'generic')}`")
        os_c = inspect_skill.constraints.get("host", {}).get("os", ["Any"])
        col_s3.markdown(f"**OS Constraints**: `{os_c}`")
        
        st.markdown(f"**Description**: {inspect_skill.description}")



        if hasattr(inspect_skill, "filepath") and os.path.exists(inspect_skill.filepath):
            st.markdown(f"**File Location**: `{inspect_skill.filepath}`")
            with open(inspect_skill.filepath, "r", encoding="utf-8") as f:
                code_content = f.read()
            with st.container(height=350):
                st.code(code_content, language="markdown")
        else:
            st.info(f"Skill '{inspect_skill.name}' is a static Python class implementation.")
            st.code(inspect_skill.__doc__ or f"# Static Python implementation for {inspect_skill.name}", language="python")
