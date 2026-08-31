"""로컬 VLM(비전-언어 모델) 클라이언트

본문에 삽입된 이미지(기사 캡처·차트·표 등)를 텍스트로 해석하기 위한 유틸리티.
Windows 호스트에서 llama.cpp(Vulkan/GPU)로 서빙되는 Qwen3-VL 8B 서버(OpenAI 호환, 포트 8081)를
사용한다. 상세: ~/.claude/docs/vlm-gpu-api.md

설계 원칙:
- 서버가 꺼져 있거나 오류가 나도 추출 자체는 절대 실패하지 않는다(graceful fallback).
  describe_* 는 실패 시 None/빈 dict 을 반환하고, 호출부는 이미지 URL 마커로 대체한다.
- 서버는 부팅 시 자동 시작되지 않으므로 호출 전에 /health 로 가용성을 확인(1회 캐시).
- 동시 슬롯 4개를 활용해 여러 이미지를 병렬 처리한다.
"""

import os
import time
import base64
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import Dict, List, Optional

logger = logging.getLogger('vlm_client')


# ---- 환경설정 (모두 env 로 오버라이드 가능) ----
DEFAULT_MODEL = 'qwen3-vl:8b-instruct'   # thinking 버전 'qwen3-vl:8b' 사용 금지
DEFAULT_TIMEOUT = int(os.environ.get('VLM_TIMEOUT', '120'))       # 이미지 1장 추론 타임아웃(초)
DEFAULT_MAX_IMAGES = int(os.environ.get('VLM_MAX_IMAGES', '8'))   # 포스트당 최대 해석 이미지 수
DEFAULT_CONCURRENCY = int(os.environ.get('VLM_CONCURRENCY', '4')) # 서버 동시 슬롯 수와 일치
# 전체 이미지 해석에 허용하는 총 시간(초). 이 예산을 넘으면 아직 안 끝난 이미지는
# 기다리지 않고 버린다(호출부가 URL 마커로 폴백). 서버가 느려졌을 때 작업이
# 8장×장당타임아웃 만큼(최악 ~20분) 늘어지는 것을 막는 wall-clock 상한.
DEFAULT_TOTAL_BUDGET = int(os.environ.get('VLM_TOTAL_BUDGET', '360'))
# 이미지 긴 변 상한(px). 이보다 큰 이미지만 이 값으로 축소해 보낸다(작은 건 원본 유지).
# 큰 사진(스마트폰 12MP 등)의 vision 토큰·추론시간을 줄이는 용도. 0이면 비활성.
# 실측(1600x1050 텍스트카드 전사 유사도): 1024px=99.5%·tok713 vs 1568px=100%·tok1609.
# 1024면 사실상 무손실이면서 토큰 56%↓ → 블로그/뉴스/차트 기본값으로 채택.
# 단 3000px+ 잔글씨 빼곡한 전체화면 문서 캡처가 잦으면 2048로 올릴 것. 1024 밑은 금지.
DEFAULT_MAX_DIM = int(os.environ.get('VLM_MAX_DIM', '1024'))
HEALTH_TIMEOUT = 5

# base_url 후보: env 우선, 그 다음 컨테이너/로컬/기타 호스트 순으로 /health 탐색.
# - Docker 컨테이너: host.docker.internal
# - Windows 네이티브 EXE: localhost (서버가 같은 호스트)
# - 그 외: 명시적 env 지정 권장
_HOST_CANDIDATES = [
    os.environ.get('VLM_BASE_URL', '').strip(),
    'http://host.docker.internal:8081/v1',
    'http://localhost:8081/v1',
    'http://127.0.0.1:8081/v1',
]

# 이미지에 담긴 정보를 '해석'이 아니라 '전사'하도록 유도하는 프롬프트.
# (8B 모델이라 수치 추론은 실수 가능 → 있는 그대로 옮기는 데 집중)
DEFAULT_PROMPT = (
    '이 이미지는 블로그 본문에 삽입된 것입니다(기사 캡처·차트·그래프·표·사진 등). '
    '이미지에 담긴 정보를 한국어로 간결하게 정리하세요.\n'
    '1) 보이는 텍스트·숫자를 정확히 전사(제목/출처/날짜 포함).\n'
    '2) 차트·그래프면 축과 추세, 핵심 수치.\n'
    '3) 표면 행·열을 마크다운 표로.\n'
    '이미지에 실제로 있는 내용만 쓰고, "차트 없음"·"추측 없음" 같은 메타 설명이나 '
    '머리말·맺음말은 넣지 마세요.'
)


class VLMClient:
    """로컬 GPU VLM 서버에 이미지를 보내 텍스트 설명을 받는 클라이언트."""

    def __init__(self,
                 enabled: bool = None,
                 base_url: str = None,
                 model: str = DEFAULT_MODEL,
                 timeout: int = DEFAULT_TIMEOUT,
                 max_images: int = DEFAULT_MAX_IMAGES,
                 concurrency: int = DEFAULT_CONCURRENCY,
                 total_budget: int = DEFAULT_TOTAL_BUDGET,
                 max_dim: int = DEFAULT_MAX_DIM,
                 request_headers: Optional[Dict[str, str]] = None):
        # enabled 기본값: env VLM_ENABLED (기본 '1')
        if enabled is None:
            enabled = os.environ.get('VLM_ENABLED', '1') not in ('0', 'false', 'False', '')
        self.enabled = enabled
        self.model = model
        self.timeout = timeout
        self.max_images = max_images
        self.concurrency = max(1, concurrency)
        self.total_budget = max(1, total_budget)
        self.max_dim = max(0, max_dim)
        # 이미지 다운로드용 헤더(네이버 등 referer 요구 대비)
        self.request_headers = request_headers or {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://blog.naver.com/',
        }
        self._base_url = base_url          # 확정된 base_url (health 성공 시 캐시)
        self._health_checked = base_url is not None
        self._cache: Dict[str, str] = {}   # url -> description (프로세스 내 중복 방지)

    # ---- 가용성 ----
    def _resolve_base_url(self) -> Optional[str]:
        """후보 호스트 중 /health 가 응답하는 첫 base_url 을 찾아 캐시."""
        if self._health_checked:
            return self._base_url
        self._health_checked = True
        for base in _HOST_CANDIDATES:
            if not base:
                continue
            health = base.rsplit('/v1', 1)[0] + '/health'
            try:
                r = requests.get(health, timeout=HEALTH_TIMEOUT)
                if r.ok and 'ok' in r.text.lower():
                    self._base_url = base
                    logger.info(f"VLM server available at {base}")
                    return base
            except Exception:
                continue
        logger.warning(
            "VLM server not reachable (health check failed). "
            "이미지 해석을 건너뜁니다. 서버 시작: vlm-gpu/start-server.cmd"
        )
        self._base_url = None
        return None

    def available(self) -> bool:
        return self.enabled and self._resolve_base_url() is not None

    # ---- 이미지 전처리 ----
    def _maybe_downscale(self, content: bytes, content_type: str):
        """긴 변이 max_dim 을 넘는 이미지만 축소해 (bytes, content_type) 반환.

        - 이미 작은 이미지는 원본 그대로(품질 손실 0).
        - Pillow 미설치/디코딩 실패 시에도 원본 그대로 반환(추출 안 깨짐).
        """
        if self.max_dim <= 0:
            return content, content_type
        try:
            import io
            from PIL import Image
        except Exception:
            return content, content_type  # Pillow 없으면 그대로
        try:
            im = Image.open(io.BytesIO(content))
            w, h = im.size
            if max(w, h) <= self.max_dim:
                return content, content_type  # 상한 이하 → 손대지 않음
            scale = self.max_dim / float(max(w, h))
            nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
            im = im.convert('RGB').resize((nw, nh), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, 'JPEG', quality=88)
            logger.info(f"VLM 이미지 다운스케일 {w}x{h} -> {nw}x{nh} (max_dim={self.max_dim})")
            return buf.getvalue(), 'image/jpeg'
        except Exception as e:
            logger.debug(f"downscale skipped: {e}")
            return content, content_type

    # ---- 단일 이미지 ----
    def describe_image(self, url: str, prompt: str = DEFAULT_PROMPT) -> Optional[str]:
        """이미지 URL 하나를 해석해 설명 텍스트 반환. 실패 시 None."""
        if url in self._cache:
            return self._cache[url]
        base = self._resolve_base_url()
        if not base:
            return None
        try:
            img = requests.get(url, headers=self.request_headers, timeout=20)
            img.raise_for_status()
            content_type = img.headers.get('content-type', 'image/png').split(';')[0]
            if not content_type.startswith('image/'):
                content_type = 'image/png'
            content, content_type = self._maybe_downscale(img.content, content_type)
            b64 = base64.b64encode(content).decode()
            payload = {
                'model': self.model,
                'max_tokens': 600,
                'temperature': 0.1,
                'messages': [{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        {'type': 'image_url',
                         'image_url': {'url': f'data:{content_type};base64,{b64}'}},
                    ],
                }],
            }
            resp = requests.post(f'{base}/chat/completions', json=payload, timeout=self.timeout)
            resp.raise_for_status()
            text = resp.json()['choices'][0]['message']['content'].strip()
            self._cache[url] = text
            return text or None
        except Exception as e:
            logger.debug(f"VLM describe failed for {url}: {e}")
            return None

    # ---- 여러 이미지 병렬 ----
    def describe_images(self, urls: List[str], prompt: str = DEFAULT_PROMPT) -> Dict[str, str]:
        """이미지 URL 목록을 병렬 해석. {url: description} 반환(실패 항목은 제외).

        - max_images 를 넘는 이미지는 처리하지 않는다(초과분은 호출부에서 URL 마커 처리).
        - total_budget(초) 를 넘기면 아직 안 끝난 이미지는 기다리지 않고 버린다.
          서버가 느려졌을 때 작업 전체가 수십 분으로 늘어지는 것을 막는 상한.
          버려진 이미지는 호출부에서 URL 마커로 폴백되므로 결과 자체는 정상.
        """
        if not self.available() or not urls:
            return {}
        # 순서 유지하며 중복 제거
        unique = list(dict.fromkeys(urls))[:self.max_images]
        results: Dict[str, str] = {}
        deadline = time.monotonic() + self.total_budget

        # 컨텍스트 매니저(__exit__=shutdown(wait=True))를 쓰면 예산 초과 후에도
        # 실행 중인 스레드가 끝날 때까지 블로킹되므로, 수동 종료로 예산을 지킨다.
        ex = ThreadPoolExecutor(max_workers=self.concurrency)
        try:
            futures = {ex.submit(self.describe_image, u, prompt): u for u in unique}
            pending = set(futures)
            while pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    logger.warning(
                        f"VLM 총 예산({self.total_budget}s) 초과 — 남은 "
                        f"{len(pending)}개 이미지는 URL 마커로 폴백."
                    )
                    break
                done, pending = wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
                for fut in done:
                    url = futures[fut]
                    try:
                        desc = fut.result()
                    except Exception:
                        desc = None
                    if desc:
                        results[url] = desc
        finally:
            # 대기 중(미시작) 작업은 취소, 실행 중인 스레드는 기다리지 않고 종료.
            # 실행 중 스레드는 각자의 per-image 타임아웃에 걸려 알아서 끝난다.
            ex.shutdown(wait=False, cancel_futures=True)
        return results
