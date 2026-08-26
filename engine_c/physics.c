#include "definitions.h"
#include <math.h>

EXPORT void update_positions(particle *particles, const int count, const float delta_time, const vector2D gravity_force, const obstacles walls , const int collision_limit) {
    update_velocities_gravity(particles, count, delta_time , gravity_force);
    for (int i = 0; i < count; i++) {
        float time_left = delta_time;
        int counter = 0;
        while (time_left > 0) {
            counter++;
            time_left = calculate_movement_and_wall_collision(particles+i, walls, time_left);
            if (counter >= collision_limit) {
                break;
            }
        }
    }
}




void update_velocities_gravity(particle *particles, const int count, const float delta_time, const vector2D gravity_force) {
    for (int i = 0; i < count; i++) {
        particles[i].velocity.x = gravity_force.x * delta_time + particles[i].velocity.x;
        particles[i].velocity.y = gravity_force.y * delta_time + particles[i].velocity.y;
    }
}

//A + t(B - A) = C + u(D - C)
//returns remaining time in a frame
float calculate_movement_and_wall_collision(particle *particle, const obstacles walls, const float delta_time) {
    const vector2D position_before = particle->position;
    vector2D position_after = particle->position;
    position_after.x = position_before.x + particle->velocity.x * delta_time;
    position_after.y = position_before.y + particle->velocity.y * delta_time;
    float result = 2;
    int hit_wall_index = -1;
    for (int i = 0; i < walls.count; i++) {
        const wall current_wall = walls.walls[i];
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
            if (u >= 0 && u <= 1 && t > 0 && t <= 1) {
                if (result > t) {
                    result = t;
                    hit_wall_index = i;
                }
            }
        }
    }
    if (result != 2) {
        calculate_bounce(particle, walls.walls[hit_wall_index], result * delta_time);
        return delta_time * (1 - result);
    }
    particle->position = position_after;
    return 0;
}


void calculate_bounce(particle *particle, const wall wall, const float delta_time) {
    particle->position.x = particle->position.x + particle->velocity.x * delta_time;
    particle->position.y = particle->position.y + particle->velocity.y * delta_time;
    vector2D normal = {.x = -(wall.point2.y - wall.point1.y), .y = wall.point2.x - wall.point1.x};
    const float normal_length = sqrtf(normal.x * normal.x + normal.y * normal.y);
    if (normal_length > 0) {
        normal.x = normal.x / normal_length;
        normal.y = normal.y / normal_length;
        const float dot_product_wall_velocity = particle->velocity.x * normal.x + particle->velocity.y * normal.y;
        particle->velocity.x = particle->velocity.x - 2 * dot_product_wall_velocity * normal.x;
        particle->velocity.y = particle->velocity.y - 2 * dot_product_wall_velocity * normal.y;
        particle->position.x = particle->position.x + normal.x * 0.0001;
        particle->position.y = particle->position.y + normal.y * 0.0001;
    }
}
