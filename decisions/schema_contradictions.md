# 스키마 모순 결정 로그 (Schema Contradiction Decisions) — Artifact A

> 하네스 오라클을 코드로 박기 전에 닫아야 했던 "정답 계약"의 모순들.
> 이 결정들은 **불변식(invariant)** 으로 코드에 박혀 있으며, 바꾸려면 "스펙 개정"이라는
> 의식적 절차를 거친다(평소엔 단단히 고정 = 자기충족 오라클 함정 방지).
> 관련 코드: [`src/fallback_engine/schemas.py`](../src/fallback_engine/schemas.py),
> [`src/fallback_engine/invariants.py`](../src/fallback_engine/invariants.py)

---

## 결정 요약 표

| # | 모순 | 결정 | 정본 근거 | 코드 영향 |
|---|------|------|-----------|-----------|
| ① | BLOCKER-01: 음원 파일 vs 비트 타임스탬프 | **파일은 폐기, `beat_timestamps`(숫자 배열)는 유지** | 둘은 차원이 다름. 파일=저작권 리스크, 타임스탬프=숫자(아이디어/사실, 저작권 비대상). 타임스탬프가 없으면 Agent A/B의 ±tolerance 검증·Speed 연산이 성립 불가 = **엔진 존재 이유 소멸** | `Template.beat_timestamps` 유지, 음원 관련 필드 없음 |
| ② | `bgm` 필드 vs "BGM 삽입 금지" RULE | **출력에서 `bgm` 필드 제거. 결과물은 BGM 없음** | 제공 `edit_instruction.json`의 `bgm` 블록은 PROJECT_PLAN("BGM 없음")·Pink RULE("삽입 금지")·BLOCKER-01("1바이트도 저장 안 함")과 정면 충돌. **샘플이 틀린 것** | `EditInstruction`에 `bgm` 없음 + `extra="forbid"`로 강제 |
| ③ | `speed` 스칼라 vs `speed_ramp` 배열 | **`speed` = 스칼라(float). `speed_ramp`는 MVP 스코프 아웃** | `speed_ramp`(구간 가변배속)는 setpts split+atempo 체이닝 A-V 싱크 = 렌더 단계 시간 블랙홀. 코어 매칭 검증엔 불필요. `schema_decisions.md` RULE 8도 스칼라(`"speed":2.0`)로 기술 | `EditClip.speed: float`, `speed_ramp` 필드 없음(`extra="forbid"`) |
| ④ | 골든 불일치 (제공 출력이 입력 template과 구조 불일치) | **제공 `edit_instruction.json`을 골든에서 폐기. 합성 골든(불변식+forced 케이스)으로 대체** | 제공 골든은 template(2컷)과 출력(3슬롯+bgm+speed_ramp)이 구조 불일치 → 정답으로 못 씀. 대신 RULE을 불변식으로, 입력을 답이 강제되게 구성 | `tests/fixtures.py` = 합성 forced 케이스. 제공 샘플은 "스키마 형태 참고"로만 |
| ⑤ | (보너스 발견) 시간 단위: ms vs 초 | **모든 시간 필드 = 초(float) 통일** | RULE 3은 ms, 예시 JSON은 초(`1.200`). cut `in/out/duration`이 명백히 초라 전체를 초로 통일(한 파일 단위 혼용 = 버그 자석). ms는 추출 내부 표현으로만 | 모든 시간=초. `±100ms` → `config.beat_tolerance_sec = 0.1` |

---

## 항목별 상세

### ① BLOCKER-01 — 음원 vs 비트 타임스탬프 → **타임스탬프 유지**
- **무엇을 버리나:** MP3 등 음원 파일은 시스템에 저장/사용하지 않는다(저작권).
- **무엇을 지키나:** `beat_timestamps`(초 단위 숫자 배열)와 `BPM`. 이건 컷 전환 타이밍의 수학적 뼈대다.
- **왜:** 사용자가 틱톡에 유행 음원을 씌웠을 때 컷이 박자에 떨어지려면 박자표가 필요. 박자 무시 시 Agent A의 Speed/Trim, Agent B의 ±tolerance 검증이 전부 무의미 → 다중 에이전트 IP 소멸.
- **PENDING.md BLOCKER-01 해제됨.**

### ② bgm 필드 → **제거**
- 결과물은 화면(영상)만. BGM은 사용자가 플랫폼(틱톡/인스타)에서 사후에 직접 씌운다.
- `EditInstruction` / `EditClip`에 `extra="forbid"`를 걸어, `bgm`을 포함한 구버전 출력은 **스키마 단계에서 거부**된다(테스트로 검증).

### ③ speed → **스칼라 정본**
- `EditClip.speed: float = 1.0`. 한 클립에 단일 배속만.
- 구간별 가변배속(`speed_ramp`)은 렌더(Pink) 난제이자 코어 매칭과 무관 → 추후 확장으로 분리(현재 stub 없음, 필드 자체를 두지 않음).

### ④ 골든 불일치 → **합성 골든으로 대체**
- 제공 `docs/schemas/edit_instruction.json`은 입력과 정합되지 않으므로 **정답으로 신뢰 불가**.
- 대신 오라클을 (a) **불변식**(RULE 직역) + (b) **forced 합성 케이스**(입력을 답이 하나로 강제되게 설계) + (c) 최소 스냅샷으로 구성.
- 제공 3종 JSON은 "스키마 형태"의 참고로만 사용(`test_schemas.py`가 template/asset_db는 로드되고, 구버전 edit_instruction은 거부됨을 검증).

### ⑤ 시간 단위 → **초(seconds)로 통일** (보너스)
- 외부 계약(3종 JSON)의 모든 시간 필드는 **초(float)**.
- `±100ms` 등 허용오차는 `config/thresholds.json`의 `beat_tolerance_sec: 0.1`로 표현(노브).
- ms는 추출 파이프라인(Yellow) 내부 표현으로만 허용하고, 경계를 넘는 계약에서는 항상 초.

---

## 단단함 등급 (오라클 붕괴 방지)

| 부위 | 등급 | 변경 절차 |
|------|------|-----------|
| 불변식(RULE 4·7·10·12·13·8) | **법 (단단)** | 스펙 개정으로만. 출력이 맘에 안 든다고 못 바꿈 |
| 임계값/가중치(±0.1s, 0.7, 2.5x, 50/30/20) | 노브 (무름) | `config/thresholds.json` 수정 |
| 레퍼런스 영상 | 데이터 (자유) | fixture 파일 교체 (저조회수→고조회수 등) |
| 스냅샷 케이스 | 재축복 | 의식적으로 "다시 OK" 표기할 때만 |
