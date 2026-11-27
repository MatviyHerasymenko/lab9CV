import argparse
from math import cos, radians, sin
import pygame
from pygame.locals import DOUBLEBUF, OPENGL, QUIT, KEYDOWN
from OpenGL.GL import *
from OpenGL.GLU import *

from car import Car, random_car_spec
from dataset_exporter import DatasetExporter
from scene import CAMERA_PRESETS, SceneEnvironment


WIDTH, HEIGHT = 1024, 680


def init_gl(width: int, height: int) -> None:
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, width / float(height), 0.5, 130.0)
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_NORMALIZE)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glShadeModel(GL_SMOOTH)

    glEnable(GL_FOG)
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogf(GL_FOG_START, 34.0)
    glFogf(GL_FOG_END, 78.0)


def set_camera(yaw: float, pitch: float, dist: float, target: tuple[float, float, float]) -> None:
    glLoadIdentity()
    ry = radians(yaw)
    rp = radians(pitch)
    eye_x = target[0] + dist * cos(rp) * sin(ry)
    eye_y = target[1] + dist * sin(rp)
    eye_z = target[2] + dist * cos(rp) * cos(ry)
    gluLookAt(eye_x, eye_y, eye_z, target[0], target[1], target[2], 0.0, 1.0, 0.0)


def create_cars() -> list[Car]:
    return [
        Car(random_car_spec(lane_z=2.1, direction=1, start_x=-30.0)),
        Car(random_car_spec(lane_z=2.1, direction=1, start_x=-14.0)),
        Car(random_car_spec(lane_z=2.1, direction=1, start_x=4.0)),
        Car(random_car_spec(lane_z=-2.1, direction=-1, start_x=28.0)),
        Car(random_car_spec(lane_z=-2.1, direction=-1, start_x=10.0)),
        Car(random_car_spec(lane_z=-2.1, direction=-1, start_x=-10.0)),
    ]


def run(auto_generate: int = 0) -> None:
    pygame.init()
    try:
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
        pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
    except pygame.error:
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 0)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 0)
        pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)

    pygame.display.set_caption("3D Passenger Cars Traffic")

    init_gl(WIDTH, HEIGHT)
    env = SceneEnvironment()
    cars = create_cars()
    exporter = DatasetExporter()

    preset_idx = 0
    cam = dict(CAMERA_PRESETS[preset_idx])
    paused = False
    auto_record = auto_generate > 0
    saved_count = 0
    tick_counter = 0

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        if auto_generate > 0:
            dt = 0.05

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_l:
                    env.day_mode = not env.day_mode
                elif event.key == pygame.K_g:
                    auto_record = not auto_record
                elif event.key == pygame.K_r:
                    path, n_obj = exporter.capture(WIDTH, HEIGHT, cars)
                    print(f"Saved {path.name} ({n_obj} objects)")
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    preset_idx = event.key - pygame.K_1
                    cam = dict(CAMERA_PRESETS[preset_idx])

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            cam["yaw"] -= 60.0 * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            cam["yaw"] += 60.0 * dt
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            cam["pitch"] = min(80.0, cam["pitch"] + 45.0 * dt)
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            cam["pitch"] = max(5.0, cam["pitch"] - 45.0 * dt)
        if keys[pygame.K_EQUALS] or keys[pygame.K_KP_PLUS]:
            cam["dist"] = max(8.0, cam["dist"] - 10.0 * dt)
        if keys[pygame.K_MINUS] or keys[pygame.K_KP_MINUS]:
            cam["dist"] = min(45.0, cam["dist"] + 10.0 * dt)

        if not paused:
            for car in cars:
                car.update(dt, cars)

        env.apply_lighting()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        set_camera(cam["yaw"], cam["pitch"], cam["dist"], cam["target"])

        env.draw()
        for car in cars:
            car.draw(env.day_mode)

        pygame.display.flip()

        tick_counter += 1
        if auto_record and tick_counter % 10 == 0:
            if auto_generate > 0:
                preset = CAMERA_PRESETS[(saved_count // 3) % len(CAMERA_PRESETS)]
                cam = dict(preset)
                env.day_mode = (saved_count % 6) < 4
                env.apply_lighting()
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                set_camera(cam["yaw"], cam["pitch"], cam["dist"], cam["target"])
                env.draw()
                for car in cars:
                    car.draw(env.day_mode)
                pygame.display.flip()

            path, n_obj = exporter.capture(WIDTH, HEIGHT, cars)
            saved_count += 1
            print(f"[{saved_count}] Saved {path.name} ({n_obj} cars)")
            if auto_generate > 0 and saved_count >= auto_generate:
                running = False

    pygame.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="3D Passenger Cars Traffic Simulation")
    parser.add_argument("--generate", type=int, default=0, help="Auto-generate N dataset frames and exit")
    args = parser.parse_args()
    run(auto_generate=args.generate)
