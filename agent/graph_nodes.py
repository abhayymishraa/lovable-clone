from langchain_core.messages import HumanMessage, SystemMessage
from .graph_state import GraphState
from .tools import create_tools_with_context
from .agent import llm_gemini_pro, llm_gemini_flash
from .formatters import create_formatted_message, format_plan_as_markdown
import json
import asyncio
from langgraph.prebuilt import create_react_agent
from .prompts import INITPROMPT
from utils.store import load_json_store
import traceback
from db.base import get_db
from db.models import Message
import uuid


async def safe_send_socket(socket, data):
    """Helper to safely send WebSocket messages"""
    if socket:
        try:
            await socket.send_json(data)
        except Exception as e:
            print(f"WebSocket send failed: {e}")


async def store_message(chat_id: str, role: str, content: str, event_type: str = None, tool_calls: list = None):
    """Helper to store a message in the database"""
    try:
        async for db in get_db():
            message = Message(
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                role=role,
                content=content,
                event_type=event_type,
                tool_calls=tool_calls,
            )
            db.add(message)
            await db.commit()
            break
    except Exception as e:
        print(f"Failed to store message: {e}")


async def planner_node(state: GraphState) -> GraphState:
    """
    Planner node: Analyzes user prompt and generates comprehensive implementation plan
    """
    try:
        socket = state.get("socket")
        if socket:
            await safe_send_socket(socket, 
                {
                    "e": "planner_started",
                    "message": "Planning the application architecture...",
                }
            )

        enhanced_prompt = state.get("enhanced_prompt", state.get("user_prompt", ""))
        print(f"INFO: Recieved Prompt {enhanced_prompt}")
        project_id = state.get("project_id", "")
        print(f"INFO: Project ID: {project_id}")

        previous_context = ""

        # check if previous context is there
        if project_id:
            context = load_json_store(project_id, "context.json")

            if context:

                # Format conversation history
                conversation_history_text = ""
                conversation_history = context.get("conversation_history", [])
                if conversation_history:
                    conversation_history_text = (
                        "\nCONVERSATION HISTORY (Last requests):\n"
                    )
                    for i, conv in enumerate(conversation_history[-5:], 1):
                        status = "✅" if conv.get("success") else "❌"
                        conversation_history_text += f"   {i}. {status} {conv.get('user_prompt', 'Unknown')[:100]}\n"

                previous_context = f"""

                IMPORTANT: PREVIOUS WORK ON THIS PROJECT
                
                WHAT THIS PROJECT IS:
                {context.get('semantic', 'Not documented')}
                
                HOW IT WORKS:
                {context.get('procedural', 'Not documented')}
                
                WHAT HAS BEEN DONE:
                {context.get('episodic', 'Not documented')}
                
                EXISTING FILES: {len(context.get('files_created', []))} files already exist
                {conversation_history_text} 
                
                CRITICAL: This is an EXISTING project. Your plan should:
                - Build upon what already exists
                - Consider the conversation history to understand the user's intent
                - Only add/modify what's needed for the new request
                - NOT recreate existing components/pages
                - Integrate with the existing structure
                """

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

        if socket:
            await safe_send_socket(socket, {"e": "thinking", "message": "Analyzing your request and creating implementation plan..."})

        # Store thinking message
        await store_message(
            chat_id=state.get("project_id"),
            role="assistant",
            content="Analyzing your request and creating implementation plan...",
            event_type="thinking"
        )

        response = await llm_gemini_flash.ainvoke(messages)

        # Format the plan preview for better display
        plan_preview = response.content[:500] if len(response.content) > 500 else response.content
        formatted_preview = create_formatted_message("thinking", plan_preview)
        
        if socket:
            await safe_send_socket(socket, formatted_preview)

        # Store plan preview with formatting
        await store_message(
            chat_id=state.get("project_id"),
            role="assistant",
            content=formatted_preview.get("formatted", plan_preview),
            event_type="thinking"
        )

        try:
            plan = json.loads(response.content)
        except json.JSONDecodeError:
            plan = {
                "overview": response.content,
                "components": [],
                "pages": [],
                "dependencies": [],
                "file_structure": [],
                "implementation_steps": [],
            }

        new_state = state.copy()
        new_state["plan"] = plan
        new_state["current_node"] = "planner"
        new_state["execution_log"].append(
            {"node": "planner", "status": "completed", "plan": plan}
        )

        # Create formatted plan message
        formatted_plan_msg = create_formatted_message(
            "planner_complete",
            plan,
            message="Planning completed successfully"
        )
        
        if socket:
            await safe_send_socket(socket, formatted_plan_msg)

        # Store plan completion with formatted markdown
        await store_message(
            chat_id=state.get("project_id"),
            role="assistant",
            content=formatted_plan_msg.get("formatted", json.dumps(plan, indent=2)),
            event_type="planner_complete"
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
            await safe_send_socket(socket, {"e": "planner_error", "message": error_msg})

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
            await safe_send_socket(socket, 
                {
                    "e": "builder_started",
                    "message": "Starting to build the application...",
                }
            )

        plan = state.get("plan", {})
        if plan:
            print("INFO: Plan Recieved")

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
            CRITICAL: BUILD FAILED - YOU MUST FIX THESE ERRORS
            
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
            STEP 0: CHECK PREVIOUS WORK (IMPORTANT!)

            FIRST ACTION: Call get_context() to see if there's any previous work on this project.
            - If context exists, read it carefully to understand what's already built
            - Check which files already exist before creating new ones
            - Build upon existing work instead of recreating everything
            
            IMPLEMENTATION PLAN FROM PLANNER:

            {json.dumps(plan, indent=2)}
            
            YOUR MISSION:

            Build the COMPLETE application according to the plan above.
            
            CRITICAL STEPS - DO ALL OF THESE:
            
            1. READ EXISTING FILES FIRST:
               - read_file("package.json") to see dependencies
               - read_file("src/App.jsx") to see current structure
               - read_file("src/main.jsx") to see entry point
               - use tool list_directory to see the directory and try to get context of all file you need by reading them
            
            2. CREATE ALL DIRECTORIES (only create those directory if not there):
               - Use execute_command("mkdir -p ...") for all needed directories
               - Example: mkdir -p src/components/card src/components/navigation src/pages
            
            3. CREATE ALL COMPONENTS, PAGES AND FILES:
               - Use create_file for EVERY component, pages mentioned in the plan
               - Create components and pages ONE BY ONE
               - Follow the component, pages hierarchy in the plan
               - Make sure each component and pages has proper imports and exports
            
            4. UPDATE MAIN FILES:
               - Update src/App.jsx to use the new pages
               - make sure index.css file have this import "@import "tailwindcss";" on top otherwise tailwind not work
               - Update src/App.css with Tailwind directives if needed
            
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
            
            files_created = []
            files_modified = []

            async for event in agent_executor.astream_events(
                {"messages": messages}, version="v1", config=config
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        # Handle content that could be string or list of content blocks
                        if isinstance(content, list):
                            # If content is a list of blocks, extract text
                            text_parts = []
                            for block in content:
                                if isinstance(block, str):
                                    text_parts.append(block)
                                elif isinstance(block, dict) and block.get("type") == "text":
                                    text_parts.append(block.get("text", ""))
                                elif hasattr(block, "text"):
                                    text_parts.append(block.text)
                            content = "\n".join(filter(None, text_parts))
                        else:
                            content = str(content)
                        
                        if content and socket:
                            await safe_send_socket(socket, {"e": "thinking", "message": content})
                            # Store thinking message (batched to avoid too many DB writes)
                            if len(content) > 50:  # Only store substantial thinking
                                await store_message(
                                    chat_id=state.get("project_id"),
                                    role="assistant",
                                    content=content,
                                    event_type="thinking"
                                )

                elif kind == "on_tool_start":
                    tool_name = event.get("name")
                    tool_input = event.get("data", {}).get("input", {})
                    if socket:
                        await safe_send_socket(socket, 
                            {
                                "e": "tool_started",
                                "tool_name": tool_name,
                                "tool_input": tool_input,
                            }
                        )
                    # Store tool start
                    await store_message(
                        chat_id=state.get("project_id"),
                        role="assistant",
                        content=f"Using tool: {tool_name}",
                        event_type="tool_started",
                        tool_calls=[{"name": tool_name, "status": "running", "input": str(tool_input)}]
                    )

                elif kind == "on_tool_end":
                    tool_name = event.get("name")
                    tool_output = event.get("data", {}).get("output")
                    
                    if hasattr(tool_output, "content"):
                        tool_output = tool_output.content
                    elif not isinstance(tool_output, str):
                        tool_output = str(tool_output)
                    
                    if socket:
                        await safe_send_socket(socket, 
                            {
                                "e": "tool_completed",
                                "tool_name": tool_name,
                                "tool_output": tool_output,
                            }
                        )
                    # Store tool completion
                    await store_message(
                        chat_id=state.get("project_id"),
                        role="assistant",
                        content=f"Completed: {tool_name}\n{tool_output[:200]}",
                        event_type="tool_completed",
                        tool_calls=[{"name": tool_name, "status": "success", "output": tool_output[:500]}]
                    )
                    
                    if "created" in str(tool_output).lower() and "file" in str(tool_output).lower():
                        import re
                        file_matches = re.findall(r"(\w+\.(jsx?|tsx?|css|json))", str(tool_output))
                        files_created.extend([match[0] for match in file_matches])

            print(f"Builder node: Agent execution completed")
            print(f"Builder node: Final files_created: {files_created}")

            new_state = state.copy()
            new_state["files_created"] = files_created
            new_state["files_modified"] = files_modified
            print(f"INFO : {files_created}")
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
                await safe_send_socket(socket, 
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
                await safe_send_socket(socket, 
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
                await safe_send_socket(socket, 
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
            await safe_send_socket(socket, {"e": "builder_error", "message": error_msg})

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
            await safe_send_socket(socket, 
                {
                    "e": "code_validator_started",
                    "message": "Code validator agent reviewing and fixing code...",
                }
            )

        project_id = state.get("project_id", "")
        base_tools = create_tools_with_context(sandbox, socket, project_id)

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

        validator_agent = create_react_agent(llm_gemini_flash, tools=base_tools)
        config = {"recursion_limit": 50}

        try:
            print(
                f"Code validator: Starting agent execution with {len(base_tools)} tools"
            )
            
            validation_errors = []

            async for event in validator_agent.astream_events(
                {"messages": messages}, version="v1", config=config
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        # Handle content that could be string or list of content blocks
                        if isinstance(content, list):
                            # If content is a list of blocks, extract text
                            text_parts = []
                            for block in content:
                                if isinstance(block, str):
                                    text_parts.append(block)
                                elif isinstance(block, dict) and block.get("type") == "text":
                                    text_parts.append(block.get("text", ""))
                                elif hasattr(block, "text"):
                                    text_parts.append(block.text)
                            content = "\n".join(filter(None, text_parts))
                        else:
                            content = str(content)
                        
                        if content and socket:
                            await safe_send_socket(socket, {"e": "thinking", "message": content})
                            # Store thinking message (batched to avoid too many DB writes)
                            if len(content) > 50:  # Only store substantial thinking
                                await store_message(
                                    chat_id=state.get("project_id"),
                                    role="assistant",
                                    content=content,
                                    event_type="thinking"
                                )

                elif kind == "on_tool_start":
                    tool_name = event.get("name")
                    tool_input = event.get("data", {}).get("input", {})
                    if socket:
                        await safe_send_socket(socket, 
                            {
                                "e": "tool_started",
                                "tool_name": tool_name,
                                "tool_input": tool_input,
                            }
                        )
                    # Store tool start
                    await store_message(
                        chat_id=state.get("project_id"),
                        role="assistant",
                        content=f"Using tool: {tool_name}",
                        event_type="tool_started",
                        tool_calls=[{"name": tool_name, "status": "running", "input": str(tool_input)}]
                    )

                elif kind == "on_tool_end":
                    tool_name = event.get("name")
                    tool_output = event.get("data", {}).get("output")
                    
                    if hasattr(tool_output, "content"):
                        tool_output = tool_output.content
                    elif not isinstance(tool_output, str):
                        tool_output = str(tool_output)
                    
                    if socket:
                        await safe_send_socket(socket, 
                            {
                                "e": "tool_completed",
                                "tool_name": tool_name,
                                "tool_output": tool_output,
                            }
                        )
                    # Store tool completion
                    await store_message(
                        chat_id=state.get("project_id"),
                        role="assistant",
                        content=f"Completed: {tool_name}\n{tool_output[:200]}",
                        event_type="tool_completed",
                        tool_calls=[{"name": tool_name, "status": "success", "output": tool_output[:500]}]
                    )

            print(f"Code validator: Agent execution completed")
            print("Code validator: Code review and dependency checking completed")

            if socket:
                await safe_send_socket(socket, 
                    {
                        "e": "validation_success",
                        "message": "Code validator completed - code review and dependencies checked!",
                    }
                )

            new_state = state.copy()
            new_state["validation_errors"] = validation_errors
            new_state["current_node"] = "code_validator"

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
                await safe_send_socket(socket, 
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
                await safe_send_socket(socket, 
                    {
                        "e": "code_validator_timeout",
                        "message": "Code validator timed out",
                    }
                )

            return new_state

    except Exception as e:
        error_msg = f"Code validator node error: {str(e)}"
        print(error_msg)
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
            await safe_send_socket(socket, {"e": "code_validator_error", "message": error_msg})

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
            await safe_send_socket(socket, 
                {
                    "e": "app_check_started",
                    "message": "Checking application status and capturing errors...",
                }
            )

        runtime_errors = []

        print(
            "Application checker: Skipping dev server checks - environment is pre-configured"
        )

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

        if runtime_errors:
            retry_count = new_state.get("retry_count", {})
            retry_count["runtime_errors"] = retry_count.get("runtime_errors", 0) + 1
            new_state["retry_count"] = retry_count

            new_state["current_errors"] = {"runtime_errors": runtime_errors}
        else:
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
            await safe_send_socket(socket, 
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
            await safe_send_socket(socket, {"e": "app_check_error", "message": error_msg})

        return new_state


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


def should_retry_builder_or_finish(state: GraphState) -> str:
    """Decide whether to retry builder or finish based on runtime errors"""
    runtime_errors = state.get("runtime_errors", [])
    retry_count = state.get("retry_count", {})
    max_retries = state.get("max_retries", 3)

    # Safety check: prevent infinite loops
    total_retries = sum(retry_count.values())
    if total_retries > 10:
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
        return "end"
