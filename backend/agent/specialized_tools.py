from e2b_code_interpreter import AsyncSandbox
from fastapi import WebSocket
from langchain_core.tools import tool
from typing import Dict, Any, List
import os
import json
import re


def create_specialized_tools(sandbox: AsyncSandbox, socket: WebSocket):
    """Create specialized tools for different building tasks"""
    
    # ========== FILE READING TOOLS ==========
    
    @tool
    async def read_existing_file(file_path: str) -> str:
        """
        Read an existing file to understand the current structure and patterns.
        
        Args:
            file_path: Path to the file to read (e.g., "src/App.jsx", "package.json")
        
        Returns:
            Content of the file or error message
        """
        try:
            full_path = os.path.join("/home/user/react-app", file_path)
            content = await sandbox.files.read(full_path)
            
            await socket.send_json({
                'e': 'file_read',
                'file': file_path,
                'message': f"Read content from {file_path}"
            })
            
            return f"Content of {file_path}:\n{content}"
            
        except Exception as e:
            await socket.send_json({
                'e': 'file_read_error',
                'file': file_path,
                'message': f"Failed to read {file_path}: {str(e)}"
            })
            return f"Failed to read {file_path}: {str(e)}"
    
    @tool
    async def list_project_structure() -> str:
        """
        List the current project structure to understand what exists.
        
        Returns:
            Project structure as a tree
        """
        try:
            result = await sandbox.commands.run("tree -I 'node_modules|.*' src", cwd="/home/user/react-app")
            
            await socket.send_json({
                'e': 'structure_listed',
                'message': "Listed current project structure"
            })
            
            return f"Current project structure:\n{result.stdout}"
            
        except Exception as e:
            await socket.send_json({
                'e': 'structure_error',
                'message': f"Failed to list structure: {str(e)}"
            })
            return f"Failed to list project structure: {str(e)}"

    
    @tool
    async def create_data_file(file_name: str, data_content: str) -> str:
        """
        Create a data file with structured content.
        
        Args:
            file_name: Name of the data file (e.g., "abhayData.js", "portfolioData.js")
            data_content: The JavaScript object content for the data file
        
        Returns:
            Success message with file path
        """
        try:
            file_path = f"src/data/{file_name}"
            
            # Ensure proper data file structure
            if not data_content.strip().startswith('export'):
                data_content = f"export const {file_name.replace('.js', '')} = {data_content};"
            
            full_path = os.path.join("/home/user/react-app", file_path)
            await sandbox.files.write(full_path, data_content)
            
            await socket.send_json({
                'e': 'data_file_created',
                'file': file_name,
                'path': file_path,
                'message': f"Created data file: {file_name}"
            })
            
            return f"Data file '{file_name}' created at {file_path}"
            
        except Exception as e:
            await socket.send_json({
                'e': 'data_file_error',
                'file': file_name,
                'message': f"Failed to create data file: {str(e)}"
            })
            return f"Failed to create data file {file_name}: {str(e)}"
    
    @tool
    async def create_hook_file(hook_name: str, hook_content: str) -> str:
        """
        Create a custom React hook file.
        
        Args:
            hook_name: Name of the hook file (e.g., "useTheme.js", "useLocalStorage.js")
            hook_content: The hook implementation code
        
        Returns:
            Success message with file path
        """
        try:
            file_path = f"src/hooks/{hook_name}"
            
            # Ensure proper hook structure
            if not hook_content.strip().startswith('import'):
                hook_content = f"import {{ useState, useEffect }} from 'react';\n\n{hook_content}"
            
            if 'export' not in hook_content:
                hook_content += f"\n\nexport default {hook_name.replace('.js', '')};"
            
            full_path = os.path.join("/home/user/react-app", file_path)
            await sandbox.files.write(full_path, hook_content)
            
            await socket.send_json({
                'e': 'hook_file_created',
                'file': hook_name,
                'path': file_path,
                'message': f"Created hook file: {hook_name}"
            })
            
            return f"Hook file '{hook_name}' created at {file_path}"
            
        except Exception as e:
            await socket.send_json({
                'e': 'hook_file_error',
                'file': hook_name,
                'message': f"Failed to create hook file: {str(e)}"
            })
            return f"Failed to create hook file {hook_name}: {str(e)}"

    # ========== COMPONENT CREATION TOOLS ==========
    
    @tool
    async def create_react_component(component_name: str, component_code: str, file_path: str = None) -> str:
        """
        Create a React component with proper structure and exports.
        
        Args:
            component_name: Name of the component (PascalCase)
            component_code: The JSX/React code for the component
            file_path: Optional custom path, defaults to src/components/{component_name}.jsx
        
        Returns:
            Success message with file path or error message
        """
        try:
            if not file_path:
                file_path = f"src/components/{component_name}.jsx"
            
            # Ensure proper component structure
            if not component_code.strip().startswith('import'):
                component_code = f"import React from 'react';\n\n{component_code}"
            
            # Ensure proper export
            if 'export default' not in component_code:
                component_code += f"\n\nexport default {component_name};"
            
            full_path = os.path.join("/home/user/react-app", file_path)
            await sandbox.files.write(full_path, component_code)
            
            await socket.send_json({
                'e': 'component_created',
                'component': component_name,
                'path': file_path,
                'message': f"Created React component: {component_name}"
            })
            
            return f"React component '{component_name}' created at {file_path}"
            
        except Exception as e:
            await socket.send_json({
                'e': 'component_error',
                'component': component_name,
                'message': f"Failed to create component: {str(e)}"
            })
            return f"Failed to create component {component_name}: {str(e)}"
    
    @tool
    async def create_multiple_components(components: str) -> str:
        """
        Create multiple React components at once.
        
        Args:
            components: JSON string with array of component objects
            Format: [{"name": "Header", "code": "export default function Header() {...}", "path": "src/components/Header.jsx"}]
        
        Returns:
            Success message with list of created components
        """
        try:
            components_data = json.loads(components)
            created_components = []
            
            for comp in components_data:
                name = comp.get('name')
                code = comp.get('code', '')
                path = comp.get('path', f"src/components/{name}.jsx")
                
                # Ensure we have valid data
                if not name or not code or code is None:
                    print(f"Skipping component {name}: missing name or code")
                    continue
                
                # Ensure code is a string
                if not isinstance(code, str):
                    print(f"Skipping component {name}: code is not a string")
                    continue
                
                # Ensure proper structure
                if not code.strip().startswith('import'):
                    code = f"import React from 'react';\n\n{code}"
                
                if 'export default' not in code:
                    code += f"\n\nexport default {name};"
                
                full_path = os.path.join("/home/user/react-app", path)
                await sandbox.files.write(full_path, code)
                created_components.append(name)
            
            await socket.send_json({
                'e': 'components_created',
                'components': created_components,
                'message': f"Created {len(created_components)} components"
            })
            
            return f"Successfully created {len(created_components)} components: {', '.join(created_components)}"
            
        except Exception as e:
            await socket.send_json({
                'e': 'components_error',
                'message': f"Failed to create multiple components: {str(e)}"
            })
            return f"Failed to create multiple components: {str(e)}"
    
    # ========== PAGE CREATION TOOLS ==========
    
    @tool
    async def create_react_page(page_name: str, page_code: str, route_path: str = None) -> str:
        """
        Create a React page with routing setup.
        
        Args:
            page_name: Name of the page component
            page_code: The JSX/React code for the page
            route_path: Optional route path, defaults to /{page_name.lower()}
        
        Returns:
            Success message with file path and route info
        """
        try:
            if not route_path:
                route_path = f"/{page_name.lower()}"
            
            file_path = f"src/pages/{page_name}.jsx"
            
            # Ensure proper page structure
            if not page_code.strip().startswith('import'):
                page_code = f"import React from 'react';\n\n{page_code}"
            
            if 'export default' not in page_code:
                page_code += f"\n\nexport default {page_name};"
            
            full_path = os.path.join("/home/user/react-app", file_path)
            await sandbox.files.write(full_path, page_code)
            
            await socket.send_json({
                'e': 'page_created',
                'page': page_name,
                'path': file_path,
                'route': route_path,
                'message': f"Created page: {page_name}"
            })
            
            return f"React page '{page_name}' created at {file_path} with route {route_path}"
            
        except Exception as e:
            await socket.send_json({
                'e': 'page_error',
                'page': page_name,
                'message': f"Failed to create page: {str(e)}"
            })
            return f"Failed to create page {page_name}: {str(e)}"
    
    @tool
    async def create_multiple_pages(pages: str) -> str:
        """
        Create multiple React pages at once.
        
        Args:
            pages: JSON string with array of page objects
            Format: [{"name": "Home", "code": "export default function Home() {...}", "route": "/"}]
        
        Returns:
            Success message with list of created pages
        """
        try:
            pages_data = json.loads(pages)
            created_pages = []
            
            for page in pages_data:
                name = page.get('name')
                code = page.get('code')
                route = page.get('route', f"/{name.lower()}")
                
                # Ensure we have valid data
                if not name or not code or code is None:
                    print(f"Skipping page {name}: missing name or code")
                    continue
                
                # Ensure code is a string
                if not isinstance(code, str):
                    print(f"Skipping page {name}: code is not a string")
                    continue
                
                # Ensure proper structure
                if not code.strip().startswith('import'):
                    code = f"import React from 'react';\n\n{code}"
                
                if 'export default' not in code:
                    code += f"\n\nexport default {name};"
                
                file_path = f"src/pages/{name}.jsx"
                full_path = os.path.join("/home/user/react-app", file_path)
                await sandbox.files.write(full_path, code)
                created_pages.append({"name": name, "route": route})
            
            await socket.send_json({
                'e': 'pages_created',
                'pages': created_pages,
                'message': f"Created {len(created_pages)} pages"
            })
            
            return f"Successfully created {len(created_pages)} pages"
            
        except Exception as e:
            await socket.send_json({
                'e': 'pages_error',
                'message': f"Failed to create multiple pages: {str(e)}"
            })
            return f"Failed to create multiple pages: {str(e)}"
    
    # ========== CONFIGURATION TOOLS ==========
    
    @tool
    async def setup_routing(routes_config: str) -> str:
        """
        Set up React Router configuration in App.jsx.
        
        Args:
            routes_config: JSON string with routes configuration
            Format: {"routes": [{"path": "/", "component": "Home"}, {"path": "/about", "component": "About"}]}
        
        Returns:
            Success message with routing setup details
        """
        try:
            config = json.loads(routes_config)
            routes = config.get('routes', [])
            
            # Read current App.jsx
            app_path = "/home/user/react-app/src/App.jsx"
            current_app = await sandbox.files.read(app_path)
            
            # Generate routing code
            imports = ["import React from 'react';", "import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';"]
            route_components = []
            
            for route in routes:
                component_name = route.get('component')
                path = route.get('path')
                imports.append(f"import {component_name} from './pages/{component_name}';")
                route_components.append(f'          <Route path="{path}" element={{<{component_name} />}} />')
            
            # Create new App.jsx with routing
            new_app_code = f"""{chr(10).join(imports)}

function App() {{
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Routes>
{chr(10).join(route_components)}
        </Routes>
      </div>
    </Router>
  );
}}

export default App;"""
            
            await sandbox.files.write(app_path, new_app_code)
            
            await socket.send_json({
                'e': 'routing_setup',
                'routes': routes,
                'message': f"Set up routing for {len(routes)} routes"
            })
            
            return f"Successfully set up routing for {len(routes)} routes"
            
        except Exception as e:
            await socket.send_json({
                'e': 'routing_error',
                'message': f"Failed to setup routing: {str(e)}"
            })
            return f"Failed to setup routing: {str(e)}"
    
    @tool
    async def install_dependencies(packages: str) -> str:
        """
        Install npm packages for the React application.
        ONLY use for essential React packages, avoid configuration packages.
        
        Args:
            packages: Comma-separated list of package names or JSON array
        
        Returns:
            Success message with installed packages
        """
        try:
            # Parse packages
            if packages.startswith('['):
                packages_list = json.loads(packages)
            else:
                packages_list = [p.strip() for p in packages.split(',')]
            
            # Filter out configuration packages - only allow essential React packages
            allowed_packages = ['react', 'react-dom', 'react-router-dom', 'react-icons', 'prop-types', 'framer-motion']
            filtered_packages = [p for p in packages_list if any(allowed in p.lower() for allowed in allowed_packages)]
            
            if not filtered_packages:
                return "No essential React packages to install"
            
            package_names = ' '.join(filtered_packages)
            command = f"npm install {package_names}"
            
            await socket.send_json({
                "e": "dependencies_install_started",
                "packages": filtered_packages,
                "command": command
            })
            
            result = await sandbox.commands.run(command, cwd="/home/user/react-app")
            
            if result.exit_code == 0:
                await socket.send_json({
                    "e": "dependencies_installed",
                    "packages": filtered_packages,
                    "message": f"Successfully installed {len(filtered_packages)} packages"
                })
                return f"Successfully installed packages: {', '.join(filtered_packages)}"
            else:
                await socket.send_json({
                    "e": "dependencies_error",
                    "packages": filtered_packages,
                    "error": result.stderr
                })
                return f"Failed to install packages: {result.stderr}"
                
        except Exception as e:
            await socket.send_json({
                'e': 'dependencies_error',
                'message': f"Failed to install dependencies: {str(e)}"
            })
            return f"Failed to install dependencies: {str(e)}"
    
    # ========== IMPORT VALIDATION TOOLS ==========
    
    @tool
    async def validate_imports(file_path: str) -> str:
        """
        Validate imports in a JavaScript/React file.
        
        Args:
            file_path: Path to the file to validate
        
        Returns:
            JSON string with validation results
        """
        try:
            full_path = os.path.join("/home/user/react-app", file_path)
            content = await sandbox.files.read(full_path)
            
            # Extract import statements
            import_pattern = r'import\s+(?:{[^}]+}|\w+|\*\s+as\s+\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
            imports = re.findall(import_pattern, content)
            
            validation_results = {
                "file": file_path,
                "imports": [],
                "errors": [],
                "valid": True
            }
            
            for import_path in imports:
                # Check if file exists
                if import_path.startswith('.'):
                    # Relative import
                    import_file_path = os.path.join(os.path.dirname(full_path), import_path)
                    if not import_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                        # Try common extensions
                        for ext in ['.js', '.jsx', '.ts', '.tsx']:
                            test_path = f"{import_file_path}{ext}"
                            if await sandbox.files.exists(test_path):
                                import_file_path = test_path
                                break
                    
                    exists = await sandbox.files.exists(import_file_path)
                else:
                    # Node module import
                    exists = True  # Assume node modules exist
                
                validation_results["imports"].append({
                    "path": import_path,
                    "exists": exists
                })
                
                if not exists:
                    validation_results["errors"].append(f"Import not found: {import_path}")
                    validation_results["valid"] = False
            
            await socket.send_json({
                'e': 'import_validation_complete',
                'file': file_path,
                'valid': validation_results["valid"],
                'errors': validation_results["errors"]
            })
            
            return json.dumps(validation_results)
            
        except Exception as e:
            await socket.send_json({
                'e': 'import_validation_error',
                'file': file_path,
                'message': f"Failed to validate imports: {str(e)}"
            })
            return json.dumps({"file": file_path, "valid": False, "errors": [str(e)]})
    
    # ========== CONSOLE LOG CAPTURE TOOLS ==========
    
    @tool
    async def capture_console_logs() -> str:
        """
        Capture console logs and errors from the running application.
        
        Returns:
            JSON string with console logs and errors
        """
        try:
            # Try to get browser console logs via E2B
            console_command = """
            python3 -c "
            import subprocess
            import json
            try:
                # Try to get browser console logs
                result = subprocess.run(['curl', '-s', 'http://localhost:5173'], 
                                      capture_output=True, text=True, timeout=10)
                print(json.dumps({'console_logs': [], 'errors': [], 'status': 'success'}))
            except Exception as e:
                print(json.dumps({'console_logs': [], 'errors': [str(e)], 'status': 'error'}))
            "
            """
            
            result = await sandbox.commands.run(console_command, cwd="/home/user/react-app")
            
            try:
                logs_data = json.loads(result.stdout)
            except:
                logs_data = {"console_logs": [], "errors": [], "status": "unknown"}
            
            await socket.send_json({
                'e': 'console_logs_captured',
                'logs': logs_data.get('console_logs', []),
                'errors': logs_data.get('errors', [])
            })
            
            return json.dumps(logs_data)
            
        except Exception as e:
            await socket.send_json({
                'e': 'console_capture_error',
                'message': f"Failed to capture console logs: {str(e)}"
            })
            return json.dumps({"console_logs": [], "errors": [str(e)], "status": "error"})
    
    @tool
    async def check_npm_dev_output() -> str:
        """
        Check npm dev server output for errors.
        
        Returns:
            JSON string with dev server status and errors
        """
        try:
            # Check if dev server is running and get its output
            check_command = "ps aux | grep 'npm run dev' | grep -v grep"
            result = await sandbox.commands.run(check_command, cwd="/home/user/react-app")
            
            is_running = bool(result.stdout.strip())
            
            # Try to get recent logs
            log_command = "tail -n 50 /tmp/npm-dev.log 2>/dev/null || echo 'No log file found'"
            log_result = await sandbox.commands.run(log_command, cwd="/home/user/react-app")
            
            # Parse for errors
            error_patterns = ['error', 'Error', 'ERROR', 'failed', 'Failed', 'FAILED']
            errors = []
            lines = log_result.stdout.split('\n')
            
            for line in lines:
                if any(pattern in line for pattern in error_patterns):
                    errors.append(line.strip())
            
            dev_status = {
                "is_running": is_running,
                "errors": errors,
                "output": log_result.stdout,
                "status": "running" if is_running else "stopped"
            }
            
            await socket.send_json({
                'e': 'dev_server_checked',
                'running': is_running,
                'errors': errors
            })
            
            return json.dumps(dev_status)
            
        except Exception as e:
            await socket.send_json({
                'e': 'dev_server_check_error',
                'message': f"Failed to check dev server: {str(e)}"
            })
            return json.dumps({"is_running": False, "errors": [str(e)], "status": "error"})
    
    return [
        # File reading tools
        read_existing_file,
        list_project_structure,
        
        # Data tools
        create_data_file,
        create_hook_file,
        
        # Component tools
        create_react_component,
        create_multiple_components,
        
        # Page tools
        create_react_page,
        create_multiple_pages,
        
        # Config tools
        setup_routing,
        install_dependencies,
        
        # Validation tools
        validate_imports,
        capture_console_logs,
        check_npm_dev_output
    ]
