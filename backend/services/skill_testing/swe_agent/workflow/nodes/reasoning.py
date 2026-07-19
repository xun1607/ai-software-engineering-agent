from langchain_core.messages import HumanMessage

class ReasoningNode:
    """
    LangGraph node responsible for the Agent's reasoning process.
    Uses CASS to filter and bind optimized skills to the LLM model.
    """
    def __init__(self, brain, skills, cass_bridge):
        self.brain = brain
        self.skills = skills
        self.cass_bridge = cass_bridge

    def __call__(self, state):
        iteration = state.get("iteration_count", 0)
        session_id = state.get("session_id", "default_session")
        last_query = state['messages'][-1].content

        print(f"\n[Node: Reasoning] Iteration: {iteration}")

        # --- CASS SKILL SELECTION ---
        if self.cass_bridge:
            selected_skills = self.cass_bridge.get_optimized_skills(
                self.skills, session_id, last_query
            )
        else:
            selected_skills = self.skills
        
        # Convert selected CASS skills into standard OpenAI tool definitions for the LLM
        tools_for_llm = [s.to_openai_tool() for s in selected_skills]
            
        # Bind the optimized candidate tools to the LLM model
        model = self.brain.get_model().bind_tools(tools_for_llm)
        
        messages = list(state["messages"])
        if state.get("feedback"):
            messages.append(HumanMessage(content=f"Previous failure: {state['feedback']}"))
            
        response = model.invoke(messages)
        
        return {
            "messages": [response], 
            "iteration_count": iteration + 1
        }