# 작업 목록: RTSP 송출 및 Sender 감시

- [X] T001 `tests/nvidia_pipe/test_send.py`에 PyAV 모의 컨테이너와 송출 패킷 픽스처를 작성한다.
- [X] T002 [US1] `tests/nvidia_pipe/test_send.py`에 mux와 첫 성공 로그 검증을 작성한다.
- [X] T003 [US1] `src/nvidia_pipe/send.py`의 패킷 매핑과 mux 동작을 검증한다.
- [X] T004 [US2] `tests/nvidia_pipe/test_send.py`에 heartbeat 갱신과 재시작 조건 검증을 작성한다.
- [X] T005 [US2] `src/nvidia_pipe/send.py`의 10초 감시 및 자식 재시작 동작을 검증한다.
- [X] T006 [US3] `tests/nvidia_pipe/test_send.py`에 제한된 종료 검증을 작성한다.
- [X] T007 전체 테스트와 문법 검사를 실행한다.
- [X] T008 `tests/nvidia_pipe/test_send.py`에 송신 워커의 YAML 파이프라인 이름 로그 설정 테스트를 추가하고, `src/nvidia_pipe/send.py`에서 워커별 로그 필터 초기화를 구현한다.

## 의존성

T001 → T002/T004/T006 → T003/T005 → T007
