---
apply: always
---

# Project Context
This is a 3D fluid simulation utilizing a Python frontend and a C/CUDA backend.

# Tech Stack
- Frontend: Python (Pygame, Tkinter) for rendering, interactive camera controls, and GUI.
- Backend: C and CUDA for performance-critical 3D SPH physics calculations and depth-buffered 3D perspective rendering into the pygame display buffer.
- Bindings: `ctypes` for memory mapping and function calls.

# Architectural Rules
- **Physics Engine:** Core simulation modifications must target the C/CUDA source files, not the Python wrapper.
- **C-Bindings:** Ensure `c_types.py` correctly interfaces with `physics_engine_gpu.dll`, `physics_engine_cpu_multi.dll`, and `physics_engine_cpu_single.dll`.
- **State Management:** All simulation parameters must be routed exclusively through `modifiable_variables.py` and `config.json`.
