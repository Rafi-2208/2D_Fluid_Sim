import pygame
import ctypes
from c_types import *
import random
wall_count = 4
walls_array = wall * wall_count
walls_array = walls_array()
walls_array[0].point1 = vector2D(100.0, 100.0)
walls_array[0].point2 = vector2D(700.0, 100.0)
walls_array[1].point1 = vector2D(700.0, 100.0)
walls_array[1].point2 = vector2D(700.0, 500.0)
walls_array[2].point1 = vector2D(700.0, 500.0)
walls_array[2].point2 = vector2D(100.0, 500.0)
walls_array[3].point1 = vector2D(100.0, 500.0)
walls_array[3].point2 = vector2D(100.0, 100.0)
obstacles = obstacles()
obstacles.count = wall_count
obstacles.walls = ctypes.cast(walls_array, ctypes.POINTER(wall))


pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

import random

particle_count = 50000
particles_array = Particle * particle_count
particles_array = particles_array()
for i in range(particle_count):
    start_x = random.uniform(150.0, 650.0)
    start_y = random.uniform(150.0, 450.0)
    particles_array[i].position = vector2D(start_x, start_y)
    vel_x = random.uniform(-200.0, 200.0)
    vel_y = random.uniform(-200.0, 200.0)
    particles_array[i].velocity = vector2D(vel_x, vel_y)

gravity = vector2D(0.0, 981.0)
collision_limit = 10


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    screen.fill((0, 0, 0))
    dt = clock.tick(120) / 1000.0
    engine.update_positions(
        particles_array,
        particle_count,
        dt,
        gravity,
        obstacles,
        collision_limit
    )
    for i in range(particle_count):
        p = particles_array[i]
        pos = (int(p.position.x), int(p.position.y))
        pygame.draw.circle(screen, (0, 150, 255), pos, 3)
    for i in range(obstacles.count):
        wall = obstacles.walls[i]
        start_pos = (wall.point1.x, wall.point1.y)
        end_pos = (wall.point2.x, wall.point2.y)
        pygame.draw.line(screen, (255, 255, 255), start_pos, end_pos, 3)
    pygame.display.flip()

pygame.quit()