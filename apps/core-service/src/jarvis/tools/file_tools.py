import os
from pathlib import Path
from jarvis.config.settings import settings
from jarvis.tools.schema import ReadFileInput, WriteFileInput


def _resolve_and_verify_path(path_str: str) -> Path:
    sandbox_root = settings.SANDBOX_ROOT.resolve()
    # Normalize path
    target = (sandbox_root / path_str).resolve()
    
    try:
        if not target.is_relative_to(sandbox_root):
            raise PermissionError(
                f"Security Violation: Path '{path_str}' traverses outside sandboxed root ({sandbox_root})"
            )
    except AttributeError:
        # Fallback for Python < 3.9 if needed
        if not str(target).startswith(str(sandbox_root)):
            raise PermissionError(
                f"Security Violation: Path '{path_str}' traverses outside sandboxed root ({sandbox_root})"
            )
            
    return target


async def read_file_tool(args: ReadFileInput | dict) -> str:
    if isinstance(args, dict):
        args = ReadFileInput(**args)

    target = _resolve_and_verify_path(args.path)

    if not target.exists():
        raise FileNotFoundError(f"File not found: '{args.path}'")
    if not target.is_file():
        raise IsADirectoryError(f"Target '{args.path}' is a directory, not a file.")

    with open(target, "r", encoding="utf-8", errors="replace") as f:
        if args.offset > 0:
            f.seek(args.offset)
        content = f.read(args.limit)
    return content


async def write_file_tool(args: WriteFileInput | dict) -> dict:
    if isinstance(args, dict):
        args = WriteFileInput(**args)

    target = _resolve_and_verify_path(args.path)
    target.parent.mkdir(parents=True, exist_ok=True)

    mode = "a" if args.append else "w"
    with open(target, mode, encoding="utf-8") as f:
        f.write(args.content)

    return {
        "path": args.path,
        "bytes_written": len(args.content.encode("utf-8")),
        "mode": "appended" if args.append else "written",
        "absolute_path": str(target)
    }
