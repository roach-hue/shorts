# STEP 3d-2 — Fallback 발산 관측 + 다후보 골든 (옵션 4)

> 후보가 여럿일 때 Fallback(rhythm-only)이 Agent A(semantic)와 **다르게** 고른다는 걸 골든으로 증명 + 로그에 관측.

| 항목     | 값                |
| -------- | ----------------- |
| 🕒 일시  | 2026-06-26 21:50  |
| 🔖 커밋  | `347a88e`         |
| 🎯 RULE  | RULE 6 / 12       |
| ✅ 테스트 | 17 passed         |

## 🎯 무슨 작업

- **다후보 골든**: `semantic_pick`(의미매칭·저모션) vs `motion_pick`(무의미·고모션) — 둘 다 충분히 김.
- **on-beat** 템플릿 → Agent B 통과 → Agent A가 `semantic_pick`(0.73). **off-beat** → Agent B 반려 → Fallback이 `motion_pick`(0.485).
- 엔진이 Fallback picks vs Agent A picks를 비교해 `diverged_from_agent_a` + `fallback_divergence` 이벤트를 로그에 기록.

## 📂 변경 파일

| 파일                              | 내용                                       |
| --------------------------------- | ------------------------------------------ |
| `tests/fixtures.py`               | `scenario_diverge_onbeat/offbeat` + `_diverge_assets` |
| `src/fallback_engine/engine.py`   | `fallback_divergence` 관측 로깅            |
| `tests/test_engine.py`            | +1 (발산 골든)                             |

## 🔬 무결성 검증

```bash
$ python -m pytest
17 passed
```

`logs/runs.jsonl` 확인:

```json
"fallback_divergence": {"diverged": true, "agent_a": [[1,"semantic_pick"]], "fallback": [[1,"motion_pick"]]}
```

## 📝 결과 / 관찰

- **단일 후보** → `diverged=false`(약점 그대로 노출). **다후보** → `diverged=true` → Fallback이 진짜 다르게 고름 = **A의 no-op clone 아님** 증명.
- 이로써 **Fallback refine(옵션1 정직표시 + 옵션4 발산관측) 묶음 완료.**
- 출력 자체 개선(비트 스냅)은 Cascading Shift 스코프라 여전히 보류.
