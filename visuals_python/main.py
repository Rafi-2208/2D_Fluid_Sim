import time
import pygame
from c_types import *
import random
from utility_functions import *
from modifiable_variables import *
from gui import start_gui_thread
VARIABLES["MAP_SIZE"] = Vector2D(VARIABLES["MAP_SIZE"][0] , VARIABLES["MAP_SIZE"][1])
VARIABLES["GRAVITY"] = Vector2D(VARIABLES["GRAVITY"][0], VARIABLES["GRAVITY"][1])
VARIABLES["STARTING_POSITION_X"] = Vector2D(VARIABLES["STARTING_POSITION_X"][0] , VARIABLES["STARTING_POSITION_X"][1])
VARIABLES["STARTING_POSITION_Y"] = Vector2D(VARIABLES["STARTING_POSITION_Y"][0] , VARIABLES["STARTING_POSITION_Y"][1])
VARIABLES["STARTING_SPEED_X"] = Vector2D(VARIABLES["STARTING_SPEED_X"][0] , VARIABLES["STARTING_SPEED_X"][1])
VARIABLES["STARTING_SPEED_Y"] = Vector2D(VARIABLES["STARTING_SPEED_Y"][0] , VARIABLES["STARTING_SPEED_Y"][1])



VARIABLES["WALL_COUNT"] = VARIABLES["WALL_COUNT"] + VARIABLES["RANDOM_WALL_COUNT"]
walls_array = Wall * VARIABLES["WALL_COUNT"]
walls_array = walls_array()
walls_array[0].point1 = Vector2D(0.0, 0.0)
walls_array[0].point2 = Vector2D(2000.0, 0.0)
walls_array[1].point1 = Vector2D(2000.0, 0.0)
walls_array[1].point2 = Vector2D(2000.0, 1200.0)
walls_array[2].point1 = Vector2D(2000.0, 1200.0)
walls_array[2].point2 = Vector2D(0.0, 1200.0)
walls_array[3].point1 = Vector2D(0.0, 1200.0)
walls_array[3].point2 = Vector2D(0.0, 0.0)
for i in range(VARIABLES["RANDOM_WALL_COUNT"]):
    walls_array[i + 4].point1 = Vector2D(random.randint(0 , 2000), random.randint(0 , 1200))
    walls_array[i + 4].point2 = Vector2D(random.randint(-VARIABLES["RANDOM_WALL_MAX_LEN"], VARIABLES["RANDOM_WALL_MAX_LEN"]) + walls_array[i + 4].point1.x, random.randint(-VARIABLES["RANDOM_WALL_MAX_LEN"], VARIABLES["RANDOM_WALL_MAX_LEN"]) + walls_array[i + 4].point1.y)
for i in range(VARIABLES["RANDOM_WALL_COUNT"] + VARIABLES["WALL_COUNT"]):
    walls_array[i].normal = calculate_normal(walls_array[i])

obstacles = Obstacles()
obstacles.count = VARIABLES["WALL_COUNT"]
obstacles.walls = ctypes.cast(walls_array, ctypes.POINTER(Wall))



pygame.init()
screen = pygame.display.set_mode((int(VARIABLES["MAP_SIZE"].x) , int(VARIABLES["MAP_SIZE"].y)))
clock = pygame.time.Clock()
pygame.font.init()
main_font = pygame.font.SysFont(None, 30)

x_limit = int(VARIABLES["MAP_SIZE"].x / VARIABLES["MAX_INFLUENCE_DISTANCE"])
y_limit = int(VARIABLES["MAP_SIZE"].y / VARIABLES["MAX_INFLUENCE_DISTANCE"])
total_areas = x_limit * y_limit
areas_array = (Area * total_areas)()
for i in range(total_areas):
    areas_array[i].area = i
    areas_array[i].count = 0
    PointerArrayType = ctypes.POINTER(Particle) * VARIABLES["MAX_PARTICLES_PER_AREA"]
    particle_pointers_buffer = PointerArrayType()
    areas_array[i].particles = ctypes.cast(particle_pointers_buffer, ctypes.POINTER(ctypes.POINTER(Particle)))



particles_array = Particle * VARIABLES["PARTICLE_COUNT"]
particles_array = particles_array()
pos_x_min = int(min(VARIABLES["STARTING_POSITION_X"].x, VARIABLES["STARTING_POSITION_X"].y))
pos_x_max = int(max(VARIABLES["STARTING_POSITION_X"].x, VARIABLES["STARTING_POSITION_X"].y))
pos_y_min = int(min(VARIABLES["STARTING_POSITION_Y"].x, VARIABLES["STARTING_POSITION_Y"].y))
pos_y_max = int(max(VARIABLES["STARTING_POSITION_Y"].x, VARIABLES["STARTING_POSITION_Y"].y))
spd_x_min = int(min(VARIABLES["STARTING_SPEED_X"].x, VARIABLES["STARTING_SPEED_X"].y))
spd_x_max = int(max(VARIABLES["STARTING_SPEED_X"].x, VARIABLES["STARTING_SPEED_X"].y))
spd_y_min = int(min(VARIABLES["STARTING_SPEED_Y"].x, VARIABLES["STARTING_SPEED_Y"].y))
spd_y_max = int(max(VARIABLES["STARTING_SPEED_Y"].x, VARIABLES["STARTING_SPEED_Y"].y))

for i in range(VARIABLES["PARTICLE_COUNT"]):
    start_x = random.randint(pos_x_min, pos_x_max)
    start_y = random.randint(pos_y_min, pos_y_max)
    particles_array[i].position = Vector2D(start_x, start_y)

    vel_x = random.randint(spd_x_min, spd_x_max)
    vel_y = random.randint(spd_y_min, spd_y_max)
    particles_array[i].velocity = Vector2D(vel_x, vel_y)



total_time = 0
time_update = 0
iteration = 0
drawing_time = 0
t = time.time()
running = True



start_gui_thread(VARIABLES)

while running:
    t = time.time()

    if VARIABLES["RESTART_CLICKED"]:
        VARIABLES["PARTICLE_COUNT"] = VARIABLES["STARTING_PARTICLE_COUNT"]
        pos_x_min = int(min(VARIABLES["STARTING_POSITION_X"].x, VARIABLES["STARTING_POSITION_X"].y))
        pos_x_max = int(max(VARIABLES["STARTING_POSITION_X"].x, VARIABLES["STARTING_POSITION_X"].y))

        pos_y_min = int(min(VARIABLES["STARTING_POSITION_Y"].x, VARIABLES["STARTING_POSITION_Y"].y))
        pos_y_max = int(max(VARIABLES["STARTING_POSITION_Y"].x, VARIABLES["STARTING_POSITION_Y"].y))

        spd_x_min = int(min(VARIABLES["STARTING_SPEED_X"].x, VARIABLES["STARTING_SPEED_X"].y))
        spd_x_max = int(max(VARIABLES["STARTING_SPEED_X"].x, VARIABLES["STARTING_SPEED_X"].y))

        spd_y_min = int(min(VARIABLES["STARTING_SPEED_Y"].x, VARIABLES["STARTING_SPEED_Y"].y))
        spd_y_max = int(max(VARIABLES["STARTING_SPEED_Y"].x, VARIABLES["STARTING_SPEED_Y"].y))

        for i in range(VARIABLES["PARTICLE_COUNT"]):
            start_x = random.randint(pos_x_min, pos_x_max)
            start_y = random.randint(pos_y_min, pos_y_max)
            particles_array[i].position = Vector2D(start_x, start_y)
            vel_x = random.randint(spd_x_min, spd_x_max)
            vel_y = random.randint(spd_y_min, spd_y_max)
            particles_array[i].velocity = Vector2D(vel_x, vel_y)
            particles_array[i].velocity = Vector2D(vel_x, vel_y)
        total_time = 0
        time_update = 0
        iteration = 0
        drawing_time = 0
        VARIABLES["RESTART_CLICKED"] = False





    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    screen.fill((0, 0, 0))
    dt = clock.tick_busy_loop(60) / 1000.0
    fps_value = clock.get_fps()

    if dt > 0.016:
        dt = 0.016
    t2 = time.time()
    friction_split_timing = VARIABLES["FRICTION_MULTIPLIER"] ** (1.0 / VARIABLES["SUB_STEPS"])
    wall_push_split_timing = VARIABLES["WALL_DEFAULT_PUSH"] / VARIABLES["SUB_STEPS"]
    engine.update(
        particles_array,
        VARIABLES["PARTICLE_COUNT"],
        dt,
        VARIABLES["GRAVITY"],
        obstacles,
        VARIABLES["COLLISION_LIMIT"],
        VARIABLES["MAX_INFLUENCE_DISTANCE"],
        VARIABLES["TARGET_DENSITY"],
        VARIABLES["PRESSURE_MULTIPLIER"],
        VARIABLES["COLLISION_DAMPENING"],
        VARIABLES["VISCOSITY"],
        VARIABLES["MAP_SIZE"],
        areas_array,
        friction_split_timing,
        wall_push_split_timing,
        VARIABLES["SUB_STEPS"],
    )
    time_update += time.time() - t2
    t3 = time.time()

    screen.fill((0, 0, 0))
    screen.lock()
    pitch = screen.get_pitch()
    view = memoryview(screen.get_view('1'))
    buffer_array = (ctypes.c_uint32 * (len(view) // 4)).from_buffer(view)
    engine.drawing(
        particles_array,
        VARIABLES["PARTICLE_COUNT"],
        ctypes.byref(obstacles),
        VARIABLES["VISUAL_RADIUS"],
        VARIABLES["MAP_SIZE"],
        buffer_array,
        VARIABLES["VISUAL_COLOUR"],
        pitch,
        VARIABLES["VISUAL_COLOUR_PRESSURE_MULTIPLIER"]
    )
    drawing_time += time.time() - t3
    view.release()
    del buffer_array
    del view
    screen.unlock()
    if VARIABLES["FPS_COUNTER"]:
        draw_text(screen, "FPS: " + str(round(fps_value, 2)), main_font, 20, 20, (0, 255, 0))
    pygame.display.flip()
    total_time += time.time() - t
    iteration+=1
    print(round((time_update + drawing_time) / (0.016 * iteration) , 4) , round(time_update / iteration * 1000 , 2) , round(total_time / iteration * 1000 , 2) , round(drawing_time / iteration * 1000 , 2))
pygame.quit()