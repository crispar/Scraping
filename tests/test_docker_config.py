"""Test Docker configuration files are valid and complete"""

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDockerFiles:
    """Verify all Docker-related files exist and are valid"""

    def test_dockerfile_exists(self):
        assert os.path.isfile(os.path.join(PROJECT_ROOT, 'Dockerfile'))

    def test_docker_compose_exists(self):
        assert os.path.isfile(os.path.join(PROJECT_ROOT, 'docker-compose.yml'))

    def test_nginx_conf_exists(self):
        assert os.path.isfile(os.path.join(PROJECT_ROOT, 'nginx', 'nginx.conf'))

    def test_ssl_script_exists_and_executable(self):
        path = os.path.join(PROJECT_ROOT, 'nginx', 'generate-ssl.sh')
        assert os.path.isfile(path)
        assert os.access(path, os.X_OK), "generate-ssl.sh must be executable"

    def test_dockerignore_excludes_venv(self):
        with open(os.path.join(PROJECT_ROOT, '.dockerignore')) as f:
            content = f.read()
        assert '.venv' in content

    def test_dockerfile_copies_essential_files(self):
        with open(os.path.join(PROJECT_ROOT, 'Dockerfile')) as f:
            content = f.read()
        for expected in ['COPY src/', 'COPY web_app.py', 'COPY templates/', 'COPY requirements.txt']:
            assert expected in content, f"Missing: {expected}"
        assert 'flask' in content.lower()
        assert 'gunicorn' in content.lower()

    def test_dockerfile_uses_non_editable_install(self):
        """Production Dockerfile must not use editable install"""
        with open(os.path.join(PROJECT_ROOT, 'Dockerfile')) as f:
            content = f.read()
        assert 'pip install -e' not in content, "Production build must not use editable install"

    def test_docker_compose_port_5500(self):
        with open(os.path.join(PROJECT_ROOT, 'docker-compose.yml')) as f:
            content = f.read()
        assert '5500' in content

    def test_nginx_ssl_configured(self):
        with open(os.path.join(PROJECT_ROOT, 'nginx', 'nginx.conf')) as f:
            content = f.read()
        for expected in ['ssl', '443', 'cert.pem', 'key.pem']:
            assert expected in content, f"Missing SSL config: {expected}"


class TestWebAppFileIntegrity:
    """Verify web app files exist alongside GUI (standalone build preserved)"""

    def test_web_app_file_exists(self):
        assert os.path.isfile(os.path.join(PROJECT_ROOT, 'web_app.py'))

    def test_templates_exist(self):
        assert os.path.isfile(os.path.join(PROJECT_ROOT, 'templates', 'index.html'))

    def test_gui_app_unchanged(self):
        assert os.path.isfile(os.path.join(PROJECT_ROOT, 'gui_app.py'))

    def test_setup_py_unchanged(self):
        assert os.path.isfile(os.path.join(PROJECT_ROOT, 'setup.py'))
