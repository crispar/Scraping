# Content Extractor

웹 기사·블로그·커뮤니티 게시물 URL을 받아 **제목·작성자·발행일·본문**을 텍스트로 추출하는 도구입니다.
44개 사이트 전용 파서와 범용(generic) 파서를 갖추고 있으며, 네이버 블로그 본문의 이미지(기사 캡처·차트·표)는
로컬 GPU VLM으로 해석해 본문 흐름 속 제자리에 끼워 넣습니다.

같은 추출 엔진(`CrawlerService` → `ParserFactory` → 사이트별 파서)을 세 가지 방식으로 실행할 수 있습니다.

| 실행 방식 | 진입점 | 용도 |
|---|---|---|
| **웹 앱 (Docker)** | `web_app.py` + nginx, `https://<host>:5500` | 주 사용 경로. 모바일 브라우저 포함 |
| 데스크톱 GUI | `gui_app.py` / `ContentExtractor_v2.exe` | Windows 단독 실행 |
| CLI | `scripts/crawler_main.py` | Reddit·네이버 블로그 대량 수집(CSV/TXT/JSON 저장) |

---

## 빠른 시작

### Docker (웹 앱)

```bash
./nginx/generate-ssl.sh          # 최초 1회: 자체 서명 인증서 생성 (nginx/ssl/)
docker compose up -d --build     # web(gunicorn) + nginx
# → https://localhost:5500  (자체 서명 인증서 경고는 수락)
```

소스는 이미지 안에 빌드되므로, **코드를 고친 뒤에는 반드시 다시 빌드**해야 반영됩니다.

```bash
docker compose build web && docker compose up -d web
```

컨테이너는 비루트 사용자(`app`, uid 10001)로 실행되며 `/api/health` 기반 `HEALTHCHECK`가 있습니다
(`docker ps`에서 `healthy` 확인).

### 로컬 개발

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt flask gunicorn pytest
pip install -e .
python web_app.py                # http://localhost:5000 (Flask 개발 서버)
```

### 테스트

```bash
pytest -m "not network"          # 오프라인 테스트 (고정 HTML·스텁 사용, 수 초)
pytest -m network                # 실제 사이트에 요청하는 파서 테스트 (사이트 차단·구조 변경에 따라 일부 실패 가능)
```

`tests/conftest.py`가 `src/`를 경로에 넣으므로 `pip install -e .` 없이도 테스트가 돌아갑니다.

---

## 웹 API

본문 이미지 VLM 해석이 붙으면 추출에 수 분이 걸릴 수 있습니다. 요청 하나를 그동안 열어 두면 모바일 망이
유휴 연결을 끊으므로, 추출은 **작업(job) 등록 → 폴링** 방식입니다.

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/api/health` | 상태 + 등록 파서 수 |
| `GET` | `/api/parsers` | 등록된 파서 이름 목록 |
| `POST` | `/api/detect` | `{"url"}` → `{"platform"}` (URL로 파서 판별만) |
| `POST` | `/api/extract` | `{"url"}` → **202** `{"job_id", "status":"pending"}` |
| `GET` | `/api/extract/result/<job_id>` | `pending` / `done`(+결과) / `error` / 404 `not_found` |
| `POST` | `/api/extract` + `"sync": true` | 하위 호환: 완료될 때까지 기다렸다가 결과를 바로 반환 |

```bash
JOB=$(curl -sk -X POST https://localhost:5500/api/extract \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://blog.naver.com/<id>/<postNo>"}' | jq -r .job_id)
curl -sk https://localhost:5500/api/extract/result/$JOB
```

완료 응답(`status: "done"`)의 형태:

```json
{
  "status": "done",
  "success": true,
  "message": "Extraction completed successfully!",
  "platform": "naver",
  "formatted_text": "Title: ...\nURL: ...\nSource: ...\nAuthor: ...\nDate: ...\n\n====...\n\nContent:\n...",
  "result": { "url": "...", "title": "...", "author": "...", "date": "...", "content": "...", "parser": "...", "status": "success" }
}
```

**오류 응답**

| 코드 | 경우 |
|---|---|
| 400 | URL 누락, http/https가 아닌 URL, **내부 네트워크 주소**(아래 보안 참고) |
| 429 | 대기 중인 작업이 `EXTRACT_MAX_PENDING`개 이상 쌓임 → 잠시 후 재시도 |
| 404 | 없거나 만료된(30분) `job_id` |

`success: false`는 요청 자체는 처리됐지만 추출에 실패했다는 뜻입니다. HTTP 오류뿐 아니라
**페이지는 받았는데 본문을 찾지 못한 경우**(사이트 구조 변경, 봇 차단 페이지 등)도 실패로 보고합니다.
이 경우에도 `formatted_text`와 `result`는 그대로 들어 있습니다.

> 작업 저장소는 프로세스 메모리에 있습니다. 그래서 gunicorn은 **워커 1개 + 스레드 N개**로 띄워야 합니다
> (`Dockerfile` CMD). 워커가 여러 개면 작업을 등록한 워커와 폴링을 받는 워커가 달라져 작업을 찾지 못합니다.
> 실제 추출은 크기가 제한된 별도 워커 풀(`EXTRACT_WORKERS`)에서 돕니다.

---

## 환경 변수

`docker-compose.yml`에 기본값이 들어 있습니다. `.env` 파일로 덮어쓸 수 있습니다.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `EXTRACT_WORKERS` | `2` | 동시에 실행할 추출 작업 수. VLM 슬롯을 나눠 쓰므로 크게 잡을 이유가 없음 |
| `EXTRACT_MAX_PENDING` | `20` | 대기 + 실행 중 작업 상한. 넘으면 429 |
| `ALLOW_PRIVATE_URLS` | `0` | `1`이면 사설·루프백 주소 추출 허용 (사내망 페이지를 추출해야 할 때만) |
| `VLM_ENABLED` | `1` | `0`이면 이미지 해석을 끄고 URL·캡션 마커만 남김 |
| `VLM_BASE_URL` | `http://host.docker.internal:8081/v1` | VLM 서버(OpenAI 호환). 비우면 docker 호스트 → localhost 순으로 `/health` 탐색 |
| `VLM_MAX_IMAGES` | `8` | 게시물당 해석할 최대 이미지 수 |
| `VLM_CONCURRENCY` | `2` | 동시 해석 수. 서버 `--parallel` 값과 맞출 것 (4는 장당 속도 급락 → 타임아웃) |
| `VLM_TIMEOUT` | `150` | 이미지 1장 추론 타임아웃(초) |
| `VLM_TOTAL_BUDGET` | `360` | 게시물 하나의 이미지 해석 전체에 허용하는 시간(초). 넘으면 남은 이미지는 마커로 대체 |
| `VLM_MAX_DIM` | `1024` | 긴 변이 이보다 큰 이미지만 축소(작은 이미지는 원본 유지). **1024 밑으로 내리지 말 것**(잔글씨 전사 품질 저하) |
| `VLM_MAX_IMAGE_BYTES` | `15728640` | 이미지 1장 다운로드 상한(15MB). 넘으면 해석하지 않고 건너뜀 |
| `VLM_BATCH` | `0` | CLI 배치 수집에서도 이미지 해석을 켤지 여부 |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | (없음) | Reddit OAuth. 없으면 공개 `.json` → RSS 순으로 폴백 |
| `REDDIT_USER_AGENT` | `linux:content-extractor:v2.0 (personal use)` | Reddit API User-Agent |
| `LOG_DIR` | `logs` (컨테이너: `/app/logs`) | 파서별 일자 로그 파일 위치 |
| `LOG_TO_FILE` | `1` | `0`이면 콘솔에만 기록. 로그 폴더에 쓸 수 없으면 자동으로 콘솔 전용으로 전환 |
| `HTTP_IMPERSONATE` | `1` | 403(봇 차단)이면 `curl_cffi`로 크롬 TLS 지문을 흉내 내 1회 재시도. `0`이면 끔 |
| `HTTP_PROXY` / `HTTPS_PROXY` | (없음) | 사이트 요청에 쓸 프록시 |

---

## 지원 사이트와 플랫폼 감지

URL의 **호스트명**(필요하면 경로 접두사까지)으로 파서를 고릅니다. 서브도메인도 매칭하므로
`old.reddit.com`은 `reddit`, `m.blog.naver.com`은 `naver`로 갑니다. 등록되지 않은 도메인은 `generic` 파서가
처리합니다(og 메타·JSON-LD·`<article>` 휴리스틱).

감지 규칙과 파서 등록은 `src/crawler/factory.py`의 **`PLATFORMS` 표 한 곳**에서 관리합니다. 순서가 곧 우선순위라서,
더 구체적인 규칙(`naver_news`: `n.news.naver.com`, `news.naver.com/main`)을 포괄 규칙(`naver`: `naver.com`)보다 앞에 둡니다.

주요 사이트: Reddit, 네이버 블로그, 네이버 뉴스, The Verge, TechCrunch, Wired, Ars Technica, CNBC, NBC News,
Fortune, Business Insider, The Economist, SCMP, Substack, Gizmodo, Engadget, Axios, 404 Media, Tom's Hardware,
Google Research, OpenAI 등. 전체 목록은 `GET /api/parsers`로 확인할 수 있습니다.

### 네이버 블로그 본문 이미지 해석

네이버 블로그 파서는 SmartEditor 컴포넌트를 문서 순서대로 훑습니다. 이미지는 VLM(Qwen3-VL 8B, Windows 호스트
GPU, 포트 8081)으로 전사·해석한 뒤 **본문 속 원래 위치에** 끼워 넣습니다.

- VLM 서버는 부팅할 때 자동으로 시작되지 않습니다. 이미지 해석 결과가 비어 있으면 먼저 서버의 `/health`를 확인하세요.
- 서버가 꺼져 있거나 시간 예산을 넘겨도 추출 자체는 실패하지 않습니다. 해당 이미지 자리에 URL·캡션 마커만 남습니다.
- 이미지가 많으면 추출에 수 분이 걸립니다(동시 2장 기준 장당 약 30초). 정상 동작입니다.

---

## 아키텍처

```
web_app.py / gui_app.py
        │  URLValidator (형식 검사, 웹은 내부 주소 차단 추가)
        ▼
CrawlerService.extract_content(url)
        │  ParserFactory.detect_platform(url)  ← PLATFORMS 표 (호스트 매칭)
        │  ParserFactory.create_parser(name)   ← 모듈 지연 로딩
        ▼
<Site>Parser.parse_single(url) → dict            ← BaseParser 상속
        │  공용: BaseParser.fetch_html / parse_with_extractor
        │        ArticleParser · JsonLdExtractor · MetaTagExtractor (utils/article_extractor.py)
        │        CommonParserMixin (core/common_parser_mixin.py)
        ▼
parser.format_result(dict) → formatted_text
        │  본문이 비어 있으면 success=false 로 판정 (CrawlerService)
        ▼
ExtractionResult(success, message, formatted_text, raw_result, platform)
```

**파서 결과 규약**: `parse_single()`은 최소한 `url`, `status`(`'success'` 또는 오류), `title`, `author`, `date`,
`content`, `parser` 키를 가진 dict를 반환합니다. `status == 'success'`여도 `content`가 비었거나
`"No content found"`면(단, Reddit처럼 `comments`가 있는 경우는 제외) 서비스 계층이 실패로 판정합니다.

**JSON-LD**: 사이트 파서에서 JSON-LD를 직접 읽을 때는 `JsonLdExtractor.find_top_level_article(soup, types)`를 쓰세요.
비어 있거나 깨진 ld+json 블록은 건너뛰고, 블록마다 최상위 노드만 봅니다. `@graph` 안은 일부러 읽지 않습니다.
`@graph`의 author는 흔히 `@id` 참조뿐이라, 읽으면 HTML에서 찾던 작성자가 `Unknown`으로 퇴행합니다
(towardsdatascience에서 실측). 파서마다 `json.loads` 루프를 따로 두지 마세요.

---

## 새 파서 추가

1. `src/crawler/parsers/<site>_parser.py` 작성. 대부분의 사이트는 `parse_with_extractor`만으로 충분합니다.

   ```python
   import logging
   from typing import Any, Dict
   from crawler.core.base_parser import BaseParser
   from crawler.utils.rate_limiter import SimpleRateLimiter


   class ExampleParser(BaseParser):
       def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
           super().__init__(max_workers=max_workers or 1, log_level=log_level)
           self.rate_limiter = SimpleRateLimiter(delay=delay or 1.0)

       def _get_logger_name(self) -> str:
           return 'example_parser'

       def parse_single(self, url: str) -> Dict[str, Any]:
           self.rate_limiter.wait()
           return self.parse_with_extractor(
               url=url,
               parser_name='example',
               custom_content_selectors=[('div', {'class': 'article-body'}), ('article', {})],
           )
   ```

2. `src/crawler/factory.py`의 `PLATFORMS`에 한 줄 추가합니다. 이것만으로 등록과 URL 감지가 함께 됩니다.

   ```python
   ('example', 'example_parser', 'ExampleParser', ('example.com',)),
   ```

3. `tests/test_parsers.py`에 실제 URL 테스트(`@pytest.mark.network`)를 추가하고, 가능하면 고정 HTML로 된 오프라인 테스트도 추가합니다.
4. `docker compose build web && docker compose up -d web`. EXE는 `pyinstaller ContentExtractor_v2.spec`로 다시 빌드합니다.

HTTP 요청은 `BaseParser.fetch_html()`(기본 UA·프록시·타임아웃·`raise_for_status`·봇 차단 재시도 포함)을 쓰세요.
직접 요청해야 한다면 `crawler.utils.http_client.fetch(url, headers=..., timeout=...)`를 쓰세요.
cloudscraper 같은 세션은 `session=`으로 넘기면 됩니다. 어떤 경우든 **`timeout=`은 반드시** 지정하세요. 타임아웃이 없으면 응답 없는 서버 하나 때문에 추출 워커가 영구히 묶입니다.

---

## CLI (대량 수집)

```bash
# Reddit: 파일에 URL을 줄 단위로 적고 실행 → parsed_reddit/ 에 CSV·JSON·TXT
python scripts/crawler_main.py reddit input.txt --batch-size 10 --min-delay 2 --max-delay 4 --max-workers 3

# 네이버 블로그 → parsed_blogs/ 에 CSV·TXT (배치에서는 VLM 해석 기본 OFF, VLM_BATCH=1로 켬)
python scripts/crawler_main.py naver https://blog.naver.com/<id>/<postNo> ... --delay 1 --max-workers 3

# 오래된 결과 파일 정리
python scripts/crawler_main.py cleanup parsed_blogs --days 1
```

---

## 봇 차단 우회

많은 사이트가 요청 헤더가 아니라 **TLS/HTTP2 지문**으로 봇을 가려냅니다. 이런 곳은 브라우저 헤더를 똑같이 보내도
`requests`는 403을 받습니다. `utils/http_client.fetch()`는 1차 응답이 403이면 `curl_cffi`
(`impersonate='chrome'`)로 한 번 더 요청합니다.

2026-09-27 실측 결과:

| 사이트 | 차단 방식 | 결과 |
|---|---|---|
| openai, axios, engadget, gamespot, marktechpost | TLS 지문 | ✅ 재시도로 추출 성공 |
| nltimes | Cloudflare JS 챌린지 | ❌ curl_cffi·Wayback·archive.ph·RSS 모두 실패 |
| economist | Cloudflare JS 챌린지 + 유료벽 | ❌ RSS는 요약만 있고 본문 없음 |

JS 챌린지 사이트를 처리하려면 실제 브라우저(Playwright 등)가 필요합니다. 이미지 크기·메모리 부담이 크고,
헤드리스 브라우저도 챌린지에 걸리는 경우가 많아 도입하지 않았습니다.

---

## 보안 참고

- **내부 주소 차단 (SSRF 방지)**: 웹 API는 사용자가 준 URL을 서버가 대신 요청합니다. 그래서 호스트가
  사설·루프백·링크로컬 등 공인 주소가 아닌 곳으로 해석되면 400으로 거절합니다(예: `host.docker.internal`,
  `127.0.0.1`, `169.254.169.254`). 이 검사는 **처음 요청하는 URL만** 봅니다. 공개 주소가 내부 주소로
  리다이렉트하는 경우는 막지 못합니다. 포트 5500을 외부에 공개하지 마세요.
- nginx 인증서는 `generate-ssl.sh`로 만든 자체 서명 인증서입니다(LAN·개인용).
- 앱에는 인증이 없습니다. 신뢰할 수 있는 네트워크에서만 쓰세요.

---

## 문제 해결

| 증상 | 확인할 것 |
|---|---|
| 이미지 해석이 빠지고 URL 마커만 남음 | VLM 서버 `/health` (수동 시작 필요), `VLM_ENABLED`, 로그의 `VLM server not reachable` |
| 추출이 수 분 걸림 | 이미지가 많은 네이버 글이면 정상. 상한은 `VLM_TOTAL_BUDGET` |
| "요청이 많습니다"(429) | 실행·대기 중 작업이 `EXTRACT_MAX_PENDING`개 이상. 잠시 후 재시도 |
| "본문을 찾지 못했습니다" | 사이트 구조가 바뀌었거나 봇 차단 페이지. 해당 파서의 선택자 확인 |
| 403 Forbidden | 봇 차단. TLS 지문 차단은 자동 재시도로 통과합니다(아래 참고). Cloudflare JS 챌린지(`Just a moment...`)는 통과하지 못합니다 |
| Reddit 403 | 비인증 `.json` 차단. OAuth 키를 `.env`에 넣거나 RSS 폴백에 의존(점수·대댓글 구조 없음) |
| WSL2 절전 복귀 후 응답 없음 | `docker ps`의 health 상태와 `docker logs scraping-web-1`부터 확인 |

---

## 알려진 한계 / 후속 과제

- **파서 중복**: 16개 파서가 자체 fetch·파싱 코드를 갖고 있고, 제목·작성자·본문 추출 로직과 헤더 dict가 파일마다
  복사돼 있습니다. JSON-LD 루프는 공용 함수로 모았지만, 나머지는 `CommonParserMixin`/`ArticleParser`로 옮길 여지가 큽니다.
- `ArticleParser.parse_article`은 본문이 없어도 `status='success'`를 반환합니다. 현재는 서비스 계층에서 보정합니다.
- `zmescience` 파서는 TLS 검증을 끈 채(`verify=False`) 요청합니다.
- `fortune`·`verge`·`generic`·`naver_news` 파서는 생성자가 `max_workers`/`delay`를 받지 않습니다(현재 호출 경로에서는 문제없음).
- `pandas`를 모듈 최상단에서 import하므로 웹 앱 기동 시에도 로드됩니다(CLI·배치 저장에서만 필요).

---

## 변경 이력

### 2026-09-27 — 코드 리뷰 반영
- 플랫폼 감지를 URL 부분문자열 매칭에서 **호스트명 매칭**으로 변경했습니다. 이전에는 `?ref=reddit.com`,
  `notopenai.com`이 엉뚱한 파서로 갔습니다. 감지 규칙과 파서 등록을 `PLATFORMS` 표 하나로 통합했습니다.
- 웹 API: 요청마다 스레드를 새로 만들던 방식을 **크기 제한 워커 풀 + 대기열 상한(429)**으로 바꿨고, 작업 저장소를 앱 단위로 분리했습니다.
- 웹 API: **내부 네트워크 주소 요청 차단**. 이전에는 `host.docker.internal:8081` 같은 내부 서비스도 조회할 수 있었습니다.
- 본문 없이 `success`로 나오던 결과를 **실패로 보고**하도록 바꿨습니다.
- 네이버 블로그 파서: 모든 요청에 **타임아웃**(20초)·프록시를 적용하고, 404 등 **HTTP 오류 페이지를 성공으로 파싱하던 문제**를 수정했습니다.
- JSON-LD 루프가 복사돼 있던 8개 파서(analyticsindiamag, arstechnica, economist, gizmodo, marktechpost, samaltman,
  techafricanews, towardsdatascience)는 빈 배열이나 빈 블록 하나만 있어도 추출 전체가 error로 끝났습니다.
  이를 공용 `JsonLdExtractor.find_top_level_article`로 교체했습니다. 노드 선택 규칙은 기존과 동일합니다.
- 로거: 로그 폴더에 쓸 수 없으면 파서 생성이 실패하던 문제를 수정했습니다(콘솔로 폴백). `LOG_DIR`, `LOG_TO_FILE`을 추가했습니다.
- **봇 차단 자동 우회**: 403이면 `curl_cffi`로 크롬 TLS 지문을 흉내 내 재시도합니다(`utils/http_client.py`).
  openai·axios·engadget·gamespot·marktechpost 추출을 복구했습니다.
- VLM 클라이언트: 이미지 다운로드 **크기 상한**(스트리밍)을 두고, 기본값을 compose 실측값(동시 2장, 150초)에 맞췄습니다.
- Docker: **비루트 실행**, `HEALTHCHECK` 추가, 불필요한 빌드 도구(build-essential 등)를 제거했습니다.
- 테스트: `conftest.py`로 import 경로 의존을 없앴고, `testpaths=tests`로 제한했으며, 회귀 테스트를 추가했습니다(오프라인 192개).
- 호환성 검증: 실제 사이트 36건을 수정 전후 코드로 추출해 비교했습니다. 30건은 필드와 본문 해시까지 동일하고,
  5건은 실패에서 성공으로 바뀌었으며(봇 차단 우회), 1건은 본문 없는 결과를 실패로 보고하도록 바뀌었습니다.

### 2026-07 — 비동기 추출·VLM
- 추출 API 비동기화(job_id + 폴링), 네이버 블로그 본문 이미지 VLM 해석, 이미지 다운스케일 상한·전체 시간 예산.

### 2026-06 — Reddit 폴백
- Reddit 파서: OAuth → 공개 `.json` → RSS 3단계 폴백.

### v2.0.0 (2025-10)
- 출력 전략 레지스트리, Reddit 병렬 처리, 네이버 배치 처리, 댓글 깊이 제한.
