import subprocess
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from tz_common.logs import log


class DockerManager:
	"""Manages Docker container operations for the Notion Agent REST server."""
	
	def __init__(self, project_root: Optional[Path] = None, compose_file_path: Optional[str] = None):
		"""
		Initialize Docker manager.
		
		Args:
			project_root: Path to project root directory. If None, auto-detected from current file.
			compose_file_path: Relative path to docker-compose file from project root.
		"""
		if project_root is None:
			# Auto-detect project root (4 levels up from this file)
			self.project_root = Path(__file__).parent.parent.parent.parent
		else:
			self.project_root = project_root
			
		if compose_file_path is None:
			self.compose_file_path = "Agents/NotionAgent/docker_compose.yaml"
		else:
			self.compose_file_path = compose_file_path
			
		self.full_compose_path = self.project_root / self.compose_file_path
		self.server_url = "http://localhost:8000"
		self.health_endpoint = f"{self.server_url}/health"


	def _run_docker_command(self, command: list, timeout: int = 60) -> Tuple[bool, str, str]:
		"""
		Run a docker command and return results.
		
		Args:
			command: Docker command as list of strings
			timeout: Command timeout in seconds
			
		Returns:
			Tuple of (success: bool, stdout: str, stderr: str)
		"""
		try:
			log.flow("Running Docker command", " ".join(command))
			log.flow("Working directory", str(self.project_root))
			
			result = subprocess.run(
				command,
				cwd=self.project_root,
				capture_output=True,
				text=True,
				timeout=timeout
			)
			
			log.flow("Command executed", f"Return code: {result.returncode}")
			if result.stdout:
				log.flow("STDOUT", result.stdout)
			if result.stderr:
				log.flow("STDERR", result.stderr)
				
			return result.returncode == 0, result.stdout, result.stderr
			
		except subprocess.TimeoutExpired:
			error_msg = f"Command timed out after {timeout} seconds"
			log.error("Docker command timeout", error_msg)
			return False, "", error_msg
		except Exception as e:
			error_msg = str(e)
			log.error("Docker command exception", error_msg)
			return False, "", error_msg


	def launch_container(self) -> str:
		"""
		Launch Docker container using docker-compose.
		
		Returns:
			Status message with emoji indicator
		"""
		try:
			log.flow("Launching Docker container", f"Compose file: {self.compose_file_path}")
			
			# Check if compose file exists
			if not self.full_compose_path.exists():
				error_msg = f"Docker compose file not found: {self.full_compose_path}"
				log.error("Compose file missing", error_msg)
				return f"❌ {error_msg}"
			
			# Run docker compose up
			command = ["docker", "compose", "-f", self.compose_file_path, "up", "-d"]
			success, stdout, stderr = self._run_docker_command(command, timeout=120)
			
			if success:
				log.flow("Container launched successfully")
				return "✅ Container launched successfully"
			else:
				log.error("Failed to launch container", stderr)
				return f"❌ Error: {stderr}"
				
		except Exception as e:
			log.error("Exception launching container", str(e))
			return f"❌ Error: {str(e)}"


	def stop_container(self) -> str:
		"""
		Stop Docker container using docker-compose.
		
		Returns:
			Status message with emoji indicator
		"""
		try:
			log.flow("Stopping Docker container", f"Compose file: {self.compose_file_path}")
			
			# Run docker compose down
			command = ["docker", "compose", "-f", self.compose_file_path, "down"]
			success, stdout, stderr = self._run_docker_command(command, timeout=60)
			
			if success:
				log.flow("Container stopped successfully")
				return "✅ Container stopped successfully"
			else:
				log.error("Failed to stop container", stderr)
				return f"❌ Error: {stderr}"
				
		except Exception as e:
			log.error("Exception stopping container", str(e))
			return f"❌ Error: {str(e)}"


	def check_server_health(self) -> str:
		"""
		Check if the REST server is responding.
		
		Returns:
			Server status message with indicator
		"""
		try:
			response = urllib.request.urlopen(self.health_endpoint, timeout=5)
			if response.status == 200:
				return "Server: Online ✓"
			else:
				return f"Server: Error (Status {response.status})"
		except Exception as e:
			return "Server: Offline ✗"


	def check_container_status(self) -> str:
		"""
		Check Docker container status.
		
		Returns:
			Container status message with indicator
		"""
		try:
			command = [
				"docker", "compose", "-f", self.compose_file_path, 
				"ps", "--services", "--filter", "status=running"
			]
			success, stdout, stderr = self._run_docker_command(command, timeout=10)
			
			if success:
				running_services = stdout.strip()
				if running_services:
					return f"Container: Running ✓ ({running_services})"
				else:
					return "Container: Stopped ○"
			else:
				return "Container: Unknown ?"
				
		except Exception as e:
			return "Container: Check failed ✗"


	def get_container_logs(self, tail_lines: int = 50) -> str:
		"""
		Get recent container logs.
		
		Args:
			tail_lines: Number of recent log lines to retrieve
			
		Returns:
			Container logs as string
		"""
		try:
			command = [
				"docker", "compose", "-f", self.compose_file_path, 
				"logs", "--tail", str(tail_lines)
			]
			success, stdout, stderr = self._run_docker_command(command, timeout=30)
			
			if success:
				return stdout
			else:
				return f"Error getting logs: {stderr}"
				
		except Exception as e:
			return f"Exception getting logs: {str(e)}"


	def is_docker_available(self) -> bool:
		"""
		Check if Docker is available and running.
		
		Returns:
			True if Docker is available, False otherwise
		"""
		try:
			command = ["docker", "version"]
			success, stdout, stderr = self._run_docker_command(command, timeout=10)
			return success
		except Exception:
			return False


	def build_container(self, no_cache: bool = False) -> str:
		"""
		Build Docker container.
		
		Args:
			no_cache: Whether to build without cache
			
		Returns:
			Build status message
		"""
		try:
			log.flow("Building Docker container", f"No cache: {no_cache}")
			
			command = ["docker", "compose", "-f", self.compose_file_path, "build"]
			if no_cache:
				command.append("--no-cache")
				
			success, stdout, stderr = self._run_docker_command(command, timeout=300)  # 5 minute timeout for build
			
			if success:
				log.flow("Container built successfully")
				return "✅ Container built successfully"
			else:
				log.error("Failed to build container", stderr)
				return f"❌ Build error: {stderr}"
				
		except Exception as e:
			log.error("Exception building container", str(e))
			return f"❌ Error: {str(e)}" 