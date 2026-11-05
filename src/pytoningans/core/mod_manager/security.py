"""
PyToNingans Mod and Modpack AST Security Scanner
=============================================
Performs Abstract Syntax Tree (AST) static analysis on custom Python scripts
in mods and modpacks. Detects dangerous behaviors such as arbitrary process execution,
unauthorized network requests, filesystem tampering, and code obfuscation.
Also extracts high-level capabilities to explain what the mod's code actually does.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import StrEnum, unique
from pathlib import Path
from typing import Optional, Any


@unique
class SecuritySeverity(StrEnum):
    DANGER = "danger"
    WARNING = "warning"
    INFO = "info"


@unique
class SecurityRiskLevel(StrEnum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    DANGEROUS = "dangerous"


@dataclass(slots=True, kw_only=True)
class SecurityIssue:
    """Represents a potential security or safety concern found during AST analysis."""
    file: str
    line: int
    col: int
    category: str
    severity: SecuritySeverity
    description: str
    code_snippet: str = ""


@dataclass(slots=True, kw_only=True)
class SecurityReport:
    """Aggregated safety audit and functional summary of a mod or modpack."""
    target_name: str
    target_path: Path
    risk_level: SecurityRiskLevel
    is_safe: bool
    issues: list[SecurityIssue] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    scanned_files: list[str] = field(default_factory=list)
    summary: str = ""
    detailed_explanation: str = ""


# Danger rules: Module or function patterns that pose serious security hazards
DANGEROUS_IMPORTS: dict[str, tuple[str, str]] = {
    # module_name -> (category, description)
    "subprocess": ("process_execution", "Spawns child processes or shell commands"),
    "socket": ("network", "Opens low-level raw network sockets"),
    "urllib.request": ("network", "Performs outbound network requests"),
    "requests": ("network", "Performs outbound HTTP network requests"),
    "httpx": ("network", "Performs outbound HTTP network requests"),
    "aiohttp": ("network", "Performs asynchronous HTTP network requests"),
    "paramiko": ("network", "Initiates SSH connections"),
    "ftplib": ("network", "Transfers files over FTP"),
    "winreg": ("system", "Reads or modifies Windows Registry"),
}

SUSPICIOUS_CALLS: dict[str, tuple[str, str, str]] = {
    # func_name -> (category, severity, description)
    "eval": ("dynamic_execution", SecuritySeverity.DANGER, "Executes arbitrary strings as Python code (eval)"),
    "exec": ("dynamic_execution", SecuritySeverity.DANGER, "Executes arbitrary dynamic Python code (exec)"),
    "__import__": ("dynamic_execution", SecuritySeverity.WARNING, "Dynamically imports modules at runtime"),
    "compile": ("dynamic_execution", SecuritySeverity.WARNING, "Compiles arbitrary code strings"),
    "os.system": ("process_execution", SecuritySeverity.DANGER, "Executes arbitrary shell commands (os.system)"),
    "os.popen": ("process_execution", SecuritySeverity.DANGER, "Opens a pipe to or from a shell command (os.popen)"),
    "os.kill": ("process_execution", SecuritySeverity.DANGER, "Sends terminate/kill signals to system processes"),
    "shutil.rmtree": ("filesystem", SecuritySeverity.DANGER, "Recursively deletes entire directory trees"),
    "os.remove": ("filesystem", SecuritySeverity.WARNING, "Deletes files from the disk"),
    "os.unlink": ("filesystem", SecuritySeverity.WARNING, "Unlinks/deletes files from the disk"),
    "webbrowser.open": ("system", SecuritySeverity.INFO, "Opens a web URL in the user's default browser"),
}


class ModASTVisitor(ast.NodeVisitor):
    """AST Visitor that inspects AST nodes for security risks and capabilities."""

    def __init__(self, rel_path: str, source_lines: list[str]) -> None:
        self.rel_path: str = rel_path
        self.source_lines: list[str] = source_lines
        self.issues: list[SecurityIssue] = []
        self.capabilities: set[str] = set()
        self.imported_modules: dict[str, str] = {}  # alias -> original_module
        self.imported_names: dict[str, str] = {}    # alias -> full_name

    def _get_line_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            mod_name: str = alias.name
            as_name: str = alias.asname or mod_name
            self.imported_modules[as_name] = mod_name

            # Check dangerous module imports
            for danger_mod, (category, description) in DANGEROUS_IMPORTS.items():
                if mod_name == danger_mod or mod_name.startswith(f"{danger_mod}."):
                    self.issues.append(
                        SecurityIssue(
                            file=self.rel_path,
                            line=node.lineno,
                            col=node.col_offset,
                            category=category,
                            severity=SecuritySeverity.DANGER,
                            description=f"Imports '{mod_name}': {description}.",
                            code_snippet=self._get_line_snippet(node.lineno),
                        )
                    )

            # Detect standard modding capabilities
            if mod_name.startswith("api") or mod_name.startswith("pytoningans"):
                self.capabilities.add("PyToNingans Modding API")
            elif mod_name in ("math", "random"):
                self.capabilities.add("Mathematics and Randomization")
            elif mod_name in ("json", "csv"):
                self.capabilities.add("Structured Data Parsing")

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            full_name: str = f"{module}.{alias.name}" if module else alias.name
            as_name: str = alias.asname or alias.name
            self.imported_names[as_name] = full_name

            for danger_mod, (category, description) in DANGEROUS_IMPORTS.items():
                if module == danger_mod or full_name == danger_mod or full_name.startswith(f"{danger_mod}."):
                    self.issues.append(
                        SecurityIssue(
                            file=self.rel_path,
                            line=node.lineno,
                            col=node.col_offset,
                            category=category,
                            severity=SecuritySeverity.DANGER,
                            description=f"Imports '{full_name}': {description}.",
                            code_snippet=self._get_line_snippet(node.lineno),
                        )
                    )

            if module.startswith("api") or module.startswith("pytoningans"):
                self.capabilities.add("PyToNingans Modding API")

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name: str = self._resolve_call_name(node.func)
        if not call_name:
            self.generic_visit(node)
            return
        
        # Check suspicious calls table
        for pattern, (cat, sev, desc) in SUSPICIOUS_CALLS.items():
            if call_name == pattern or call_name.endswith(f".{pattern}"):
                self.issues.append(
                    SecurityIssue(
                        file=self.rel_path,
                        line=node.lineno,
                        col=node.col_offset,
                        category=cat,
                        severity=SecuritySeverity(sev),
                        description=desc,
                        code_snippet=self._get_line_snippet(node.lineno),
                    )
                )

        # Check subprocess call patterns
        if "subprocess" in call_name:
            self.issues.append(
                SecurityIssue(
                    file=self.rel_path,
                    line=node.lineno,
                    col=node.col_offset,
                    category="process_execution",
                    severity=SecuritySeverity.DANGER,
                    description=f"Executes external system process via '{call_name}'.",
                    code_snippet=self._get_line_snippet(node.lineno),
                )
            )

        # Check file writing calls
        if call_name in ("open",) and len(node.args) >= 2:
            # check mode argument
            mode_arg = node.args[1]
            if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
                if any(mode in mode_arg.value for mode in ("w", "a", "x", "+")):
                    self.issues.append(
                        SecurityIssue(
                            file=self.rel_path,
                            line=node.lineno,
                            col=node.col_offset,
                            category="filesystem",
                            severity=SecuritySeverity.WARNING,
                            description=f"Opens file in write/append mode ('{mode_arg.value}').",
                            code_snippet=self._get_line_snippet(node.lineno),
                        )
                    )
                    self.capabilities.add("File Modification")

        if (
            call_name in ("write_text", "write_bytes")
            or call_name.endswith((".write_text", ".write_bytes"))
            or (isinstance(node.func, ast.Attribute) and node.func.attr in ("write_text", "write_bytes"))
        ):
            self.issues.append(
                SecurityIssue(
                    file=self.rel_path,
                    line=node.lineno,
                    col=node.col_offset,
                    category="filesystem",
                    severity=SecuritySeverity.WARNING,
                    description=f"Writes data to filesystem via '{call_name or 'write_text'}'.",
                    code_snippet=self._get_line_snippet(node.lineno),
                )
            )
            self.capabilities.add("File Modification")

        # Check network requests calls
        if any(net in call_name for net in ("requests.", "urllib.", "socket.", "httpx.", "aiohttp.")):
            self.issues.append(
                SecurityIssue(
                    file=self.rel_path,
                    line=node.lineno,
                    col=node.col_offset,
                    category="network",
                    severity=SecuritySeverity.DANGER,
                    description=f"Initiates network communication via '{call_name}'.",
                    code_snippet=self._get_line_snippet(node.lineno),
                )
            )
            self.capabilities.add("External Network Communication")

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Detect behavioral lifecycle hooks
        hook_capabilities: dict[str, str] = {
            "on_tick": "Frame Update Simulation (on_tick)",
            "on_collision": "Custom Physics Collision Response (on_collision)",
            "on_spawn": "Spawn Initialization (on_spawn)",
            "on_interact": "Interactive Entity Behavior (on_interact)",
            "on_attack": "Custom Combat Logic (on_attack)",
            "on_death": "Custom Death Handler (on_death)",
            "on_pack_loaded": "Modpack State Initialization (on_pack_loaded)",
            "on_entity_spawned": "Modpack Entity Tracking (on_entity_spawned)",
            "get_context_menu_actions": "Desktop Context Menu Extension",
        }
        if node.name in hook_capabilities:
            self.capabilities.add(hook_capabilities[node.name])

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for base in node.bases:
            base_name: str = self._resolve_call_name(base)
            if "BaseBehavior" in base_name:
                self.capabilities.add("Custom Entity Controller (BaseBehavior)")
            elif "BaseModPack" in base_name:
                self.capabilities.add("Multi-Entity Modpack Controller (BaseModPack)")

        self.generic_visit(node)

    def _resolve_call_name(self, node: ast.AST) -> str:
        """Resolves an AST node into a dotted string call name, resolving alias mappings."""
        if isinstance(node, ast.Name):
            name: str = node.id
            if name in self.imported_names:
                return self.imported_names[name]
            if name in self.imported_modules:
                return self.imported_modules[name]
            return name
        elif isinstance(node, ast.Attribute):
            value: str = self._resolve_call_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        return ""


def scan_python_file(
    file_path: Path, base_dir: Optional[Path] = None
) -> tuple[list[SecurityIssue], list[str]]:
    """
    Parses and scans a single Python script for security issues and capabilities.
    Returns (issues_list, capabilities_list).
    """
    relative_path: str = (
        str(file_path.relative_to(base_dir)).replace("\\", "/")
        if base_dir is not None
        else file_path.name
    )
    
    source: str
    try:
        source = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            source = file_path.read_text(encoding="latin-1")
        except Exception as e:
            return [
                SecurityIssue(
                    file=relative_path,
                    line=1,
                    col=0,
                    category="syntax",
                    severity=SecuritySeverity.WARNING,
                    description=f"Could not read file: {e}",
                )
            ], []

    source_lines: list[str] = source.splitlines()

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        return [
            SecurityIssue(
                file=relative_path,
                line=e.lineno or 1,
                col=e.offset or 0,
                category="syntax",
                severity=SecuritySeverity.WARNING,
                description=f"Python Syntax Error: {e.msg}",
                code_snippet=e.text.strip() if e.text else "",
            )
        ], []

    visitor = ModASTVisitor(relative_path, source_lines)
    visitor.visit(tree)

    return visitor.issues, sorted(visitor.capabilities)


def scan_mod_or_pack(target_dir: Path) -> SecurityReport:
    """
    Performs a thorough security scan across all Python files in a mod or modpack.
    Produces a detailed SecurityReport with risk level and human explanation.
    """
    target_dir = target_dir.resolve()
    target_name: str = target_dir.name
    all_issues: list[SecurityIssue] = []
    all_capabilities: set[str] = set()
    scanned_files: list[str] = []

    # Check for pack manifest name if applicable
    manifest_file: Path = target_dir / "pack.json"
    data: dict[str, Any]
    if manifest_file.exists():
        try:
            import json
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
            target_name = data.get("name", target_name)
        except Exception:
            pass
    else:
        config_file: Path = target_dir / "config.json"
        if config_file.exists():
            try:
                import json
                data = json.loads(config_file.read_text(encoding="utf-8"))
                target_name = data.get("name", target_name)
            except Exception:
                pass

    # Gather and scan all python scripts
    for py_file in target_dir.rglob("*.py"):
        # Ignore pycache and virtualenvs
        if any(part in ("__pycache__", ".git", ".venv", "venv") for part in py_file.parts):
            continue

        relative_path: str = str(py_file.relative_to(target_dir)).replace("\\", "/")
        scanned_files.append(relative_path)

        issues, caps = scan_python_file(py_file, base_dir=target_dir)
        all_issues.extend(issues)
        all_capabilities.update(caps)

    # Determine highest risk level
    has_danger: bool = any(issue.severity == "danger" for issue in all_issues)
    has_warning: bool = any(issue.severity == "warning" for issue in all_issues)
    has_info: bool = any(issue.severity == "info" for issue in all_issues)

    if has_danger:
        risk_level = SecurityRiskLevel.DANGEROUS
        is_safe = False
    elif has_warning:
        risk_level = SecurityRiskLevel.MEDIUM
        is_safe = False
    elif has_info:
        risk_level = SecurityRiskLevel.LOW
        is_safe = True
    else:
        risk_level = SecurityRiskLevel.SAFE
        is_safe = True

    # Generate summary and detailed explanation
    summary: str
    detailed_explanation: str
    if not scanned_files:
        summary = "No custom Python scripts found (pure visual/config mod)."
        detailed_explanation = (
            "This mod contains only static configuration and sprite graphics. "
            "No executable code is present, making it completely safe."
        )
    elif risk_level == SecurityRiskLevel.SAFE:
        summary = "Clean AST scan. Uses standard PyToNingans modding API."
        detailed_explanation = (
            "The scripts in this mod were analyzed via Abstract Syntax Tree (AST) inspection. "
            "No dangerous calls, network requests, or system processes were detected. "
            "The mod cleanly interacts with the desktop environment using safe sandbox APIs."
        )
    elif risk_level == SecurityRiskLevel.LOW:
        summary = "Safe with minor system interactions (e.g. browser launch)."
        detailed_explanation = (
            "The scripts appear safe, but perform minor non-destructive operations "
            "(such as opening documentation links in your browser)."
        )
    elif risk_level == SecurityRiskLevel.MEDIUM:
        summary = "Potential security warning: dynamic execution or local file writing."
        detailed_explanation = (
            "This mod performs operations that write to disk or execute dynamic code. "
            "Inspect the issues list to ensure this matches the mod's intended behavior."
        )
    else:
        summary = "DANGER: Risky system operations detected (network or process execution)!"
        detailed_explanation = (
            "CRITICAL: The static analyzer detected high-risk system operations. "
            "This mod attempts to run external system commands or communicate over the network. "
            "Do not run this mod unless you completely trust the author."
        )

    return SecurityReport(
        target_name=target_name,
        target_path=target_dir,
        risk_level=risk_level,
        is_safe=is_safe,
        issues=all_issues,
        capabilities=sorted(all_capabilities),
        scanned_files=sorted(scanned_files),
        summary=summary,
        detailed_explanation=detailed_explanation,
    )
