# 구현 계획: YOLO 차량 검출 및 NV12 박스 오버레이

## 기술 맥락

PyNvVideoCodec의 GPU 디코드 프레임은 DLPack을 통해 PyTorch 텐서로 연결된다. YOLO는 GPU RGB 텐서를 입력으로 받고, 자동차 검출 상자의 좌표를 GPU에 유지한다. 출력 프레임은 NV12 GPU 버퍼 그대로 NVENC에 전달된다.

## 설계

1. NV12 GPU 버퍼를 복사 없이 텐서로 보고 RGB 텐서로 변환한다.
2. 모델 입력의 너비와 높이를 32 배수로 맞추기 위해 오른쪽과 아래쪽에만 GPU 패딩을 추가한다.
3. YOLO의 검출 결과 중 COCO 자동차 클래스만 유지한다.
4. 자동차 상자 좌표로 GPU 마스크를 만들고, NV12의 휘도 및 색차 평면에 초록색 윤곽선을 기록한다.
5. 추론이 생략된 프레임은 가장 최근의 GPU 상자 결과를 사용한다.

## 파일 변경

- `examples/inference.py`: 모델 로드, NV12-RGB 변환, 자동차 필터링, 초록색 상자 오버레이 및 이전 결과 재사용을 제공한다.
- `tests/test_inference_example.py`: 자동차 필터, 상자 색상, 추론 생략 시 결과 재사용, 모델 입력 패딩을 검증한다.
- `pipe2.yml`: 차량 검출 예제와 모델 경로·신뢰도 파라미터를 제공한다.

## 검증

`PYTHONPATH=src python -m unittest tests.test_inference_example -v`, 전체 단위 테스트 및 문법 검사를 실행한다. 실제 NVIDIA GPU 환경에서는 CUDA 지원 torchvision과 모델 가중치를 준비한 뒤 RTSP 입력으로 초록 상자 출력과 NVENC 전송을 확인한다.
