# 작업 목록: NVENC 영상 인코딩

## 1단계: 준비

- [X] T001 `tests/nvidia_pipe/test_encode.py`에 PyNvVideoCodec 모의 인코더를 작성한다.

## 2단계: 사용자 스토리 1 - GPU 프레임 인코딩

- [X] T002 [US1] `tests/nvidia_pipe/test_encode.py`에 100개 프레임 순서 및 메타데이터 테스트를 작성한다.
- [X] T003 [US1] `src/nvidia_pipe/encode.py`의 인코더 초기화와 패킷 변환 계약을 명확히 한다.

## 3단계: 사용자 스토리 2 - 종료 패킷 배출

- [X] T004 [US2] `tests/nvidia_pipe/test_encode.py`에 `EndEncode` 잔여 패킷 테스트를 작성한다.
- [X] T005 [US2] `src/nvidia_pipe/encode.py`의 종료 처리와 B-frame 비활성 설정을 검증한다.

## 4단계: 마무리

- [X] T006 전체 단위 테스트와 문법 검사를 실행한다.

## 5단계: 사용자 스토리 3 - 송신 재접속 후 키프레임부터 출력 재개

- [X] T007 [US3] `tests/nvidia_pipe/test_send.py`에 키프레임 이전 패킷 폐기와 H.264/H.265 IDR 판별 테스트를 추가한다.
- [X] T008 [US3] `src/nvidia_pipe/stream.py`, `src/nvidia_pipe/cli.py`, `src/nvidia_pipe/send.py`에 키프레임 계약과 재접속 송출 게이트를 구현한다.
- [X] T009 [US3] 전체 단위 테스트와 문법 검사를 실행한다.

## 의존성

T001 → T002/T004 → T003/T005 → T006

## MVP 범위

T001~T003 (GPU 프레임을 인코딩 패킷으로 변환하는 핵심 흐름)
