# STEP 3b — Semantic 축 (RULE 6 코사인)

> Agent A에 의미 매칭(코사인)을 활성화 — `Cut`에 semantic_vector 추가.

| 항목     | 값                |
| -------- | ----------------- |
| 🕒 일시  | 2026-06-24 23:07  |
| 🔖 커밋  | `457a129`         |
| 🎯 RULE  | RULE 6            |
| ✅ 테스트 | 10 passed         |

## 🎯 무슨 작업

- `Cut.semantic_vector` 추가 — 원 설계의 빈틈(스키마/계약)이라 **flag 후 진행**.
- Agent A 점수 = `0.5·코사인(semantic)` + `0.3·motion` + `0.2·duration`.

## 📂 변경 파일

| 파일                                | 내용                          |
| ----------------------------------- | ----------------------------- |
| `src/fallback_engine/schemas.py`    | `Cut.semantic_vector` 추가    |
| `src/fallback_engine/engine.py`     | `_semantic_fit`(코사인) + 3축 `_score` |
| `tests/fixtures.py` · `test_engine.py` | `obvious_winner` 활성화    |

## 🔬 무결성 검증

```bash
$ python -m pytest
10 passed
```

- 적대 검증: **컷 벡터를 뒤집으면 승자도 뒤집힘**(A↔B) → 코사인이 진짜 판별. 하드코딩 0.

## 📝 결과 / 관찰

- 의미상 맞는 세그먼트가 슬롯을 차지 → 진짜 IP의 핵심 축 동작.
- 실제 임베딩 모델은 스코프 밖(제공 벡터 사용).
