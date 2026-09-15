# HTTP API 계약

기본 주소는 `http://127.0.0.1:8080`이다. 모든 API 응답은 UTF-8 JSON이다.

## 상태 표현

```json
{
  "name": "pipe1",
  "state": "running",
  "pid": 1234,
  "exit_code": null,
  "config": "D:\\Project\\pipe-works\\pipe.yml"
}
```

`state`는 `stopped`, `running`, `failed` 중 하나다.

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

등록 파이프라인을 표시하고 시작·중지 동작을 제공하는 로컬 브라우저 화면을 반환한다.
