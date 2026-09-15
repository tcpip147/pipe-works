# 작업 목록: NVDEC 영상 디코딩

## 1단계: 준비

- [X] T001 `tests/nvidia_pipe/test_decode.py`에 PyNvVideoCodec 모의 객체 구조를 작성한다.

## 2단계: 기반

- [X] T002 [P] `tests/nvidia_pipe/test_decode.py`에 `GpuFrame` 메타데이터 검증 픽스처를 작성한다.

## 3단계: 사용자 스토리 1 - 압축 패킷 디코딩

- [X] T003 [US1] `tests/nvidia_pipe/test_decode.py`에 다중 프레임 출력 순서 테스트를 작성한다.
- [X] T004 [US1] `src/nvidia_pipe/decode.py`의 기존 디코더 초기화와 프레임 변환 동작이 명세와 일치함을 검증한다.

## 4단계: 사용자 스토리 2 - 입력 색상 형식

- [X] T005 [US2] `tests/nvidia_pipe/test_decode.py`에 native/rgb/rgbp 및 잘못된 형식 테스트를 작성한다.
- [X] T006 [US2] `src/nvidia_pipe/decode.py`의 기존 형식 매핑과 오류 메시지를 검증한다.

## 5단계: 사용자 스토리 3 - FPS 계산

- [X] T007 [US3] `tests/nvidia_pipe/test_decode.py`에 FPS 계산 경계 조건 테스트를 작성한다.
- [X] T008 [US3] `src/nvidia_pipe/decode.py`의 기존 FPS 계산이 유효한 PTS만 사용하는지 검증한다.

## 6단계: 마무리 검증

- [X] T009 `specs/002-nvdec-decode/quickstart.md`에 테스트 및 GPU 통합 검증 절차를 작성한다.
- [X] T010 전체 단위 테스트와 Python 문법 검사를 실행한다.

## 의존성

T001 → T002 → T003/T005/T007 → T004/T006/T008 → T009/T010

## MVP 범위

T001~T004 (수신 패킷을 GPU 프레임으로 변환하는 핵심 흐름)
