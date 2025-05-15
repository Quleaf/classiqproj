# Converter Shor Script Manual
---

## Why This QASM Conversion Is Necessary

The QASM 2.0 files we received are written using IBM’s **extended OpenQASM 2.0** format, enabled by `qiskit.qasm2.LEGACY_CUSTOM_INSTRUCTIONS`. This format significantly differs from the standard OpenQASM 2.0 specification by:

* Including additional gates from `qelib1.inc` such as `sx`, `rzx`, `rxx`, etc., which are not defined in the official OpenQASM 2.0 grammar;
* Supporting **deeply nested custom gate definitions**, allowing gates to be composed recursively from other gates;
* Enabling a wide range of **controlled and parameterized unitary operations** that are not natively supported by many QASM interpreters.

More details are available in the [Qiskit QASM 2.0 documentation](https://docs.quantum.ibm.com/api/qiskit/qasm2).

Our simulator backend is designed to process a simplified JSON-like intermediate format, which:

* **Does not support nested gate definitions**;
* **Does not recognize IBM-specific extensions**;
* Expects all gates to be fully decomposed into basic gates like `u`, `cx`, etc.

---

## What the Converter Does

To bridge this compatibility gap, we implemented a custom Python script (`convert_shorqasm.py`) that performs the following steps:

* **Parses and removes custom gate blocks** from the QASM file;
* **Recursively unfolds** nested gate calls into primitive instructions;
* **Maps `cp(θ)` gates** into a sequence of `u(0, 0, θ/2)`, `cx`, and their inverses;
* **Converts `p(θ)` gates** into `u(0, 0, θ)` form;
* **Performs variable substitution** for gate parameters and qubit arguments;
* **Strips unnecessary formatting**, producing a clean, flattened circuit.

This approach ensures the converted QASM is readable by our QCompute simulator backend without the need for runtime QASM parsing.

---

## Why Not Just Use `LEGACY_CUSTOM_INSTRUCTIONS`?

While `LEGACY_CUSTOM_INSTRUCTIONS` allows Qiskit’s own parser to interpret extended OpenQASM files, this does not help with non-Qiskit simulators. Our backend:

* Is not built to interpret QASM natively;
* Requires explicit decomposition of all gates;
* Aims to remain independent of Qiskit-specific behaviors.

Rewriting our backend to fully support IBM's extended OpenQASM grammar would be complex and time-consuming. Instead, this script provides a practical and deterministic translation path that guarantees compatibility.

---

## Example

Original QASM snippet:

```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
sx q[0];
cp(pi/4) q[0], q[1];
```

Converted version:

```qasm
qreg q[2];
u(0,0,(pi/4)/2) q[1];
cx q[0],q[1];
u(0,0,-(pi/4)/2) q[1];
cx q[0],q[1];
```

This format eliminates dependencies on external includes or custom gate declarations.

---

## References

* [Qiskit QASM 2.0 API Reference](https://docs.quantum.ibm.com/api/qiskit/qasm2)
* [Qiskit Issue Tracker on LEGACY\_CUSTOM\_INSTRUCTIONS](https://github.com/Qiskit/qiskit/issues/12124)

---
