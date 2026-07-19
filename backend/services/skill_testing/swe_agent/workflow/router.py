def edge_router(state):
    """decide next node based on validation chain result"""
    
    if state.get("is_valid"):
        print("✅ Verification Passed. Mission Accomplished.")
        return "end"
    
    # retry count available
    if state.get("iteration_count", 0) < 3:
        print(f"⚠️ Verification Failed. Retrying... (Attempt {state['iteration_count']}/3)")
        return "retry"
    
    # out of retries
    print("❌ Max retries reached. Task failed.")
    return "end"