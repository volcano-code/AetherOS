"""Isolated adapter to the pinned Hermes AIAgent public facade.

The adapter runs Hermes in its own Python process. This avoids mixing Hermes'
large module namespace and dependency environment into the AetherOS API process.
Phase 1 deliberately exposes no toolsets: live external effects remain disabled
until the Effect Kernel is wired into the actual Hermes dispatch boundary.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Protocol

from aetheros.harness.schema import HarnessSpec


class HermesRuntimeError(RuntimeError):
    """Hermes returned a definite runtime/turn failure."""


class HermesExecutionUnknown(HermesRuntimeError):
    """A Hermes turn started but its terminal result could not be confirmed."""


class HermesProtocolError(HermesExecutionUnknown):
    """The isolated worker violated the protocol after execution may have started."""


@dataclass(frozen=True, slots=True)
class ModelRoute:
    """An operator-approved mapping from a Harness route name to Hermes settings."""

    provider: str | None = None
    model: str | None = None


@dataclass(frozen=True, slots=True)
class HermesRuntimeConfig:
    hermes_root: Path
    python_executable: Path = field(default_factory=lambda: Path(sys.executable))
    hermes_home: Path | None = None
    model_routes: Mapping[str, ModelRoute] = field(
        default_factory=lambda: {"approved-default": ModelRoute()}
    )
    timeout_seconds: float = 300.0
    max_iterations: int = 12

    def __post_init__(self) -> None:
        root = Path(self.hermes_root).expanduser().resolve()
        python = Path(self.python_executable).expanduser().resolve()
        home = Path(self.hermes_home).expanduser().resolve() if self.hermes_home else None
        if not root.is_dir() or not (root / "run_agent.py").is_file():
            raise ValueError("hermes_root must point to a Hermes checkout containing run_agent.py")
        if not python.is_file():
            raise ValueError("python_executable must point to an existing interpreter")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be positive")
        routes = dict(self.model_routes)
        if not routes or any(not name.strip() for name in routes):
            raise ValueError("at least one non-empty approved model route is required")
        if any(not isinstance(route, ModelRoute) for route in routes.values()):
            raise TypeError("model_routes values must be ModelRoute instances")
        object.__setattr__(self, "hermes_root", root)
        object.__setattr__(self, "python_executable", python)
        object.__setattr__(self, "hermes_home", home)
        object.__setattr__(self, "model_routes", MappingProxyType(routes))


@dataclass(frozen=True, slots=True)
class HermesRunRequest:
    task_id: str
    execution_id: str
    user_id: str
    goal: str
    harness: HarnessSpec

    def __post_init__(self) -> None:
        for name in ("task_id", "execution_id", "user_id", "goal"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must be non-empty")
        if len(self.harness.system_prompt) > 100_000:
            raise ValueError("Harness system_prompt exceeds the 100 KB runtime limit")


@dataclass(frozen=True, slots=True)
class HermesRunResult:
    session_id: str
    final_response: str
    model: str | None
    response_digest: str

    @classmethod
    def from_response(
        cls, *, session_id: str, final_response: str, model: str | None
    ) -> "HermesRunResult":
        if not session_id.strip():
            raise ValueError("Hermes returned an empty session_id")
        if not isinstance(final_response, str):
            raise TypeError("Hermes final_response must be a string")
        digest = hashlib.sha256(final_response.encode("utf-8")).hexdigest()
        return cls(session_id, final_response, model, digest)


class HermesRuntime(Protocol):
    async def run_task(
        self,
        request: HermesRunRequest,
        *,
        on_session_started: Callable[[str], None] | None = None,
    ) -> HermesRunResult:
        """Run one task and report the Hermes session ID as soon as it exists."""
        ...


class HermesRuntimeAdapter:
    """Runs the pinned Hermes AIAgent facade in an isolated child process.

    The child process uses the configured Hermes Python environment and Hermes
    checkout. The model route is selected from an operator-supplied allowlist;
    Harness data cannot introduce arbitrary provider/model endpoints.

    Toolsets are intentionally fixed to an empty list in this first integration
    slice. This prevents ungoverned external side effects before the AetherOS
    Effect Kernel is connected to Hermes tool dispatch.
    """

    def __init__(self, config: HermesRuntimeConfig) -> None:
        self.config = config
        self.worker_path = Path(__file__).with_name("worker.py")

    def _route(self, route_name: str) -> ModelRoute:
        try:
            return self.config.model_routes[route_name]
        except KeyError as exc:
            raise HermesRuntimeError(
                f"Harness requested unapproved model route: {route_name}"
            ) from exc

    async def run_task(
        self,
        request: HermesRunRequest,
        *,
        on_session_started: Callable[[str], None] | None = None,
    ) -> HermesRunResult:
        route = self._route(request.harness.model_route)
        payload = {
            "task_id": request.task_id,
            "execution_id": request.execution_id,
            "user_id": request.user_id,
            "goal": request.goal,
            "system_prompt": request.harness.system_prompt,
            "model_route": request.harness.model_route,
            "provider": route.provider,
            "model": route.model,
            "max_iterations": self.config.max_iterations,
        }
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env.pop("HERMES_KANBAN_TASK", None)
        env.pop("HERMES_TUI", None)
        if self.config.hermes_home is not None:
            env["HERMES_HOME"] = str(self.config.hermes_home)

        process = await asyncio.create_subprocess_exec(
            str(self.config.python_executable),
            str(self.worker_path),
            cwd=str(self.config.hermes_root),
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stderr_task = asyncio.create_task(self._read_stderr(process.stderr))
        session_id: str | None = None
        result_event: dict | None = None
        error_event: dict | None = None
        deadline = asyncio.get_running_loop().time() + self.config.timeout_seconds

        try:
            assert process.stdin is not None
            process.stdin.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            await process.stdin.drain()
            process.stdin.close()
            if hasattr(process.stdin, "wait_closed"):
                await process.stdin.wait_closed()

            assert process.stdout is not None
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise asyncio.TimeoutError
                line = await asyncio.wait_for(process.stdout.readline(), timeout=remaining)
                if not line:
                    break
                try:
                    event = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise HermesProtocolError("Hermes worker emitted invalid JSON protocol data") from exc
                if not isinstance(event, dict):
                    raise HermesProtocolError("Hermes worker protocol event must be an object")
                event_type = event.get("type")
                if event_type == "session_started":
                    value = event.get("session_id")
                    if not isinstance(value, str) or not value.strip():
                        raise HermesProtocolError("Hermes worker emitted an invalid session_id")
                    if session_id is not None and session_id != value:
                        raise HermesProtocolError("Hermes worker changed session_id during one execution")
                    session_id = value
                    if on_session_started is not None:
                        on_session_started(value)
                elif event_type == "result":
                    if result_event is not None:
                        raise HermesProtocolError("Hermes worker emitted multiple result events")
                    result_event = event
                elif event_type == "error":
                    error_event = event
                else:
                    raise HermesProtocolError(f"Unknown Hermes worker event type: {event_type!r}")

            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise asyncio.TimeoutError
            return_code = await asyncio.wait_for(process.wait(), timeout=remaining)
            await stderr_task

            if error_event is not None:
                error_type = str(error_event.get("error_type") or "UnknownError")
                if bool(error_event.get("outcome_unknown")) or session_id is not None:
                    raise HermesExecutionUnknown(
                        f"Hermes execution ended without a confirmed result ({error_type})"
                    )
                raise HermesRuntimeError(f"Hermes worker failed during initialization ({error_type})")
            if return_code != 0:
                if session_id is not None:
                    raise HermesExecutionUnknown("Hermes worker exited after starting a session")
                raise HermesRuntimeError(f"Hermes worker exited with status {return_code}")
            if result_event is None:
                if session_id is not None:
                    raise HermesExecutionUnknown("Hermes worker exited without a terminal result")
                raise HermesRuntimeError("Hermes worker exited before creating a session")
            result_session = result_event.get("session_id")
            if not isinstance(result_session, str) or not result_session.strip():
                raise HermesProtocolError("Hermes result omitted session_id")
            if session_id is not None and result_session != session_id:
                raise HermesProtocolError("Hermes result session_id does not match session_started")
            if result_event.get("interrupted") is True:
                raise HermesExecutionUnknown("Hermes turn was interrupted before a terminal response")
            if result_event.get("failed") is True:
                raise HermesRuntimeError("Hermes reported a failed turn")
            final_response = result_event.get("final_response")
            if not isinstance(final_response, str):
                raise HermesProtocolError("Hermes result omitted a string final_response")
            model = result_event.get("model")
            return HermesRunResult.from_response(
                session_id=result_session,
                final_response=final_response,
                model=model if isinstance(model, str) else None,
            )
        except asyncio.TimeoutError as exc:
            await self._terminate(process)
            await stderr_task
            if session_id is not None:
                raise HermesExecutionUnknown("Hermes worker timed out after creating a session") from exc
            raise HermesRuntimeError("Hermes worker timed out before creating a session") from exc
        except asyncio.CancelledError:
            await self._terminate(process)
            await stderr_task
            raise
        except Exception:
            await self._terminate(process)
            if not stderr_task.done():
                await stderr_task
            raise

    @staticmethod
    async def _read_stderr(stream) -> str:
        if stream is None:
            return ""
        data = await stream.read()
        return data.decode("utf-8", errors="replace")[-4000:]

    @staticmethod
    async def _terminate(process: asyncio.subprocess.Process) -> None:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass
