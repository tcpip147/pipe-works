# RTSP 수신 운영 보완

현재 `receive.py` 구현에 맞춘 추가 계약이다.

- 연결 열기와 읽기 timeout은 각각 5초이며 PyAV의 TCP 전송 설정을 사용한다.
- 첫 번째 영상 스트림(`video=0`)만 처리하고 오디오 스트림은 대상이 아니다.
- H.264, H.265, HEVC를 NVDEC 코덱으로 매핑한다.
- 지원하지 않는 코덱은 오류를 기록하고 재연결하지 않고 `ValueError`를 전파한다.
- `av.FFmpegError`, `OSError`, `IndexError`는 연결을 닫고 3초 후 재시도한다.
- PTS와 DTS가 모두 없는 패킷은 전달하지 않는다.
- 연속 유효 패킷의 PTS 차이가 0 이하이면 duration을 0으로 설정하고 경고를 기록한다.
- `ReceivedPacket`은 ctypes bitstream 버퍼 참조를 함께 보유한다.
