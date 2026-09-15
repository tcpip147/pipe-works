# NVDEC 디코딩 검증 안내

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -p "test_*.py" -v
.\.venv\Scripts\python.exe -m py_compile src\nvidia_pipe\decode.py
```

실제 GPU 검증은 PyNvVideoCodec과 NVIDIA 드라이버가 설치된 환경에서 수행한다.
