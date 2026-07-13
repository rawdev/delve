# 00. 개요 — 이 프로젝트는 무엇이고, 무엇이 성공인가

## 한 줄 요약

**웹 턴제 로그라이크 `Delve`를 실제로 만들면서, 그 개발 과정 전체를 AiAkiv에
저장하고 readonly로 공개한다. 데모의 주인공은 게임이 아니라 개발 궤적이다.**

방문자는 공개된 그래프에 직접 질문을 던져 "여러 사람·여러 AI가 함께 쌓은 공유
메모리"가 무엇을 할 수 있는지 체감한다. git 히스토리는 **무엇이** 바뀌었는지만
보여주지만, 공개 메모리는 각 결정의 **왜**(어떤 대안을 검토하고 왜 버렸는지)를
보여준다.

원 기획: `F:\Gemini\k2g-doc\ops\demo_scenario.md`

## 성공 기준 (측정 가능한 것만)

| 항목 | 목표 |
|---|---|
| 플레이 가능한 게임 | 5층 클리어 가능, 배포 URL에서 바로 플레이 |
| 공개 메모리 이벤트 수 | 80~120개 |
| 결정 이벤트 수 | 15개 이상 (4요소 전부 채워진 것만 카운트) |
| 목표 심문 쿼리 | [01_demo_goals.md](01_demo_goals.md)의 DQ/IQ/BQ/PQ 전부가 공개 그래프에서 납득 가능한 답을 냄 |
| 참여자 | 사람 2명(rawdev + 동료) + AI 2~3(Claude Code / ChatGPT / Gemini) |
| 커밋 provenance | 모든 결정·버그 이벤트에 커밋 해시가 붙어 있음 |
| 큐레이션 비용 | **0** — 처음부터 공개 전제로 저장하므로 나중에 지울 게 없다 |

게임이 재밌을 필요는 없다. **궤적이 진짜여야 한다.**

## 설계 원칙 네 가지 (전 문서를 지배함)

1. **쿼리 역산** — 방문자가 던질 질문을 먼저 확정하고, 그 질문에 좋은 답이 나오도록
   개발 과정을 통과시킨다. 그래프는 저절로 좋아지지 않는다. 답이 되는 사건이 과정
   안에 실제로 있어야 한다.
2. **작지만 진짜** — 게임 규모는 최소, 개발은 실제로. 연출된 히스토리는 개발자
   눈에 즉시 티가 난다. **미리 설계하는 통과 지점은 아키텍처 전환 1회뿐이며**
   ([04_turn_system_pivot.md](04_turn_system_pivot.md)), 그것도 로그라이크를 실제로
   만들면 겪는 일이다.
3. **버그는 심지 않는다** — 특정 버그를 심고 거기 맞는 쿼리를 만드는 순간 그게 제일
   작위적이다. 대신 **저장 규약**만 정한다: 모든 버그를 *증상 + 근본 원인 링크*로
   저장한다. 어떤 버그가 나오든 그래프가 인과를 물어올 준비가 된다.
4. **처음부터 공개 전제** — 저장 시점부터 "이건 공개된다"를 전제한다. 실명·키·비용·
   사적 잡담을 애초에 넣지 않으면 공개 전환 시 큐레이션이 필요 없다.

## 결정된 것 (이 문서 세트가 확정하는 범위)

- **스택**: FastAPI + 순수 Python 게임 엔진, 프레임워크 없는 단일 HTML 프론트.
  → 근거와 기각된 대안: [03_architecture.md](03_architecture.md) §1
- **사전 설계된 유일한 전환점**: 전투 턴 처리 = *즉시판정(lockstep)* → *에너지
  스케줄러*. 적 3종의 속도 차이가 이 전환을 강제한다.
  → [04_turn_system_pivot.md](04_turn_system_pivot.md)
- **원 기획의 "실시간 → 턴제 전환"은 폐기**. FastAPI 서버가 게임 본체인 구조에서
  실시간 전투는 애초에 존재할 수 없으므로 그 전환은 연출이 된다. 같은 자리(DQ1의
  답)를 위 전환점이 대체한다.

## 문서 지도

> **진행 상태의 단일 출처는 [05_roadmap.md](05_roadmap.md)의 체크박스 + AiAkiv 메모리다.**
> 이 문서를 포함해 다른 문서는 상태를 갖지 않는다. 별도의 PLAN/TODO 파일도 만들지 않는다.
> 세션 진입 규칙은 저장소 루트의 `CLAUDE.md`에 있다.

| 문서 | 내용 | 이걸 읽어야 할 때 |
|---|---|---|
| `CLAUDE.md` (루트) | **세션 진입 규칙** — 저장 규약, 금지 3가지, 불변식 | 매 세션 시작 (자동 주입) |
| [00_overview.md](00_overview.md) | 취지·성공 기준·원칙 (이 문서) | 처음 |
| [01_demo_goals.md](01_demo_goals.md) | 목표 심문 쿼리와 **쿼리 역산 표** | 무엇을 저장해야 하는지 판단할 때 |
| [02_game_design.md](02_game_design.md) | 게임 스펙 — 코어 루프, 던전, 적, 아이템, 밸런스 | 게임을 구현할 때 |
| [03_architecture.md](03_architecture.md) | 레이어, 상태 모델, API 계약, 결정론 | 코드를 짜기 전에 |
| [04_turn_system_pivot.md](04_turn_system_pivot.md) | **유일한 사전 설계 전환점** 상세 | Phase 1→2 경계에서 |
| [05_roadmap.md](05_roadmap.md) | Phase 0~5, 각 페이즈의 산출물 + 저장할 이벤트 | 매 세션 시작 시 |
| [06_memory_protocol.md](06_memory_protocol.md) | **저장 규약** — 결정/버그 필수 요소, 엔티티 이름, 태그 | 저장할 때마다 |
| [07_github_provenance.md](07_github_provenance.md) | 커밋 ↔ 이벤트 양방향 연결 | 커밋할 때마다 |
| [08_participants_workflow.md](08_participants_workflow.md) | 사람 2 + AI 3의 역할과 세션 운영 | 협업 세팅할 때 |
| [09_risks_checklist.md](09_risks_checklist.md) | 리스크, 공개 전환 체크리스트 | Phase 0과 Phase 5 |
| [10_running.md](10_running.md) | **실행 방법** — 설치, 서버 구동, 조작, 시드, 테스트 | 게임을 돌려보거나 플레이할 때 |

## 저장 대상 (AiAkiv)

- Team **AiAkiv-Roguelike** / Project **AiAkivRogueLike** / org `org_57670f180213`
- domain `default`, group `root`
- 본 계정 프로젝트 `k2g`와 **완전 분리** — 공개 전환 시 본체 데이터가 섞이지 않는다.

## 이 문서 세트에 대응하는 저장된 이벤트 (양방향 provenance)

| 이벤트 | 내용 | 근거 문서 | 커밋 |
|---|---|---|---|
| `evt_cb9a017f8342488badd283b5c3db6f24` | 프로젝트 취지 (최초 기억) | — | — |
| `evt_7f0846bfc503419599493d07176a94d0` | 결정 — 스택: FastAPI + 순수 Python 엔진 (TS+Canvas 기각) | [03_architecture.md](03_architecture.md) | `229aaac` |
| `evt_87b564e85ee14c4695bcec3435671e81` | 결정 — 사전 설계 전환점 교체 (실시간→턴제 폐기, 즉시판정→에너지 채택) | [04_turn_system_pivot.md](04_turn_system_pivot.md) | `229aaac` |
| `evt_d61ded1d63a44403857b5881457f70ff` | 결정 — 저장 규약 확정 + 문서 세트 | [06_memory_protocol.md](06_memory_protocol.md) | `229aaac` |
| `evt_1f08127e492f4077a9914836b843f164` | 구현 — Phase 0 첫 커밋. 위 세 결정에 해시를 연결 | 이 문서 | `229aaac` |

커밋 `229aaac`의 메시지에는 위 세 결정이 `ak:evt_` 트레일러로 들어가 있다 →
**양방향 provenance 성립.** → [07_github_provenance.md](07_github_provenance.md)
