# 3D Fluid Simulation

A real-time 3D fluid simulation project built around a Python visual frontend and a high-performance C/CUDA physics and 3D software-rasterization engine. The project simulates large particle counts in 3D space with configurable forces, 3D quad walls, spawning volumes, interactive orbit camera controls, and multiple rendering/compute backends.

## Overview

This project focuses on fluid behavior in a 3D environment, combining:

- a Python GUI (Tkinter + Pygame) for controls, interactive 3D camera orbiting/zooming, and display
- optimized 3D SPH physics and depth-buffered perspective rendering kernels in C/CUDA
- ctypes-based interop between Python and native engine code
- runtime tuning of simulation parameters through configuration files and UI controls

It is intended as an experimental, performance-oriented sandbox for 3D fluid dynamics, particle interaction, and rendering tuning.

## Features

- Large particle-count 3D SPH fluid simulation
- Configurable 3D gravity, viscosity, pressure, damping, and friction
- 3D bounding container + adjustable 3D planar quad wall creation and removal
- Randomized 3D obstacle generation
- Interactive 3D orbit camera (mouse drag to rotate, scroll wheel to zoom, plus GUI sliders)
- Depth-buffered sphere-shaded 3D particle rasterization and 3D wireframe obstacle rendering
- Multiple rendering/engine modes:
  - single-core CPU
  - multi-core CPU (OpenMP)
  - CUDA GPU
- GUI-based controls for spawning, physics, visuals, camera, and walls
- Save/load support for simulation settings through the app UI
