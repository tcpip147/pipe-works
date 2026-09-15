# 기능 명세: 파이프라인 데이터 계약

**기능 식별자**: `007-pipeline-data-contracts`

## 기능 요구사항

- **FR-001**: `ReceivedPacket`은 코덱, 입력 스트림, NVDEC packet data, bitstream 버퍼를 포함해야 한다.
- **FR-002**: bitstream 버퍼는 하드웨어 디코더가 읽는 동안 수명을 유지해야 한다.
- **FR-003**: `GpuFrame`은 GPU 번호, 코덱, 해상도, 픽셀 형식, 시간 기준, PTS, 프레임 데이터를 제공해야 한다.
- **FR-006**: `GpuFrame`은 추론 또는 후속 처리 단계가 프레임 데이터를 교체할 수 있도록 `set_frame_data` 함수를 제공해야 한다.
- **FR-004**: `EncodedPacket`은 코덱, 해상도, 시간 기준, timestamp, 인코더 packet data를 제공해야 한다.
- **FR-005**: 단계 간 데이터는 정의된 필드와 순서를 유지해야 한다.

## 성공 기준

- **SC-001**: 세 데이터 객체의 필수 필드 접근 테스트가 100% 통과한다.
- **SC-002**: 수신 bitstream 버퍼가 다음 단계 처리 완료 전까지 유효하다.

## 구현 계약

- 데이터 객체는 현재 생성 시점의 값을 보유하며 자동 범위 검증은 수행하지 않는다.
- `ReceivedPacket.bitstream_buffer`는 ctypes 버퍼 참조를 유지하는 용도이며 NVDEC 호출 중 객체가 살아 있어야 한다.
- `GpuFrame` 속성은 읽기 전용 property로 노출된다.
- `EncodedPacket.packet_data`는 인코더 원본 객체일 수 있으며 송출 직전에 bytes 계열로 변환한다.

## 현재 구현 기준

- 구현 파일은 `src/nvidia_pipe/stream.py`이며 세 계약 객체는 `@dataclass(slots=True)`로
  정의된다.
- `GpuFrame`은 원본 영상 스트림의 평균 FPS도 보존한다. 메타데이터는 읽기 전용 property로 노출되고 `set_frame_data()`만 GPU
  프레임 데이터 참조를 교체한다. 이 메서드는 GPU 데이터를 CPU로 복사하지 않는다.
- `EncodedPacket.is_keyframe`은 송출 직전 Annex-B bitstream을 검사해 설정된다.
