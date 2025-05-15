#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_shorqasm.py
==================

This script converts a QASM (Quantum Assembly) file containing Shor's algorithm
circuit into a compatible format for QCompute SDK. It handles custom gate definitions,
expands them into native gates, and performs necessary transformations.

Features:
    - Parses and processes QASM gate definitions
    - Converts custom gates to native gates
    - Handles parameter and qubit mapping
    - Expands nested gate definitions
    - Converts cp(theta) gates to u1+cx combinations
    - Converts p(theta) gates to u(0,0,theta)
    - Cleans and formats the output QASM

Dependencies:
    - Python 3.x
    - Standard libraries: sys, re, pathlib, collections

Usage:
    python convert_shorqasm.py

Input/Output:
    - Input:  Example/Level_1/data/shor_circuit.qasm
    - Output: Example/Level_1/data/shor_compatible.qasm

Note:
    This script is specifically designed to process Shor's algorithm QASM files
    and convert them into a format compatible with QCompute SDK.
"""

import sys, re, pathlib
from collections import OrderedDict

###############################################################################
# ----- 1. read the qasm file ----------------------------------------------------------------
###############################################################################
SRC  = pathlib.Path('Example/Level_1/data/shor_circuit.qasm')       # original qasm file
DEST = pathlib.Path('Example/Level_1/data/shor_compatible.qasm')  # output

text = SRC.read_text()

###############################################################################
# ----- 2. parse the gate definition (stack method, support nested braces) -----------------------------
###############################################################################
gate_defs = OrderedDict()          # name -> {params, qubits, body_lines}

lines = text.splitlines()
i, n = 0, len(lines)
while i < n:
    line = lines[i]
    m = re.match(r'\s*gate\s+(\w+)\s*(\([^)]*\))?\s*([\w,\s]+)\s*\{', line)
    if m:
        name = m.group(1)
        params = [p.strip() for p in (m.group(2)[1:-1].split(','))] if m.group(2) else []
        qubits = [q.strip() for q in m.group(3).split(',')]
        body = []
        brace = 0
        # read to the corresponding }
        while i < n:
            body.append(lines[i])
            brace += lines[i].count('{') - lines[i].count('}')
            i += 1
            if brace == 0:
                break
        # remove the first and last gate line
        body = body[1:-1]
        gate_defs[name] = {'params': params, 'qubits': qubits,
                           'body': [b.strip() for b in body if b.strip()]}
    else:
        i += 1

###############################################################################
# ----- 3. remove the gate definition, keep the main line ------------------------------------------
###############################################################################
def remove_gate_blocks(qasm: str) -> str:
    return re.sub(r'(?s)^\s*gate\s+\w+\s*(\([^)]*\))?\s*[\w,\s]+\s*\{[^}]*\}\s*', '',
                  qasm, flags=re.MULTILINE)

header, *body_part = remove_gate_blocks(text).splitlines()
body_lines = body_part          # list[str]  (包含空行)

###############################################################################
# ----- 4. tool: cp(theta) -> u1+cx ------------------------------------------
###############################################################################
cp_pattern = re.compile(
    r'cp\(([^)]+)\)\s+([\w\[\]0-9]+)\s*,\s*([\w\[\]0-9]+)\s*;'
)

def cp_to_native(line: str) -> str:
    if not cp_pattern.search(line):
        return line

    def _sub(m):
        theta, ctrl, tgt = m.groups()
        half = f"(({theta})/2)"          #
        return '\n'.join([
            f'u(0,0,{half}) {tgt};',
            f'cx {ctrl},{tgt};',
            f'u(0,0,-{half}) {tgt};',
            f'cx {ctrl},{tgt};'
        ])
    
    return cp_pattern.sub(_sub, line)

###############################################################################
# ----- Additional: p(theta) -> u(0,0,theta) ---------------------------------------
###############################################################################
p_pattern = re.compile(
    r'p\(([^)]+)\)\s+([\w\[\]0-9]+)\s*;'
)
def p_to_native(line: str) -> str:
    if not p_pattern.search(line):
        return line
    def _sub(m):
        theta, tgt = m.groups()
        return f'u(0,0,{theta}) {tgt};'
    return p_pattern.sub(_sub, line)


###############################################################################
# ----- 5. recursively expand the custom gate call --------------------------------------------
###############################################################################
call_pat = re.compile(
    r'^\s*(\w+)\s*(\([^)]*\))?\s*([\w\[\]0-9_,\s]+);\s*$'
)

def convert_line(line: str) -> str:
    line = cp_to_native(line)   # first expand cp(...)
    line = p_to_native(line)    # then replace p(...) with u(0,0,θ)
    line = re.sub(r'\+\+', '+', line)
    line = re.sub(r'-\+', '-', line)
    line = re.sub(r'\+-', '-', line)
    line = re.sub(r'--', '-', line)
    return line

def expand_once(lines_in):
    out, changed = [], False
    for ln in lines_in:
        m = call_pat.match(ln)
        if not m or m.group(1) not in gate_defs:
            out.append(convert_line(ln)) 
            continue
        # ---- need to expand ----
        gname, arg_str, qub_str = m.group(1), m.group(2) or '', m.group(3)
        gdef  = gate_defs[gname]
        # 1) parameter mapping
        formal_p = gdef['params']
        actual_p = [p.strip() for p in arg_str[1:-1].split(',')] if arg_str else []
        p_map = dict(zip(formal_p, actual_p))
        # 2) quantum bit mapping
        formal_q = gdef['qubits']
        actual_q = [q.strip() for q in qub_str.split(',')]
        q_map = dict(zip(formal_q, actual_q))
        # 3) replace line by line
        for b in gdef['body']:
            line = b
            # parameter
            for fp, ap in p_map.items():
                line = re.sub(rf'\b{re.escape(fp)}\b', ap, line)
            # qubits
            for fq, aq in q_map.items():
                line = re.sub(rf'\b{re.escape(fq)}\b', aq, line)
            out.append(convert_line(line))
        changed = True
    return out, changed

# repeatedly expand until there are no custom gates
changed = True
while changed:
    body_lines, changed = expand_once(body_lines)

###############################################################################
# ----- 6. remove extra empty lines / format -----------------------------------------------
###############################################################################
clean = '\n'.join([ln for ln in body_lines if ln.strip()])

###############################################################################
# ----- 7. write the result --------------------------------------------------------------
###############################################################################
DEST.write_text(header + '\n' + clean + '\n')
print(f'Done! Write to {DEST}')
