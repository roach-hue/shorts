# VIDEO FALLBACK ENGINE — 전체 프로젝트 플랜

> 유행하는 영상의 편집 문법(구조/리듬/흐름)을 추출해서, 내가 가진 소스로 같은 문법을 적용한 결과물을 만들어내는 엔진

---

## 목차

1. [프로젝트 본질 및 핵심 철학](#1-프로젝트-본질-및-핵심-철학)
2. [전체 시스템 아키텍처](#2-전체-시스템-아키텍처)
3. [확정된 기술 스택](#3-확정된-기술-스택)
4. [UX 플로우](#4-ux-플로우)
5. [Yellow 파이프라인 상세](#5-yellow-파이프라인-상세)
6. [Blue 파이프라인 상세](#6-blue-파이프라인-상세)
7. [Core Engine — 다중 에이전트 Fallback 매칭](#7-core-engine--다중-에이전트-fallback-매칭)
8. [Pink — 최종 렌더링](#8-pink--최종-렌더링)
9. [비용 방어 전략](#9-비용-방어-전략)
10. [저작권 및 법적 리스크 처리 방침](#10-저작권-및-법적-리스크-처리-방침)
11. [미완성 단계 (Claude Code에서 순서대로 진행)](#11-미완성-단계-claude-code에서-순서대로-진행)
12. [개발 방법론](#12-개발-방법론)

---

## 1. 프로젝트 본질 및 핵심 철학

### 무엇을 만드는가

- 유행하는 숏폼 영상(YouTube Shorts)의 **편집 문법(구조, 리듬, 컷 타이밍)** 을 AI로 추출
- 사용자가 가진 원본 클립(Blue)을 그 문법의 빈칸에 **최적으로 욱여넣는** 자동 편집 엔진
- "복제"가 아니라 **"내가 가진 걸로 저런 걸 배치하고 싶어"** 가 핵심 포인트

### Fallback이 본체다

- 완벽한 소스가 없을 때 에러를 내는 게 아니라, **가진 것 중 최선을 찾아 채워넣는** 구조가 메인 엔진
- 공식 명칭: **Best-Effort Allocation / Semantic Asset Mapping**
- 음식점 홍보는 예시일 뿐, 도메인 비종속 범용 엔진이 목표

### MVP 스코프

- **대상 플랫폼:** YouTube Shorts (인스타/틱톡은 안티봇으로 제외)
- **대상 도메인:** 정적·일반 모션 영상 (음식, 일상, 브이로그 등). 게임 쇼츠는 나중
- **대상 환경:** PC 웹 브라우저 (모바일은 추후 네이티브 앱 전환 시 대응)

---

## 2. 전체 시스템 아키텍처

```
[사용자]
   │
   ├─ YouTube Shorts URL 입력
   │        │
   │        ▼
   │   [Yellow 파이프라인] ── 서버
   │   yt-dlp 480p 임시 다운로드
   │   → 오디오 분석 (librosa): 비트 타임스탬프 배열 추출
   │   → 컷 분할 (PySceneDetect): 컷별 In/Out 타임코드
   │   → 키프레임 추출 → VLM(moondream2): 시각 속성(모션 포함) 태깅
   │   → OCR: 자막 텍스트/위치/시간/크기변동(Scale/Highlight) 추출
   │   → 원본 영상 즉시 삭제
   │   → 출력: template.json
   │
   ├─ Blue 소스 영상 다중 업로드 (PC 브라우저)
   │        │
   │        ▼
   │   [Blue 파이프라인] ── 클라이언트 1차 전처리
   │   브라우저 JS: Optical Flow 기반 컷 분할 (최대 5개, 최소 1초 강제)
   │   → 서버로 경량 키프레임 이미지 + 오디오 파형 데이터만 전송
   │        │
   │        ▼
   │   [서버] VLM(moondream2): 키프레임별 시각 속성 태깅
   │   → 출력: asset_db.json (유저 에셋 벡터 DB)
   │
   ├─ [Core Engine] ── 서버 (다중 에이전트)
   │   Agent A: 경량 임베딩 모델 기반 코사인 유사도 스코어링 → 타임라인 조립
   │   Agent B: 1-Hit 즉결 검증 (길이 초과 / 오디오 엇박자 판별)
   │   Fallback: 검증 반려 및 구역별 UX 슬라이더 기준 미달 시 오디오 리듬 기반 즉축 강제 할당
   │   → 출력: edit_instruction.json
   │
   └─ [Pink — 최종 렌더링] ── 클라이언트
       edit_instruction.json 수신
       → FFmpeg.wasm이 하이브리드 속도 변조(Speed Ramp 등) 적용하여 로컬 재생산
       → 현장음 스마트 음소거(Semantic Muting) 반영
       → 브라우저 내 재생 + 다운로드 버튼
```

---

## 3. 확정된 기술 스택

| 항목 | 확정값 | 선택 근거 |
|------|--------|-----------|
| 프론트엔드 | React + TypeScript | FFmpeg.wasm CSR 환경에 가장 안정적. SSR(Next.js)은 Hydration 에러 리스크 |
| 백엔드 | Python + FastAPI | yt-dlp, librosa, HuggingFace 등 AI/ML 생태계 전부 Python. 비동기 처리 최적화 |
| VLM | moondream2 (HuggingFace Inference API — PRO 플랜) | 경량(파라미터 작음), 추론 비용 낮음, PRO 플랜으로 Rate Limit 제거. 추후 WebGPU 클라이언트 이전 적합 |
| 임베딩 모델 | all-MiniLM-L6-v2 | 가벼움과 코사인 유사도 연산 최적 포멧 |
| 영상 수집 | yt-dlp | YouTube Shorts 파싱 가장 안정적 |
| 오디오 분석 | librosa | BPM, 비트 타임스탬프, 데시벨 스파이크 추출 |
| 컷 분할 | PySceneDetect | 화면 전환점 타임코드 추출 |
| 로컬 렌더링 | FFmpeg.wasm | 서버 렌더링 비용 제로, 브라우저 내 mp4 인코딩 |
| OCR | EasyOCR | CPU 환경 동작, 한글 인식률 양호, FastAPI 통합 직관적 |
| 폰트 | SIL OFL 오픈소스 폰트 한정 | 저작권 100% 차단 (G마켓 산스, Noto Sans 등) |

---

## 4. UX 플로우

### Step 1 — 입력

```
사용자 PC 브라우저 접속
  → 템플릿용 YouTube Shorts URL 입력 (단일)
  → Blue 원본 소스 영상 다중 업로드 (로컬 파일)
  → 편집 방식 설정: 슬롯별 개별 선택 가능. [비트 우선] 해당 슬롯 비트/길이 절대 고정 / [서사 우선] 유저 소스 흐름 우선 + 해당 슬롯 이후 타임라인 가변(Cascading Shift 발동)
  → UX 패널에서 구역별 Fallback 방어율 슬라이더 (정확도 임계값) 조작
```

### Step 2 — 전처리 및 분석

```
[클라이언트]
  → Optical Flow 기반 분할 추출 (로컬 프로그레스 바 노출 / 한계 상한선 방어)
  → 경량 키프레임 이미지 + 오디오 파형만 서버 전송

[서버 - Yellow]
  → yt-dlp로 480p 임시 다운로드
  → librosa 오디오 분석 → 비트 타임스탬프 배열 추출
  → PySceneDetect 컷 분할
  → moondream2 키프레임 시각 태깅
  → 원본 즉시 삭제 → template.json 생성

[서버 - Blue]
  → moondream2로 유저 키프레임 시각 태깅
  → 생성 출력: asset_db.json

[서버 - Core Engine]
  → Agent A/B 가안 검토 (루프 제한 1-Hit)
  → 부족 시 오디오 템포만 보고 강제 할당 (Fallback)
  → 출력: edit_instruction.json → 클라이언트 반환
```

### Step 3 — 렌더링 및 결과

```
[클라이언트]
  → edit_instruction.json 수신
  → FFmpeg.wasm이 원본을 배속/홀딩 혼용하여 렌더링 (렌더링 프로그레스 바)
  → 템플릿 지시서(keep_audio)에 따라 현장음 스마트 Muting 처리
  → 완료: 브라우저 내 재생 + [다운로드] 버튼
  → is_original_sync_broken: true인 경우 다운로드 버튼 상단에 경고 강제 노출:
     "사용자의 흐름을 보존하기 위해 타임라인이 연장되었습니다.
      틱톡/인스타그램에서 유행 음원을 씌우면 하이라이트 싱크가 맞지 않을 수 있습니다.
      자체 BGM을 사용하거나 현장음을 그대로 활용하는 것을 권장합니다."
  → 결과물은 BGM 없음 (사용자가 인스타/틱톡에서 직접 음원 씌우기)
```

---

## 5. Yellow 파이프라인 상세

### 수집 기준

- **플랫폼:** YouTube Shorts 전용 (인스타/틱톡 MVP 제외)
- **해상도:** 480p 고정 (VLM 분석 최적점, 게임 도메인 제외 기준)
- **길이 필터:** 60초 초과 롱폼 URL 즉시 Reject
- **비공개 영상:** HTTP 403 처리

### 처리 순서

1. yt-dlp 480p 임시 다운로드
2. librosa: 오디오 파형 분석 → BPM, 비트/드랍 타임스탬프 배열 추출 (ms 단위)
3. PySceneDetect: 화면 전환점 타임코드 추출 → 컷 단위 분절
4. 각 컷 중간 지점에서 대표 키프레임 1~2장 추출
5. moondream2: 키프레임 → 시각 속성 태깅
   - 샷 구도: 클로즈업 / 풀샷 / POV 등
   - 객체 및 행동: 인물, 음식, 간판, 먹기, 요리, 불쇼 등
   - 카메라 무빙/역동성: 정적 / 줌인 / 흔들림 / 패닝 등
6. OCR: 화면 내 자막 텍스트, 위치, 시간, 크기 변동(Scale/Highlight) 애니메이션 추출
7. **원본 영상 즉시 영구 삭제**
8. template.json 생성

### template.json 예시 구조 (미확정 — 2단계에서 정의)

```json
{
  "template_id": "youtube_shorts_001",
  "total_duration": 45.0,
  "beat_timestamps": [1.200, 2.800, 3.500, 5.100],
  "cuts": [
    {
      "cut_id": 1,
      "in": 0.0,
      "out": 1.5,
      "duration": 1.5,
      "keep_audio": true,
      "beat_ref": 0,
      "visual": {
        "shot_type": "close_up",
        "objects": ["food", "meat"],
        "motion": "static",
        "motion_level": 0.1
      },
      "subtitle": {
        "text": "여기 정말 미쳤는데요?",
        "position": "top_center",
        "style": {
          "is_highlighted": false,
          "animation": "pop_up"
        }
      }
    }
  ]
}
```

---

## 6. Blue 파이프라인 상세

### 클라이언트 1차 전처리 (비용 방어 핵심)

- 원본 영상 파일 전체를 서버로 업로드하지 않음
- 브라우저 JS에서 Optical Flow 기반 픽셀 급변점 감지
- 오디오 파형 데이터 다운샘플링 하여 경량화

### 세그먼트 범위 한계선

- **EOF(End of File):** 영상 파일의 물리적 끝단. 카메라 녹화 종료 시점 = 마지막 세그먼트의 아웃포인트. 컷 포인트가 아니며 장면 전환과 무관한 클립 경계선임.

### 컷 포인트 감지 기준 (비용 방어 룰 적용)

1. **흔들림 기준:** 카메라 이동 시 Optical Flow(프레임 간 픽셀 변화량) 급증 → 그 직전을 컷 포인트로 판단
2. **분할 상한 제어:** VLM API 호출 비용 폭증을 막기 위해 클립 1개당 **최대 5개**까지만 분할을 허용하며, 세그먼트 **최소 길이는 1.0초**로 강제한다.
3. **Web Worker 격리:** Optical Flow 픽셀 연산은 반드시 Web Worker 백그라운드 스레드에서 실행한다. 메인 스레드 블로킹(UI 멈춤) 및 FFmpeg.wasm과의 메모리 충돌을 차단하기 위한 필수 구조.

### 서버 처리

- moondream2로 키프레임 시각 속성 태깅 (Yellow와 동일 방식)
- asset_db.json 생성

### asset_db.json 예시 구조 (미확정 — 2단계에서 정의)

```json
{
  "assets": [
    {
      "clip_id": "clip_A",
      "file_name": "video_001.mp4",
      "duration": 8.5,
      "segments": [
        {
          "in": 0.0,
          "out": 3.2,
          "visual": {
            "shot_type": "wide",
            "objects": ["restaurant_exterior"],
            "motion": "static"
          },
          "motion_score": 0.1
        },
        {
          "in": 3.2,
          "out": 8.5,
          "visual": {
            "shot_type": "close_up",
            "objects": ["food", "boiling"],
            "motion": "medium"
          },
          "motion_score": 0.6
        }
      ]
    }
  ]
}
```

---

## 7. Core Engine — 다중 에이전트 Fallback 매칭

### Agent A — 매칭 에이전트 (3차원 스코어링)

template.json의 각 컷 슬롯에 대해 asset_db.json의 세그먼트들을 0~100점으로 채점 (템플릿 컷 순서 절대 고정 원칙 준수)

| 지표 | 가중치 | 계산 방법 |
|------|--------|-----------|
| Semantic Score | 50% | 경량 모델(`all-MiniLM-L6-v2`)을 통한 텍스트 임베딩 벡터 코사인 유사도 연산 |
| Motion Score | 30% | 템플릿 요구 역동성 vs 유저 세그먼트 Optical Flow 액티비티 동기화 수준 |
| Duration Score | 20% | 모자라면 부족량 비례 감점. 슬롯보다 긴 경우는 모드에 따라 분기 — [비트 우선] 2.5x 이하: 감점 없음 / 2.5x 초과: 기하급수적 감점으로 매칭 차단 / [서사 우선] 슬롯 자체가 늘어나는 구조이므로 감점 면제 |

* **에셋 중복 할당 방침:** 한 번 사용된 클립도 영원히 폐기하지 않고, 다음 슬롯 경쟁 시 최종 스코어를 30% 감점(Soft Penalty)한 채 레이스에 출전시킴. 이를 통해 무분별한 오류 대신 '수미상관' 연출을 자연스럽게 유도함.

### 유저 원본 흐름 보존 — 모드별 분기 (Agent A 연산 책임)

Agent A가 Speed Ramp 포함 최종 `speed` 배수와 `timeline_position`을 모두 계산하여 edit_instruction.json에 기록. Pink는 지시서대로 실행만 하는 Dumb 렌더러.

**[비트 우선 모드]** 템플릿 슬롯 절대 고정:
- 유저 소스가 슬롯보다 길면 Smart Trim(핵심 구간 발췌) 또는 제한적 Speed Ramp로 슬롯 길이에 강제로 맞춤.
- 슬롯 시작점이 템플릿 원본 비트 타임스탬프에 고정되므로 하위 슬롯의 타임라인 재계산 불필요.

**[서사 우선 모드]** 타임라인 가변 허용:
- 유저 소스 길이에 맞춰 슬롯을 늘리고, 뒤따라오는 모든 컷의 `timeline_position`과 비트 기준점을 뒤로 미루는 **연쇄 지연(Cascading Shift) 재계산**을 Agent A가 수행.
- 비트가 물리적으로 어긋나는 것이 허용된 구조.

### Agent B — 1-Hit 검증 에이전트 (리듬 팩트 체크)

Agent A가 조립한 타임라인 가안을 1회 검토

**검증 기준:**
- Agent A가 조립을 완료한 **가안 타임라인의 총합 길이**가 템플릿 최소 런타임에 미달하는지 검증 (Fail Fast 에러 반환). 원본 소스 풀 검증(RULE 7)과 계층이 다름 — RULE 7은 입력값(Blue 소스 총합)을 보고, Agent B는 Agent A가 실제로 조립한 출력물을 봄.
- **[비트 우선 모드]** 컷 전환 시점(`timeline_position`)과 템플릿 원본 `beat_timestamps` 오차(±100ms) 엄격 검증.
- **[서사 우선 모드]** 비트 어긋남이 허용된 모드이므로 ±100ms 검증을 강제 Bypass. 타임라인 총합 길이 부족 여부만 확인.

**순환 구조 (1-Hit 제한):**
- 연산 자원 및 레이턴시 등 서버 비용 낭비를 막기 위해 무한 핑퐁 루프를 금지함.
- Agent B가 가안을 반려(Reject)하면, 두 번째 조합을 재탐색하지 않고 과감히 **즉각 내용 포기(Fallback)** 로직으로 이관됨.

### 최후의 보루 — Fallback 발동 (무중단 파이프라인)

**발동 조건:** 
1. Agent B의 1-Hit 검증에서 단 한 번이라도 반려(Reject)된 경우.
2. 매칭 점수가 **사용자가 UX 구역 슬라이더로 직접 설정한 매칭 임계값**에 도달하지 못했을 경우.

**발동 시 동작:**
- 시각적 매칭(Semantic Score) 전면 포기.
- 남은 세그먼트 중 **오디오 리듬(Motion & Beat)** 수치 기준으로 강제 병합 할당. **템플릿의 슬롯 순서(1번→2번→…)와 시간표는 Fallback 모드에서도 100% 절대 고정. 예외 없음. 변경되는 것은 각 슬롯을 채우는 유저 세그먼트의 선택 기준뿐이다.**
- 시각적 내용은 맞지 않더라도 **숏폼 특유의 템포와 쿵짝거리는 리듬감은 끝까지 사수**하며, 무한 로딩 지연 없이 클라이언트로 결과값을 넘김.

### edit_instruction.json 예시 구조 (미확정 — 2단계에서 정의)

```json
{
  "total_duration": 45.0,
  "is_original_sync_broken": false,
  "clips": [
    {
      "slot_id": 1,
      "source_file": "video_001.mp4",
      "in": 3.2,
      "out": 4.7,
      "timeline_position": 0.0,
      "speed": 1.0,
      "fallback_used": false
    },
    {
      "slot_id": 2,
      "source_file": "video_002.mp4",
      "in": 0.0,
      "out": 2.2,
      "timeline_position": 1.5,
      "speed": 1.25,
      "fallback_used": true
    }
  ],
  "subtitles": [
    {
      "text": "여기 정말 미쳤는데요?",
      "timeline_in": 0.0,
      "timeline_out": 1.5,
      "position": "top_center",
      "style": {
        "is_highlighted": false,
        "animation": "pop_up"
      }
    }
  ]
}
```

---

## 8. Pink — 최종 렌더링

- **주체:** 클라이언트 (사용자 PC 브라우저)
- **방식:** FFmpeg.wasm
- **입력:** edit_instruction.json + 로컬 원본 고화질 영상 파일들
- **출력:** 템플릿의 오리지널 BGM이 없는 화면(영상) 단위 결과물 .mp4
- **현장음 분기(Semantic Muting):** 템플릿의 `keep_audio` 플래그에 따라, ASMR 등 꼭 살려야 하는 중요한 컷은 현장음(Natural Sound)을 고스란히 믹싱하고, 식당 주변 잡음이 섞이는 불필요한 컷은 오디오 트랙을 완전히 삭제(Mute)함. `keep_audio` 값은 Yellow 파이프라인에서 moondream2가 추출한 `objects` 태그(예: "boiling", "eating", "grilling" 등 소리가 중요한 행동 태그 여부)를 규칙 기반으로 해석하여 세팅한다. VLM이 오디오를 직접 분석하는 것이 아니라 시각 태그를 기준으로 추론함.
- **이후 단계:** 사용자가 틱톡/인스타에 업로드 후 플랫폼 인기 음악을 자체적으로 씌우면, 편집 타이밍이 똑떨어지는 영상 탄생.

- **렌더링 소요 시간 고지:** 렌더링 시작 전, 브라우저 JS가 `navigator.hardwareConcurrency`(CPU 코어 수)와 타겟 영상의 총 클립 수/길이를 읽어 예상 소요 시간을 동적으로 수식화하여 UI에 고지한다. 임의의 고정 수치를 명세서에 박지 않는다.

**모바일 대응:**
- MVP는 PC 웹 기준 (iOS Safari 메모리 제한 크래시 리스크로 제외)
- 추후 네이티브 앱 전환 시 AVFoundation(iOS) / MediaCodec(Android)으로 교체

---

## 9. 비용 방어 전략

### 1차 방어선 — 로컬 전처리 극대화

- 클라이언트에서 Optical Flow로 급변점 5개 한계 돌파 방어
- 과도한 API 콜 완전 차단, 서버 비용 90% 이상 삭감

### 2차 방어선 — Serverless GPU (스케일업 시)

- Modal, RunPod, Baseten 등 서버리스 GPU 인프라
- 분석 요청 시 2~3초 동안만 컨테이너 켜짐 (Scale-to-Zero)
- 상시 GPU 서버 고정비 제거

### 3차 방어선 — WebGPU 클라이언트 직접 추론 (궁극 구조)

- moondream2 (1~2B 파라미터)는 ONNX Runtime Web으로 브라우저에서 직접 구동 가능
- 사용자 그래픽카드를 빌려 VLM 추론
- 서버 VLM 연산 비용 = 0원

---

## 10. 저작권 및 법적 리스크 처리 방침

### 음원 저작권

- 상업용 원본 음악 첨부 금지 (시스템 내 1바이트도 저장 안 함)
- Sped up / Pitch 변조 방식 기각 (2차 저작물 침해 리스크 존재)
- **채택 방식:** 비트 타임스탬프 숫자 배열만 추출 후 원본 즉시 완전 파기, BGM은 유저 커뮤니티(플랫폼) 책임으로 유도.

### 폰트 저작권

- SIL OFL 오픈소스 폰트만 시스템 내장 (G마켓 산스, Noto Sans 등)
- 100% 차단

### 영상 문법 저작권

- 편집 흐름(인트로 → 클로즈업 → 전경) 자체는 아이디어/Scènes à faire의 영역으로 저작권 대상 아님. 추출값은 타임코드 숫자일 뿐.

### 플랫폼 책임 관리

- Safe Harbor 원칙에 의거 통신판매 보조 도구 역할 명확화.
- 초상권(블러링)은 Export 구조이므로 사용자 책임으로 돌림.

---

## 11. 미완성 단계 (Claude Code에서 순서대로 진행)

> ⛔ **작업 진입 전 [`PENDING.md`](PENDING.md) 확인 필수. 미결 항목이 남아 있으면 개발 단계 진입 금지.**

> ⚠️ 아래 단계들을 순서대로 진행해야 함. 건너뛰기 금지.

### 2단계 — 데이터 스키마 정의 ← **현재 여기서 시작**

- [ ] 2-1. Yellow 출력 JSON 스키마 확정
  - 비트 타임스탬프 배열 포맷 등
- [ ] 2-2. Blue 출력 JSON 스키마 확정
  - 벡터값 저장 형식
- [ ] 2-3. Pink 출력 JSON 스키마 확정

### 3단계 — CLAUDE.md + Skill 파일 작성

- [ ] 3-1. CLAUDE.md 작성
- [ ] 3-2. `.claude/skills/yellow_extractor.md`
- [ ] 3-3. `.claude/skills/blue_indexer.md`
- [ ] 3-4. `.claude/skills/pink_orchestrator.md`

### 4단계 — MVP 마일스톤 수립

- [ ] 4-1. 랄프루프(/loop) 실행 순서 확정
- [ ] 4-2. Mock 데이터 기준 Pink Orchestrator 단독 검증 계획
- [ ] 4-3. 모듈별 개발 우선순위 및 통합 순서

---

## 12. 개발 방법론

### 도구 스택

- **Claude Code** 올인 (전체 개발 주도)
- **CLAUDE.md** — 모든 규칙, 임계값 제어, 1~12번 합의 룰 강제 탑재
- **랄프루프 (`/loop`)** — 시스템 통합 및 자동 반복 생태계 관리
- **다중 에이전트 구조** — A/B 1-Hit Fallback 체계 가동

### 선행 원칙

- **코드 작성 전 반드시 `.md` Planning 파일 완성**
- 모든 기획은 md 파일로 문서화 후 Claude Code 투입
- 핵심 엔진(Pink Orchestrator)의 Mock 데이터 검증을 UI보다 우선

---

*이 문서는 Gemini와의 첫 설계 대화 및 1~12번 합의 규칙을 기반으로 재통합된 '결정판' 프로젝트 플랜입니다.*
*다음 작업: 하단 목차(2단계) 지시가 떨어질 때까지 분해(Decoupling)하지 않고 이 원본을 유지함.*
