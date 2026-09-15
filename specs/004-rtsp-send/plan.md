# 구현 계획: RTSP 송출 및 Sender 감시

**기능**: `004-rtsp-send`  
**명세**: [spec.md](spec.md)

## 기술 맥락

Python multiprocessing과 PyAV를 사용한다. `Sender`가 큐·자식 프로세스·감시 스레드를 소유하며, 자식은 `send_worker`를 통해 `send`를 실행한다.

## 설계

패킷은 제한된 multiprocessing 큐에 저장하고 가득 차면 오래된 항목을 제거한다. 송출 자식은 mux 성공 시 공유 heartbeat를 갱신한다. 별도 프로세스로 생성된 송출 워커는 YAML의 파이프라인 이름으로 자신의 로그 필터를 초기화한다. 감시 스레드는 1초 주기로 프로세스 생존과 10초 timeout을 확인하고 자식만 재시작한다. 종료는 join, terminate, kill의 제한된 순서로 수행한다.

## 파일 변경

- `src/nvidia_pipe/send.py`: Sender 및 송출 계약을 명확히 한다.
- `tests/nvidia_pipe/test_send.py`: mux, heartbeat, 큐, 종료 동작을 검증한다.
