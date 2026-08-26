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
} vector2D;

typedef struct {
    vector2D position;
    vector2D velocity;
} particle;

typedef struct {
    vector2D point1;
    vector2D point2;
} wall;

typedef struct {
    wall *walls;
    int count;
} obstacles;


EXPORT void update_positions(particle *particles, int count, float delta_time, vector2D gravity_force , obstacles walls , int collision_limit);

void update_velocities_gravity(particle *particles, int count, float delta_time, vector2D gravity_force);

float calculate_movement_and_wall_collision(particle* particle, obstacles walls, float delta_time);

void calculate_bounce(particle* particle, wall wall , float delta_time);

#endif //ENGINE_C_DEFINITIONS_H
