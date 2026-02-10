# Amind-signal-data-engine

## 1. 📝 프로젝트 개요 (Project Overview)

본 프로젝트는 **실시간으로 EGG 데이터 전달 및 데이터를 분석**하는 것을 주요 목표로 합니다.

---

## 2. 🛠️ Tech Stack

* **Environment:** Conda (로컬 가상 환경)
* **Local (Conda):** Python 3.10

---

## 3. 🚀 프로젝트 실행 방법 (Getting Started)


### 1. 저장소 복제 (Clone)

```bash
git clone https://github.com/KWONSEOK02/mind-signal-data-engine.git
cd mind-signal-data-engine
```


### 2. 로컬 가상 환경 설정 (Conda)

#### Python 3.10로 'mind-signal' 환경 생성
```bash
conda create -n mind-signal python=3.10
conda activate mind-signal
```

#### requirements.txt로 모든 라이브러리 설치
```bash
pip install -r requirements.txt
```

### 3. 각 파일 실행 명령어
 ```bash
 python -m core.main
 python -m core.streamer
 ``` 

## 4. 코드 스타일 관리 (Lint & Format)
협업 시 동일한 코딩 스타일을 유지하기 위해 아래 명령어를 권장합니다.

* **코드 자동 정렬 (Formatter):**
  ```bash
  # Black(포맷팅)
  black .
  
  #isort(임포트 정렬)
  isort .

  # 코드 스타일 검사 (Linter):
  # PEP8 표준 준수 여부 및 잠재적 에러 확인
  flake8 .
  ```
---

## 5. 📁 프로젝트 구조
```
mind-signal-data-engine/
├── core/               # 핵심 엔진
│   ├── analyzer.py     # FAA, ERP 계산 로직 (수학적 연산)
│   ├── main.py         # 프로그램을 실행하는 엔트리 포인트
│   └── streamer.py     # Redis로 데이터를 쏘는 실시간 스트리머
├── sdk/                # 제공받은 원본 소스 코드 (수정 금지)
│   ├── cortex.py       # 핵심 통신 라이브러리
│   ├── marker.py       # 마커 로직 참고용
│   ├── record.py       # 녹화 로직 참고용
│   └── sub_data.py     # 데이터 구독 참고용
├── .env.example        # 환경 변수 가이드 
├── .env.local          # CLIENT_ID, CLIENT_SECRET 보관
├── .flake8             # 파이썬 코드 스타일 가이드(PEP8) 및 문법 검사 설정 
├── .gitignore          # 제외 목록
├── pyproject.toml      # 코드 포맷터(Black, isort) 통합 설정 파일
├── README.md           # 프로젝트 설명서
└── requirements.txt    # 의존성 목록
```

## 6. 🤝 협업 가이드라인 (Contribution Guidelines)

---

### 파일별 핵심 역할 요약 (팀원 공유용)

| 파일명 | 핵심 역할 |
| :--- | :--- |
| **`.flake8`** | **ESLint의 파이썬 버전**입니다. 코드 가독성을 해치는 요소나 사용하지 않는 변수 등을 잡아내며, 수정하면 안 되는 `sdk/` 폴더는 무시하도록 설정되어 있습니다. |
| **`pyproject.toml`** | **Prettier의 파이썬 설정**과 같습니다. `Black`이 코드를 어떻게 예쁘게 정렬할지, `isort`가 상단 `import`문을 어떤 순서로 배치할지 정의합니다. |

---

### Git Workflow
- `master` (Production): 최종 배포 브랜치
- `develop` (Staging): 개발 완료 코드를 병합하는 메인 브랜치
- `feat/*`, `fix/*`, `docs/*`: 기능별, 목적별 브랜치

### 작업 흐름
1. `develop` 브랜치에서 `feat/my-new-feature` 브랜치를 생성하여 작업을 시작합니다.
2. 기능 완료 후 **Pull Request(PR)** 를 생성합니다.
3. 1명 이상의 팀원에게 **Approve(리뷰 승인)** 를 받습니다.
4. Merge 전, `develop` 최신 변경 사항을 `pull` 하여 충돌을 최소화합니다.

### 프로젝트 규칙
- **PR은 작은 단위로.** 하나의 PR은 하나의 기능에만 집중합니다.
- 세부 작업은 체크리스트로 관리합니다.
- 작업 충돌을 방지하기 위해 회의 중 역할을 명확히 나눕니다.

### 개발 가이드라인
- 코딩 스타일: **PEP8 준수**, `flake8` 권장
- 함수·클래스 주석: **Google Style Docstring**
- 모든 팀원은 동일한 `requirements.txt` 환경에서 개발합니다.

### 커밋 및 브랜치 컨벤션
- 커밋 메시지 및 브랜치는 **Conventional Commits 규칙 준수**
  - 예시:  
    - `feat(agent): Add A2C agent logic`  
    - `fix(reward): Fix reward calculation bug`

📄 상세 컨벤션 문서 (Notion)  
https://www.notion.so/27167d3af687803ca8c1ec0a66bbeb59?source=copy_link

---

## 📝 커밋 컨벤션
**Conventional Commits** 규칙 준수

- `feat:` 새 기능
- `fix:` 버그 수정
- `docs:` 문서 변경
- `style:` 코드 포매팅, 세미콜론
- `refactor:` 코드 리팩토링
- `perf:` 성능 개선
- `test:` 테스트 관련
- `chore:` 빌드/배포/패키지
- `ci:` CI 설정
- `revert:` 이전 커밋 되돌리기

**메시지 형식**
```
feat(agent): add PPO multi-agent training
fix(reward): correct negative reward assignment
perf(train): reduce inference time by caching model
```
---

## 🌱 Git 브랜치 네이밍 컨벤션 (요약)

- **feature/** → 새로운 기능 / 알고리즘 / 환경 추가  
  예) `feature/ppo-agent`, `feature/gomoku-env-enhancement`

- **fix/** → 버그 수정  
  예) `fix/reward-calculation`, `fix/model-forward-error`

- **hotfix/** → 긴급 수정  
  예) `hotfix/training-crash-epoch-100`

- **refactor/** → 코드 구조 개선  
  예) `refactor/env-clean-structure`, `refactor/agent-base-class`

- **docs/** → 문서 작업  
  예) `docs/update-readme-install-guide`, `docs/add-evaluation-results`

---
참고 자료 링크
*🔗 [Emotiv Cortex API Python 공식 예제 저장소](https://github.com/Emotiv/cortex-example/tree/master/python)

*🔗 [Emotiv Cortex API](https://emotiv.gitbook.io/cortex-api)

---