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

#### Python 3.12로 'gomoku_py312' 환경 생성
```bash
conda create -n mind-signal python=3.10
conda activate mind-signal
```

#### requirements.txt로 모든 라이브러리 설치
```bash
pip install -r requirements.txt
```

### 3. Colab을 이용한 GPU 학습 (Training)
#### 1.Colab 노트북을 열고 런타임 유형을 T4 GPU로 변경합니다.

#### 2.Google Drive를 마운트(연결)합니다.
```bash
from google.colab import drive
drive.mount('/content/drive')
```


#### 3. 프로젝트를 클론하고 라이브러리를 설치
```bash
# Git 클론 경로가 꼬이지 않도록, Colab 기본 디렉토리(/content)로 이동합니다.
%cd /content

# GitHub에서 프로젝트를 복제합니다. (마크다운 없이 URL만 사용)
!git clone https://github.com/KWONSEOK02/mind-signal-data-engine.git

# 복제된 폴더 안으로 작업 디렉터리를 이동합니다.
%cd mind-signal-data-engine

# 프로젝트 폴더 안에서 requirements.txt 파일로 라이브러리를 설치합니다.
!pip install -r requirements.txt

# 2. 
#
!pip install 
```

## 4. 알고리즘 (Algorithms)



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
├── .env.local          # CLIENT_ID, CLIENT_SECRET 보관
├── .env.example        # 환경 변수 가이드 
├── .gitignore          # 제외 목록
├── requirements.txt    # 의존성 목록
└── README.md           # 프로젝트 설명서
```

## 6. 🤝 협업 가이드라인 (Contribution Guidelines)

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
🔗 [Emotiv Cortex API Python 공식 예제 저장소](https://github.com/Emotiv/cortex-example/tree/master/python)
🔗 [Emotiv Cortex API](https://emotiv.gitbook.io/cortex-api)

---