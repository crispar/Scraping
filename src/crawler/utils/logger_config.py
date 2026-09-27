import logging
import os
import sys
import time
from datetime import datetime

def cleanup_old_logs(log_dir='logs', days=30):
    """
    오래된 로그 파일 자동 삭제

    Args:
        log_dir: 로그 디렉토리
        days: 유지할 일수 (기본: 30일)

    Returns:
        int: 삭제된 파일 수
    """
    if not os.path.exists(log_dir):
        return 0

    now = time.time()
    cutoff_time = now - (days * 24 * 60 * 60)
    deleted_count = 0

    try:
        for filename in os.listdir(log_dir):
            if not filename.endswith('.log'):
                continue

            filepath = os.path.join(log_dir, filename)

            # 파일 수정 시간 확인
            if os.path.getmtime(filepath) < cutoff_time:
                os.remove(filepath)
                deleted_count += 1
    except Exception:
        # 조용히 실패 (로거 초기화 중이므로)
        pass

    return deleted_count


def _open_file_handler(name, log_dir, level, cleanup_days):
    """
    일자별 로그 파일 핸들러 생성. 디렉터리를 만들 수 없거나 쓸 수 없으면 None.

    로그 파일은 부가 기능이다. 컨테이너를 비루트로 돌리거나 읽기 전용 볼륨에서
    실행할 때 파일을 못 연다고 파서 생성(=추출 전체)이 실패하면 안 된다.
    """
    try:
        os.makedirs(log_dir, exist_ok=True)
        if cleanup_days > 0:
            cleanup_old_logs(log_dir, cleanup_days)
        timestamp = datetime.now().strftime('%Y%m%d')
        handler = logging.FileHandler(
            os.path.join(log_dir, f'{name}_{timestamp}.log'), encoding='utf-8'
        )
    except OSError as e:
        sys.stderr.write(f"[logger] '{log_dir}'에 로그 파일을 열 수 없어 콘솔에만 기록합니다: {e}\n")
        return None
    handler.setLevel(level)
    return handler


def setup_logger(name, log_dir=None, level=logging.INFO, cleanup_days=30):
    """
    로깅 시스템 설정 및 로거 반환

    Args:
        name (str): 로거 이름
        log_dir (str): 로그 파일 디렉토리 (기본: env LOG_DIR, 없으면 'logs')
        level (int): 로깅 레벨 (기본: INFO)
        cleanup_days (int): 오래된 로그 유지 기간 (기본: 30일, 0이면 자동 삭제 안 함)

    env LOG_TO_FILE=0 이면 파일 없이 콘솔에만 기록한다.

    Returns:
        logging.Logger: 설정된 로거 객체
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 로거가 이미 핸들러를 가지고 있다면 함수 종료 (중복 방지)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Windows 환경에서 UTF-8 인코딩 보장
    if sys.platform == 'win32':
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if os.environ.get('LOG_TO_FILE', '1') in ('0', 'false', 'False'):
        return logger

    file_handler = _open_file_handler(
        name, log_dir or os.environ.get('LOG_DIR', 'logs'), level, cleanup_days
    )
    if file_handler:
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.debug(f"Logger '{name}' writing to {file_handler.baseFilename}")

    return logger

def get_logger(name):
    """
    기존 로거 가져오기
    
    Args:
        name (str): 로거 이름
        
    Returns:
        logging.Logger: 로거 객체
    """
    return logging.getLogger(name)