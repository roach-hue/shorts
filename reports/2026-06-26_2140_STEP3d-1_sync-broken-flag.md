# STEP 3d-1 — Fallback 싱크 깨짐 정직 표시 (RULE 13)

> Fallback이 못 고친 off-beat을 `is_original_sync_broken=true`로 정직하게 신고.

| 항목     | 값                |
| -------- | ----------------- |
| 🕒 일시  | 2026-06-26 21:40  |
| 🔖 커밋  | `ac2d37e`         |
| 🎯 RULE  | RULE 13           |
| ✅ 테스트 | 16 passed         |

## 🎯 무슨 작업

- `offbeat_strict_slots` **공용 헬퍼**로 비트 체크 단일화 → Agent B / 플래그 / 불변식이 한 기준 사용(중복 제거).
- RULE 13 확장: 플래그 = `(Cascading Shift)` **OR** `(off-beat strict 슬롯)`. 불변식도 같이 갱신해 거짓 플래그를 적발.
- Fallback 결과가 여전히 off-beat이면 `is_original_sync_broken=true` set + `sync_check` 로깅.

## 📂 변경 파일

| 파일                                | 내용                                     |
| ----------------------------------- | ---------------------------------------- |
| `src/fallback_engine/invariants.py` | `offbeat_strict_slots` + `inv_sync_broken_flag` 확장 |
| `src/fallback_engine/engine.py`     | Agent B가 헬퍼 재사용 + Fallback 플래그 set |
| `tests/test_engine.py`              | +1 (fallback flags sync broken)          |

## 🔬 무결성 검증

```bash
$ python -m pytest
16 passed
```

- `logs/runs.jsonl` 확인: `sync_check: fail`, `is_original_sync_broken: true`, `offbeat_slots: [2]`.
- 성공 경로는 플래그 `false` 유지(테스트로 고정).

## 📝 결과 / 관찰

- 못 고칠 땐 **솔직히 신고**(Pink가 사용자에게 싱크 경고 가능).
- 출력 자체를 고치는 **비트 스냅**은 Cascading Shift(스코프 밖)라 보류 → 별도 스코프 결정.
