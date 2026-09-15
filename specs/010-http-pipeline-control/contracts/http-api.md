# HTTP API 계약

기본 주소는 `http://127.0.0.1:8900`이다. 모든 API 응답은 UTF-8 JSON이다.

## 상태 표현

```json
{
  "name": "pipe1",
  "state": "running",
  "pid": 1234,
  "exit_code": null,
  "config": "D:\\Project\\pipe-works\\pipe.yml",
  "statistics": {
    "received_frame_count": 12,
    "sent_frame_count": 12,
    "inference_success_frame_count": 4,
    "inference_failure_frame_count": 0,
    "out_of_order_frame_count": 0,
    "input_rtsp_status": "connected",
    "output_rtsp_status": "connected"
  }
}
```

`state`는 `stopped`, `running`, `failed` 중 하나다.
`statistics`는 다섯 개의 프레임 누계와 `input_rtsp_status`,
`output_rtsp_status`를 포함한다. 두 RTSP 상태 값은 각각 `disconnected`,
`connected` 중 하나이며, 파이프라인의 `state`와 독립적이다.

## `GET /api/pipelines`

등록된 모든 파이프라인의 상태 배열을 반환한다.

- 성공: `200 OK`, 상태 표현 배열

## `GET /api/pipelines/{name}`

특정 파이프라인의 상태를 반환한다.

- 성공: `200 OK`, 상태 표현
- 이름 없음: `404 Not Found`, `{"error": "pipeline not found"}`

## `POST /api/pipelines/{name}/start`

파이프라인을 시작한다. 이미 실행 중이면 새 실행 단위를 만들지 않고 현재 상태를 반환한다.

- 성공: `200 OK`, 상태 표현
- 이름 없음: `404 Not Found`, `{"error": "pipeline not found"}`

## `POST /api/pipelines/{name}/stop`

파이프라인을 중지하고 상태를 반환한다.

- 성공: `200 OK`, 상태 표현
- 이름 없음: `404 Not Found`, `{"error": "pipeline not found"}`

## `GET /`

등록 파이프라인의 실행 상태, 중앙 Endpoint 영역의 수신·송신 RTSP 상태, 시작·중지
동작을 제공하는 로컬 브라우저 화면을 반환한다. 정상 상태 조회가 실패하면 화면은
이전에 표시한 카드의 실행 상태를 `stopped`, Endpoint와 두 RTSP 상태를
`disconnected`로 표시한다. 동일 파이프라인의 갱신은 기존 카드와 제어 요소를
교체하지 않고 표시값만 변경한다.

## `POST /api/pipelines/{name}/statistics`

로컬에서 시작된 파이프라인이 최신 통계와 RTSP 연결 상태를 보고하는 내부
엔드포인트다. 요청 본문은 상태 표현의 `statistics` 객체와 같은 일곱 필드를
정확히 포함해야 한다.

- 성공: `200 OK`, 갱신된 상태 표현
- 이름 없음: `404 Not Found`, `{"error": "pipeline not found"}`
- 필드 누락·추가, 음수 카운터 또는 허용되지 않은 RTSP 상태: `400 Bad Request`
