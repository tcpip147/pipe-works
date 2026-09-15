# 파이프라인 설정 스키마

```yaml
input:
  rtsp:
    url: string       # 필수
    transport: string # 필수
output:
  rtsp:
    url: string       # 필수
    transport: string # 필수
inference:
  gpuid: integer          # 필수
  interval_frames: integer # 필수, 0 이상
  input_format: native|rgb|rgbp # 필수
  frame_type: pytorch     # 현재 지원값
  model: string            # 추론 모듈 파일 경로
```

`plumber.yml`은 다음 목록을 사용한다.

```yaml
pipelines:
  - name: string   # 선택
    config: string # 필수, 파이프라인 YAML 경로
```

현재 구현은 별도 스키마 검증기를 제공하지 않으며, 누락된 키는 Python 예외로 보고된다.
