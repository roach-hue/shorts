# 📍 STATUS — 프로젝트 총정리

> 지금까지 한 번도 안 봤어도, **이 문서 하나면 현재 상태가 전부 파악**되게 썼습니다.
> 기준 커밋: `189758e` · 저장소: https://github.com/roach-hue/shorts (public)

---

## TL;DR (30초 요약)

- **무엇:** 유행 숏폼의 *편집 문법*(컷 타이밍/비트/자막 구조)을 추출해, **사용자가 가진 실제 촬영본**을 그 빈칸에 의미 기반으로 자동 배치하는 엔진. 회사 포폴용.
- **진짜 IP:** "유저 영상을 박자표에 수학적으로 맞춰주는 다중 에이전트 매칭"(Agent A→B→Fallback). 나머지(영상 추출/브라우저/렌더)는 이미 상품화돼서 차별점 아님.
- **지금 상태:** 그 핵심 엔진의 **Agent A(매칭) + Agent B(검증)까지 구현 완료, 테스트 12개 전부 green.** 마지막 조각 **Fallback**만 남음.
- **다음:** Fallback 구현 → 핵심 IP 루프 완성.

## 0. 직접 확인하는 법 (1분)

```bash
cd c:\simhwa\shorts
python -m pytest          # => 12 passed
```
초록 12개 뜨면 정상. 코드는 [src/fallback_engine/](src/fallback_engine/), 테스트는 [tests/](tests/).

---

## 1. 이게 뭔 프로젝트인가

유행하는 YouTube Shorts URL을 넣으면 그 영상의 **편집 문법**(몇 초에 컷이 바뀌고, 비트가 어디 떨어지고, 자막이 어떻게 튀는지)을 숫자로 뽑아내고, 사용자가 올린 **자기 원본 클립들**을 그 슬롯에 "가장 잘 맞는 것"으로 자동 배치해 편집 결과를 만든다.

- **Fallback이 본체:** 완벽한 소스가 없어도 에러 대신 *가진 것 중 최선*을 욱여넣는 구조가 메인 엔진.
- **포지셔닝(시장 읽기):** 생성형(Bluma 등 — AI가 영상을 만듦)이 아니라 **실촬영본 채우기**. 2026년 AI영상 반감·진정성 프리미엄 데이터(실제 사람 영상 신뢰 78%, AI 창작 선호 60→26% 붕괴, Sora 소비자앱 종료)가 이 방향을 뒷받침. 검증 스코프는 국내 푸드 쇼츠로 한정, 아키텍처는 도메인 비종속.
- **상세 기획:** [PROJECT_PLAN.md](PROJECT_PLAN.md), 규칙 [schema_decisions.md](schema_decisions.md)(RULE 1~13).

---

## 2. 어디까지 했나 (진행 표)

| STEP | 내용 | 상태 |
|------|------|------|
| 1 | 스키마 모순 4종 + 단위 결정 | ✅ |
| 2 | **하네스(오라클)** — 불변식 + 합성 케이스 + config 노브 | ✅ |
| 3 (Agent A) | 3축 스코어링(RULE6) + 슬롯순서고정(RULE4) + Soft Penalty(RULE10) + strict 채우기(RULE8/12) | ✅ |
| 3c (Agent B) | 1-Hit 비트 검증(RULE12), 서사모드 bypass | ✅ |
| **다음** | **Fallback** — 반려 시 오디오 리듬 강제할당(RULE11/12) | ⏸ |
| 이후 | Yellow(추출) / Blue(브라우저) / Pink(렌더) | ⬜ 미착수 |

**테스트: 12 passed.** 코드 라인 기준 핵심 엔진은 동작하는 상태.

---

## 3. 어떻게 일하기로 했나 (방법론 + 룰)

### 방법론 — "하네스 우선"
엔진보다 **"정답 기준(오라클)"을 먼저** 코드로 박았다. 그래야 (1) 자율 개발에 검증 신호가 생기고 (2) "지금만 통과하는 눈속임"을 막는다.
오라클 = **불변식**(RULE을 코드 단언으로) + **합성 forced 케이스**(입력을 답이 하나로 강제되게 구성) + config 노브.

### 단단함 등급 (오라클 붕괴 방지)
| 부위 | 등급 |
|------|------|
| 불변식(RULE) | 법 — 단단. 스펙 개정으로만 변경 |
| 임계값(±0.1s, 0.7, 50/30/20) | 노브 — [config/thresholds.json](config/thresholds.json)에서 자유 |
| 레퍼런스 영상 | 데이터 — fixture 교체 자유 |

### 작업 규칙 ([CLAUDE.md](CLAUDE.md))
1. **병렬개발 금지** — 한 번에 하나. 개발은 백그라운드 워크플로우 말고 직접 포그라운드에서.
2. **scope 확장 금지** — 정의된 범위만.
3. **큰 줄기 먼저, 잔가지 나중.**
4. **눈속임 금지** — 항상 원인부터. 원인이 스키마/계약 건드리면 멈추고 flag.

---

## 4. 핵심 의사결정 — 스키마 모순 5종 ([decisions/](decisions/schema_contradictions.md))

| # | 모순 | 결정 |
|---|------|------|
| ① | 음원 vs 비트 타임스탬프 | 음원 폐기, **비트 타임스탬프 유지**(엔진 존재 이유) |
| ② | `bgm` 필드 vs "BGM 금지" | **bgm 제거**, 결과물 BGM 없음 |
| ③ | `speed` 스칼라 vs 배열 | **스칼라**, speed_ramp는 스코프 밖 |
| ④ | 제공 골든이 입력과 불일치 | **폐기 → 합성 골든** |
| ⑤ | ms vs 초 | **전부 초(seconds)로 통일** |

---

## 5. 아키텍처 — Core Engine

```
입력(template.json + asset_db.json)
   │
   ▼
[RULE7 게이트] 소스 총량 미달 → Reject(SOURCE_INSUFFICIENT)
   │ 통과
   ▼
[Agent A: 그리디 매칭]  슬롯 순서 고정(RULE4)
   • 점수 = 0.5·코사인(semantic, RULE6) + 0.3·motion + 0.2·duration
   • 재사용 시 ×0.7 Soft Penalty(RULE10) — 영구폐기 없음(수미상관)
   • strict 슬롯: cut.duration에 맞춰 Trim/배속, 비트에 핀 고정(RULE8/12)
   │
   ▼
[Agent B: 1-Hit 검증, RULE12]
   • strict 슬롯 전환이 비트(±0.1s)에 맞나? / 서사모드는 bypass
   • 조립 길이가 템플릿 길이 채우나?
   │
   ├─ 통과 → edit_instruction.json ✅
   └─ 반려 → (1-Hit, 재탐색 0회) → [Fallback] ⏸ 아직 빈자리
                                    └ 현재는 Reject(AGENT_B_REJECTED) 플레이스홀더
```

세 덩어리(`_agent_a_assemble` / `agent_b_validate` / `assemble` 오케스트레이터)로 **코드에서 다중 에이전트 구조가 그대로 보이게** 분리함 → [engine.py](src/fallback_engine/engine.py).

---

## 6. 코드 맵

```
c:\simhwa\shorts\
├─ STATUS.md                         ← 이 문서
├─ CLAUDE.md                         ← 작업 룰
├─ decisions\schema_contradictions.md ← 모순 5종 결정(근거표)
├─ config\thresholds.json            ← 임계값 노브
├─ src\fallback_engine\
│   ├─ schemas.py                     ← 데이터 계약(pydantic): Template/AssetDB/EditInstruction
│   ├─ invariants.py                  ← 오라클(불변식 = RULE을 코드로)
│   ├─ engine.py                      ← Core Engine: Agent A / Agent B / orchestrator
│   └─ config.py                      ← 노브 로더
├─ tests\
│   ├─ fixtures.py                    ← 합성 forced 케이스
│   ├─ test_schemas.py               ← 계약 검증
│   ├─ test_invariants.py            ← 오라클 자체 검증
│   └─ test_engine.py                ← 엔진 행동 검증
└─ docs\schemas\                      ← 원본 예시 JSON(참고용)
```
*기획 문서:* PROJECT_PLAN / schema_decisions / tech_stack_decisions / expansion_roadmap (루트).

---

## 7. 지금 통과하는 12개 테스트 = "증명된 것"

**계약([test_schemas.py](tests/test_schemas.py), 3):** template/asset_db 로드 OK · 구버전 골든(bgm/speed_ramp)은 거부됨(②③④ 강제 증명).

**오라클([test_invariants.py](tests/test_invariants.py), 4):** 오라클이 정상 출력 통과 · 슬롯순서 위반(RULE4) 적발 · 싱크플래그 불일치(RULE13) 적발 · 소스부족(RULE7) 판별. → *오라클이 진짜 작동함을 먼저 증명.*

**엔진([test_engine.py](tests/test_engine.py), 5):**
- 소스 부족 → Reject (RULE7)
- 세그먼트 1개·슬롯 2개 → 재사용+수미상관 (RULE10)
- 의미 매칭: 컷 벡터에 맞는 세그먼트가 슬롯 차지 (RULE6 코사인)
- Agent B: 비트에 맞으면 통과
- Agent B: strict 슬롯 off-beat이면 반려 (RULE12)

> 추가로 적대적 수동 검증 완료: 컷 벡터 뒤집으면 승자도 뒤집힘(코사인 진짜) · strict는 반려/flexible은 bypass(모드 분기 진짜). **하드코딩 0.**

---

## 8. 아직 안 한 것 / 알려진 한계 (정직하게)

**다음 작업:**
- **Fallback** — Agent B 반려 시 시각 매칭 포기, 오디오 리듬 기준 강제 할당(RULE11/12). 이거 하면 핵심 IP 루프 완성.
- 그 후: **Yellow**(yt-dlp/librosa/PySceneDetect/VLM/OCR 추출), **Blue**(브라우저 전처리), **Pink**(FFmpeg 렌더). — 전부 미착수.

**스코프 밖(의도적 미구현):** speed_ramp 구간배속, Cascading Shift, RULE11 슬라이더 실모델 보정, 실제 임베딩/VLM 모델(지금은 제공 벡터 사용), Yellow/Blue/Pink.

**알려진 마이너 메모(버그 아님, 나중에 손볼 것):**
1. `engine.py`가 `invariants`의 헬퍼를 import — 결합도 냄새(공용 util로 분리 권장).
2. 길이 0 세그먼트 엣지케이스 → speed=0 나눗셈 방어 필요.
3. 짧은 클립을 슬롯에 "느리게 늘려" 채우는 설계 선택 — 재검토 대상.

**검증 vs 데모:** 지금은 **합성/Mock 데이터로 엔진 로직을 검증**한 단계. 실제 영상으로 결과물 mp4를 뽑는 데모는 아직(Yellow+Pink 필요).

---

## 9. 왜 이 부분을 만드나 (시장 메모)

- 컨셉 자체는 더 이상 신박하지 않음 — **Bluma**(YC F25, 생성형, 바이럴 구조 복제)가 유사 방향으로 펀딩받아 성장 중. CapCut도 비트싱크 템플릿 슬롯 채우기를 출시(수동 배치).
- **남은 차별점:** "임의 URL 자동 역설계 + **내 실촬영본** 의미 기반 자동 배치" — 이건 아직 표준 출시 기능 아님. 그게 곧 이 **Core Engine**.
- 그래서 포폴은 *"잘 만든 엔진 + 시장 안목"*으로 승부. 커모디티 부분(비트싱크/자막/렌더)은 "의도적으로 재발명 안 함"으로 명시.

---

## 10. git / 잔디

| 커밋 | 내용 |
|------|------|
| `078ee58` | Init: 하네스(오라클) + 트렁크 |
| `457a129` | STEP 3b: semantic 코사인(RULE6) |
| `189758e` | STEP 3c: Agent B 1-Hit 검증(RULE12) |

author = `roach-hue <roach2812@gmail.com>` → 잔디 카운트. 단계 끝낼 때마다 커밋 1개 = 잔디 1칸.
