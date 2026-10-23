import ctypes
from modifiable_variables import *
import os

class Vector2D(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float)
    ]

class Particle(ctypes.Structure):
    _fields_ = [
        ("position", Vector2D),
        ("velocity", Vector2D),
        ("density", ctypes.c_float),
        ("area" , ctypes.c_int)
    ]

class Wall(ctypes.Structure):
    _fields_ = [
        ("point1", Vector2D),
        ("point2", Vector2D),
        ("normal" , Vector2D)
    ]

class Obstacles(ctypes.Structure):
    _fields_ = [
        ("walls", ctypes.POINTER(Wall)),
        ("count", ctypes.c_int)
    ]

class Area(ctypes.Structure):
    _fields_ = [
        ("area", ctypes.c_int),
        ("count", ctypes.c_int),
        ("particles", ctypes.POINTER(ctypes.POINTER(Particle)))

    ]


_ENGINE_DLLS = {
    0: ("single-core CPU", "physics_engine_cpu_single.dll"),
    1: ("multi-core CPU", "physics_engine_cpu_multi.dll"),
    2: ("CUDA GPU", "physics_engine_gpu.dll"),
}
engine = None
engine_mode = None


def has_cuda_gpu():
    try:
        if os.name == "nt":
            driver = ctypes.WinDLL("nvcuda.dll")
        else:
            driver = ctypes.CDLL("libcuda.so.1")
        driver.cuInit.argtypes = [ctypes.c_uint]
        driver.cuInit.restype = ctypes.c_int
        driver.cuDeviceGetCount.argtypes = [ctypes.POINTER(ctypes.c_int)]
        driver.cuDeviceGetCount.restype = ctypes.c_int

        device_count = ctypes.c_int()
        return (
            driver.cuInit(0) == 0
            and driver.cuDeviceGetCount(ctypes.byref(device_count)) == 0
            and device_count.value > 0
        )
    except (AttributeError, OSError):
        return False


def _automatic_modes():
    modes = []
    if has_cuda_gpu():
        modes.append(2)
    modes.append(1 if (os.cpu_count() or 1) > 1 else 0)
    if modes[-1] != 0:
        modes.append(0)
    return modes


def initialize_engine():
    global engine, engine_mode

    requested_mode = VARIABLES.get("RENDERING", "auto")
    if requested_mode == "auto":
        candidate_modes = _automatic_modes()
        automatic = True
    elif isinstance(requested_mode, int) and not isinstance(requested_mode, bool) and requested_mode in _ENGINE_DLLS:
        candidate_modes = [requested_mode]
        automatic = False
    else:
        raise ValueError('RENDERING must be "auto", 0 (single-core), 1 (multi-core), or 2 (GPU)')

    if engine is not None and engine_mode in candidate_modes:
        return engine

    errors = []
    for mode in candidate_modes:
        mode_name, dll_filename = _ENGINE_DLLS[mode]
        dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), dll_filename)
        try:
            loaded_engine = ctypes.CDLL(dll_path)
        except OSError as error:
            errors.append(f"{mode_name}: {error}")
            if not automatic:
                raise
            continue

        _configure_engine_functions(loaded_engine)
        engine = loaded_engine
        engine_mode = mode
        print(f"Using {mode_name} simulation engine")
        return engine

    raise OSError("Could not load any simulation engine. " + "; ".join(errors))


def get_engine():
    if engine is None:
        return initialize_engine()
    return engine


def _configure_engine_functions(loaded_engine):
    loaded_engine.update.argtypes = [
        ctypes.POINTER(Particle),
        ctypes.c_int,
        ctypes.c_float,
        Vector2D,
        Obstacles,
        ctypes.c_int,
        ctypes.c_float,
        ctypes.c_float,
        ctypes.c_float,
        ctypes.c_float,
        ctypes.c_float,
        Vector2D,
        ctypes.POINTER(Area),
        ctypes.c_float,
        ctypes.c_float,
        ctypes.c_int,
    ]
    loaded_engine.update.restype = None

    loaded_engine.drawing.argtypes = [
        ctypes.POINTER(Particle),
        ctypes.c_int,
        ctypes.POINTER(Obstacles),
        ctypes.c_int,
        Vector2D,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_float,
    ]
    loaded_engine.drawing.restype = None
