# STEP 3 — 하네스 오라클 + Core Engine 트렁크

> 정답 기준(오라클)을 먼저 코드로 박고, 그 위에 그리디 할당 트렁크를 얹음.

| 항목     | 값                            |
| -------- | ----------------------------- |
| 🕒 일시  | 2026-06-24 23:00              |
| 🔖 커밋  | `078ee58`                     |
| 🎯 RULE  | RULE 4 / 7 / 8 / 10 / 12      |
| ✅ 테스트 | 9 passed, 1 skipped           |

## 🎯 무슨 작업

- **오라클** = 불변식(RULE을 코드 단언) + 합성 forced 케이스 + config 노브.
- **Core Engine 트렁크** = RULE7 reject → 슬롯순서 고정 그리디 할당 → Soft Penalty 재사용 → strict 채우기(Trim/배속·비트 핀).
- semantic(코사인)은 `Cut` 벡터 결정 전이라 **보류(스킵)**.

## 📂 변경 파일

| 파일                                            | 내용                  |
| ----------------------------------------------- | --------------------- |
| `src/fallback_engine/schemas.py`                | 데이터 계약(pydantic) |
| `src/fallback_engine/invariants.py`             | 오라클(불변식)        |
| `src/fallback_engine/config.py` · `config/thresholds.json` | 임계값 노브 |
| `src/fallback_engine/engine.py`                 | 트렁크 할당           |
| `tests/`                                        | 합성 케이스 + 검증    |

## 🔬 무결성 검증

```bash
$ python -m pytest
9 passed, 1 skipped
```

- 소스 부족 → Reject(RULE7) · 1세그먼트 2슬롯 → 재사용(RULE10) · 슬롯순서(RULE4)·싱크플래그(RULE13) 위반 적발.
- semantic 판별 1건 `skip`(다음 구간).

## 📝 결과 / 관찰

- 오라클이 **정상/불량 출력을 실제로 가른다**는 걸 먼저 증명.
- semantic 매칭은 `Cut`에 벡터가 필요 → 스키마 결정 후 다음 구간(3b).
