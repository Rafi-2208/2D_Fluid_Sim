#include "definitions.h"
#include <math.h>
#include <stdio.h>


EXPORT void update(particle_t *particles, const int count, const float delta_time, const vector2D_t gravity_force,
                   const obstacles_t walls, const int collision_limit, const float max_influence_radius,
                   const float target_density, const float pressure_multiplier, const float collision_dampening,
                   const float viscosity, const vector2D_t map_size, area_t *areas, const float friction_multiplier) {
    area_segregation(particles, count, areas, max_influence_radius, map_size);
    calculate_densities(particles, count, max_influence_radius, areas, map_size);
    calculate_pressure_and_viscosity_forces(particles, count, target_density, pressure_multiplier, max_influence_radius,
                                            delta_time,
                                            areas, map_size, viscosity);
    update_velocities_gravity(particles, count, delta_time, gravity_force, friction_multiplier);
    change_positions(particles, count, delta_time, &walls, collision_dampening, collision_limit, max_influence_radius,
                     map_size);
}

void change_positions(particle_t *particles, const int count, const float delta_time, const obstacles_t * walls,
                      const float collision_dampening, const int collision_limit, const float influence_radius,
                      const vector2D_t map_size) {
#pragma omp parallel for
    for (int i = 0; i < count; i++) {
        float time_left = delta_time;
        int counter = 0;
        while (time_left > 0) {
            counter++;
            time_left = calculate_movement_and_wall_collision(particles + i, walls, time_left, collision_dampening,
                                                              influence_radius, map_size);
            if (counter >= collision_limit) {
                break;
            }
        }
    }
}


void update_velocities_gravity(particle_t *particles, const int count, const float delta_time,
                               const vector2D_t gravity_force, const float friction_multiplier) {
    float gravity_per_time_x = gravity_force.x * delta_time;\
    float gravity_per_time_y = gravity_force.y * delta_time;
#pragma omp parallel for
    for (int i = 0; i < count; i++) {
        particles[i].velocity.x = gravity_per_time_x + particles[i].velocity.x * friction_multiplier;
        particles[i].velocity.y = gravity_per_time_y + particles[i].velocity.y * friction_multiplier;
    }
}

//A + t(B - A) = C + u(D - C)
//returns remaining time in a frame
float calculate_movement_and_wall_collision(particle_t *particle, const obstacles_t * walls, const float delta_time,
                                            const float collision_dampening, const float influence_radius,
                                            const vector2D_t map_size) {
    const vector2D_t position_before = particle->position;
    vector2D_t position_after = particle->position;
    position_after.x = position_before.x + particle->velocity.x * delta_time;
    position_after.y = position_before.y + particle->velocity.y * delta_time;
    float result = 2;
    int hit_wall_index = -1;
    for (int i = 0; i < walls->count; i++) {
        const wall_t current_wall = walls->walls[i];
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
        calculate_bounce(particle, walls->walls[hit_wall_index], result * delta_time, collision_dampening);
        return delta_time * (1 - result);
    }
    particle->position = position_after;
    particle->area = get_area_code(particle->position, influence_radius, map_size);
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
        particle->velocity.x = particle->velocity.x - (1.0f + collision_dampening) * dot_product_wall_velocity * normal.
                               x;
        particle->velocity.y = particle->velocity.y - (1.0f + collision_dampening) * dot_product_wall_velocity * normal.
                               y;
        particle->position.x = particle->position.x + normal.x * 0.05f;
        particle->position.y = particle->position.y + normal.y * 0.05f;
    }
}


float calculate_distance_squared(const particle_t * particle_a, const particle_t * particle_b) {
    const float distance_x = particle_a->position.x - particle_b->position.x;
    const float distance_y = particle_a->position.y - particle_b->position.y;
    return distance_x * distance_x + distance_y * distance_y;
}

float calculate_influence(const particle_t * particle_a, const particle_t * particle_b, const float max_influence_radius, const float max_influence_radius_squared) {
    const float distance_squared = calculate_distance_squared(particle_a, particle_b );
    if (distance_squared < max_influence_radius_squared) {
        const float distance = sqrtf(distance_squared);
        return (max_influence_radius - distance) * (max_influence_radius - distance) * (
                   max_influence_radius - distance);
    }
    return 0;
}


void calculate_densities(particle_t *particles, const int count, const float max_influence_radius,
                         const area_t *areas, const vector2D_t map_size) {
    const float max_influence_radius_squared = max_influence_radius * max_influence_radius;
    const int x_limit = (int) (map_size.x / max_influence_radius);
    const int y_limit = (int) (map_size.y / max_influence_radius);
#pragma omp parallel for
    for (int i = 0; i < count; i++) {
        particles[i].density = 0;
        const int cell_x = (int) (particles[i].position.x / max_influence_radius);
        const int cell_y = (int) (particles[i].position.y / max_influence_radius);
        for (int dy = -1; dy <= 1; dy++) {
            for (int dx = -1; dx <= 1; dx++) {
                const int neighbor_x = cell_x + dx;
                const int neighbor_y = cell_y + dy;
                if (neighbor_x >= 0 && neighbor_x < x_limit &&
                    neighbor_y >= 0 && neighbor_y < y_limit) {
                    const int cell_index = neighbor_y * x_limit + neighbor_x;
                    const area_t current_area = areas[cell_index];
                    for (int j = 0; j < current_area.count; j++) {
                        const particle_t *neighbor = current_area.particles[j];
                        particles[i].density += calculate_influence(particles+i, neighbor, max_influence_radius , max_influence_radius_squared);
                    }
                }
            }
        }
    }
}


void calculate_pressure_and_viscosity_forces(particle_t *particles, const int count, const float target_density,
                                             const float pressure_multiplier, const float max_influence_radius,
                                             const float delta_time, const area_t *areas, const vector2D_t map_size,
                                             const float viscosity) {
    const float max_influence_radius_squared = max_influence_radius * max_influence_radius;
    const int x_limit = (int) (map_size.x / max_influence_radius);
    const int y_limit = (int) (map_size.y / max_influence_radius);
#pragma omp parallel for
    for (int i = 0; i < count; i++) {
        const float pressure = (particles[i].density - target_density) * pressure_multiplier;
        const int cell_x = (int) (particles[i].position.x / max_influence_radius);
        const int cell_y = (int) (particles[i].position.y / max_influence_radius);
        float velocity_change_x = 0.0f;
        float velocity_change_y = 0.0f;
        for (int dy = -1; dy <= 1; dy++) {
            for (int dx = -1; dx <= 1; dx++) {
                const int neighbor_x = cell_x + dx;
                const int neighbor_y = cell_y + dy;
                if (neighbor_x >= 0 && neighbor_x < x_limit &&
                    neighbor_y >= 0 && neighbor_y < y_limit) {
                    const int cell_index = neighbor_y * x_limit + neighbor_x;
                    const area_t current_area = areas[cell_index];
                    for (int j = 0; j < current_area.count; j++) {
                        const particle_t *neighbor = current_area.particles[j];
                        if (&particles[i] != neighbor) {
                            const float distance_squared = calculate_distance_squared(particles + i, neighbor);
                            if (distance_squared < max_influence_radius_squared) {
                                const float distance = sqrtf(distance_squared);
                                if (0.001f < distance_squared) {
                                    const float pressure2 = (neighbor->density - target_density) * pressure_multiplier;
                                    const float average_pressure = (pressure + pressure2) / 2;
                                    if (average_pressure > 0) {
                                        const float pressure_gradient =
                                                (max_influence_radius - distance) * (max_influence_radius - distance);
                                        const vector2D_t pressure_force_vector = {
                                            .x = (particles[i].position.x - neighbor->position.x) / distance *
                                                 pressure_gradient * average_pressure,
                                            .y = (particles[i].position.y - neighbor->position.y) / distance *
                                                 pressure_gradient * average_pressure,
                                        };
                                        velocity_change_x += +pressure_force_vector.x * delta_time;
                                        velocity_change_y += +pressure_force_vector.y * delta_time;
                                    }
                                }
                                const float viscosity_relative =
                                        (1 - distance / max_influence_radius) * viscosity * delta_time;
                                velocity_change_x += (neighbor->velocity.x - particles[i].velocity.x) *
                                        viscosity_relative;
                                velocity_change_y += (neighbor->velocity.y - particles[i].velocity.y) *
                                        viscosity_relative;
                            }
                        }
                    }
                }
            }
        }
        particles[i].velocity.x += velocity_change_x;
        particles[i].velocity.y += velocity_change_y;
    }
}


int get_area_code(const vector2D_t point, const float influence_radius, const vector2D_t size) {
    int x = (int) (point.x / influence_radius);
    int y = (int) (point.y / influence_radius);

    const int x_limit = (int) (size.x / influence_radius);
    const int y_limit = (int) (size.y / influence_radius);
    if (x < 0) {
        x = 0;
    }
    if (x >= x_limit) {
        x = x_limit - 1;
    }
    if (y < 0) {
        y = 0;
    }
    if (y >= y_limit) {
        y = y_limit - 1;
    }
    return y * x_limit + x;
}

void area_segregation(particle_t *particles, const int count, area_t *areas, const float max_influence_radius,
                      const vector2D_t size) {
    const int x_limit = (int) (size.x / max_influence_radius);
    const int y_limit = (int) (size.y / max_influence_radius);
    const int area_count = x_limit * y_limit;
    for (int i = 0; i < area_count; i++) {
        areas[i].count = 0;
    }
    for (int i = 0; i < count; i++) {
        const int area_code = get_area_code(particles[i].position, max_influence_radius, size);
        if (area_code >= 0 && area_code < area_count) {
            areas[area_code].particles[areas[area_code].count] = particles + i;
            areas[area_code].count++;
        }
    }
}
