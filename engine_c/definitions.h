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
} particle_t;

typedef struct {
    vector2D_t point1;
    vector2D_t point2;
} wall_t;

typedef struct {
    wall_t *walls;
    int count;
} obstacles_t;


EXPORT void update_positions(particle_t *particles, int count, float delta_time, vector2D_t gravity_force,
                             obstacles_t walls, int collision_limit, float max_influence_radius, float target_density,
                             float pressure_multiplier , float collision_dampening);

void update_velocities_gravity(particle_t *particles, int count, float delta_time, vector2D_t gravity_force);

float calculate_movement_and_wall_collision(particle_t *particle, obstacles_t walls, float delta_time, float collision_dampening);

void calculate_bounce(particle_t *particle, wall_t wall, float delta_time, float collision_dampening);

float calculate_influence(particle_t particle_a, particle_t particle_b, float max_influence_radius);

void calculate_densities(particle_t *particles, int count, float max_influence_radius);

void calculate_pressure_forces(particle_t *particles, int count, float target_density, float pressure_multiplier,
                               float max_influence_radius, float delta_time);

float calculate_distance_squared(particle_t particle_a, particle_t particle_b);

#endif //ENGINE_C_DEFINITIONS_H
