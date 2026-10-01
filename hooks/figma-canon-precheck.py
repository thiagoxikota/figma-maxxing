#!/usr/bin/env python3
"""figma-canon-precheck: optional PreToolUse hook for figma_execute (figma-console MCP).

Scans the JavaScript an agent is about to run in Figma for Plugin API patterns that are known
to fail, and tells the agent before the call runs instead of after.

Modes (environment variable FIGMA_PRECHECK_MODE):
  warn   (default) never blocks. Findings are added to the agent's context and the normal
         permission flow continues.
  block  findings marked BLOCK deny the call with the reason. WARN findings still only warn.

The default is warn because some BLOCK patterns are valid in other editors: createConnector,
for example, works in FigJam. Turn on block mode when you only work in Figma Design files.

Nothing is written to disk unless FIGMA_PRECHECK_LOG points to a file; then one JSON line per
call is appended (decision and findings, never the script itself).

This hook never opens Figma and never repairs the bridge. Recovery belongs to the
figma-bridge-doctor skill.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REFS = 'skills/figma-canon/references/'

# (regex, severity, reason, reference)
PATTERNS = [
    # Broken patterns with no recovery.
    (r'figma\.currentPage\s*=\s*[a-zA-Z_]', 'BLOCK',
     'Sync `figma.currentPage = X` assignment does not work. Use `await figma.setCurrentPageAsync(X)`.',
     'plugin-api-core.md#page-switching-async-only'),
    (r'figma\.createConnector\s*\(', 'BLOCK',
     '`createConnector()` is FigJam only and throws in Design files. Use `createNodeFromSvg(...)` for arrow shapes.',
     'plugin-api-anomalies.md#createconnector-figjam-only'),
    # Missing await: the call starts a statement, so its promise is thrown away.
    # Calls inside an expression (Promise.all, a variable, a return) are left alone.
    (r'(?m)(?:^|[;{}])\s*figma\.loadFontAsync\s*\(', 'BLOCK',
     'Missing `await` on `figma.loadFontAsync()`. Required before any text operation.',
     'plugin-api-core.md#font-loading-required-before-text-ops'),
    (r'(?m)(?:^|[;{}])\s*figma\.setCurrentPageAsync\s*\(', 'BLOCK',
     'Missing `await` on `figma.setCurrentPageAsync()`.',
     'plugin-api-core.md#page-switching-async-only'),
    (r'(?m)(?:^|[;{}])\s*figma\.importComponentByKeyAsync\s*\(', 'BLOCK',
     'Missing `await` on `figma.importComponentByKeyAsync()`.',
     'plugin-api-core.md#await-every-async-call'),
    # True in the official Figma MCP `use_figma` context; a warning everywhere else.
    (r'figma\.notify\s*\(', 'WARN',
     '`figma.notify()` throws "not implemented" in the `use_figma` context, and a toast never '
     'reaches the agent in any context. Use `return` for output.',
     'plugin-api-data.md#figmanotify-not-implemented-in-use_figma'),
    (r'\.setPluginData\s*\(', 'WARN',
     '`setPluginData` is not supported in the `use_figma` context. '
     '`setSharedPluginData(namespace, key, value)` works in both.',
     'plugin-api-data.md#getplugindata-and-setplugindata-not-supported-in-use_figma'),
    # Anchored to color contexts so URL fragments and markdown anchors do not match.
    (r"(?i:\w*(?:color|fills?|stroke|background))\s*[:=]\s*['\"`]#[0-9a-fA-F]{3,8}\b", 'WARN',
     'Hex literal in a color, fill or stroke assignment. Check whether a variable covers this value: '
     'hardcoded hex is a violation when variables exist.',
     'ai-slop-signatures.md#token-violations'),
    (r"figma\.util\.(?:rgba?|solidPaint)\s*\(\s*['\"`]#[0-9a-fA-F]{3,8}\b", 'WARN',
     'Hex literal in a color, fill or stroke assignment. Check whether a variable covers this value: '
     'hardcoded hex is a violation when variables exist.',
     'ai-slop-signatures.md#token-violations'),
    (r'figma\.createRectangle\s*\(', 'WARN',
     'Raw `createRectangle`. Verify that no existing component matches; prefer `createInstance()`.',
     'ai-slop-signatures.md#component-reuse-failures'),
    (r"layoutSizing(?:Horizontal|Vertical)\s*=\s*['\"]FILL", 'WARN',
     '`layoutSizing = "FILL"` must be set AFTER `parent.appendChild(child)`. '
     'The hook cannot verify the order: check it yourself.',
     'plugin-api-core.md#layout-sizing-order-matters'),
    (r'\bconsole\.log\s*\(', 'WARN',
     '`console.log()` does not reach the agent: the payload is dropped silently. '
     'Use `return { ... }` for structured output.',
     'plugin-api-data.md#consolelog-not-the-output-channel'),
    (r"['\"]ALL_SCOPES['\"]", 'WARN',
     '`ALL_SCOPES` floods the variable picker and breaks token mapping. '
     'Pick the narrowest scope set (FRAME_FILL, TEXT_FILL, STROKE_COLOR, GAP, CORNER_RADIUS).',
     'plugin-api-data.md#variable-scopes-never-default-to-all_scopes'),
]

MAX_SCRIPT_CHARS = 20000
BRIDGE_PORTS = '9223-9232'


NON_CODE = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`', re.S)


def code_only(code: str) -> str:
    """Blank out comments and string literals, keeping offsets, so a rule quoted in a comment does not count."""
    return NON_CODE.sub(lambda m: re.sub(r'[^\n]', ' ', m.group(0)), code)


def scan(code: str) -> list:
    """Return one finding per match of a known pattern."""
    findings = []
    stripped = code_only(code)
    for pattern, severity, reason, ref in PATTERNS:
        for match in re.finditer(pattern, stripped if severity == 'BLOCK' else code):
            findings.append({
                'severity': severity,
                'match': match.group(0)[:80],
                'reason': reason,
                'ref': REFS + ref,
                'position': match.start(),
            })
    if len(code) > MAX_SCRIPT_CHARS:
        findings.append({
            'severity': 'WARN',
            'match': f'{len(code)} characters',
            'reason': 'Script over 20 KB: likely to hit the figma_execute output cap or time out. '
                      'Split it across several calls.',
            'ref': REFS + 'figma-execute-atomicity.md#output-protocol',
            'position': 0,
        })
    return findings


def bridge_note() -> str:
    """Report a missing bridge connection when that can be measured. Read-only, never repairs."""
    try:
        result = subprocess.run(['lsof', '-nP', f'-iTCP:{BRIDGE_PORTS}', '-sTCP:ESTABLISHED'],
                                capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return ''
    if result.returncode == 0 and result.stdout.strip():
        return ''
    return ('No established connection on the bridge ports (' + BRIDGE_PORTS + '). '
            'If this call fails, run the figma-bridge-doctor skill. This hook does not open Figma.')


def log(decision: str, findings: list, code_length: int):
    target = os.environ.get('FIGMA_PRECHECK_LOG')
    if not target:
        return
    try:
        path = Path(target).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a') as handle:
            handle.write(json.dumps({
                'iso': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'decision': decision,
                'code_length': code_length,
                'findings': [{k: f[k] for k in ('severity', 'reason', 'ref')} for f in findings],
            }) + '\n')
    except OSError:
        pass


def emit(context: str = '', deny_reason: str = ''):
    """Print the PreToolUse decision. Silence means: no opinion, normal permission flow."""
    output = {'hookEventName': 'PreToolUse'}
    if deny_reason:
        output['permissionDecision'] = 'deny'
        output['permissionDecisionReason'] = deny_reason
    if context:
        output['additionalContext'] = context
    if len(output) > 1:
        print(json.dumps({'hookSpecificOutput': output}))


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode('utf-8', errors='replace'))
    except ValueError:
        return 0
    tool_input = payload.get('tool_input') if isinstance(payload, dict) else None
    code = tool_input.get('code') if isinstance(tool_input, dict) else None
    if not isinstance(code, str) or not code:
        return 0

    findings = scan(code)
    note = bridge_note() if os.environ.get('FIGMA_PRECHECK_BRIDGE', '1') != '0' else ''
    lines = [f"[{f['severity']}] {f['reason']} (see {f['ref']})" for f in findings]
    blocking = [line for line, f in zip(lines, findings) if f['severity'] == 'BLOCK']
    mode = os.environ.get('FIGMA_PRECHECK_MODE', 'warn').lower()

    if blocking and mode == 'block':
        log('deny', findings, len(code))
        emit(deny_reason='figma-canon-precheck blocked this script:\n\n' + '\n\n'.join(blocking))
        return 0

    notes = ([note] if note else []) + lines
    log('warn' if findings else 'pass', findings, len(code))
    if notes:
        emit(context='figma-canon-precheck:\n\n' + '\n\n'.join(notes))
    return 0


if __name__ == '__main__':
    sys.exit(main())
