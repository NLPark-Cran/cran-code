"""MiniMax consultation tool for Cran Code.

Provides a second opinion from MiniMax AI when facing hard problems.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import override

from kosong.tooling import CallableTool2, ToolReturnValue
from pydantic import BaseModel, Field

from cran_code import logger
from cran_code.tools.utils import ToolResultBuilder


class Params(BaseModel):
    question: str = Field(
        description=(
            "A concise summary of the hard problem or dilemma you face. "
            "Be specific about what you've tried, what's blocking you, and what kind of "
            "help you need (e.g., alternative approaches, root cause analysis, architectural advice)."
        ),
    )
    context: str = Field(
        default="",
        description=(
            "Optional additional context: error messages, code snippets, file paths, "
            "or any relevant background that helps MiniMax understand the situation."
        ),
    )


class MiniMaxConsult(CallableTool2[Params]):
    name: str = "MiniMaxConsult"
    description: str = (
        "Consult MiniMax AI for a second opinion on a hard problem. "
        "Use this when you are stuck, facing an architectural dilemma, unsure about the best approach, "
        "or need alternative perspectives. Summarize the problem concisely and ask for ideas. "
        "Integrate the best suggestions into your own recommendation while maintaining critical judgment."
    )
    params: type[Params] = Params

    @override
    async def __call__(self, params: Params) -> ToolReturnValue:
        builder = ToolResultBuilder()

        system_prompt = (
            "You are a senior software engineering consultant. "
            "The user (another AI agent) is stuck on a hard problem and needs your second opinion. "
            "Provide clear, actionable advice. Consider multiple approaches and their trade-offs. "
            "Be concise but thorough. If relevant, suggest specific files, patterns, or tools."
        )

        user_message = params.question
        if params.context:
            user_message += f"\n\nAdditional context:\n{params.context}"

        cmd = [
            "mmx",
            "text",
            "chat",
            "--non-interactive",
            "--no-color",
            "--output", "text",
            "--system", system_prompt,
            "--message", user_message,
        ]

        logger.info("MiniMaxConsult: calling mmx for second opinion")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
        except asyncio.TimeoutError:
            return ToolReturnValue(
                is_error=True,
                output="",
                message="MiniMax consultation timed out after 60 seconds.",
            )
        except FileNotFoundError:
            return ToolReturnValue(
                is_error=True,
                output="",
                message="mmx CLI not found. Please ensure mmx-cli is installed (`npm install -g mmx-cli`).",
            )

        if proc.returncode != 0:
            err_text = stderr.decode("utf-8", errors="replace")[:500]
            builder.write(f"MiniMax exited with code {proc.returncode}.\n")
            builder.write(f"stderr: {err_text}\n")
            return builder.error(
                f"MiniMax consultation failed (exit code {proc.returncode}).",
                brief="MiniMax error",
            )

        response = stdout.decode("utf-8", errors="replace").strip()
        if not response:
            return ToolReturnValue(
                is_error=True,
                output="",
                message="MiniMax returned an empty response.",
            )

        builder.write(response)
        return builder.ok(
            message="MiniMax second opinion received.",
            brief="Got MiniMax advice",
        )
