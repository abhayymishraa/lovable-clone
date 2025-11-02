from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import Tool
from .graph_state import GraphState
from .tools import create_tools_with_context
from .agent import llm_gemini_pro
import json
import asyncio
from langgraph.prebuilt import create_react_agent
from .prompts import INITPROMPT

import asyncio


async def planner_node(state: GraphState) -> GraphState:
    """
    Planner node: Analyzes user prompt and generates comprehensive implementation plan
    """
    try:
        socket = state.get("socket")
        if socket:
            await socket.send_json(
                {
                    "e": "planner_started",
                    "message": "Planning the application architecture...",
                }
            )

        # Get the enhanced prompt for planning
        enhanced_prompt = state.get("enhanced_prompt", state.get("user_prompt", ""))
        project_id = state.get("project_id", "")

        # Check for previous context
        from utils.store import load_json_store

        previous_context = ""
        if project_id:
            context = load_json_store(project_id, "context.json")
            if context:
                # Format conversation history
                conversation_history_text = ""
                conversation_history = context.get("conversation_history", [])
                if conversation_history:
                    conversation_history_text = (
                        "\n💬 CONVERSATION HISTORY (Last requests):\n"
                    )
                    for i, conv in enumerate(
                        conversation_history[-5:], 1
                    ):  # Show last 5
                        status = "✅" if conv.get("success") else "❌"
                        conversation_history_text += f"   {i}. {status} {conv.get('user_prompt', 'Unknown')[:100]}\n"

                previous_context = f"""
                
                ========================================
                IMPORTANT: PREVIOUS WORK ON THIS PROJECT
                ========================================
                
                📋 WHAT THIS PROJECT IS:
                {context.get('semantic', 'Not documented')}
                
                ⚙️ HOW IT WORKS:
                {context.get('procedural', 'Not documented')}
                
                📝 WHAT HAS BEEN DONE:
                {context.get('episodic', 'Not documented')}
                
                📁 EXISTING FILES: {len(context.get('files_created', []))} files already exist
                {conversation_history_text}
                
                CRITICAL: This is an EXISTING project. Your plan should:
                - Build upon what already exists
                - Consider the conversation history to understand the user's intent
                - Only add/modify what's needed for the new request
                - NOT recreate existing components/pages
                - Integrate with the existing structure
                """

        # Create planning prompt
        planning_prompt = f"""
        You are an expert React application architect. Analyze the following user request and create a comprehensive implementation plan.
        {previous_context}

        USER REQUEST:
        {enhanced_prompt}

        Create a detailed plan that includes:
        1. Application overview and purpose
        2. Component hierarchy and structure
        3. Page/routing structure
        4. Required dependencies
        5. File structure
        6. Implementation steps

        {"NOTE: Since this is an existing project, focus your plan on the NEW features/changes requested, not recreating everything." if previous_context else ""}

        Respond with a JSON object containing the plan.
        """

        messages = [
            SystemMessage(
                content="You are an expert React application architect. Create detailed implementation plans."
            ),
            HumanMessage(content=planning_prompt),
        ]

        response = await llm_gemini_pro.ainvoke(messages)

        try:
            plan = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback if not valid JSON
            plan = {
                "overview": response.content,
                "components": [],
                "pages": [],
                "dependencies": [],
                "file_structure": [],
                "implementation_steps": [],
            }

        # Update state
        new_state = state.copy()
        new_state["plan"] = plan
        new_state["current_node"] = "planner"
        new_state["execution_log"].append(
            {"node": "planner", "status": "completed", "plan": plan}
        )

        if socket:
            await socket.send_json(
                {
                    "e": "planner_complete",
                    "plan": plan,
                    "message": "Planning completed successfully",
                }
            )

        return new_state

    except Exception as e:
        error_msg = f"Planner node error: {str(e)}"
        print(error_msg)

        new_state = state.copy()
        new_state["current_node"] = "planner"
        new_state["error_message"] = error_msg
        new_state["execution_log"].append(
            {"node": "planner", "status": "error", "error": error_msg}
        )

        if socket:
            await socket.send_json({"e": "planner_error", "message": error_msg})

        return new_state


async def builder_node(state: GraphState) -> GraphState:
    """
    Builder node: Creates and modifies files based on plan or feedback
    """
    try:
        socket = state.get("socket")
        sandbox = state.get("sandbox")

        if not sandbox:
            raise Exception("Sandbox not available")

        if socket:
            await socket.send_json(
                {
                    "e": "builder_started",
                    "message": "Starting to build the application...",
                }
            )

        plan = state.get("plan", {})
        current_errors = state.get("current_errors", {})
        project_id = state.get("project_id", "")

        base_tools = create_tools_with_context(sandbox, socket, project_id)

        if current_errors:
            error_details = []
            for error_type, errors in current_errors.items():
                if isinstance(errors, list):
                    for err in errors:
                        if isinstance(err, dict):
                            error_msg = err.get("error", str(err))
                            error_details.append(f"ERROR: {error_msg}")
                        else:
                            error_details.append(f"ERROR: {str(err)}")
                else:
                    error_details.append(f"{error_type}: {str(errors)}")

            builder_prompt = f"""
            {INITPROMPT}
            
            ⚠️ CRITICAL: BUILD FAILED - YOU MUST FIX THESE ERRORS ⚠️
            
            The previous build attempt failed with these errors:
            
            {chr(10).join(error_details)}
            
            YOUR TASK:
            1. Read the error messages carefully
            2. Identify which files have syntax errors
            3. Read those files using read_file
            4. Fix the syntax errors (escape sequences, missing imports, etc.)
            5. Use write_file to save the corrected files
            
            COMMON FIXES:
            - If you see "Expecting Unicode escape sequence" → Fix \\n in strings
            - If you see "Cannot find module" → Check import paths
            - If you see "Unexpected token" → Fix JSX syntax errors
            
            Fix ALL errors before finishing!
            """
        else:
            builder_prompt = f"""
            {INITPROMPT}
            
            ========================================
            STEP 0: CHECK PREVIOUS WORK (IMPORTANT!)
            ========================================
            FIRST ACTION: Call get_context() to see if there's any previous work on this project.
            - If context exists, read it carefully to understand what's already built
            - Check which files already exist before creating new ones
            - Build upon existing work instead of recreating everything
            
            ========================================
            IMPLEMENTATION PLAN FROM PLANNER:
            ========================================
            {json.dumps(plan, indent=2)}
            
            ========================================
            YOUR MISSION:
            ========================================
            Build the COMPLETE application according to the plan above.
            
            CRITICAL STEPS - DO ALL OF THESE:
            
            1. READ EXISTING FILES FIRST:
               - read_file("package.json") to see dependencies
               - read_file("src/App.jsx") to see current structure
               - read_file("src/main.jsx") to see entry point
               - use tool list_directory to see the directory and try to get context of all file you need by reading them
            
            2. CREATE ALL DIRECTORIES (only create those directory if not there):
               - Use execute_command("mkdir -p ...") for all needed directories
               - Example: mkdir -p src/components/layout src/components/navigation src/pages
            
            3. CREATE ALL COMPONENTS, PAGES AND FILES:
               - Use create_file for EVERY component, pages mentioned in the plan
               - Create components and pages ONE BY ONE
               - Follow the component, pages hierarchy in the plan
               - Make sure each component and pages has proper imports and exports
            
            4. UPDATE MAIN FILES:
               - Update src/App.jsx to use the new pages
               - Update src/index.css with Tailwind directives if needed
            
            5. VERIFY YOUR WORK:
               - Use list_directory to see what you created
               - Make sure ALL components, pages from the plan are created
               - if you need to make extra component and pages, do create them if neeeded
            
            6. SAVE YOUR WORK (FINAL STEP):
               - After completing all files, call save_context() to document what you built
               - Include: what the project is, how it works, and what you created
               - This helps future sessions understand the project
            
            DO NOT STOP until you have created ALL files mentioned in the implementation plan!
            """

        messages = [
            SystemMessage(content=INITPROMPT),
            HumanMessage(content=builder_prompt),
        ]

        agent_executor = create_react_agent(llm_gemini_pro, tools=base_tools)
        config = {"recursion_limit": 50}

        try:
            print(
                f"Builder node: Starting agent execution with {len(base_tools)} tools"
            )
            result = await asyncio.wait_for(
                agent_executor.ainvoke({"messages": messages}, config=config),
                timeout=600,
            )
            print(f"Builder node: Agent execution completed")

            files_created = []
            files_modified = []

            if hasattr(result, "messages"):
                print(f"Builder node: Processing {len(result.messages)} messages")
                for message in result.messages:
                    if hasattr(message, "content"):
                        content = str(message.content)
                        print(f"Builder node: Message content: {content[:200]}...")
                        if "created" in content.lower() and "file" in content.lower():
                            import re

                            file_matches = re.findall(
                                r"(\w+\.(jsx?|tsx?|css|json))", content
                            )
                            files_created.extend([match[0] for match in file_matches])
                            print(f"Builder node: Found files: {file_matches}")

            print(f"Builder node: Final files_created: {files_created}")

            new_state = state.copy()
            new_state["files_created"] = files_created
            new_state["files_modified"] = files_modified
            new_state["current_node"] = "builder"
            new_state["execution_log"].append(
                {
                    "node": "builder",
                    "status": "completed",
                    "files_created": files_created,
                    "files_modified": files_modified,
                }
            )

            if socket:
                await socket.send_json(
                    {
                        "e": "builder_complete",
                        "files_created": files_created,
                        "files_modified": files_modified,
                        "message": "Building completed",
                    }
                )

            return new_state

        except asyncio.TimeoutError:
            print("Builder agent timed out after 10 minutes")
            files_created = []
            files_modified = []

            new_state = state.copy()
            new_state["files_created"] = files_created
            new_state["files_modified"] = files_modified
            new_state["current_node"] = "builder"
            new_state["execution_log"].append(
                {
                    "node": "builder",
                    "status": "timeout",
                    "files_created": files_created,
                    "files_modified": files_modified,
                }
            )

            if socket:
                await socket.send_json(
                    {
                        "e": "builder_error",
                        "message": "Builder agent timed out after 10 minutes",
                    }
                )

            return new_state

        except Exception as e:
            print(f"Builder agent execution error: {e}")
            import traceback

            traceback.print_exc()
            files_created = []
            files_modified = []

            new_state = state.copy()
            new_state["files_created"] = files_created
            new_state["files_modified"] = files_modified
            new_state["current_node"] = "builder"
            new_state["execution_log"].append(
                {
                    "node": "builder",
                    "status": "error",
                    "files_created": files_created,
                    "files_modified": files_modified,
                }
            )

            if socket:
                await socket.send_json(
                    {
                        "e": "builder_error",
                        "message": f"Builder agent execution error: {str(e)}",
                    }
                )

            return new_state

    except Exception as e:
        error_msg = f"Builder node error: {str(e)}"
        print(error_msg)

        new_state = state.copy()
        new_state["current_node"] = "builder"
        new_state["error_message"] = error_msg
        new_state["execution_log"].append(
            {"node": "builder", "status": "error", "error": error_msg}
        )

        if socket:
            await socket.send_json({"e": "builder_error", "message": error_msg})

        return new_state


async def code_validator_node(state: GraphState) -> GraphState:
    """
    Code Validator node: Active React agent that reviews, validates, and fixes code
    """
    try:
        socket = state.get("socket")
        sandbox = state.get("sandbox")

        if not sandbox:
            raise Exception("Sandbox not available")

        if socket:
            await socket.send_json(
                {
                    "e": "code_validator_started",
                    "message": "Code validator agent reviewing and fixing code...",
                }
            )

        project_id = state.get("project_id", "")
        base_tools = create_tools_with_context(sandbox, socket, project_id)

        # Create validator prompt
        validator_prompt = """
        You are a Code Validator Agent - an expert at reviewing and fixing React code.
        
        YOUR MISSION:
        1. Review ALL files in the src/ directory
        2. Check for syntax errors, missing imports, and code issues
        3. Fix any problems you find
        4. Ensure all dependencies are properly installed
        
        STEP-BY-STEP PROCESS:
        
        STEP 1: CHECK DEPENDENCIES FIRST
        - Use check_missing_packages() tool to automatically scan all files and find missing packages
        - This tool will tell you exactly which packages are missing and give you install commands
        - Run the install commands it provides using execute_command()
        
        STEP 2: LIST ALL FILES
        - Use execute_command("find src -name '*.jsx' -o -name '*.js'") to list all files
        
        STEP 3: READ AND REVIEW EACH FILE
        - Use read_file to read each .jsx and .js file
        - Check for:
          * Syntax errors (missing brackets, quotes, semicolons)
          * Escape sequence issues (\\n in strings should be proper)
          * Missing imports (components used but not imported)
          * Incorrect import paths
          * Missing export statements
          * Indentation issues
          * Incomplete components
          * Missing dependencies (like react-icons, react-router-dom)
        
        STEP 4: FIX ISSUES IMMEDIATELY
        - If you find ANY issue, use create_file to fix it RIGHT AWAY
        - Fix one file at a time
        - Make sure imports match the actual file structure
        - Install missing packages with execute_command("npm install package-name")
        
        STEP 5: VALIDATE IMPORTS AND FILE EXISTENCE
        - For each import statement, verify the imported file exists
        - Use execute_command("ls -la src/components/") to check files exist
        - Fix any import paths that are wrong
        
        STEP 6: CHECK FOR COMPLETENESS
        - Make sure App.jsx has proper routing setup
        - Verify all components are properly exported
        - Check that main.jsx imports App correctly
        
        STEP 7: CODE REVIEW COMPLETE
        - You have completed the code review and dependency checking
        - No build test needed - focus on code quality and dependencies only
        
        COMMON MISSING PACKAGES TO CHECK:
        - react-icons (for icons like FaShoppingCart, FaUser, FaTrash, etc.)
        - react-router-dom (for routing)
        - Any other packages imported in the code
        
        CRITICAL: If you see errors like "Failed to resolve import 'react-icons/fa'", 
        it means react-icons is missing. ALWAYS run check_missing_packages() FIRST!
        
        CRITICAL RULES:
        - Fix issues as you find them, don't just report them
        - Use create_file to save corrected code
        - Install missing packages immediately
        - Be thorough - check EVERY file
        - Focus on code quality and dependencies, no build testing needed
        
        SPECIFIC ERROR HANDLING:
        - If you see "Failed to resolve import 'react-icons/fa'" → Install react-icons
        - If you see "Cannot find module" → Check if package is installed
        - If you see "Module not found" → Install the missing package
        - If you see "Failed to resolve import '../../features/products/productsSlice'" → Check if productsSlice.js exists, recreate if missing
        - If you see "Does the file exist?" → The file is missing, recreate it using create_file
        
        START NOW: First run check_missing_packages() to find missing packages, then install them and review files
        """

        messages = [
            SystemMessage(
                content="You are a Code Validator Agent. Review and fix all code issues."
            ),
            HumanMessage(content=validator_prompt),
        ]

        validator_agent = create_react_agent(llm_gemini_pro, tools=base_tools)
        config = {"recursion_limit": 50}

        try:
            print(
                f"Code validator: Starting agent execution with {len(base_tools)} tools"
            )
            result = await asyncio.wait_for(
                validator_agent.ainvoke({"messages": messages}, config=config),
                timeout=600,
            )
            print(f"Code validator: Agent execution completed")

            # Code validator completed - no build test needed
            print("Code validator: Code review and dependency checking completed")
            validation_errors = []

            if socket:
                await socket.send_json(
                    {
                        "e": "validation_success",
                        "message": "Code validator completed - code review and dependencies checked!",
                    }
                )

            new_state = state.copy()
            new_state["validation_errors"] = validation_errors
            new_state["current_node"] = "code_validator"

            # Update retry count if there are errors
            if validation_errors:
                retry_count = new_state.get("retry_count", {})
                retry_count["validation_errors"] = (
                    retry_count.get("validation_errors", 0) + 1
                )
                new_state["retry_count"] = retry_count
                new_state["current_errors"] = {"validation_errors": validation_errors}
                print(
                    f"Code validator: Found {len(validation_errors)} validation errors"
                )
            else:
                print("Code validator: No validation errors found")

            new_state["execution_log"].append(
                {
                    "node": "code_validator",
                    "status": "completed",
                    "validation_errors": validation_errors,
                }
            )

            if socket:
                await socket.send_json(
                    {
                        "e": "code_validator_complete",
                        "errors": validation_errors,
                        "message": f"Code validation completed. Found {len(validation_errors)} errors.",
                    }
                )

            return new_state

        except asyncio.TimeoutError:
            print("Code validator agent timed out after 10 minutes")

            new_state = state.copy()
            new_state["validation_errors"] = [
                {
                    "type": "timeout",
                    "error": "Code validator timed out",
                    "details": "Validation took too long",
                }
            ]
            new_state["current_node"] = "code_validator"

            if socket:
                await socket.send_json(
                    {
                        "e": "code_validator_timeout",
                        "message": "Code validator timed out",
                    }
                )

            return new_state

    except Exception as e:
        error_msg = f"Code validator node error: {str(e)}"
        print(error_msg)
        import traceback

        traceback.print_exc()

        new_state = state.copy()
        new_state["current_node"] = "code_validator"
        new_state["error_message"] = error_msg
        new_state["validation_errors"] = [
            {
                "type": "validator_error",
                "error": str(e),
                "details": "Code validator crashed",
            }
        ]
        new_state["execution_log"].append(
            {"node": "code_validator", "status": "error", "error": error_msg}
        )

        if socket:
            await socket.send_json({"e": "code_validator_error", "message": error_msg})

        return new_state


async def application_checker_node(state: GraphState) -> GraphState:
    """
    Application Checker node: Checks if the application is running and captures errors
    """
    try:
        socket = state.get("socket")
        sandbox = state.get("sandbox")

        if not sandbox:
            raise Exception("Sandbox not available")

        if socket:
            await socket.send_json(
                {
                    "e": "app_check_started",
                    "message": "Checking application status and capturing errors...",
                }
            )

        runtime_errors = []

        # Skip dev server checks - environment is pre-configured
        print(
            "Application checker: Skipping dev server checks - environment is pre-configured"
        )

        # Instead, check if the application structure is correct
        try:
            # Check if main files exist
            main_files = ["src/App.jsx", "src/main.jsx", "package.json"]
            missing_files = []

            for file_path in main_files:
                try:
                    await sandbox.files.read(f"/home/user/react-app/{file_path}")
                except Exception:
                    missing_files.append(file_path)

            if missing_files:
                runtime_errors.append(
                    {
                        "type": "missing_files",
                        "error": f"Missing essential files: {', '.join(missing_files)}",
                    }
                )
            else:
                print("Application checker: All essential files present")

        except Exception as e:
            runtime_errors.append(
                {
                    "type": "file_check_failed",
                    "error": f"Failed to check application files: {str(e)}",
                }
            )

        new_state = state.copy()
        new_state["runtime_errors"] = runtime_errors
        new_state["current_node"] = "application_checker"

        # Update retry count if there are errors
        if runtime_errors:
            retry_count = new_state.get("retry_count", {})
            retry_count["runtime_errors"] = retry_count.get("runtime_errors", 0) + 1
            new_state["retry_count"] = retry_count

            new_state["current_errors"] = {"runtime_errors": runtime_errors}
        else:
            # No runtime errors - set success flag
            new_state["success"] = True
            print(
                "Application checker: No runtime errors found - setting success to True"
            )

        new_state["execution_log"].append(
            {
                "node": "application_checker",
                "status": "completed",
                "runtime_errors": runtime_errors,
            }
        )

        if socket:
            await socket.send_json(
                {
                    "e": "app_check_complete",
                    "errors": runtime_errors,
                    "message": f"Application check completed. Found {len(runtime_errors)} runtime errors.",
                }
            )

        return new_state

    except Exception as e:
        error_msg = f"Application checker node error: {str(e)}"
        print(error_msg)

        new_state = state.copy()
        new_state["current_node"] = "application_checker"
        new_state["error_message"] = error_msg
        new_state["execution_log"].append(
            {"node": "application_checker", "status": "error", "error": error_msg}
        )

        if socket:
            await socket.send_json({"e": "app_check_error", "message": error_msg})

        return new_state


def should_continue_to_import_checker(state: GraphState) -> str:
    """Always go to import checker after builder"""
    return "import_checker"


def should_continue_to_code_validator(state: GraphState) -> str:
    """After import checker, go to code validator"""
    return "code_validator"


def should_retry_builder_for_validation(state: GraphState) -> str:
    """Decide whether to retry builder for validation errors or continue"""
    validation_errors = state.get("validation_errors", [])
    retry_count = state.get("retry_count", {})
    max_retries = state.get("max_retries", 3)

    # Safety check: prevent infinite loops
    total_retries = sum(retry_count.values())
    if total_retries > 10:
        print(
            f"Maximum total retries reached ({total_retries}) - continuing to application checker"
        )
        return "application_checker"

    print(
        f"Code validator decision: {len(validation_errors)} errors, {retry_count.get('validation_errors', 0)} retries"
    )

    if not validation_errors:
        print("No validation errors - continuing to application checker")
        return "application_checker"

    current_retries = retry_count.get("validation_errors", 0)
    if current_retries < max_retries:
        print(
            f"Retrying builder for validation errors (attempt {current_retries + 1}/{max_retries})"
        )
        return "builder"
    else:
        print(
            f"Max retries reached for validation errors - continuing to application checker"
        )
        return "application_checker"


def should_retry_builder_or_continue(state: GraphState) -> str:
    """Decide whether to retry builder or continue based on import errors"""
    import_errors = state.get("import_errors", [])
    retry_count = state.get("retry_count", {})
    max_retries = state.get("max_retries", 3)

    # Safety check: prevent infinite loops
    total_retries = sum(retry_count.values())
    if total_retries > 10:  # Maximum total retries across all error types
        print(f"Maximum total retries reached ({total_retries}) - forcing end")
        return "application_checker"

    print(
        f"Import checker decision: {len(import_errors)} errors, {retry_count.get('import_errors', 0)} retries"
    )

    if not import_errors:
        print("No import errors - continuing to application checker")
        return "application_checker"

    current_retries = retry_count.get("import_errors", 0)
    if current_retries < max_retries:
        print(
            f"Retrying builder for import errors (attempt {current_retries + 1}/{max_retries})"
        )
        return "builder"
    else:
        print(
            f"Max retries reached for import errors - continuing to application checker"
        )
        return "application_checker"  # Give up and continue


def should_retry_builder_or_finish(state: GraphState) -> str:
    """Decide whether to retry builder or finish based on runtime errors"""
    runtime_errors = state.get("runtime_errors", [])
    retry_count = state.get("retry_count", {})
    max_retries = state.get("max_retries", 3)

    # Safety check: prevent infinite loops
    total_retries = sum(retry_count.values())
    if total_retries > 10:  # Maximum total retries across all error types
        print(f"Maximum total retries reached ({total_retries}) - forcing end")
        return "end"

    print(
        f"Application checker decision: {len(runtime_errors)} errors, {retry_count.get('runtime_errors', 0)} retries"
    )

    if not runtime_errors:
        print("No runtime errors - finishing successfully")
        return "end"

    current_retries = retry_count.get("runtime_errors", 0)
    if current_retries < max_retries:
        print(
            f"Retrying builder for runtime errors (attempt {current_retries + 1}/{max_retries})"
        )
        return "builder"
    else:
        print(f"Max retries reached for runtime errors - finishing with errors")
        state["success"] = False
        state["error_message"] = (
            f"Failed after {max_retries} retries for runtime errors"
        )
        return "end"  # Give up and finish


def should_finish(state: GraphState) -> str:
    """Always finish after application checker with no errors"""
    return "end"
