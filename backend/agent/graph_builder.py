from langgraph.graph import StateGraph, END
from .graph_state import GraphState
from .graph_nodes import (
    planner_node,
    builder_node,
    code_validator_node,
    application_checker_node,
    should_retry_builder_for_validation,
    should_retry_builder_or_finish,
)
from typing import Dict, Any


def create_langgraph_workflow():
    """Returns the LangGraph workflow for the multi-agent system"""

    # Create the state graph
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("builder", builder_node)
    workflow.add_node("code_validator", code_validator_node)
    workflow.add_node("application_checker", application_checker_node)

    # Set entry point
    workflow.set_entry_point("planner")

    # Add edges with retry logic
    workflow.add_edge("planner", "builder")
    workflow.add_edge("builder", "code_validator")

    # Code validator can retry builder or continue to app checker
    workflow.add_conditional_edges(
        "code_validator",
        should_retry_builder_for_validation,
        {"builder": "builder", "application_checker": "application_checker"},
    )

    # Application checker can retry builder or finish
    workflow.add_conditional_edges(
        "application_checker",
        should_retry_builder_or_finish,
        {"builder": "builder", "end": END},
    )

    # Compile the workflow
    app = workflow.compile()

    return app


class LangGraphWorkflow:
    """
    Wrapper class for the LangGraph workflow with additional functionality
    """

    def __init__(self):
        self.app = create_langgraph_workflow()

    async def run_workflow(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the workflow with the given initial state

        Args:
            initial_state: Initial state for the workflow (must match GraphState schema)

        Returns:
            Final state after workflow execution
        """
        try:
            # LangGraph handles state management based on GraphState TypedDict
            final_state = await self.app.ainvoke(initial_state)
            return final_state

        except Exception as e:
            print(f"Workflow execution error: {e}")
            # Return error state
            return {
                **initial_state,
                "success": False,
                "error_message": str(e),
                "execution_log": [
                    {"node": "workflow", "status": "error", "error": str(e)}
                ],
            }

langgraph_workflow = LangGraphWorkflow()


def get_workflow() -> LangGraphWorkflow:
    """
    Get the main workflow instance

    Returns:
        LangGraphWorkflow instance
    """
    return langgraph_workflow
