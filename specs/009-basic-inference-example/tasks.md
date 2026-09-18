# 작업 목록: YOLO 차량 검출 및 NV12 박스 오버레이

## 1단계: 사용자 스토리 1 - 자동차 검출 결과 표시

- [X] T001 [US1] `tests/test_inference_example.py`에 자동차 상자와 `set_frame_data` 호출 테스트를 추가한다.
- [X] T002 [US1] `examples/inference.py`에 NV12 GPU 프레임의 RGB 변환, YOLO 자동차 필터 및 초록색 상자 오버레이를 구현한다.
- [X] T003 [US1] `tests/test_inference_example.py`에 추론 생략 시 결과 재사용과 비-NV12 입력 거부를 검증한다.
- [X] T004 [US1] 모델 입력을 32 배수로 패딩하되 원본 영상 좌표를 유지하는 동작을 검증한다.

## 2단계: 구성 및 마무리

- [X] T005 `pipe2.yml`에 YOLO 모델 경로와 신뢰도 파라미터를 설정한다.
- [X] T006 예제 단위 테스트, 전체 단위 테스트 및 문법 검사를 실행한다.
- [X] T007 [US1] GPU 결과를 pinned CPU 버퍼에 비동기 복사하고 완료 event 확인 뒤 CPU 큐에 적재하는 dispatcher와 큐 적체 테스트를 추가한다.
