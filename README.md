# 2D Fluid Simulation

A real-time 2D fluid simulation project built around a Python visual frontend and a high-performance C/CUDA physics engine. The project is designed to simulate large particle counts with configurable forces, walls, spawning conditions, and rendering modes.

## Overview

This project focuses on fluid behavior in a 2D environment, combining:

- a Python GUI for controls and visualization
- optimized backend physics kernels in C/CUDA
- ctypes-based interop between Python and native engine code
- runtime tuning of simulation parameters through configuration files and UI controls

It is intended as an experimental, performance-oriented sandbox for fluid dynamics, particle interaction, and rendering tuning.

## Features

- Large particle-count fluid simulation
- Configurable gravity, viscosity, pressure, damping, and friction
- Adjustable wall creation and removal
- Randomized obstacle generation
- Multiple rendering/engine modes:
  - single-core CPU
  - multi-core CPU
  - CUDA GPU
- GUI-based controls for spawning, physics, visuals, and walls
- Save/load support for simulation settings through the app UI