from langgraph.graph import StateGraph, END
from .graph_state import GraphState
from .graph_nodes import (
    planner_node,
    builder_node,
    code_validator_node,
    application_checker_node,
    should_retry_builder_for_validation,
    should_retry_builder_or_finish
)
from typing import Dict, Any


def create_langgraph_workflow():
    """
    Create and compile the LangGraph workflow for the multi-agent system
    
    Workflow:
    1. Planner → Creates implementation plan
    2. Builder → Creates all files
    3. Code Validator → Checks for syntax/build errors
       - If errors → Back to Builder
       - If no errors → Continue
    4. Application Checker → Verifies application
       - If errors → Back to Builder
       - If no errors → Success
    """
    
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
        {
            "builder": "builder",
            "application_checker": "application_checker"
        }
    )
    
    # Application checker can retry builder or finish
    workflow.add_conditional_edges(
        "application_checker",
        should_retry_builder_or_finish,
        {
            "builder": "builder",
            "end": END
        }
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
            initial_state: Initial state for the workflow
            
        Returns:
            Final state after workflow execution
        """
        try:
            # Initialize state with defaults
            state = {
                "user_prompt": "",
                "enhanced_prompt": "",
                "plan": None,
                "files_created": [],
                "files_modified": [],
                "current_errors": {},
                "import_errors": [],
                "validation_errors": [],
                "runtime_errors": [],
                "retry_count": {"import_errors": 0, "validation_errors": 0, "runtime_errors": 0},
                "max_retries": 3,
                "sandbox": None,
                "socket": None,
                "messages": [],
                "current_node": "",
                "execution_log": [],
                "success": False,
                "final_url": None,
                "error_message": None,
                **initial_state
            }
            
            # Run the workflow
            final_state = await self.app.ainvoke(state)
            
            return final_state
            
        except Exception as e:
            print(f"Workflow execution error: {e}")
            # Return error state
            return {
                **initial_state,
                "success": False,
                "error_message": str(e),
                "execution_log": [{"node": "workflow", "status": "error", "error": str(e)}]
            }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """
        Get information about the workflow structure
        
        Returns:
            Dictionary with workflow information
        """
        return {
            "nodes": ["planner", "builder", "code_validator", "application_checker"],
            "entry_point": "planner",
            "end_points": ["end"],
            "retry_logic": {
                "validation_errors": "max 3 retries",
                "runtime_errors": "max 3 retries"
            },
            "flow": "planner → builder → code_validator → application_checker → end",
            "feedback_loops": [
                "code_validator → builder (on validation errors)",
                "application_checker → builder (on runtime errors)"
            ]
        }


# Create the main workflow instance
langgraph_workflow = LangGraphWorkflow()


def get_workflow() -> LangGraphWorkflow:
    """
    Get the main workflow instance
    
    Returns:
        LangGraphWorkflow instance
    """
    return langgraph_workflow
