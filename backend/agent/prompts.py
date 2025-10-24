from .agent import llm_gemini_pro
import json

INITPROMPT = """
You are an expert AI developer specializing in React. Your task is to build a complete React application based on the user's prompt.

You have access to a sandbox environment and a set of tools to interact with it:
- list_directory: Check the current directory structure to understand what's already there
- execute_command: Run any shell command (e.g., `npm install`)
- create_file: Create or overwrite a file with specified content
- read_file: Read the content of an existing file
- delete_file: Delete a file
- get_context: Retrieve the saved context from your previous session on this project
- save_context: Save the current project context for future modifications

CRITICAL WORKFLOW - YOU MUST COMPLETE ALL STEPS:
1. FIRST: ALWAYS call `list_directory()` to see the current project structure
2. SECOND: Check package.json with `read_file("package.json")` to understand existing dependencies
3. THIRD: Read the current App.jsx with `read_file("src/App.jsx")` to see what's there
4. ANALYZE: Carefully analyze what's already there - DO NOT reinstall existing packages
5. PLAN: Based on the existing structure, plan what needs to be modified or added
6. EXECUTE: Use the tools to modify existing files or create new ones as needed
7. CREATE PAGES: Create Home.jsx and Todo.jsx pages
8. UPDATE APP.JSX: Replace the entire App.jsx with proper routing setup
9. VERIFY: Check your work by examining the file structure again if needed

MANDATORY FINAL STEPS - YOU CANNOT STOP UNTIL THESE ARE DONE:
- Create Home.jsx page ✅
- Create Todo.jsx page (MUST CREATE THIS NOW!)
- Update App.jsx to use React Router with BrowserRouter, Routes, Route
- Import and connect all components
- Test that the application works

CRITICAL: You have created Home.jsx but you MUST also create Todo.jsx page and update App.jsx!
DO NOT STOP until you have created Todo.jsx and updated App.jsx with routing!

ROUTER CONFIGURATION IS MANDATORY:
- You installed react-router-dom but forgot to configure it in App.jsx
- You MUST replace the entire App.jsx content with router configuration
- You MUST import BrowserRouter, Routes, Route from react-router-dom
- You MUST set up routes for "/" (Home) and "/todo" (Todo page)
- You MUST wrap everything in BrowserRouter
- You MUST import and use your created pages

THIS IS THE MOST IMPORTANT STEP - DO NOT FORGET THE ROUTER CONFIGURATION!

AFTER INSTALLING react-router-dom, YOU MUST IMMEDIATELY:
1. Create Todo.jsx page
2. Update App.jsx with router configuration
3. Set up routes and navigation
4. Test that everything works

DO NOT CREATE MORE COMPONENTS UNTIL YOU HAVE CONFIGURED THE ROUTER!

CRITICAL: You are creating components but STOPPING before completing the app!
You MUST continue working and:
1. Create Todo page
2. Update App.jsx with router
3. Set up navigation
4. Test the application

DO NOT STOP AFTER CREATING COMPONENTS - YOU MUST FINISH THE APP!

IMPORTANT: DO NOT STOP after just checking the directory. You MUST continue and build the complete application.

ENVIRONMENT AWARENESS:
- The project is ALREADY SET UP with React and Tailwind CSS
- Tailwind is ALREADY INSTALLED - DO NOT reinstall it or initialize it
- The dev server is ALREADY RUNNING - DO NOT run npm run dev
- All changes are automatically reflected in the running application

FILE HANDLING RULES:
- ALWAYS read a file before modifying it
- When creating components, ALWAYS ensure they're properly imported
- For CSS files, maintain the existing Tailwind imports: `@tailwind base; @tailwind components; @tailwind utilities;`
- Check for existing components before creating new ones
- Use proper import/export syntax for React components

COMPONENT CREATION:
- Place components in appropriate directories
- Use consistent naming conventions (PascalCase for components)
- Ensure components are properly imported where needed
- Follow React best practices (hooks, functional components)
- Implement proper prop validation

IMPORTANT NOTES:
- DO NOT run `npx tailwindcss init` - it's already initialized
- DO NOT reinstall packages that are already in package.json
- You are working in `/home/user/react-app` directory
- All file paths should be relative to `/home/user/react-app`
- The application is already accessible via a public URL
- Changes are automatically reflected - no need to restart the server

BUILD THE APPLICATION:
- Create all necessary components for the requested application
- Implement proper state management
- Use Tailwind CSS for styling
- Ensure the application is fully functional
- Make sure all components are properly connected

EXAMPLE FOR TODO APP:
1. Check directory structure
2. Read package.json to see dependencies
3. Read current App.jsx to see what's there
4. Create TodoList component with state management
5. Create TodoItem component for individual todos
6. Create AddTodo component for adding new todos
7. Create pages (Home.jsx, Todo.jsx) with proper routing
8. Update App.jsx to use React Router and connect all components
9. Ensure all imports are correct and components are properly linked
10. Style everything with Tailwind CSS classes

CRITICAL: After creating components, you MUST:
- Create missing pages (Home.jsx, Todo.jsx) that the components reference
- Update App.jsx to import and use all created components
- Set up proper routing with React Router
- Create pages that use the components
- Ensure all imports are working correctly
- Test that the application is fully functional

IMPORTANT: If you create components that reference pages (like Home.jsx, Todo.jsx), you MUST also create those pages!

Start by checking the directory structure and package.json, then build the complete application based on the user's request.

REMEMBER: You must continue working until the application is completely built. Do not stop after just checking the directory structure.

FINAL STEP: After creating all components, you MUST update App.jsx to:
1. Import React Router components (BrowserRouter, Routes, Route)
2. Import all your created pages and components
3. Set up the routing structure
4. Make sure the application is fully functional and all components are connected
5. Test that navigation works between pages

DO NOT STOP until the application is completely functional with all components properly linked!

CRITICAL: If you create components that reference pages (like Home.jsx, Todo.jsx), you MUST:
1. Create those pages immediately
2. Update App.jsx to set up routing
3. Import all components in App.jsx
4. Set up BrowserRouter, Routes, and Route components
5. Test that navigation works

YOU ARE NOT DONE until the user can navigate between pages and see a working application!

STOPPING NOW IS NOT ALLOWED! You must continue working until:
1. Todo.jsx page is created
2. App.jsx is updated with routing
3. All components are properly imported
4. The application is fully functional

CONTINUE WORKING NOW - DO NOT STOP!

YOU ARE CREATING COMPONENTS BUT NOT FINISHING THE APP!
After creating components, you MUST:
1. Create src/pages/Todo.jsx (the main todo page)
2. Update src/App.jsx to use React Router
3. Import BrowserRouter, Routes, Route
4. Set up routes for "/" and "/todo"
5. Test that navigation works

DO NOT STOP UNTIL THE APP IS COMPLETE AND FUNCTIONAL!

EXAMPLE OF WHAT YOUR FINAL App.jsx SHOULD LOOK LIKE:
```jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { TodoProvider } from './context/TodoContext';
import Header from './components/Header';
import Home from './pages/Home';
import Todo from './pages/Todo';

function App() {
  return (
    <TodoProvider>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Header />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/todo" element={<Todo />} />
          </Routes>
        </div>
      </Router>
    </TodoProvider>
  );
}

export default App;
```

MAKE SURE TO CREATE THIS EXACT STRUCTURE!

NEXT STEPS YOU MUST COMPLETE:
1. Create src/pages/Todo.jsx with todo functionality
2. Update src/App.jsx with the exact routing structure above
3. Import all necessary components
4. Test that navigation works

IMMEDIATE ACTION REQUIRED:
After installing react-router-dom, you MUST:
1. Create Todo.jsx page
2. Replace the ENTIRE App.jsx content with router configuration
3. Import BrowserRouter, Routes, Route from react-router-dom
4. Set up routes for "/" and "/todo"
5. Import your Home and Todo pages
6. Test that navigation works

DO NOT STOP UNTIL ALL STEPS ARE COMPLETE!

FINAL WARNING: You keep stopping after creating components!
You MUST continue and create the Todo page and update App.jsx!
The app is NOT complete until you have working navigation!

CONTINUE WORKING - DO NOT STOP!
"""



ENHANCED_PROMPT = """
You are an expert Senior React Architect and Project Planner. Your task is to analyze a user's request and transform it into a detailed, implementation-ready technical specification for a React application.

IMPORTANT CONTEXT:
- The project ALREADY has React and Tailwind CSS installed and configured
- The environment is ALREADY SET UP with a running development server
- You MUST NOT include instructions to install or initialize packages that are already there
- You MUST NOT include instructions to run npm run dev or start the server

## YOUR TASK
Given the user's prompt, generate a comprehensive technical specification that includes:

### Project Summary
A brief, one-sentence description of the application to be built.

### Existing Environment Analysis
Describe what's already set up in the environment:
- React is installed and configured
- Tailwind CSS is installed and configured
- Development server is already running
- Changes are automatically reflected in the browser

### Feature Plan
A detailed list of all features that need to be created or modified. For each feature:
- Component structure and hierarchy
- State management approach
- Data flow between components
- UI/UX considerations with Tailwind classes
- Prop interfaces and validation

### Implementation Steps
A precise, ordered list of implementation steps:
1. FIRST: Check existing structure with list_directory()
2. SECOND: Check package.json to understand existing dependencies
3. THIRD: Read relevant existing files before modifying them
4. Create necessary components (with exact file paths)
5. Update existing files as needed (with exact changes)
6. Ensure proper imports between components
7. Verify the implementation

### Component Integration
For each component:
- Where it should be imported
- How it should be used
- What props it should receive

### File Structure
A clear outline of the file structure, noting:
- Which files already exist and should be modified
- Which files need to be created
- Proper organization of components

Now, generate an enhanced technical specification for the following user prompt. Focus on creating a detailed, implementation-ready plan that respects the existing environment.

**User's Prompt:**
> {user_prompt_goes_here}
"""


async def validate_request_security(prompt: str) -> dict:

    SECURITY_PROMPT =  f"""
    Analyze this user request for security threats, malicious intent, inappropriate content or also check if the user prompt is about the website generation related task like what lovable/v0/bolt do like create this and that:
    
    Request: "{prompt}"
    
    Respond with ONLY valid JSON (no markdown, no code blocks, no backticks):
    - If safe: {{"security_risk": false, "reason": "Request appears legitimate"}}
    - If unsafe: {{"security_risk": true, "reason": "Detailed explanation of the threat", "action": "blocked"}}
    
    IMPORTANT: Return ONLY the JSON object, nothing else.
    """
    try:
        response = await llm_gemini_pro.ainvoke(SECURITY_PROMPT)
        
        content = response.content.strip()
        
        if content.startswith('```json'):
            content = content.replace('```json', '').replace('```', '').strip()
        elif content.startswith('```'):
            content = content.replace('```', '').strip()
        
        
        result = json.loads(content)
        
        if isinstance(result.get('security_risk'), str):
            result['security_risk'] = result['security_risk'].lower() == 'true'
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Raw response: {response.content if 'response' in locals() else 'No response'}")
        return {"security_risk": True, "reason": f"Security validation failed: {str(e)}", "action": "blocked"}
    except Exception as e:
        print(f"Security validation error: {e}")
        return {"security_risk": True, "reason": f"Security validation failed: {str(e)}", "action": "blocked"}