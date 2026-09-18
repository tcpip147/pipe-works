# 데이터 모델: GPU 추론 결과 CPU 큐

## GpuFrame

| 필드 | 유형 | 규칙 |
|---|---|---|
| `frame_data` | GPU 프레임 객체 | 기존 영상·인코딩 경로가 소비한다. 변경하지 않는다. |
| `inference_result` | 객체 또는 `None` | 추론을 수행한 프레임의 GPU 결과이다. 결과가 없으면 `None`이다. |

## PendingInferenceResult

| 필드 | 유형 | 규칙 |
|---|---|---|
| `cpu_result` | pinned CPU 텐서 | GPU 복사 대상이며 완료 전에는 외부에 공개하지 않는다. |
| `ready` | CUDA 완료 event | 완료 확인에만 사용한다. |
| `dependency` | CUDA 완료 event | producer stream과 copy stream의 순서를 보장한다. |

## CPU 결과 큐

| 속성 | 규칙 |
|---|---|
| 용량 | 고정 상한을 가진다. |
| 적재 | 복사 완료 결과만 비차단으로 적재한다. |
| 포화 | 가장 오래된 결과를 제거한 뒤 최신 결과를 적재한다. |
