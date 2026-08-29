//
// Created by rafal on 26.08.2026.
//
#ifndef ENGINE_C_DEFINITIONS_H
#define ENGINE_C_DEFINITIONS_H

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

typedef struct {
    float x, y;
} vector2D_t;

typedef struct {
    vector2D_t position;
    vector2D_t velocity;
    float density;
    int area;
} particle_t;

typedef struct {
    vector2D_t point1;
    vector2D_t point2;
} wall_t;

typedef struct {
    wall_t *walls;
    int count;
} obstacles_t;

typedef struct {
    int area;
    int count;
    particle_t **particles;
} area_t;


EXPORT void update(particle_t *particles, int count, float delta_time, vector2D_t gravity_force,
                   obstacles_t walls, int collision_limit, float max_influence_radius, float target_density,
                   float pressure_multiplier, float collision_dampening, float viscosity, vector2D_t map_size,
                   area_t *areas , float friction_multiplier);

void change_positions(particle_t *particles, int count, float delta_time, obstacles_t walls, float collision_dampening,
                      int collision_limit, float influence_radius, vector2D_t map_size);

void update_velocities_gravity(particle_t *particles, int count, float delta_time, vector2D_t gravity_force , float friction_multiplier);

float calculate_movement_and_wall_collision(particle_t *particle, obstacles_t walls, float delta_time,
                                            float collision_dampening, float influence_radius, vector2D_t map_size);

void calculate_bounce(particle_t *particle, wall_t wall, float delta_time, float collision_dampening);

float calculate_influence(particle_t particle_a, particle_t particle_b, float max_influence_radius);

void calculate_densities(particle_t *particles, int count, float max_influence_radius,
                         const area_t *areas, vector2D_t map_size);

void calculate_pressure_and_viscosity_forces(particle_t *particles, int count, float target_density,
                               float pressure_multiplier, float max_influence_radius,
                               float delta_time, const area_t *areas, vector2D_t map_size, float viscosity);

float calculate_distance_squared(particle_t particle_a, particle_t particle_b);

int get_area_code(vector2D_t point, float influence_radius, vector2D_t size);

void area_segregation(particle_t *particles, int count, area_t *areas, float max_influence_radius, vector2D_t size);


#endif //ENGINE_C_DEFINITIONS_H
