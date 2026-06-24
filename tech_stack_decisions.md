# 기술 스택 결정 로그 (Tech Stack Decision Log)
> 파일명: `tech_stack_decisions.md`
> 목적: Fallback 매칭 엔진 및 로컬 렌더링 파이프라인 구축을 위한 프론트엔드, 백엔드, VLM 모델의 검토 후보군과 최종 채택 근거 명세

---

## 1. 검토된 기술 스택 후보군

* **프론트엔드 프레임워크:**
  1. React + TypeScript
  2. Next.js + TypeScript
  3. Vue.js
* **백엔드 프레임워크:**
  1. Python + FastAPI
  2. Python + Django
  3. Node.js + Express
* **VLM (비전 언어 모델):**
  1. moondream2 (초경량 모델)
  2. LLaVA (고성능/무거운 모델)
* **VLM 추론 인프라:**
  1. HuggingFace Inference API — 무료 티어
  2. HuggingFace Inference API — PRO 플랜 (유료)
  3. RunPod / Modal 자체 서버리스 엔드포인트
* **OCR:**
  1. EasyOCR
  2. Tesseract
  3. PaddleOCR

---

## 2. 스택 조합별 장단점 분석

### 조합 1: MVP 최적화 스택 (최종 채택)
* **스택 구성:** React + TypeScript / Python + FastAPI / moondream2
* **장점:**
  * **CSR 환경의 안정성:** 브라우저 내 `FFmpeg.wasm` 구동은 SSR(서버 사이드 렌더링) 간섭이 없는 순수 CSR 환경(React)에서 메모리 누수와 충돌이 가장 적음.
  * **비동기 I/O 최적화:** `yt-dlp` 파싱 및 다중 에이전트(Agent A/B)의 잦은 LLM API 호출로 인해 발생하는 병목을 FastAPI의 비동기(Async) 아키텍처가 완벽히 처리함.
  * **비용 방어:** `moondream2`는 파라미터가 작아 서버 추론 비용이 극도로 낮으며, 추후 클라이언트 단(WebGPU)으로 모델을 오프로딩하기에 가장 적합한 체급임.
* **단점:** SSR 미지원으로 인해 초기 로딩 속도 최적화 및 SEO(검색 엔진 최적화)에 불리함.

### 조합 2: 고정밀 시각 분석 스택
* **스택 구성:** React + TypeScript / Python + FastAPI / LLaVA
* **장점:** 객체 식별 및 행동 인식의 해상력이 매우 뛰어나, 엔진의 매칭 점수화(Scoring) 정확도를 극대화할 수 있음.
* **단점:** LLaVA의 무거운 체급으로 인해 VLM API 호출 비용 및 GPU 연산 리소스 소모가 극심하며, 파이프라인 전체의 처리 속도(Latency)가 크게 저하됨.

### 조합 3: 웹 성능 및 확장성 스택
* **스택 구성:** Next.js + TypeScript / Python + FastAPI / moondream2
* **장점:** SSR/SSG 지원으로 초기 렌더링 속도가 빠르고 B2C 마케팅을 위한 SEO에 완벽히 대응함.
* **단점:** `FFmpeg.wasm`은 브라우저 네이티브 API에 강하게 의존함. 이를 Next.js의 SSR 환경에 억지로 통합할 경우 하이드레이션(Hydration) 에러 대처 및 클라이언트 사이드 분기 처리에 막대한 개발 리소스가 낭비됨.

### 조합 4: 언어 통일성 스택
* **스택 구성:** React + TypeScript / Node.js + Express / 미정
* **장점:** 프론트엔드와 백엔드를 모두 TypeScript 생태계로 통일하여 풀스택 개발이 용이함.
* **단점:** AI/ML 파이프라인, 비전 모델 연동, `yt-dlp` 영상 처리 등 본 프로젝트의 핵심 생태계 90%가 Python에 종속되어 있음. Node.js 채택 시 라이브러리 지원 부족으로 비효율적인 우회 코드를 대량 작성해야 함.

### 조합 5: 모놀리식 레거시 스택
* **스택 구성:** Vue.js / Python + Django / LLaVA
* **장점:** 뷰/템플릿 기반의 전통적이고 안정적인 백엔드 아키텍처 구성 가능.
* **단점:** Django의 기본 동기식(Synchronous) 처리 구조는 수십 번의 API 호출과 비동기 파싱이 필요한 현재의 다중 에이전트 환경에서 심각한 시스템 병목을 유발함. 또한 `FFmpeg.wasm` 관련 트러블슈팅에 있어 Vue.js의 커뮤니티 레퍼런스가 React 대비 현저히 부족함.

---

## 3. 최종 결정 및 아키텍처적 근거

**최종 채택 스택: [조합 1] React+TS / FastAPI / moondream2 (HuggingFace Inference API PRO 플랜) / EasyOCR**

본 프로젝트의 본질은 무거운 렌더링 환경을 구축하는 것이 아니라, **"가진 소스를 분석해 템플릿에 끼워 넣는 Fallback 매칭 엔진"**의 논리적 증명에 있습니다. 

* **프론트엔드 (React+TS):** 서버 비용 방어의 핵심인 `FFmpeg.wasm` 로컬 렌더링을 구현하는 데 있어 가장 변수가 적고 확실한 프레임워크입니다.
* **백엔드 (FastAPI):** Python 기반의 강력한 AI 생태계를 그대로 활용하면서도, 다중 에이전트 순환 구조에서 발생하는 I/O 대기 시간을 최소화합니다.
* **VLM (moondream2):** 서버 유지비 파산을 막고 향후 Edge Computing(WebGPU)으로의 스케일업을 대비하기 위한 필수적인 경량화 선택입니다. 

이 스택은 초기 MVP 개발 속도를 확보함과 동시에, 서버 리소스와 클라이언트 렌더링 사이의 물리적 부하를 가장 완벽하게 분리해 내는 아키텍처 정답지입니다.
