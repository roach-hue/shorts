# STEP 3c — Agent B 1-Hit 검증 (RULE 12)

> 조립 가안의 비트 정합을 1회 팩트체크. 서사모드는 bypass.

| 항목     | 값                |
| -------- | ----------------- |
| 🕒 일시  | 2026-06-24 23:15  |
| 🔖 커밋  | `189758e`         |
| 🎯 RULE  | RULE 12           |
| ✅ 테스트 | 12 passed         |

## 🎯 무슨 작업

- 엔진을 **Agent A / Agent B / orchestrator** 세 덩어리로 분리(코드에서 다중 에이전트 구조가 보이게).
- Agent B: strict 슬롯 전환이 비트(±0.1s)에 맞나 검증 / **flexible은 bypass** / 길이 미달 체크.
- **1-Hit**: 반려 시 재탐색 0회.

## 📂 변경 파일

| 파일                            | 내용                       |
| ------------------------------- | -------------------------- |
| `src/fallback_engine/engine.py` | `agent_b_validate` + 분리  |
| `tests/test_engine.py` · `fixtures.py` | off-beat/on-beat 케이스 +2 |

## 🔬 무결성 검증

```bash
$ python -m pytest
12 passed
```

- 적대 검증: **strict는 off-beat 반려 / flexible은 통과**(모드 분기 진짜).

## 📝 결과 / 관찰

- 반려 시 아직 placeholder `Reject(AGENT_B_REJECTED)` → 다음 구간(3d)에서 Fallback이 가로챔.
