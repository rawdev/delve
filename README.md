# Delve

웹 턴제 로그라이크. 그리고 **이 게임의 개발 과정 전체가 AI 공유 메모리로 남아
있습니다.**

- ▶ **플레이**: _(Phase 5에서 배포 — 준비 중)_
- 📦 **코드**: 이 저장소
- 🧠 **왜 이렇게 만들었나 (읽기 — 가입 불필요)**: _(Phase 5 — 준비 중)_
- 💬 **그래프에 직접 물어보기**: _(Phase 5 — AiAkiv 가입 시 Delve sample 프로젝트 제공)_

## 이게 뭔가요

git 히스토리는 **무엇이** 바뀌었는지 보여줍니다.
메모리는 **왜** 그렇게 했는지 — 어떤 대안을 검토하고 왜 버렸는지 — 를 보여줍니다.

이 프로젝트에서는 게임을 실제로 만들면서, 모든 설계 결정·버그 수정·밸런스 조정을
AiAkiv에 저장합니다. 사람 2명과 AI 3종(Claude Code / ChatGPT / Gemini)이 같은 메모리에
함께 쌓습니다.

**주인공은 게임이 아니라 개발 궤적입니다.** 게임이 재밌을 필요는 없고, 궤적이 진짜면
됩니다.

## 궤적을 보는 두 가지 방법

**읽기 (가입 불필요)** — 정적 페이지에서 이벤트·결정·인과를 그대로 읽습니다. 각 이벤트는
그것을 구현한 커밋으로 링크됩니다.

**물어보기 (AiAkiv 가입)** — 그래프에 직접 질문을 던집니다. **라이브 읽기전용**이라 개발이
진행되는 대로 최신 궤적이 보이고, 방문자가 그래프를 수정할 수는 없습니다.

- "전투 시스템 설계가 지금까지 어떻게 바뀌었어?"
- "적 AI 로직은 어떻게 구현됐어?" (설계·구현·리뷰를 각각 다른 AI가 했습니다)
- "가장 최근 버그랑 그 원인이 뭐야?"
- "인벤토리랑 세이브 포맷이 왜 같은 시점에 같이 바뀌었어?"

키워드 검색으로는 마지막 두 질문에 답할 수 없습니다 — 버그 텍스트와 원인이 된 설계 결정
텍스트에는 겹치는 단어가 없기 때문입니다.

## 게임

턴제 로그라이크. 절차 생성 던전 5층, permadeath, 적 3종 + 보스, 인벤토리.
한 칸 이동 = HTTP 요청 1개 → 서버가 한 턴 진행 → JSON 상태 반환.

- **백엔드**: FastAPI + 순수 Python 게임 엔진 (엔진은 프레임워크를 import하지 않습니다)
- **프론트**: 프레임워크 없는 단일 HTML. 처음엔 텍스트 그리드 (`@` 플레이어, `#` 벽)
- **에셋 0개** — 로그라이크는 그래픽 없이 태어난 장르입니다

## 직접 돌려보기

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

→ http://127.0.0.1:8000

의존성은 FastAPI + uvicorn 둘뿐입니다. Node도, 번들러도, DB 서버도 필요 없습니다.
이동은 방향키 또는 `hjkl`, **적이 있는 칸으로 이동하면 공격**입니다.

같은 시드는 항상 같은 던전을 만듭니다 — 버그를 발견하면 시드를 함께 적어주세요.
전체 실행 문서: **[docs/10_running.md](docs/10_running.md)**

## 설계 문서

| 문서 | 내용 |
|---|---|
| [docs/00_overview.md](docs/00_overview.md) | 취지·성공 기준·원칙 |
| [docs/01_demo_goals.md](docs/01_demo_goals.md) | 목표 심문 쿼리와 쿼리 역산 |
| [docs/02_game_design.md](docs/02_game_design.md) | 게임 스펙 |
| [docs/03_architecture.md](docs/03_architecture.md) | 아키텍처 |
| [docs/04_turn_system_pivot.md](docs/04_turn_system_pivot.md) | 유일한 사전 설계 전환점 |
| [docs/05_roadmap.md](docs/05_roadmap.md) | Phase 0~5 |
| [docs/06_memory_protocol.md](docs/06_memory_protocol.md) | 저장 규약 |
| [docs/07_github_provenance.md](docs/07_github_provenance.md) | 커밋 ↔ 이벤트 양방향 |
| [docs/08_participants_workflow.md](docs/08_participants_workflow.md) | 참여자와 세션 운영 |
| [docs/09_risks_checklist.md](docs/09_risks_checklist.md) | 리스크와 체크리스트 |

## 상태

**Phase 1 완료** — 코어 루프가 돕니다. 던전 5층, 이동/전투, Goblin, FOV, 레벨업,
permadeath. 턴 처리는 **v1 즉시판정**입니다 — Phase 2에서 적 3종(속도 150/100/60)을
넣으면 이 구조가 깨지고, 그때 에너지 스케줄러로 전환합니다.
왜 그렇게 하는지는 [docs/04_turn_system_pivot.md](docs/04_turn_system_pivot.md)에.

진행 상태의 단일 출처는 **[docs/05_roadmap.md](docs/05_roadmap.md)의 체크박스**입니다
(+ AiAkiv 메모리). 별도의 PLAN/TODO 파일은 두지 않습니다 — 상태를 이중 관리하면
어긋나고, "메모리가 계획 파일을 대체한다"는 이 프로젝트의 주장이 약해집니다.
