"""setup_logger 가 로그 파일을 못 열어도 파서 생성이 실패하지 않아야 한다."""

import logging
import os
import stat
import uuid

import pytest

from crawler.utils.logger_config import setup_logger


def _fresh_name():
    return f'test_logger_{uuid.uuid4().hex[:8]}'


@pytest.mark.skipif(os.geteuid() == 0, reason='root 는 권한 없이도 쓸 수 있음')
def test_unwritable_log_dir_falls_back_to_console(tmp_path):
    log_dir = tmp_path / 'logs'
    log_dir.mkdir()
    log_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)  # 읽기 전용
    try:
        logger = setup_logger(_fresh_name(), log_dir=str(log_dir))
    finally:
        log_dir.chmod(stat.S_IRWXU)
    kinds = {type(h) for h in logger.handlers}
    assert logging.FileHandler not in kinds
    assert logging.StreamHandler in kinds
    logger.info('still works')


def test_log_dir_env_overrides_default(tmp_path, monkeypatch):
    monkeypatch.setenv('LOG_DIR', str(tmp_path / 'custom'))
    name = _fresh_name()
    setup_logger(name)
    assert any(p.name.startswith(name) for p in (tmp_path / 'custom').iterdir())


def test_log_to_file_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv('LOG_DIR', str(tmp_path / 'off'))
    monkeypatch.setenv('LOG_TO_FILE', '0')
    logger = setup_logger(_fresh_name())
    assert not any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    assert not (tmp_path / 'off').exists()
