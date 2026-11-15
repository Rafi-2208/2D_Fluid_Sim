from c_types import *
import math


def draw_text(surface, text, font, x, y, color=(255, 255, 255)):
    text_surface = font.render(str(text), True, color)
    surface.blit(text_surface, (x, y))


def calculate_normal(wall):
    ux = wall.point2.x - wall.point1.x
    uy = wall.point2.y - wall.point1.y
    uz = wall.point2.z - wall.point1.z

    vx = wall.point3.x - wall.point1.x
    vy = wall.point3.y - wall.point1.y
    vz = wall.point3.z - wall.point1.z

    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx

    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length <= 1e-6:
        return Vector3D(0.0, -1.0, 0.0)
    return Vector3D(nx / length, ny / length, nz / length)


def build_orbit_camera(map_size, yaw, pitch, distance, fov):
    target_x = map_size.x * 0.5
    target_y = map_size.y * 0.5
    target_z = map_size.z * 0.5

    cos_p = math.cos(pitch)
    sin_p = math.sin(pitch)
    cos_y = math.cos(yaw)
    sin_y = math.sin(yaw)

    forward_x = sin_y * cos_p
    forward_y = sin_p
    forward_z = cos_y * cos_p

    cam = Camera()
    cam.position = Vector3D(
        target_x - forward_x * distance,
        target_y - forward_y * distance,
        target_z - forward_z * distance,
    )
    cam.yaw = yaw
    cam.pitch = pitch
    cam.fov = fov
    return cam
