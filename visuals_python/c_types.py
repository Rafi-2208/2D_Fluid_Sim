import ctypes
import os
from modifiable_variables import *
os.add_dll_directory(MINGW_DLL_DIRECTORY)


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
        ("point2", Vector2D)
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


if USE_GPU:
    dll_name = './physics_engine_gpu.dll'
else:
    dll_name = './physics_engine.dll'
engine = ctypes.CDLL(dll_name)


engine.update.argtypes = [
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
]
engine.update.restype = None