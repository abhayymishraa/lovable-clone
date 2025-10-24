from langchain_core.tools import tool
from typing import Dict, Any
import os

def create_tools_with_context(sandbox, socket):
    """Create tools with sandbox and socket context"""
    
    @tool
    async def create_file(file_path: str, content: str) -> str:
        """Creates or overwrites a file with the given content at the specified path within the react-app directory."""
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
        """Reads the content of a file from the react-app directory."""
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
        """Deletes a file from the react-app directory."""
        try:
            # The React app is in /home/user/react-app
            full_path = os.path.join("/home/user/react-app", file_path)
            await sandbox.files.delete(full_path)
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
        """Executes a shell command within the react-app directory."""
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
        """Lists the directory structure using tree command, excluding node_modules and hidden files."""
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
    def save_context(semantic: str, procedural: str = "", episodic: str = "") -> str:
        """Saves project context (semantic, procedural, episodic memory) for future sessions."""
        return "Save context - not implemented yet"

    return [create_file, read_file, execute_command, delete_file, list_directory, get_context, save_context]

