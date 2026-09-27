"""VLMClient: 이미지 다운로드 크기 상한과 기본값 검증 (네트워크 없이)."""

import crawler.utils.vlm_client as vlm_mod
from crawler.utils.vlm_client import VLMClient


class _StreamResp:
    """청크 단위로만 읽을 수 있는 가짜 응답. 몇 바이트를 읽었는지 기록한다."""

    def __init__(self, total_bytes, content_length=None):
        self.total = total_bytes
        self.read = 0
        self.headers = {'content-type': 'image/png'}
        if content_length is not None:
            self.headers['content-length'] = str(content_length)

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        while self.read < self.total:
            n = min(chunk_size, self.total - self.read)
            self.read += n
            yield b'x' * n

    @property
    def content(self):  # 스트리밍을 무시하고 한 번에 읽으면 전체를 메모리에 올린다
        self.read = self.total
        return b'x' * self.total

    def close(self):
        pass


def _client():
    return VLMClient(enabled=True, base_url='http://vlm.test/v1', max_image_bytes=1024)


def test_oversized_image_is_skipped_without_reading_it_all(monkeypatch):
    resp = _StreamResp(total_bytes=50 * 1024 * 1024)
    posted = []
    monkeypatch.setattr(vlm_mod.requests, 'get', lambda *a, **k: resp)
    monkeypatch.setattr(vlm_mod.requests, 'post', lambda *a, **k: posted.append(1))

    assert _client().describe_image('https://img.test/huge.png') is None
    assert not posted, 'oversized image must not be sent to the VLM'
    assert resp.read <= 1024 + 64 * 1024, f'read {resp.read} bytes'


def test_declared_content_length_over_cap_is_rejected_before_download(monkeypatch):
    resp = _StreamResp(total_bytes=10, content_length=10 * 1024 * 1024)
    monkeypatch.setattr(vlm_mod.requests, 'get', lambda *a, **k: resp)
    assert _client().describe_image('https://img.test/huge.png') is None
    assert resp.read == 0


def test_defaults_match_measured_server_capacity(monkeypatch):
    # compose 실측값: 서버 --parallel 2, 장당 타임아웃 150s. env 없이 도는 EXE 도 같은 값을 써야 한다.
    for key in ('VLM_CONCURRENCY', 'VLM_TIMEOUT'):
        monkeypatch.delenv(key, raising=False)
    import importlib
    fresh = importlib.reload(vlm_mod)
    try:
        assert fresh.DEFAULT_CONCURRENCY == 2
        assert fresh.DEFAULT_TIMEOUT == 150
    finally:
        importlib.reload(vlm_mod)
