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


if RENDERING == 2:
    dll_name = './physics_engine_gpu.dll'
elif RENDERING == 1:
    dll_name = './physics_engine_cpu_multi.dll'
elif RENDERING == 0:
    dll_name = './physics_engine_cpu_single.dll'




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
    ctypes.c_float,
    ctypes.c_int,
]
engine.update.restype = None

engine.drawing.argtypes = [
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
engine.drawing.restype = None