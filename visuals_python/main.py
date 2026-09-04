import random
import pygame
from utility_functions import *
from modifiable_variables import *
from gui import start_gui_thread


def initialize_vectors():
    VARIABLES["MAP_SIZE"] = Vector2D(VARIABLES["MAP_SIZE"][0], VARIABLES["MAP_SIZE"][1])
    VARIABLES["NEW_MAP_SIZE"] = Vector2D(VARIABLES["NEW_MAP_SIZE"][0], VARIABLES["NEW_MAP_SIZE"][1])
    VARIABLES["GRAVITY"] = Vector2D(VARIABLES["GRAVITY"][0], VARIABLES["GRAVITY"][1])
    VARIABLES["STARTING_POSITION_X"] = Vector2D(VARIABLES["STARTING_POSITION_X"][0],
                                                VARIABLES["STARTING_POSITION_X"][1])
    VARIABLES["STARTING_POSITION_Y"] = Vector2D(VARIABLES["STARTING_POSITION_Y"][0],
                                                VARIABLES["STARTING_POSITION_Y"][1])
    VARIABLES["STARTING_SPEED_X"] = Vector2D(VARIABLES["STARTING_SPEED_X"][0], VARIABLES["STARTING_SPEED_X"][1])
    VARIABLES["STARTING_SPEED_Y"] = Vector2D(VARIABLES["STARTING_SPEED_Y"][0], VARIABLES["STARTING_SPEED_Y"][1])
    VARIABLES["WALL_POINT_1"] = Vector2D(VARIABLES["WALL_POINT_1"][0], VARIABLES["WALL_POINT_1"][1])
    VARIABLES["WALL_POINT_2"] = Vector2D(VARIABLES["WALL_POINT_2"][0], VARIABLES["WALL_POINT_2"][1])


def initialize_walls(saved_user_walls=None):
    if saved_user_walls is None:
        saved_user_walls = []

    walls_array = Wall * VARIABLES["MAX_WALLS"]
    walls_array = walls_array()

    walls_array[0].point1 = Vector2D(0.0, 0.0)
    walls_array[0].point2 = Vector2D(VARIABLES["MAP_SIZE"].x, 0.0)
    walls_array[1].point1 = Vector2D(VARIABLES["MAP_SIZE"].x, 0.0)
    walls_array[1].point2 = Vector2D(VARIABLES["MAP_SIZE"].x, VARIABLES["MAP_SIZE"].y)
    walls_array[2].point1 = Vector2D(VARIABLES["MAP_SIZE"].x, VARIABLES["MAP_SIZE"].y)
    walls_array[2].point2 = Vector2D(0.0, VARIABLES["MAP_SIZE"].y)
    walls_array[3].point1 = Vector2D(0.0, VARIABLES["MAP_SIZE"].y)
    walls_array[3].point2 = Vector2D(0.0, 0.0)

    for i in range(4, 4 + VARIABLES["RANDOM_WALL_COUNT"]):
        walls_array[i].point1 = Vector2D(random.randint(0, int(VARIABLES["MAP_SIZE"].x)),
                                         random.randint(0, int(VARIABLES["MAP_SIZE"].y)))
        walls_array[i].point2 = Vector2D(walls_array[i].point1.x + random.randint(-VARIABLES["RANDOM_WALL_MAX_LEN"],
                                                                                  VARIABLES["RANDOM_WALL_MAX_LEN"]),
                                         walls_array[i].point1.y + random.randint(-VARIABLES["RANDOM_WALL_MAX_LEN"],
                                                                                  VARIABLES["RANDOM_WALL_MAX_LEN"]))

    user_start_index = 4 + VARIABLES["RANDOM_WALL_COUNT"]
    for i, (p1, p2) in enumerate(saved_user_walls):
        walls_array[user_start_index + i].point1 = p1
        walls_array[user_start_index + i].point2 = p2

    total_walls = 4 + VARIABLES["RANDOM_WALL_COUNT"] + len(saved_user_walls)

    for i in range(total_walls):
        walls_array[i].normal = calculate_normal(walls_array[i])

    obstacles = Obstacles()
    obstacles.count = total_walls
    obstacles.walls = ctypes.cast(walls_array, ctypes.POINTER(Wall))

    return walls_array, obstacles


def initialize_areas():
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

    return areas_array


def initialize_particles(particle_count):
    particles_array = Particle * VARIABLES["MAX_PARTICLES"]
    particles_array = particles_array()

    pos_x_min = int(min(VARIABLES["STARTING_POSITION_X"].x, VARIABLES["STARTING_POSITION_X"].y))
    pos_x_max = int(max(VARIABLES["STARTING_POSITION_X"].x, VARIABLES["STARTING_POSITION_X"].y))
    pos_y_min = int(min(VARIABLES["STARTING_POSITION_Y"].x, VARIABLES["STARTING_POSITION_Y"].y))
    pos_y_max = int(max(VARIABLES["STARTING_POSITION_Y"].x, VARIABLES["STARTING_POSITION_Y"].y))
    spd_x_min = int(min(VARIABLES["STARTING_SPEED_X"].x, VARIABLES["STARTING_SPEED_X"].y))
    spd_x_max = int(max(VARIABLES["STARTING_SPEED_X"].x, VARIABLES["STARTING_SPEED_X"].y))
    spd_y_min = int(min(VARIABLES["STARTING_SPEED_Y"].x, VARIABLES["STARTING_SPEED_Y"].y))
    spd_y_max = int(max(VARIABLES["STARTING_SPEED_Y"].x, VARIABLES["STARTING_SPEED_Y"].y))

    for i in range(particle_count):
        start_x = random.randint(pos_x_min, pos_x_max)
        start_y = random.randint(pos_y_min, pos_y_max)
        particles_array[i].position = Vector2D(start_x, start_y)

        vel_x = random.randint(spd_x_min, spd_x_max)
        vel_y = random.randint(spd_y_min, spd_y_max)
        particles_array[i].velocity = Vector2D(vel_x, vel_y)

    return particles_array


def add_user_wall(walls_array, obstacles):
    if VARIABLES["WALL_COUNT"] + VARIABLES["RANDOM_WALL_COUNT"] < VARIABLES["MAX_WALLS"]:
        new_wall_index = VARIABLES["WALL_COUNT"] + VARIABLES["RANDOM_WALL_COUNT"]
        walls_array[new_wall_index].point1 = Vector2D(VARIABLES["WALL_POINT_1"].x, VARIABLES["WALL_POINT_1"].y)
        walls_array[new_wall_index].point2 = Vector2D(VARIABLES["WALL_POINT_2"].x, VARIABLES["WALL_POINT_2"].y)
        walls_array[new_wall_index].normal = calculate_normal(walls_array[new_wall_index])
        VARIABLES["WALL_COUNT"] += 1
        obstacles.count = VARIABLES["WALL_COUNT"] + VARIABLES["RANDOM_WALL_COUNT"]


def remove_user_wall(obstacles):
    if VARIABLES["WALL_COUNT"] > 4:
        VARIABLES["WALL_COUNT"] -= 1
        obstacles.count = VARIABLES["WALL_COUNT"] + VARIABLES["RANDOM_WALL_COUNT"]


def extract_saved_walls(walls_array, obstacles):
    user_wall_count = VARIABLES["WALL_COUNT"] - 4
    saved_user_walls = []

    for i in range(obstacles.count - user_wall_count, obstacles.count):
        p1 = Vector2D(walls_array[i].point1.x, walls_array[i].point1.y)
        p2 = Vector2D(walls_array[i].point2.x, walls_array[i].point2.y)
        saved_user_walls.append((p1, p2))

    return saved_user_walls


def handle_restart(walls_array, obstacles):
    VARIABLES["MAP_SIZE"].x = VARIABLES["NEW_MAP_SIZE"].x
    VARIABLES["MAP_SIZE"].y = VARIABLES["NEW_MAP_SIZE"].y

    areas_array = initialize_areas()
    screen = pygame.display.set_mode((int(VARIABLES["MAP_SIZE"].x), int(VARIABLES["MAP_SIZE"].y)), pygame.RESIZABLE)

    VARIABLES["PARTICLE_COUNT"] = int(VARIABLES["STARTING_PARTICLE_COUNT"])
    particles_array = initialize_particles(VARIABLES["PARTICLE_COUNT"])

    saved_user_walls = extract_saved_walls(walls_array, obstacles)
    walls_array, obstacles = initialize_walls(saved_user_walls)

    VARIABLES["RESTART_CLICKED"] = False

    return screen, areas_array, particles_array, walls_array, obstacles


def update_physics(particles_array, obstacles, areas_array, dt):
    if dt > 0.016:
        dt = 0.016

    friction_split_timing = VARIABLES["FRICTION_MULTIPLIER"] ** (1.0 / VARIABLES["SUB_STEPS"])
    wall_push_split_timing = VARIABLES["WALL_DEFAULT_PUSH"] / VARIABLES["SUB_STEPS"]

    engine.update(
        ctypes.cast(particles_array, ctypes.POINTER(Particle)),
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


def draw_screen(screen, particles_array, obstacles, fps_value, main_font):
    screen.fill((0, 0, 0))
    screen.lock()

    pitch = screen.get_pitch()
    view = memoryview(screen.get_view('1'))
    buffer_array = (ctypes.c_uint32 * (len(view) // 4)).from_buffer(view)

    engine.drawing(
        ctypes.cast(particles_array, ctypes.POINTER(Particle)),
        VARIABLES["PARTICLE_COUNT"],
        ctypes.byref(obstacles),
        VARIABLES["VISUAL_RADIUS"],
        VARIABLES["MAP_SIZE"],
        buffer_array,
        VARIABLES["VISUAL_COLOUR"],
        pitch,
        VARIABLES["VISUAL_COLOUR_PRESSURE_MULTIPLIER"]
    )

    view.release()
    del buffer_array
    del view

    screen.unlock()

    if VARIABLES["FPS_COUNTER"]:
        draw_text(screen, "FPS: " + str(round(fps_value, 2)), main_font, 20, 20, (0, 255, 0))

    pygame.display.flip()


def main():
    pygame.init()
    pygame.font.init()

    main_font = pygame.font.SysFont(None, 30)
    clock = pygame.time.Clock()

    initialize_vectors()
    walls_array, obstacles = initialize_walls()
    areas_array = initialize_areas()
    particles_array = initialize_particles(VARIABLES["MAX_PARTICLES"])

    screen = pygame.display.set_mode((int(VARIABLES["MAP_SIZE"].x), int(VARIABLES["MAP_SIZE"].y)), pygame.RESIZABLE)
    start_gui_thread(VARIABLES)

    running = True

    while running:
        if VARIABLES["RESTART_CLICKED"]:
            screen, areas_array, particles_array, walls_array, obstacles = handle_restart(walls_array, obstacles)

        if VARIABLES["ADD_WALL_CLICKED"]:
            add_user_wall(walls_array, obstacles)
            VARIABLES["ADD_WALL_CLICKED"] = False

        if VARIABLES["REMOVE_WALL_CLICKED"]:
            remove_user_wall(obstacles)
            VARIABLES["REMOVE_WALL_CLICKED"] = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                VARIABLES["NEW_MAP_SIZE"].x = event.w
                VARIABLES["NEW_MAP_SIZE"].y = event.h
                VARIABLES["MAP_SIZE"].x = event.w
                VARIABLES["MAP_SIZE"].y = event.h
                VARIABLES["RESTART_CLICKED"] = True

        dt = clock.tick_busy_loop(60) / 1000.0
        fps_value = clock.get_fps()

        update_physics(particles_array, obstacles, areas_array, dt)
        draw_screen(screen, particles_array, obstacles, fps_value, main_font)

    pygame.quit()


if __name__ == "__main__":
    main()