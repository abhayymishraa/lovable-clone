from e2b_code_interpreter import AsyncSandbox
from fastapi import WebSocket
from langchain_core.tools import tool
from typing import Dict, Any
import os

def create_tools_with_context(sandbox: AsyncSandbox, socket: WebSocket):
    """Create tools with sandbox and socket context"""
    
    @tool
    async def create_file(file_path: str, content: str) -> str:
        """
        Create a file with the given content at the specified path.
        
        Args:
            file_path: The path where the file should be created (e.g., "src/App.jsx", "src/components/Header.jsx")
            content: The content to write to the file (React components, HTML, CSS, etc.)
        
        Returns:
            Success message with file path or error message if failed
        
        Example:
            create_file("src/App.jsx", "import React from 'react'; export default function App() { return <div>Hello</div>; }")
        """
        try:
            # The React app is in /home/user/react-app
            full_path = os.path.join("/home/user/react-app", file_path)
            await sandbox.files.write(full_path, content)
            await socket.send_json({
                'e': 'file_created',
                'message': f"Created {file_path}"
            })
            return f"File {file_path} created successfully."
        except Exception as e:
            await socket.send_json({
                'e': 'file_error',
                'message': f"Failed to create {file_path}: {str(e)}"
            })
            return f"Failed to create file {file_path}: {str(e)}"

    @tool 
    async def read_file(file_path: str) -> str:
        """
        Read the content of a file from the react-app directory.
        
        Args:
            file_path: The path of the file to read (e.g., "src/App.jsx", "package.json")
        
        Returns:
            The file content as a string, or error message if file not found
        
        Example:
            read_file("src/App.jsx") - reads the main App component
            read_file("package.json") - reads package dependencies
        """
        try:
            # The React app is in /home/user/react-app
            full_path = os.path.join("/home/user/react-app", file_path)
            content = await sandbox.files.read(full_path)
            await socket.send_json({
                'e': 'file_read', 
                'message': f"Read content from {file_path}"
            })
            return f"Content from {file_path}:\n{content}"
        except Exception as e:
            await socket.send_json({
                'e': 'file_error',
                'message': f"Failed to read {file_path}: {str(e)}"
            })
            return f"Failed to read file {file_path}: {str(e)}"

    @tool
    async def delete_file(file_path: str) -> str:
        """
        Delete a file from the react-app directory.
        
        Args:
            file_path: The path of the file to delete (e.g., "src/old-component.jsx")
        
        Returns:
            Success message or error message if deletion failed
        
        Example:
            delete_file("src/old-component.jsx") - removes an unused component
        """
        try:
            # The React app is in /home/user/react-app
            full_path = os.path.join("/home/user/react-app", file_path)
            await sandbox.files.remove(full_path)
            await socket.send_json({
                'e': 'file_deleted',
                'message': f"Deleted {file_path}"
            })
            return f"File {file_path} deleted successfully."
        except Exception as e:
            await socket.send_json({
                'e': 'file_error',
                'message': f"Failed to delete {file_path}: {str(e)}"
            })
            return f"Failed to delete file {file_path}: {str(e)}"

    @tool
    async def execute_command(command: str) -> str:
        """
        Execute a shell command within the react-app directory.
        
        Args:
            command: The shell command to execute (e.g., "npm install", "npm run dev", "mkdir src/components")
        
        Returns:
            Command output and success/error status
        
        Common Commands:
            - "npm install" - install dependencies
            - "npm install react-router-dom" - install specific package
            - "mkdir -p src/components" - create directory structure
            - "npm run dev" - start development server (usually already running)
        
        Example:
            execute_command("npm install react-router-dom") - installs routing library
        """
        try:
            await socket.send_json({
                "e": "command_started",
                "command": command
            })
            
            # The React app is in /home/user/react-app
            result = await sandbox.commands.run(command, cwd="/home/user/react-app")
            
            await socket.send_json({
                "e": "command_output",
                "command": command,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code
            })

            if result.exit_code == 0:
                await socket.send_json({
                    "e": "command_executed",
                    "command": command,
                    "message": "Command executed successfully"
                })
                return f"Command '{command}' executed successfully. Output: {result.stdout[:500]}{'...' if len(result.stdout) > 500 else ''}"
            else:
                await socket.send_json({
                    "e": "command_failed",
                    "command": command,
                    "message": f"Command failed with exit code {result.exit_code}"
                })
                return f"Command '{command}' failed with exit code {result.exit_code}. Error: {result.stderr[:500]}{'...' if len(result.stderr) > 500 else ''}"
                
        except Exception as e:
            await socket.send_json({
                "e": "command_error",
                "command": command,
                "message": f"Command execution error: {str(e)}"
            })
            return f"Command '{command}' failed with error: {str(e)}"

    @tool
    async def list_directory(path: str = ".") -> str:
        """
        List the directory structure using tree command, excluding node_modules and hidden files.
        
        Args:
            path: The directory path to list (default: "." for current directory)
        
        Returns:
            Formatted directory tree structure
        
        Example:
            list_directory() - lists current directory
            list_directory("src") - lists src directory structure
        
        Note:
            Automatically excludes node_modules and hidden files for cleaner output
        """
        try:
            await socket.send_json({
                "e": "command_started",
                "command": f"tree -I 'node_modules|.*' {path}"
            })
            
            result = await sandbox.commands.run(f"tree -I 'node_modules|.*' {path}", cwd="/home/user/react-app")
            
            await socket.send_json({
                "e": "command_output",
                "command": f"tree -I 'node_modules|.*' {path}",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code
            })

            if result.exit_code == 0:
                await socket.send_json({
                    "e": "command_executed",
                    "command": f"tree -I 'node_modules|.*' {path}",
                    "message": "Directory structure listed successfully"
                })
                return f"Directory structure:\n{result.stdout}"
            else:
                await socket.send_json({
                    "e": "command_failed",
                    "command": f"tree -I 'node_modules|.*' {path}",
                    "message": f"Command failed with exit code {result.exit_code}"
                })
                return f"Failed to list directory structure. Error: {result.stderr}"
                
        except Exception as e:
            await socket.send_json({
                "e": "command_error",
                "command": f"tree -I 'node_modules|.*' {path}",
                "message": f"Command execution error: {str(e)}"
            })
            return f"Failed to list directory: {str(e)}"

    @tool
    def get_context() -> str:
        """Fetches the last saved context for the current project."""
        return "Get context - not implemented yet"

    @tool
    async def write_multiple_files(files: str) -> str:
        """
        Write multiple files to the sandbox at once for better efficiency.
        
        Args:
            files: JSON string containing array of file objects with 'path' and 'data' keys
        
        Returns:
            Success message with list of created files or error message
        
        Format:
            [
                {"path": "src/App.jsx", "data": "import React from 'react';..."},
                {"path": "src/components/Header.jsx", "data": "export default function Header() {...}"}
            ]
        
        Example:
            write_multiple_files('[{"path": "src/App.jsx", "data": "import React from \'react\'; export default function App() { return <div>Hello</div>; }"}]')
        
        Benefits:
            - More efficient than creating files one by one
            - Prevents agent from stopping prematurely
            - Creates complete application structure at once
        """
        try:
            import json
            files_data = json.loads(files)
            
            # Convert to the format expected by E2B
            file_objects = []
            for file_info in files_data:
                file_objects.append({
                    "path": os.path.join("/home/user/react-app", file_info["path"]),
                    "data": file_info["data"]
                })
            
            await sandbox.files.write_files(file_objects)
            
            file_names = [f["path"] for f in files_data]
            await socket.send_json({
                'e': 'files_created',
                'message': f"Created {len(file_names)} files: {', '.join(file_names)}"
            })
            
            return f"Successfully created {len(file_names)} files: {', '.join(file_names)}"
            
        except Exception as e:
            await socket.send_json({
                'e': 'file_error',
                'message': f"Failed to create multiple files: {str(e)}"
            })
            return f"Failed to create multiple files: {str(e)}"

    @tool
    def get_context() -> str:
        """
        Fetch the last saved context for the current project.
        
        Returns:
            Saved project context or "not implemented yet" message
        
        Note:
            This tool is not yet implemented but available for future use
        """
        return "Get context - not implemented yet"

    @tool
    def save_context(semantic: str, procedural: str = "", episodic: str = "") -> str:
        """
        Save project context for future sessions.
        
        Args:
            semantic: Semantic memory about the project
            procedural: Procedural memory about how things work
            episodic: Episodic memory about specific events
        
        Returns:
            Success message or "not implemented yet" message
        
        Note:
            This tool is not yet implemented but available for future use
        """
        return "Save context - not implemented yet"

    return [create_file, read_file, execute_command, delete_file, list_directory, write_multiple_files, get_context, save_context]

