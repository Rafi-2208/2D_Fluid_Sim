import ctypes
class Vector2D(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float)
    ]

class Particle(ctypes.Structure):
    _fields_ = [
        ("position", Vector2D),
        ("velocity", Vector2D),
        ("density", ctypes.c_float)
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
engine = ctypes.CDLL('./physics_engine.dll')

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
]
engine.update.restype = None