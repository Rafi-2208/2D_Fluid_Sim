import time

import pygame
from c_types import *
import random

wall_count = 6
walls_array = Wall * wall_count
walls_array = walls_array()
walls_array[0].point1 = Vector2D(100.0, 100.0)
walls_array[0].point2 = Vector2D(1300.0, 100.0)
walls_array[1].point1 = Vector2D(1300.0, 100.0)
walls_array[1].point2 = Vector2D(1300.0, 1100.0)
walls_array[2].point1 = Vector2D(1300.0, 1100.0)
walls_array[2].point2 = Vector2D(100.0, 1100.0)
walls_array[3].point1 = Vector2D(100.0, 1100.0)
walls_array[3].point2 = Vector2D(100.0, 100.0)
walls_array[4].point1 = Vector2D(100.0, 600.0)
walls_array[4].point2 = Vector2D(500.0, 600.0)
walls_array[5].point1 = Vector2D(500.0, 600.0)
walls_array[5].point2 = Vector2D(500.0, 100.0)


obstacles = Obstacles()
obstacles.count = wall_count
obstacles.walls = ctypes.cast(walls_array, ctypes.POINTER(Wall))

pygame.init()
screen = pygame.display.set_mode((2000, 1200))
clock = pygame.time.Clock()

PARTICLE_COUNT = 2000
MAX_INFLUENCE_DISTANCE = 40
GRAVITY = Vector2D(0.0, 981.0)
COLLISION_LIMIT = 10
TARGET_DENSITY = 250000
PRESSURE_MULTIPLIER = 0.00001
COLLISION_DAMPENING = 0.75
VISCOSITY = 1

particles_array = Particle * PARTICLE_COUNT
particles_array = particles_array()
for i in range(PARTICLE_COUNT):
    start_x = random.randint(110, 450)
    start_y = random.randint(110, 450)
    particles_array[i].position = Vector2D(start_x, start_y)
    vel_x = random.randint(-20, 20)
    vel_y = random.randint(-20, 20)
    particles_array[i].velocity = Vector2D(vel_x, vel_y)


t = time.time()
running = True
while running:
    if time.time() - t > 10:
        walls_array[5].point1 = Vector2D(500.0, 550.0)
        obstacles = Obstacles()
        obstacles.count = wall_count
        obstacles.walls = ctypes.cast(walls_array, ctypes.POINTER(Wall))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    screen.fill((0, 0, 0))
    dt = clock.tick(120) / 1000.0
    if dt > 0.016:
        dt = 0.016
    engine.update(
        particles_array,
        PARTICLE_COUNT,
        dt,
        GRAVITY,
        obstacles,
        COLLISION_LIMIT,
        MAX_INFLUENCE_DISTANCE,
        TARGET_DENSITY,
        PRESSURE_MULTIPLIER,
        COLLISION_DAMPENING,
        VISCOSITY,

    )
    for i in range(PARTICLE_COUNT):
        p = particles_array[i]
        colour_calculation_helper = min(1.0, p.density / 550000.0)
        r = int(colour_calculation_helper * 255)
        g = 50
        b = int((1.0 - colour_calculation_helper) * 255)
        pos = (int(p.position.x), int(p.position.y))
        pygame.draw.circle(screen, (r, g, b), pos, 3)
    for i in range(obstacles.count):
        wall = obstacles.walls[i]
        start_pos = (wall.point1.x, wall.point1.y)
        end_pos = (wall.point2.x, wall.point2.y)
        pygame.draw.line(screen, (255, 255, 255), start_pos, end_pos, 3)
    pygame.display.flip()

pygame.quit()
