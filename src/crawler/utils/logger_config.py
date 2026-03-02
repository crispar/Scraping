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


def setup_logger(name, log_dir='logs', level=logging.INFO, cleanup_days=30):
    """
    로깅 시스템 설정 및 로거 반환

    Args:
        name (str): 로거 이름
        log_dir (str): 로그 파일을 저장할 디렉토리
        level (int): 로깅 레벨 (기본: INFO)
        cleanup_days (int): 오래된 로그 유지 기간 (기본: 30일, 0이면 자동 삭제 안 함)

    Returns:
        logging.Logger: 설정된 로거 객체
    """
    # 로그 디렉토리 생성
    os.makedirs(log_dir, exist_ok=True)

    # 오래된 로그 파일 자동 삭제
    if cleanup_days > 0:
        deleted_count = cleanup_old_logs(log_dir, cleanup_days)
        if deleted_count > 0:
            # 삭제 완료 메시지 (로거 초기화 전이므로 print 사용)
            pass  # 조용히 삭제
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 로거가 이미 핸들러를 가지고 있다면 함수 종료 (중복 방지)
    if logger.handlers:
        return logger
    
    # 현재 날짜와 시간을 포함한 로그 파일명 생성
    timestamp = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f'{name}_{timestamp}.log')
    
    # 파일 핸들러 생성
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    
    # 콘솔 핸들러 생성 (UTF-8 인코딩 강제)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Windows 환경에서 UTF-8 인코딩 보장
    if sys.platform == 'win32':
        try:
            # stdout을 UTF-8로 재설정
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            # 재설정 실패 시 조용히 넘어감
            pass
    
    # 포맷터 생성
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 핸들러에 포맷터 설정
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 로거에 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"Logger '{name}' has been set up. Logs will be saved to {log_file}")
    
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