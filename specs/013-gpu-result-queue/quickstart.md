# 빠른 검증: GPU 추론 결과 CPU 큐

## 사전 조건

- CUDA 지원 PyTorch와 NVIDIA GPU가 준비되어 있다.
- 파이프라인 설정은 GPU 추론 콜백을 사용한다.

## 단위 검증

```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python.exe -m unittest tests.nvidia_pipe.test_stream tests.nvidia_pipe.test_infer_queue tests.nvidia_pipe.test_cli -v
```

예상 결과: 결과 속성의 기본값·교체, 결과 없음 건너뛰기, 최신 우선 큐 정책, CLI 결과 제출이 통과한다.

## GPU 통합 검증

1. `pipe2.yml`로 차량 검출 파이프라인을 실행한다.
2. 추론 콜백이 프레임의 `inference_result`에 차량 상자 GPU 텐서를 설정하는지 확인한다.
3. CPU 결과 큐 소비자에서 결과를 읽어 좌표를 기록한다.
4. 출력 RTSP 영상이 계속 인코딩되고, 결과 소비를 잠시 멈춰도 파이프라인이 중단되지 않는지 확인한다.
