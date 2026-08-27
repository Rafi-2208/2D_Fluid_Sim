#include "definitions.h"
#include <math.h>

EXPORT void update(particle_t *particles, const int count, const float delta_time, const vector2D_t gravity_force,
                   const obstacles_t walls, const int collision_limit, const float max_influence_radius,
                   const float target_density, const float pressure_multiplier, const float collision_dampening,
                   const float viscosity) {
    calculate_densities(particles, count, max_influence_radius, walls);
    calculate_pressure_forces(particles, count, target_density, pressure_multiplier, max_influence_radius, delta_time);
    calculate_viscosity_forces(particles, count, max_influence_radius, viscosity, delta_time);
    update_velocities_gravity(particles, count, delta_time, gravity_force);
    change_positions(particles, count, delta_time, walls, collision_dampening, collision_limit);
}

void change_positions(particle_t *particles, const int count, const float delta_time, const obstacles_t walls,
                      const float collision_dampening, const int collision_limit) {
    for (int i = 0; i < count; i++) {
        float time_left = delta_time;
        int counter = 0;
        while (time_left > 0) {
            counter++;
            time_left = calculate_movement_and_wall_collision(particles + i, walls, time_left, collision_dampening);
            if (counter >= collision_limit) {
                break;
            }
        }
    }
}


void update_velocities_gravity(particle_t *particles, const int count, const float delta_time,
                               const vector2D_t gravity_force) {
    for (int i = 0; i < count; i++) {
        particles[i].velocity.x = gravity_force.x * delta_time + particles[i].velocity.x;
        particles[i].velocity.y = gravity_force.y * delta_time + particles[i].velocity.y;
    }
}

//A + t(B - A) = C + u(D - C)
//returns remaining time in a frame
float calculate_movement_and_wall_collision(particle_t *particle, const obstacles_t walls, const float delta_time,
                                            const float collision_dampening) {
    const vector2D_t position_before = particle->position;
    vector2D_t position_after = particle->position;
    position_after.x = position_before.x + particle->velocity.x * delta_time;
    position_after.y = position_before.y + particle->velocity.y * delta_time;
    float result = 2;
    int hit_wall_index = -1;
    for (int i = 0; i < walls.count; i++) {
        const wall_t current_wall = walls.walls[i];
        const float dX1 = position_after.x - position_before.x;
        const float dY1 = position_after.y - position_before.y;
        const float dX2 = current_wall.point1.x - current_wall.point2.x;
        const float dY2 = current_wall.point1.y - current_wall.point2.y;
        const float dX3 = current_wall.point1.x - position_before.x;
        const float dY3 = current_wall.point1.y - position_before.y;
        const float W = dX1 * dY2 - dY1 * dX2;
        const float Wt = dX3 * dY2 - dY3 * dX2;
        const float Wu = dX1 * dY3 - dY1 * dX3;
        if (W != 0) {
            const float t = Wt / W;
            const float u = Wu / W;
            if (u >= -0.01f && u <= 1.01f && t > 0 && t <= 1) {
                if (result > t) {
                    result = t;
                    hit_wall_index = i;
                }
            }
        }
    }
    if (result != 2) {
        calculate_bounce(particle, walls.walls[hit_wall_index], result * delta_time, collision_dampening);
        return delta_time * (1 - result);
    }
    particle->position = position_after;
    return 0;
}


void calculate_bounce(particle_t *particle, const wall_t wall, const float delta_time,
                      const float collision_dampening) {
    particle->position.x = particle->position.x + particle->velocity.x * delta_time;
    particle->position.y = particle->position.y + particle->velocity.y * delta_time;
    vector2D_t normal = {.x = -(wall.point2.y - wall.point1.y), .y = wall.point2.x - wall.point1.x};
    const float normal_length = sqrtf(normal.x * normal.x + normal.y * normal.y);
    if (normal_length > 0) {
        normal.x = normal.x / normal_length;
        normal.y = normal.y / normal_length;
        float dot_product_wall_velocity = particle->velocity.x * normal.x + particle->velocity.y * normal.y;
        if (dot_product_wall_velocity > 0) {
            normal.x = -normal.x;
            normal.y = -normal.y;
            dot_product_wall_velocity = -dot_product_wall_velocity;
        }
        particle->velocity.x = particle->velocity.x -  (1.0f + collision_dampening) * dot_product_wall_velocity * normal.x;
        particle->velocity.y = particle->velocity.y -  (1.0f + collision_dampening) * dot_product_wall_velocity * normal.y;
        particle->position.x = particle->position.x + normal.x * 0.05f;
        particle->position.y = particle->position.y + normal.y * 0.05f;
    }
}


float calculate_distance_squared(const particle_t particle_a, const particle_t particle_b) {
    const float distance_x = particle_a.position.x - particle_b.position.x;
    const float distance_y = particle_a.position.y - particle_b.position.y;
    return distance_x * distance_x + distance_y * distance_y;
}

float calculate_influence(const particle_t particle_a, const particle_t particle_b, const float max_influence_radius) {
    const float distance_squared = calculate_distance_squared(particle_a, particle_b);
    if (distance_squared < max_influence_radius * max_influence_radius) {
        const float distance = sqrtf(distance_squared);
        return (max_influence_radius - distance) * (max_influence_radius - distance) * (
                   max_influence_radius - distance);
    }
    return 0;
}

void calculate_densities(particle_t *particles, const int count, const float max_influence_radius,
                         const obstacles_t obstacles) {
    for (int i = 0; i < count; i++) {
        particles[i].density = 0;
        for (int j = 0; j < count; j++) {
            particles[i].density += calculate_influence(particles[i], particles[j], max_influence_radius);
        }
    }
}

void calculate_pressure_forces(particle_t *particles, const int count, const float target_density,
                               const float pressure_multiplier, const float max_influence_radius,
                               const float delta_time) {
    for (int i = 0; i < count; i++) {
        const float pressure = (particles[i].density - target_density) * pressure_multiplier;
        for (int j = 0; j < count; j++) {
            if (i != j) {
                const float distance_squared = calculate_distance_squared(particles[i], particles[j]);
                if (0.001f < distance_squared && distance_squared < max_influence_radius * max_influence_radius) {
                    const float pressure2 = (particles[j].density - target_density) * pressure_multiplier;
                    const float average_pressure = (pressure + pressure2) / 2;
                    if (average_pressure > 0) {
                        const float distance = sqrtf(distance_squared);
                        const float pressure_gradient =
                                (max_influence_radius - distance) * (max_influence_radius - distance);
                        const vector2D_t pressure_force_vector = {
                            .x = (particles[i].position.x - particles[j].position.x) / distance * pressure_gradient *
                                 average_pressure,
                            .y = (particles[i].position.y - particles[j].position.y) / distance * pressure_gradient *
                                 average_pressure,
                        };
                        particles[i].velocity.x = particles[i].velocity.x + pressure_force_vector.x * delta_time;
                        particles[i].velocity.y = particles[i].velocity.y + pressure_force_vector.y * delta_time;
                    }
                }
            }
        }
    }
}

void calculate_viscosity_forces(particle_t *particles, const int count, const float max_influence_radius,
                                const float viscosity, const float delta_time) {
    for (int i = 0; i < count; i++) {
        for (int j = 0; j < count; j++) {
            if (i != j) {
                const float distance_squared = calculate_distance_squared(particles[i], particles[j]);
                if (distance_squared < max_influence_radius * max_influence_radius) {
                    particles[i].velocity.x = particles[i].velocity.x + (
                                                  particles[j].velocity.x - particles[i].velocity.x) * (
                                                  1 - sqrtf(distance_squared) / max_influence_radius) * viscosity *
                                              delta_time;
                    particles[i].velocity.y = particles[i].velocity.y + (
                                                  particles[j].velocity.y - particles[i].velocity.y) * (
                                                  1 - sqrtf(distance_squared) / max_influence_radius) * viscosity *
                                              delta_time;
                }
            }
        }
    }
}