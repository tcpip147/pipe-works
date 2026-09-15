# 데이터 모델: HTTP 파이프라인 제어

## 파이프라인 정의

| 필드 | 설명 | 검증 |
| --- | --- | --- |
| `name` | 운영자가 제어하는 고유 이름 | 비어 있지 않고 전체 등록 목록에서 유일 |
| `config_path` | 개별 영상 파이프라인 설정 위치 | 읽을 수 있는 YAML 파일 |

## 파이프라인 실행 단위

| 필드 | 설명 |
| --- | --- |
| `name` | 연결된 파이프라인 정의의 이름 |
| `pid` | 실행 중이거나 마지막으로 실행된 자식 프로세스 식별자 |
| `exit_code` | 종료된 경우의 결과 코드 |
| `state` | 현재 운영 상태 |

## RTSP 연결 상태

| 필드 | 설명 | 허용 값 |
| --- | --- | --- |
| `input_rtsp_status` | 입력 RTSP의 현재 연결 상태 | `disconnected`, `connected` |
| `output_rtsp_status` | 출력 RTSP의 현재 연결 상태 | `disconnected`, `connected` |

RTSP 연결 상태는 실행 중인 파이프라인의 실행 상태와 독립적이다. 따라서
`running`이어도 입력 또는 출력 연결 상태는 `disconnected`일 수 있다. 브라우저
표시는 `stopped` 또는 상태 조회 실패 시 두 연결 상태를 모두 `disconnected`로
정규화한다.

## 상태 전이

```text
stopped --start--> running
running --stop--> stopped
running --unexpected exit--> failed
failed --start--> running
```

이미 `running`인 항목에 대한 시작 요청은 상태를 바꾸지 않는다. `stopped` 항목을 중지해도 상태를 유지한다.
