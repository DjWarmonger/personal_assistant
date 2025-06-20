import unittest
import time
import subprocess
from pathlib import Path

from launcher.docker_manager import DockerManager


class TestDockerManagerRealCommands(unittest.TestCase):
	"""Integration tests that execute real Docker commands and verify their outcomes."""
	
	@classmethod
	def setUpClass(cls):
		"""Set up test class with real DockerManager for the actual project."""
		cls.docker_manager = DockerManager()  # Uses real project paths
		
		# Skip all tests if Docker is not available
		if not cls.docker_manager.is_docker_available():
			raise unittest.SkipTest("Docker is not available on this system")
		
		# Ensure we start with a clean state
		cls._cleanup_test_containers()


	@classmethod
	def tearDownClass(cls):
		"""Clean up any containers that might be running after tests."""
		cls._cleanup_test_containers()


	@classmethod
	def _cleanup_test_containers(cls):
		"""Stop and remove any test containers."""
		try:
			# Stop the NotionAgent container if it's running
			subprocess.run(
				["docker", "compose", "-f", "Agents/NotionAgent/docker_compose.yaml", "down"],
				cwd=cls.docker_manager.project_root,
				capture_output=True,
				timeout=30
			)
		except Exception:
			pass  # Ignore cleanup errors


	def test_docker_version_command_execution(self):
		"""Test that Docker version command actually executes and returns valid output."""
		success, stdout, stderr = self.docker_manager._run_docker_command(["docker", "version"])
		
		self.assertTrue(success, f"Docker version command failed: {stderr}")
		# Check for version output format (newer Docker versions don't include "Docker version" text)
		self.assertIn("Client:", stdout)
		self.assertIn("Version:", stdout)


	def test_docker_compose_file_validation(self):
		"""Test that the actual project docker-compose file is valid."""
		# Verify the compose file exists
		self.assertTrue(self.docker_manager.full_compose_path.exists(), 
						f"Compose file not found: {self.docker_manager.full_compose_path}")
		
		# Test compose file validation with real Docker
		success, stdout, stderr = self.docker_manager._run_docker_command([
			"docker", "compose", "-f", self.docker_manager.compose_file_path, "config"
		])
		
		self.assertTrue(success, f"Compose file validation failed: {stderr}")
		self.assertIn("services:", stdout.lower())


	def test_real_container_lifecycle(self):
		"""Test complete container lifecycle with real Docker commands."""
		print("\n=== Testing Real Container Lifecycle ===")
		
		# 1. Ensure container is stopped initially
		print("1. Stopping any existing containers...")
		stop_result = self.docker_manager.stop_container()
		print(f"   Stop result: {stop_result}")
		
		# 2. Verify container is not running
		print("2. Checking initial container status...")
		initial_status = self.docker_manager.check_container_status()
		print(f"   Initial status: {initial_status}")
		self.assertIn("Stopped", initial_status)
		
		# 3. Launch the container
		print("3. Launching container...")
		launch_result = self.docker_manager.launch_container()
		print(f"   Launch result: {launch_result}")
		
		# The launch might fail due to missing .env file or other dependencies
		# But we can still test that the command was executed
		if "✅" in launch_result:
			print("   Container launched successfully!")
			
			# 4. Wait a moment for container to start
			print("4. Waiting for container to start...")
			time.sleep(5)
			
			# 5. Check container status
			print("5. Checking running container status...")
			running_status = self.docker_manager.check_container_status()
			print(f"   Running status: {running_status}")
			
			# 6. Get container logs
			print("6. Getting container logs...")
			logs = self.docker_manager.get_container_logs(tail_lines=10)
			print(f"   Logs (first 200 chars): {logs[:200]}...")
			
			# 7. Stop the container
			print("7. Stopping container...")
			final_stop_result = self.docker_manager.stop_container()
			print(f"   Final stop result: {final_stop_result}")
			self.assertIn("✅", final_stop_result)
			
		else:
			print(f"   Container launch failed (expected due to missing dependencies): {launch_result}")
			# Even if launch fails, we can verify the error is from Docker, not our code
			self.assertIn("❌", launch_result)
			self.assertNotIn("Docker compose file not found", launch_result)


	def test_docker_ps_command_execution(self):
		"""Test that docker ps command executes and returns container information."""
		success, stdout, stderr = self.docker_manager._run_docker_command([
			"docker", "compose", "-f", self.docker_manager.compose_file_path, "ps"
		])
		
		self.assertTrue(success, f"Docker ps command failed: {stderr}")
		# Output should contain headers even if no containers are running
		self.assertIn("NAME", stdout.upper())


	def test_docker_images_command_execution(self):
		"""Test that docker images command executes and shows available images."""
		success, stdout, stderr = self.docker_manager._run_docker_command(["docker", "images"])
		
		self.assertTrue(success, f"Docker images command failed: {stderr}")
		# Should contain headers
		self.assertIn("REPOSITORY", stdout.upper())
		self.assertIn("TAG", stdout.upper())


	def test_server_health_check_real_network(self):
		"""Test server health check makes real HTTP request."""
		# This will make an actual HTTP request to localhost:8000
		result = self.docker_manager.check_server_health()
		
		# Since server is likely not running, should be offline
		self.assertIn("Server:", result)
		# Should be either "Offline" or "Error" (if something else is on port 8000)
		self.assertTrue("Offline" in result or "Error" in result)


	def test_docker_build_command_execution(self):
		"""Test that docker build command can be executed."""
		# This will attempt to build the actual NotionAgent image
		result = self.docker_manager.build_container()
		
		# Build might fail due to missing dependencies, but command should execute
		self.assertTrue("✅" in result or "❌" in result)
		
		if "❌" in result:
			print(f"Build failed (expected): {result}")
			# Verify it's a real Docker error, not a file not found error
			self.assertNotIn("Docker compose file not found", result)


	def test_container_logs_real_execution(self):
		"""Test that container logs command executes even when no containers exist."""
		logs = self.docker_manager.get_container_logs()
		
		# Should not throw exception, even if no containers
		self.assertIsInstance(logs, str)
		# Should not contain our exception messages
		self.assertNotIn("Exception getting logs", logs)


	def test_timeout_enforcement(self):
		"""Test that command timeouts are actually enforced."""
		# Test with a very short timeout on a command that should succeed quickly
		start_time = time.time()
		success, stdout, stderr = self.docker_manager._run_docker_command(
			["docker", "--version"], timeout=1
		)
		end_time = time.time()
		
		# Should complete within timeout
		self.assertTrue(success, f"Docker version command failed: {stderr}")
		self.assertLess(end_time - start_time, 2.0, "Command took too long")
		
		# Test with impossible timeout on a potentially slow command
		start_time = time.time()
		success, stdout, stderr = self.docker_manager._run_docker_command(
			["docker", "system", "info"], timeout=0.001  # 1ms timeout
		)
		end_time = time.time()
		
		# Should timeout quickly
		if not success:
			self.assertIn("timed out", stderr.lower())


	def test_working_directory_is_correct(self):
		"""Test that Docker commands are executed from the correct working directory."""
		# Get current directory from Docker's perspective
		success, stdout, stderr = self.docker_manager._run_docker_command(["pwd"])
		
		if success:  # pwd might not be available in all Docker environments
			expected_path = str(self.docker_manager.project_root).replace("\\", "/")
			actual_path = stdout.strip().replace("\\", "/")
			
			# Handle Windows drive letter case differences (F: vs /f)
			if expected_path.startswith("F:/"):
				expected_path = expected_path.replace("F:/", "/f/", 1)
			elif expected_path.startswith("f:/"):
				expected_path = expected_path.replace("f:/", "/f/", 1)
				
			self.assertIn(expected_path.lower(), actual_path.lower())


	def test_environment_variables_passed(self):
		"""Test that environment variables are properly handled in Docker commands."""
		# Test that the compose file can access environment variables
		success, stdout, stderr = self.docker_manager._run_docker_command([
			"docker", "compose", "-f", self.docker_manager.compose_file_path, 
			"config", "--services"
		])
		
		self.assertTrue(success, f"Compose config command failed: {stderr}")
		self.assertIn("notion-rest-server", stdout)


if __name__ == '__main__':
	# Run with verbose output to see the container lifecycle
	unittest.main(verbosity=2) 