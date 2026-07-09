"""Colab launch helper for the VibeVoice TTS service.

Run this from a Colab cell after `git clone`:

    from tts.colab_launch import launch
    url = launch()          # prints ENDPOINT_URL
    # paste url into orchestrator: export ENDPOINT_URL=<url>

The returned URL is ephemeral (~90 min idle timeout on trycloudflare.com).
After a Colab restart, re-run launch() and update ENDPOINT_URL in the
orchestrator.  This is expected — see PROJECT_PLAN.md section 6.

For a permanent URL, deploy to Modal/RunPod using the same tts/server.py
FastAPI app; only ENDPOINT_URL changes in the orchestrator (INFRA-01 contract).

# ponytail: colab_launch.py has no automated test; Colab env required
"""
import subprocess
import threading
import time


def launch(port: int = 8000) -> str:
    """Start FastAPI + cloudflared. Returns public HTTPS URL. Call once per Colab session."""
    import uvicorn

    def _run():
        uvicorn.run("tts.server:app", host="0.0.0.0", port=port, log_level="warning")

    threading.Thread(target=_run, daemon=True).start()
    time.sleep(3)  # wait for uvicorn

    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
        stderr=subprocess.PIPE, text=True,
    )
    for line in proc.stderr:
        if "trycloudflare.com" in line:
            url = line.strip().split()[-1]
            print(f"ENDPOINT_URL = {url}")
            print("Paste into orchestrator: export ENDPOINT_URL=" + url)
            return url
    raise RuntimeError("cloudflared did not print a URL — is cloudflared installed?")
