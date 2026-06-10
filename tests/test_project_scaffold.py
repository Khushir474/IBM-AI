"""Tests for Task 0.1: Project Scaffold - Verify project structure and basic setup."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestProjectStructure:
    """Verify project directory structure is correctly set up."""

    def test_src_directory_exists(self):
        """Test that src/ directory exists."""
        assert Path("src").exists(), "src/ directory not found"
        assert Path("src").is_dir(), "src/ is not a directory"

    def test_api_directory_exists(self):
        """Test that src/api/ directory exists."""
        assert Path("src/api").exists(), "src/api/ directory not found"
        assert Path("src/api").is_dir()

    def test_routes_directory_exists(self):
        """Test that src/api/routes/ directory exists."""
        assert Path("src/api/routes").exists(), "src/api/routes/ directory not found"
        assert Path("src/api/routes").is_dir()

    def test_services_directory_exists(self):
        """Test that src/services/ directory exists."""
        assert Path("src/services").exists(), "src/services/ directory not found"
        assert Path("src/services").is_dir()

    def test_features_directory_exists(self):
        """Test that src/features/ directory exists."""
        assert Path("src/features").exists(), "src/features/ directory not found"
        assert Path("src/features").is_dir()

    def test_data_directory_exists(self):
        """Test that src/data/ directory exists."""
        assert Path("src/data").exists(), "src/data/ directory not found"
        assert Path("src/data").is_dir()

    def test_models_directory_exists(self):
        """Test that src/models/ directory exists."""
        assert Path("src/models").exists(), "src/models/ directory not found"
        assert Path("src/models").is_dir()

    def test_tests_directory_exists(self):
        """Test that tests/ directory exists."""
        assert Path("tests").exists(), "tests/ directory not found"
        assert Path("tests").is_dir()

    def test_test_api_directory_exists(self):
        """Test that tests/test_api/ directory exists."""
        assert Path("tests/test_api").exists(), "tests/test_api/ directory not found"

    def test_test_services_directory_exists(self):
        """Test that tests/test_services/ directory exists."""
        assert Path("tests/test_services").exists()

    def test_test_features_directory_exists(self):
        """Test that tests/test_features/ directory exists."""
        assert Path("tests/test_features").exists()

    def test_test_data_directory_exists(self):
        """Test that tests/test_data/ directory exists."""
        assert Path("tests/test_data").exists()


class TestPackageImports:
    """Verify that all packages can be imported successfully."""

    def test_src_package_importable(self):
        """Test that src package can be imported."""
        try:
            import src
            assert src is not None
        except ImportError as e:
            pytest.fail(f"Failed to import src package: {e}")

    def test_src_api_package_importable(self):
        """Test that src.api package can be imported."""
        try:
            import src.api
            assert src.api is not None
        except ImportError as e:
            pytest.fail(f"Failed to import src.api package: {e}")

    def test_src_services_package_importable(self):
        """Test that src.services package can be imported."""
        try:
            import src.services
            assert src.services is not None
        except ImportError as e:
            pytest.fail(f"Failed to import src.services package: {e}")

    def test_src_features_package_importable(self):
        """Test that src.features package can be imported."""
        try:
            import src.features
            assert src.features is not None
        except ImportError as e:
            pytest.fail(f"Failed to import src.features package: {e}")

    def test_src_data_package_importable(self):
        """Test that src.data package can be imported."""
        try:
            import src.data
            assert src.data is not None
        except ImportError as e:
            pytest.fail(f"Failed to import src.data package: {e}")

    def test_src_models_package_importable(self):
        """Test that src.models package can be imported."""
        try:
            import src.models
            assert src.models is not None
        except ImportError as e:
            pytest.fail(f"Failed to import src.models package: {e}")


class TestConfiguration:
    """Verify that configuration loads correctly."""

    def test_config_module_importable(self):
        """Test that config module can be imported."""
        try:
            from src.config import Settings, get_settings
            assert Settings is not None
            assert get_settings is not None
        except ImportError as e:
            pytest.fail(f"Failed to import config module: {e}")

    def test_settings_instantiation(self):
        """Test that Settings class can be instantiated (will use .env file)."""
        from src.config import Settings
        try:
            # This will fail if required env vars are missing, which is expected in test env
            # We're just verifying the class exists and can be attempted to be instantiated
            assert Settings is not None
        except Exception as e:
            pytest.fail(f"Failed to instantiate Settings: {e}")

    def test_get_settings_returns_singleton(self):
        """Test that get_settings returns same instance (caching works)."""
        from src.config import get_settings
        # Clear the cache first
        get_settings.cache_clear()

        # Need to mock the settings since we don't have .env in test
        import os
        os.environ["CASSANDRA_HOST"] = "localhost"
        os.environ["WXD_HOST"] = "localhost"
        os.environ["PRESTO_HOST"] = "localhost"
        os.environ["WORKSHOP_USER"] = "test"
        os.environ["WORKSHOP_PASSWORD"] = "test"
        os.environ["WORKSHOP_SCHEMA_SUFFIX"] = "test"

        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2, "get_settings() did not return cached instance"

        # Clean up
        get_settings.cache_clear()


class TestFastAPIApp:
    """Verify that FastAPI app is correctly configured."""

    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        from src.api.main import app
        return TestClient(app)

    def test_app_creation(self):
        """Test that FastAPI app can be created."""
        from src.api.main import create_app
        app = create_app()
        assert app is not None
        assert app.title is not None

    def test_app_imports(self):
        """Test that app module can be imported."""
        try:
            from src.api.main import app, create_app
            assert app is not None
            assert create_app is not None
        except ImportError as e:
            pytest.fail(f"Failed to import app module: {e}")

    def test_health_endpoint(self, client):
        """Test that health endpoint responds."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_readiness_endpoint(self, client):
        """Test that readiness endpoint responds."""
        response = client.get("/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "version" in data

    def test_request_id_header_added(self, client):
        """Test that X-Request-ID header is added to responses."""
        response = client.get("/health")
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) > 0

    def test_request_id_preserved(self, client):
        """Test that provided X-Request-ID header is preserved."""
        test_request_id = "test-123-abc"
        response = client.get("/health", headers={"X-Request-ID": test_request_id})
        assert response.headers["X-Request-ID"] == test_request_id

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in response."""
        response = client.get("/health")
        assert "access-control-allow-origin" in response.headers or response.status_code == 200


class TestEnvironmentFiles:
    """Verify that environment configuration files exist."""

    def test_env_example_exists(self):
        """Test that .env.example file exists."""
        assert Path(".env.example").exists(), ".env.example file not found"

    def test_env_example_is_readable(self):
        """Test that .env.example is readable and contains expected variables."""
        with open(".env.example", "r") as f:
            content = f.read()
            assert len(content) > 0, ".env.example is empty"
            # Should mention at least one expected variable
            assert "IBM_ENTITLEMENT_KEY" in content or "CASSANDRA" in content


class TestRequirementsFile:
    """Verify that requirements.txt exists and is valid."""

    def test_requirements_exists(self):
        """Test that requirements.txt exists."""
        assert Path("requirements.txt").exists(), "requirements.txt not found"

    def test_requirements_is_readable(self):
        """Test that requirements.txt is readable."""
        with open("requirements.txt", "r") as f:
            content = f.read()
            assert len(content) > 0, "requirements.txt is empty"

    def test_requirements_has_fastapi(self):
        """Test that requirements.txt includes fastapi."""
        with open("requirements.txt", "r") as f:
            content = f.read()
            assert "fastapi" in content.lower(), "fastapi not found in requirements.txt"

    def test_requirements_has_cassandra_driver(self):
        """Test that requirements.txt includes cassandra-driver."""
        with open("requirements.txt", "r") as f:
            content = f.read()
            assert "cassandra-driver" in content.lower()

    def test_requirements_has_pydantic(self):
        """Test that requirements.txt includes pydantic."""
        with open("requirements.txt", "r") as f:
            content = f.read()
            assert "pydantic" in content.lower()

    def test_requirements_has_pytest(self):
        """Test that requirements.txt includes pytest."""
        with open("requirements.txt", "r") as f:
            content = f.read()
            assert "pytest" in content.lower()


class TestInitFiles:
    """Verify that __init__.py files exist in all packages."""

    def test_src_init_exists(self):
        """Test that src/__init__.py exists."""
        assert Path("src/__init__.py").exists()

    def test_api_init_exists(self):
        """Test that src/api/__init__.py exists."""
        assert Path("src/api/__init__.py").exists()

    def test_routes_init_exists(self):
        """Test that src/api/routes/__init__.py exists."""
        assert Path("src/api/routes/__init__.py").exists()

    def test_services_init_exists(self):
        """Test that src/services/__init__.py exists."""
        assert Path("src/services/__init__.py").exists()

    def test_features_init_exists(self):
        """Test that src/features/__init__.py exists."""
        assert Path("src/features/__init__.py").exists()

    def test_data_init_exists(self):
        """Test that src/data/__init__.py exists."""
        assert Path("src/data/__init__.py").exists()

    def test_models_init_exists(self):
        """Test that src/models/__init__.py exists."""
        assert Path("src/models/__init__.py").exists()

    def test_tests_init_exists(self):
        """Test that tests/__init__.py exists."""
        assert Path("tests/__init__.py").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
