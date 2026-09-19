import json
import re
import subprocess


class WindowsProcessLocator:
    def getProcessIds(self, process_id: str) -> list[int]:
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); "
                "Get-CimInstance Win32_Process | "
                "Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress"
            ),
        ]
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if not result.stdout.strip():
            return []

        entries = json.loads(result.stdout)
        if isinstance(entries, dict):
            entries = [entries]

        process_id_argument = subprocess.list2cmdline([process_id])
        pattern = re.compile(
            rf"(?<!\S)--process-id\s+{re.escape(process_id_argument)}(?=\s|$)"
        )
        return [
            int(entry["ProcessId"])
            for entry in entries
            if entry.get("CommandLine")
            and "-m stream.cli" in entry["CommandLine"]
            and pattern.search(entry["CommandLine"])
        ]
