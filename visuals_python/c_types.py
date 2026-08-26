import ctypes
class vector2D(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float)
    ]

class Particle(ctypes.Structure):
    _fields_ = [
        ("position", vector2D),
        ("velocity", vector2D)
    ]

class wall(ctypes.Structure):
    _fields_ = [
        ("point1", vector2D),
        ("point2", vector2D)
    ]

class obstacles(ctypes.Structure):
    _fields_ = [
        ("walls", ctypes.POINTER(wall)),
        ("count", ctypes.c_int)
    ]
engine = ctypes.CDLL('./physics_engine.dll')

engine.update_positions.argtypes = [
    ctypes.POINTER(Particle),
    ctypes.c_int,
    ctypes.c_float,
    vector2D,
    obstacles,
    ctypes.c_int
]
engine.update_positions.restype = None