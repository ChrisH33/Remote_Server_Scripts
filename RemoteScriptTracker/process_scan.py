# std modules
import os
import time
import psutil

def get_active_scripts_with_runtime(keywords: list[str]) -> dict[str, float]:
    scripts = {}

    for proc in psutil.process_iter(["cmdline", "create_time"]):
        try:
            cmd = proc.info["cmdline"]
            if not cmd or "python" not in os.path.basename(cmd[0]).lower():
                continue
            if any(keyword in " ".join(cmd).lower() for keyword in keywords):
                continue

            for arg in cmd[1:]:
                if arg.lower().endswith(".py"):
                    name = os.path.splitext(os.path.basename(arg))[0]
                    runtime = time.time() - proc.info["create_time"]

                    scripts[name] = runtime
                    break

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return scripts