# 10. 실행 방법 — 개발 환경과 플레이

> ✅ **Phase 1 완료 — 아래 명령이 실제로 동작한다.** (커밋 `84d6eca` 이후)
>
> 이 문서는 원래 "Phase 1이 만족시켜야 할 **실행 계약**"으로 쓰였다. 계약을 먼저
> 못 박은 덕에 실제로 하나가 잡혔다 — 문서에 `pytest`라고 적어뒀는데 실제로는
> `ModuleNotFoundError`로 죽었다(`pyproject.toml`로 수정). 계약이 없었으면
> `python -m pytest`로 돌려보고 넘어갔을 것이고, 문서를 따라한 사람은 첫 명령에서
> 막혔을 것이다.
>
> **현재 플레이 가능한 것**: 던전 5층, 이동/전투, Goblin, FOV, 레벨업, permadeath.
> **아직 없는 것**: 인벤토리·아이템(Phase 2), 적 3종·보스(Phase 2), 세이브(Phase 4).

## 1. 요구사항

| 항목 | 버전 | 비고 |
|---|---|---|
| Python | **3.12+** | `dataclass`, 타입 힌트 최신 문법 사용 |
| 브라우저 | 아무거나 | 텍스트 그리드만 그린다. 빌드 도구 없음 |

**필요 없는 것**: Node.js, npm, 번들러, DB 서버, 로그인, 계정.
Phase 4의 세이브도 SQLite 파일 하나라 별도 설치가 없다.

의존성은 **FastAPI + uvicorn 둘뿐이다.** 게임 엔진(`engine/`)은 순수 Python +
표준 라이브러리만 쓴다 — [03_architecture.md](03_architecture.md) §2의 불변식 1.

## 2. 설치

```bash
git clone https://github.com/rawdev/delve.git
cd delve

python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

`requirements.txt` (Phase 1에서 생성):

```
fastapi
uvicorn[standard]
```

> **의존성이 늘어나면 그건 결정이다.** 새 패키지를 추가할 때는 `결정` 이벤트로
> 저장한다 (무엇을 / 왜 / 표준 라이브러리로 안 되는 이유 / 커밋).
> "의존성 최소"는 이 프로젝트의 제약이지 취향이 아니다.

## 3. 실행 (개발 서버)

```bash
uvicorn app.main:app --reload
```

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

브라우저에서 **http://127.0.0.1:8000** 을 연다. 바로 새 게임이 시작된다.

`--reload`는 코드를 고치면 서버를 자동 재시작한다. **단, 서버가 재시작되면 진행 중인
게임이 전부 날아간다** — 상태가 프로세스 메모리에 있기 때문이다
([03_architecture.md](03_architecture.md) §5). Phase 4의 세이브 구현 전까지는 정상 동작이다.

## 4. 조작

| 키 | 동작 |
|---|---|
| 방향키 또는 `h` `j` `k` `l` | 이동. **적이 있는 칸으로 이동 = 공격** (별도 공격 키 없음) |
| `.` | 대기 (턴만 소비) |
| `g` | 아이템 줍기 |
| `i` | 인벤토리 열기 |
| `>` | 계단(`>`) 위에서 다음 층으로 |

### 화면 읽는 법

| 기호 | 의미 |
|---|---|
| `@` | 플레이어 |
| `#` | 벽 |
| `.` | 바닥 |
| `>` | 내려가는 계단 |
| `r` | Rat — 약하지만 **플레이어보다 1.5배 빠르다** |
| `g` | Goblin — 표준. HP가 낮아지면 도망친다 |
| `G` | Golem — 느리지만 아프다 |
| `W` | **Delve Warden** (5층 보스). HP 절반 이하에서 빨라진다 |
| `!` `/` `[` `?` | 포션 / 검 / 방패 / 귀환 스크롤 |

밝게 보이는 곳 = 현재 시야(FOV 반경 8). 어둡게 보이는 곳 = 가봤지만 지금은 안 보이는 곳.
공백 = 미탐색.

**목표**: 5층까지 내려가 Delve Warden을 잡는다. **죽으면 처음부터** (permadeath).

## 5. 시드 지정 — 버그 리포트와 플레이테스트의 핵심

같은 시드는 **항상 같은 던전**을 만든다 ([03_architecture.md](03_architecture.md) §6).

```bash
# 특정 시드로 새 게임
curl -X POST http://127.0.0.1:8000/api/game -H "Content-Type: application/json" -d '{"seed": 42}'
```

응답에는 **시드가 항상 포함된다.** 시드를 지정하지 않아도 서버가 생성한 시드가
돌아온다.

> **버그를 발견하면 시드를 반드시 적는다.** `seed=42, floor=2, turn=137` 형태.
> 시드가 없는 버그 리포트는 재현이 안 되고, 재현이 안 되면 근본 원인을 못 찾고,
> 근본 원인을 못 찾으면 `docs/06_memory_protocol.md` §2의 버그 이벤트를 규약대로
> 저장할 수 없다. **BQ1·BQ2가 시드에 걸려 있다.**
>
> 동료 플레이테스트(Phase 3)도 마찬가지 — "3층이 너무 어렵다"가 아니라
> "seed=42의 3층에 Golem 2마리가 붙어 있어서 무리다"여야 재현되고, 재현되어야
> 밸런스 결정이 근거를 갖는다.

## 6. API 직접 호출 (디버깅 / 자동 플레이)

프론트 없이 서버만으로 게임이 성립한다 — 이게 "Python이 게임 본체"라는 말의 의미다.

```bash
# 새 게임
curl -X POST http://127.0.0.1:8000/api/game -H "Content-Type: application/json" -d '{"seed": 42}'

# 한 칸 이동 (한 턴 진행)
curl -X POST http://127.0.0.1:8000/api/game/{game_id}/action \
  -H "Content-Type: application/json" -d '{"type": "move", "dir": "north"}'

# 현재 상태
curl http://127.0.0.1:8000/api/game/{game_id}
```

FastAPI 자동 문서: **http://127.0.0.1:8000/docs**

> Phase 2의 턴 시스템 전환 이후 `action` 응답에 `events[]` 배열이 추가된다.
> 플레이어 1입력에 Rat이 2번 행동할 수 있기 때문이다
> ([04_turn_system_pivot.md](04_turn_system_pivot.md)). API 계약이 바뀌는 지점이다.

## 7. 테스트

```bash
pip install -r requirements-dev.txt
pytest
```

**런타임 의존성은 여전히 둘(fastapi + uvicorn)뿐이다.** `requirements-dev.txt`는 테스트
전용이고 배포 컨테이너에 들어가지 않는다 — "의존성 둘뿐"이라는 주장의 실체는 *배포되는
것에 뭐가 들어가나*이지 저장소의 requirements 파일 개수가 아니다.

엔진이 순수 Python이라 **엔진 테스트는 HTTP 없이 돈다.** `app/`의 경계만 `TestClient`로
검증하고, 그것 때문에 `httpx`가 테스트 의존성에 들어간다.

| 테스트 | 검증 | 도입 |
|---|---|---|
| `tests/test_dungeon.py` | 같은 시드 → 같은 맵 (결정론), 도달 가능성 | Phase 1 |
| `tests/test_turn_v1.py` | v1 즉시판정 가드 — **Phase 2에서 깨져야 정상** | Phase 1 |
| `tests/test_api.py` | HTTP 계약 (404/409/422), 정보 은닉, **동시성 직렬화** | Phase 1 |
| `tests/test_turn.py` | 속도 150/100/60의 행동 횟수 비율 | **Phase 2 (전환 후 필수)** |
| `tests/test_serialize.py` | 저장 → 로드 → 상태 동일 (`rng_state` 포함) | Phase 4 |

> **동시성 테스트는 결과가 아니라 겹침 자체를 관측한다.** 처음엔 "N번 요청 → turn == N"으로
> 썼는데 **Lock을 지워도 통과했다** — GIL 아래에서 `turn += 1`의 경합 창이 너무 좁아
> 우연히 안 터진 것이다. 경쟁 조건이 실재하는데 테스트가 못 잡는 상태였고, 그건 방어선이
> 아니라 방어선이 있다는 착각이다. 지금은 "같은 게임을 두 요청이 동시에 처리 중인 순간이
> 있었나"를 직접 센다 — Lock을 지우면 반드시 실패한다.

## 8. 배포 (Phase 5)

Railway. 단일 컨테이너, 빌드 스텝 없음.

```bash
# Procfile
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

배포 후 [07_github_provenance.md](07_github_provenance.md) §5의 README **4종 링크**
(플레이 URL / GitHub / 정적 메모리 페이지 / AiAkiv sample 프로젝트)를 채운다.

## 9. AiAkiv 메모리 연결 (개발자용)

이 저장소의 `.mcp.json`이 AiAkiv MCP 서버를 가리킨다:

```json
{ "mcpServers": { "AiAkiv": {
  "type": "http",
  "url": "https://mcp.aiakiv.com/mcp",
  "headers": { "X-K2G-Project": "AiAkivRogueLike" }
} } }
```

**시크릿이 없다.** 공개(Phase 5) 후에는 방문자가 이 파일을 그대로 써서 자기 AI에 연결하고
개발 히스토리에 직접 질문할 수 있다 — 저장소 자체가 데모의 일부다.

> **단, AiAkiv 계정이 필요하다.** 비인증 방문자에게 그래프를 여는 기능은 없다(R1).
> 가입하면 `Delve` sample 프로젝트를 **라이브 읽기전용**으로 받고, 그때 이 `.mcp.json`이
> 그대로 동작한다. 가입 없이 궤적만 읽고 싶다면 **정적 메모리 페이지**를 보면 된다.
> → [09_risks_checklist.md](09_risks_checklist.md) R1

개발 세션 시작 시:

```
ak target 확인          → AiAkivRogueLike 인지 확인
ak 지난 세션 뭐 했지?    → 컨텍스트 회수
```

→ [08_participants_workflow.md](08_participants_workflow.md) §5

## 10. 문제 해결

| 증상 | 원인 / 조치 |
|---|---|
| 서버 재시작 후 게임이 사라짐 | **정상.** 상태가 인메모리다. Phase 4의 세이브가 해결한다 |
| `ModuleNotFoundError: fastapi` | 가상환경을 활성화하지 않았다 |
| 같은 시드인데 던전이 다르다 | **버그다.** `engine/rng.py`를 안 거치고 `random`을 직접 호출한 코드가 있다 ([03_architecture.md](03_architecture.md) §2 불변식 3). 시드와 함께 이슈로 등록하고, 규약대로 "증상 + 근본 원인"으로 저장한다 |
| 적이 이상한 횟수로 움직인다 | Phase 2 전환 직후라면 에너지 스케줄러 버그일 수 있다. `tests/test_turn.py`부터 확인 |
