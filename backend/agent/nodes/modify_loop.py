from backend.agent.state import State


def modify_loop_node(state: State) -> dict:
    """Increment modification count and route back to content_generation."""
    return {
        "enter_loop": True,
        "messages": [{
            "role": "user",
            "content": f"修改意见（第{state.get('modification_count', 1)}次）: {state.get('user_input_text', '')}",
        }],
    }
