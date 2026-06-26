# STEP 3d — Fallback(무중단) + 파일 로깅

> 반려 시 리듬으로 강제 채워 절대 안 멈춤. 모든 단계를 파일에 기록(터미널 X).

| 항목     | 값                |
| -------- | ----------------- |
| 🕒 일시  | 2026-06-26 21:19  |
| 🔖 커밋  | `d25cdc1`         |
| 🎯 RULE  | RULE 12           |
| ✅ 테스트 | 15 passed         |

## 🎯 무슨 작업

- B 반려 → **Fallback**: semantic 버리고 `motion + duration`(리듬)으로 강제 할당 → `EditInstruction(fallback_used=true)`. 충분한 소스면 **reject 없음(무중단)**.
- `trace.py`: 매 단계 `ok/fail` + 어떻게/무엇으로를 `logs/engine.log`(사람용) + `logs/runs.jsonl`(JSON 덤프)에 기록. 로거 `propagate=False` → **터미널로 한 줄도 안 샘**.

## 📂 변경 파일

| 파일                              | 내용                               |
| --------------------------------- | ---------------------------------- |
| `src/fallback_engine/engine.py`   | `_allocate` 공유 + Fallback 배선   |
| `src/fallback_engine/trace.py`    | **신규** — 파일 로깅/덤프          |
| `tests/test_engine.py` · `test_trace.py` | +3 (fallback·무중단·로깅)   |
| `.gitignore`                      | `logs/` 제외                       |

## 🔬 무결성 검증

```bash
$ python -m pytest
15 passed
```

- `logs/runs.jsonl` 덤프에 매 단계 기록 확인 · `test_trace.py`가 "파일에 남고 터미널엔 안 샘"을 단언.

## 📝 결과 / 관찰

- ⚠️ **로그가 약점 노출**: off-beat 케이스에서 Fallback이 Agent A와 **같은 picks** 반환 → 구조적 문제는 못 고치고 그냥 받아내기만. → 다음 refine 거리(3d-1, 3d-2).
