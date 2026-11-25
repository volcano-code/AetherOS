"""Child-process bridge to Hermes' public run_agent.AIAgent facade.

Protocol: one JSON request on stdin; newline-delimited JSON events on stdout.
Hermes stdout is redirected to stderr so its diagnostics cannot corrupt the
AetherOS protocol stream.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import sys
import traceback


def _emit(stream, event: dict) -> None:
    stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    stream.flush()


def main() -> int:
    protocol_stdout = sys.stdout
    request = json.load(sys.stdin)
    hermes_root = Path.cwd()
    if not (hermes_root / "run_agent.py").is_file():
        _emit(protocol_stdout, {"type": "error", "error_type": "HermesCheckoutNotFound",
                                "outcome_unknown": False})
        return 2
    sys.path.insert(0, str(hermes_root))
    agent = None
    session_started = False
    try:
        with redirect_stdout(sys.stderr):
            from run_agent import AIAgent

            agent = AIAgent(
                provider=request.get("provider"),
                model=request.get("model") or "",
                user_id=request["user_id"],
                max_iterations=int(request["max_iterations"]),
                quiet_mode=True,
                save_trajectories=False,
                enabled_toolsets=[],
                disabled_toolsets=[],
                ephemeral_system_prompt=request.get("system_prompt") or None,
                skip_context_files=True,
                load_soul_identity=False,
                skip_memory=True,
                skip_background_review=True,
            )
            session_id = getattr(agent, "session_id", None)
            if not isinstance(session_id, str) or not session_id.strip():
                raise RuntimeError("Hermes AIAgent did not expose a session_id")
            session_started = True
            _emit(protocol_stdout, {"type": "session_started", "session_id": session_id})
            result = agent.run_conversation(
                request["goal"],
                task_id=request["execution_id"],
            )
            if not isinstance(result, dict):
                raise TypeError("Hermes run_conversation returned a non-object result")
            final_response = result.get("final_response")
            _emit(protocol_stdout, {
                "type": "result",
                "session_id": session_id,
                "final_response": final_response,
                "failed": result.get("failed") is True,
                "interrupted": result.get("interrupted") is True,
                "model": getattr(agent, "model", None),
            })
        return 0
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        _emit(protocol_stdout, {
            "type": "error",
            "error_type": type(exc).__name__,
            "outcome_unknown": session_started,
        })
        return 1
    finally:
        if agent is not None:
            try:
                with redirect_stdout(sys.stderr):
                    agent.close()
            except Exception:
                traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
