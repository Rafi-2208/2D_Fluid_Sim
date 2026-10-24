import ctypes
from modifiable_variables import *
import os
from app_logging import APP_LOGGER, log_native
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
ENGINE_NAMES = {mode: name for mode, (name, _) in _ENGINE_DLLS.items()}
engine = None
engine_mode: int | None = None
_native_log_callback_type = ctypes.CFUNCTYPE(
    None, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p
)
_native_log_callback = _native_log_callback_type(log_native)


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
        init_result = driver.cuInit(0)
        if init_result != 0:
            APP_LOGGER.warning("CUDA driver initialization failed with code %d", init_result)
            return False
        device_result = driver.cuDeviceGetCount(ctypes.byref(device_count))
        if device_result != 0:
            APP_LOGGER.warning("Could not query CUDA devices; driver returned code %d", device_result)
            return False
        available = device_count.value > 0
        APP_LOGGER.info("CUDA availability check: available=%s devices=%d",
                        available, device_count.value)
        return available
    except (AttributeError, OSError):
        APP_LOGGER.info("CUDA driver unavailable; GPU engine will not be auto-selected", exc_info=True)
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
        if requested_mode == 2 and not has_cuda_gpu():
            raise OSError("CUDA was selected, but no CUDA-capable GPU/driver is available.")
        candidate_modes = [requested_mode]
        automatic = False
    else:
        raise ValueError('RENDERING must be "auto", 0 (single-core), 1 (multi-core), or 2 (GPU)')
    APP_LOGGER.info("Initializing simulation engine: requested=%s candidates=%s",
                    requested_mode, [ENGINE_NAMES[mode] for mode in candidate_modes])

    if engine is not None and engine_mode in candidate_modes:
        APP_LOGGER.info("Keeping existing simulation engine: %s", ENGINE_NAMES[engine_mode])
        return engine

    errors = []
    for mode in candidate_modes:
        mode_name, dll_filename = _ENGINE_DLLS[mode]
        dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), dll_filename)
        try:
            loaded_engine = ctypes.CDLL(dll_path)
        except OSError as error:
            APP_LOGGER.warning("Could not load %s engine library at %s: %s",
                               mode_name, dll_path, error)
            errors.append(f"{mode_name}: {error}")
            if not automatic:
                raise
            continue

        _configure_engine_functions(loaded_engine)
        engine = loaded_engine
        engine_mode = mode
        APP_LOGGER.info("Selected %s simulation engine", mode_name)
        return engine

    raise OSError("Could not load any simulation engine. " + "; ".join(errors))


def get_engine():
    if engine is None:
        return initialize_engine()
    return engine


def get_engine_name():
    if engine_mode is None:
        return "uninitialized"
    return ENGINE_NAMES[engine_mode]


def get_engine_mode():
    return engine_mode


def _configure_engine_functions(loaded_engine):
    try:
        loaded_engine.set_log_callback.argtypes = [_native_log_callback_type]
        loaded_engine.set_log_callback.restype = None
        loaded_engine.set_log_callback(_native_log_callback)
    except AttributeError:
        APP_LOGGER.warning("Native engine has no logging callback; rebuild it to enable C/CUDA log entries")

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
