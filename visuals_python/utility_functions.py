from c_types import *
import math



def draw_text(surface, text, font, x, y, color=(255, 255, 255)):
    text_surface = font.render(str(text), True, color)
    surface.blit(text_surface, (x, y))

def rotate_vector(x, y, angle_degrees):
    rad = math.radians(angle_degrees)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    new_x = x * cos_a - y * sin_a
    new_y = x * sin_a + y * cos_a
    return new_x, new_y

def calculate_normal(wall):
    dx = wall.point2.x - wall.point1.x
    dy = wall.point2.y - wall.point1.y
    length = math.sqrt(dx * dx + dy * dy)
    return Vector2D(-dy/length, dx/length)

