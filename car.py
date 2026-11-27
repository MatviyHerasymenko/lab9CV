from dataclasses import dataclass
from math import atan2, cos, pi, sin
from random import choice, uniform
from OpenGL.GL import *
from OpenGL.GLU import *


CAR_COLORS = [
    (0.78, 0.11, 0.12, 1.0),
    (0.10, 0.32, 0.72, 1.0),
    (0.84, 0.85, 0.87, 1.0),
    (0.14, 0.15, 0.17, 1.0),
    (0.12, 0.46, 0.25, 1.0),
    (0.85, 0.62, 0.10, 1.0),
    (0.45, 0.48, 0.52, 1.0),
    (0.55, 0.12, 0.24, 1.0),
]

BODY_TYPES = ("sedan", "hatchback", "suv")


@dataclass
class CarSpec:
    body_type: str
    length: float
    width: float
    height: float
    wheel_radius: float
    wheel_width: float
    body_color: tuple[float, float, float, float]
    target_speed: float
    current_speed: float
    lane_z: float
    direction: int
    x: float


def random_car_spec(lane_z: float, direction: int, start_x: float) -> CarSpec:
    body_type = choice(BODY_TYPES)
    if body_type == "sedan":
        length = uniform(4.3, 4.7)
        width = uniform(1.78, 1.88)
        height = uniform(1.38, 1.48)
        wheel_radius = 0.34
    elif body_type == "hatchback":
        length = uniform(3.8, 4.15)
        width = uniform(1.74, 1.84)
        height = uniform(1.42, 1.52)
        wheel_radius = 0.33
    else:
        length = uniform(4.4, 4.85)
        width = uniform(1.88, 1.98)
        height = uniform(1.62, 1.76)
        wheel_radius = 0.39

    speed = uniform(7.5, 13.5)
    return CarSpec(
        body_type=body_type,
        length=length,
        width=width,
        height=height,
        wheel_radius=wheel_radius,
        wheel_width=0.23,
        body_color=choice(CAR_COLORS),
        target_speed=speed,
        current_speed=speed,
        lane_z=lane_z,
        direction=direction,
        x=start_x,
    )


def _extrude_profile(profile: list[tuple[float, float]], z0: float, z1: float) -> None:
    n = len(profile)
    # Ліва та права бічні грані
    for z, nz in ((z1, 1.0), (z0, -1.0)):
        glBegin(GL_POLYGON)
        glNormal3f(0.0, 0.0, nz)
        pts = profile if nz > 0 else list(reversed(profile))
        for x, y in pts:
            glVertex3f(x, y, z)
        glEnd()

    # Периметр
    glBegin(GL_QUADS)
    for i in range(n):
        x_a, y_a = profile[i]
        x_b, y_b = profile[(i + 1) % n]
        dx = x_b - x_a
        dy = y_b - y_a
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1e-6:
            continue
        nx, ny = dy / length, -dx / length
        glNormal3f(nx, ny, 0.0)
        glVertex3f(x_a, y_a, z1)
        glVertex3f(x_b, y_b, z1)
        glVertex3f(x_b, y_b, z0)
        glVertex3f(x_a, y_a, z0)
    glEnd()


def _draw_box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> None:
    glBegin(GL_QUADS)
    glNormal3f(0, 0, 1)
    glVertex3f(x0, y0, z1); glVertex3f(x1, y0, z1); glVertex3f(x1, y1, z1); glVertex3f(x0, y1, z1)
    glNormal3f(0, 0, -1)
    glVertex3f(x1, y0, z0); glVertex3f(x0, y0, z0); glVertex3f(x0, y1, z0); glVertex3f(x1, y1, z0)
    glNormal3f(0, 1, 0)
    glVertex3f(x0, y1, z1); glVertex3f(x1, y1, z1); glVertex3f(x1, y1, z0); glVertex3f(x0, y1, z0)
    glNormal3f(0, -1, 0)
    glVertex3f(x0, y0, z0); glVertex3f(x1, y0, z0); glVertex3f(x1, y0, z1); glVertex3f(x0, y0, z1)
    glNormal3f(1, 0, 0)
    glVertex3f(x1, y0, z1); glVertex3f(x1, y0, z0); glVertex3f(x1, y1, z0); glVertex3f(x1, y1, z1)
    glNormal3f(-1, 0, 0)
    glVertex3f(x0, y0, z0); glVertex3f(x0, y0, z1); glVertex3f(x0, y1, z1); glVertex3f(x0, y1, z0)
    glEnd()


class Car:
    def __init__(self, spec: CarSpec, road_half_length: float = 42.0):
        self.spec = spec
        self.road_half_length = road_half_length
        self.wheel_angle = 0.0
        self._quadric = gluNewQuadric()

    def update(self, dt: float, all_cars: list["Car"]) -> None:
        # Пошук найближчого авто попереду на тій самій смузі
        min_gap = float("inf")
        lead_speed = self.spec.target_speed

        for other in all_cars:
            if other is self or abs(other.spec.lane_z - self.spec.lane_z) > 0.5:
                continue
            dist_center = (other.spec.x - self.spec.x) * self.spec.direction
            if dist_center > 0:
                gap = dist_center - 0.5 * (self.spec.length + other.spec.length)
                if gap < min_gap:
                    min_gap = gap
                    lead_speed = other.spec.current_speed

        safe_gap = 3.2 + self.spec.current_speed * 0.25
        if min_gap < safe_gap:
            desired = max(0.0, lead_speed - max(0.0, (safe_gap - min_gap) * 2.5))
            self.spec.current_speed += (desired - self.spec.current_speed) * min(1.0, dt * 6.0)
        else:
            self.spec.current_speed += (self.spec.target_speed - self.spec.current_speed) * min(1.0, dt * 2.5)

        dx = self.spec.current_speed * dt * self.spec.direction
        self.spec.x += dx
        self.wheel_angle = (self.wheel_angle - (dx / self.spec.wheel_radius) * (180.0 / pi)) % 360.0

        limit = self.road_half_length + self.spec.length
        if (self.spec.direction > 0 and self.spec.x > limit) or (
            self.spec.direction < 0 and self.spec.x < -limit
        ):
            self._respawn(all_cars, limit)

    def _respawn(self, all_cars: list["Car"], limit: float) -> None:
        spawn_x = -limit if self.spec.direction > 0 else limit
        for other in all_cars:
            if other is self or abs(other.spec.lane_z - self.spec.lane_z) > 0.5:
                continue
            if self.spec.direction > 0:
                spawn_x = min(spawn_x, other.spec.x - other.spec.length - 6.0)
            else:
                spawn_x = max(spawn_x, other.spec.x + other.spec.length + 6.0)
        self.spec = random_car_spec(self.spec.lane_z, self.spec.direction, spawn_x)

    def get_world_bbox(self) -> list[tuple[float, float, float]]:
        hl = self.spec.length * 0.5
        hw = self.spec.width * 0.5
        h = self.spec.height
        cx, cz = self.spec.x, self.spec.lane_z
        return [
            (cx - hl, 0.0, cz - hw),
            (cx + hl, 0.0, cz - hw),
            (cx + hl, 0.0, cz + hw),
            (cx - hl, 0.0, cz + hw),
            (cx - hl, h, cz - hw),
            (cx + hl, h, cz - hw),
            (cx + hl, h, cz + hw),
            (cx - hl, h, cz + hw),
        ]

    def _body_profiles(self) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
        hl = self.spec.length * 0.5
        h = self.spec.height
        y_floor = self.spec.wheel_radius * 0.55
        y_belt = y_floor + (h - y_floor) * 0.52

        if self.spec.body_type == "sedan":
            lower = [
                (-hl, y_floor),
                (hl, y_floor),
                (hl + 0.05, y_floor + 0.22),
                (hl - 0.08, y_belt - 0.06),
                (hl * 0.42, y_belt),
                (-hl * 0.68, y_belt + 0.03),
                (-hl, y_belt - 0.02),
                (-hl - 0.04, y_floor + 0.24),
            ]
            cabin = [
                (-hl * 0.65, y_belt - 0.02),
                (hl * 0.44, y_belt - 0.02),
                (hl * 0.14, h),
                (-hl * 0.40, h),
            ]
        elif self.spec.body_type == "hatchback":
            lower = [
                (-hl, y_floor),
                (hl, y_floor),
                (hl + 0.04, y_floor + 0.22),
                (hl - 0.08, y_belt - 0.05),
                (hl * 0.40, y_belt),
                (-hl * 0.88, y_belt + 0.04),
                (-hl - 0.03, y_floor + 0.25),
            ]
            cabin = [
                (-hl * 0.85, y_belt),
                (hl * 0.42, y_belt - 0.02),
                (hl * 0.12, h),
                (-hl * 0.62, h),
            ]
        else:
            lower = [
                (-hl, y_floor),
                (hl, y_floor),
                (hl + 0.05, y_floor + 0.28),
                (hl - 0.06, y_belt),
                (hl * 0.42, y_belt + 0.02),
                (-hl * 0.92, y_belt + 0.05),
                (-hl - 0.04, y_floor + 0.28),
            ]
            cabin = [
                (-hl * 0.90, y_belt + 0.01),
                (hl * 0.44, y_belt),
                (hl * 0.18, h),
                (-hl * 0.78, h),
            ]

        return lower, cabin

    def draw(self, day_mode: bool = True) -> None:
        s = self.spec
        hl = s.length * 0.5
        hw = s.width * 0.5
        y_floor = s.wheel_radius * 0.55
        y_belt = y_floor + (s.height - y_floor) * 0.52

        glPushMatrix()
        glTranslatef(s.x, 0.0, s.lane_z)
        if s.direction < 0:
            glRotatef(180.0, 0.0, 1.0, 0.0)

        # Контактна тінь на асфальті
        glDisable(GL_LIGHTING)
        glColor4f(0.03, 0.03, 0.04, 0.55)
        glBegin(GL_QUADS)
        glVertex3f(-hl * 1.02, 0.015, -hw * 1.06)
        glVertex3f(hl * 1.02, 0.015, -hw * 1.06)
        glVertex3f(hl * 1.02, 0.015, hw * 1.06)
        glVertex3f(-hl * 1.02, 0.015, hw * 1.06)
        glEnd()

        if not day_mode:
            # Світловий конус фар ввечері
            glBegin(GL_TRIANGLES)
            glColor4f(1.0, 0.95, 0.72, 0.28)
            glVertex3f(hl, 0.02, -hw * 0.55)
            glColor4f(1.0, 0.95, 0.72, 0.0)
            glVertex3f(hl + 8.0, 0.02, -hw * 1.6)
            glVertex3f(hl + 8.0, 0.02, hw * 0.2)

            glColor4f(1.0, 0.95, 0.72, 0.28)
            glVertex3f(hl, 0.02, hw * 0.55)
            glColor4f(1.0, 0.95, 0.72, 0.0)
            glVertex3f(hl + 8.0, 0.02, -hw * 0.2)
            glVertex3f(hl + 8.0, 0.02, hw * 1.6)
            glEnd()
        glEnable(GL_LIGHTING)

        lower_prof, cabin_prof = self._body_profiles()

        # Основний кузов
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, s.body_color)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.75, 0.75, 0.78, 1.0))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 64.0)
        _extrude_profile(lower_prof, -hw, hw)

        # Рамка даху та стійки
        _extrude_profile(cabin_prof, -hw * 0.87, hw * 0.87)

        # Засклення (з відступом від стійок, щоб уникнути Z-fighting)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.12, 0.19, 0.27, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.95, 0.95, 1.0, 1.0))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 96.0)
        glass_prof = [
            (cabin_prof[0][0] - 0.04, cabin_prof[0][1] + 0.07),
            (cabin_prof[1][0] + 0.04, cabin_prof[1][1] + 0.07),
            (cabin_prof[2][0] - 0.05, cabin_prof[2][1] - 0.06),
            (cabin_prof[3][0] + 0.05, cabin_prof[3][1] - 0.06),
        ]
        _extrude_profile(glass_prof, -hw * 0.90, hw * 0.90)

        # Дзеркала заднього виду
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, s.body_color)
        for side in (-1.0, 1.0):
            _draw_box(hl * 0.24, hl * 0.34, y_belt + 0.02, y_belt + 0.14, side * hw, side * (hw + 0.14))

        # Бампери та решітка радіатора
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.10, 0.10, 0.11, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.25, 0.25, 0.25, 1.0))
        _draw_box(hl - 0.06, hl + 0.08, y_floor, y_floor + 0.22, -hw * 0.99, hw * 0.99)
        _draw_box(-hl - 0.07, -hl + 0.05, y_floor, y_floor + 0.22, -hw * 0.99, hw * 0.99)
        _draw_box(hl - 0.02, hl + 0.04, y_floor + 0.25, y_belt - 0.12, -hw * 0.42, hw * 0.42)

        # Номерні знаки
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.92, 0.92, 0.92, 1.0))
        _draw_box(hl + 0.06, hl + 0.09, y_floor + 0.08, y_floor + 0.19, -0.24, 0.24)
        _draw_box(-hl - 0.08, -hl - 0.05, y_floor + 0.12, y_floor + 0.23, -0.24, 0.24)

        # Передні фари
        em_front = (0.95, 0.92, 0.65, 1.0) if not day_mode else (0.55, 0.52, 0.35, 1.0)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, em_front)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (1.0, 0.96, 0.72, 1.0))
        for z_side in (-hw * 0.70, hw * 0.70):
            _draw_box(hl - 0.05, hl + 0.03, y_floor + 0.27, y_belt - 0.10, z_side - 0.18, z_side + 0.18)

        # Задні ліхтарі
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.85, 0.06, 0.06, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.95, 0.1, 0.1, 1.0))
        for z_side in (-hw * 0.72, hw * 0.72):
            _draw_box(-hl - 0.03, -hl + 0.04, y_floor + 0.28, y_belt - 0.08, z_side - 0.19, z_side + 0.19)

        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))

        # Колеса
        wheel_x_positions = (-hl * 0.58, hl * 0.58)
        wheel_z_positions = (-hw - 0.01, hw - s.wheel_width + 0.01)
        for wx in wheel_x_positions:
            for wz in wheel_z_positions:
                self._draw_wheel(wx, s.wheel_radius, wz)

        glPopMatrix()

    def _draw_wheel(self, x: float, y: float, z: float) -> None:
        r = self.spec.wheel_radius
        w = self.spec.wheel_width

        glPushMatrix()
        glTranslatef(x, y, z)
        glRotatef(self.wheel_angle, 0.0, 0.0, 1.0)

        # Шина
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.09, 0.09, 0.10, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.15, 0.15, 0.15, 1.0))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 12.0)
        gluCylinder(self._quadric, r, r, w, 24, 1)

        glPushMatrix()
        glRotatef(180.0, 1.0, 0.0, 0.0)
        gluDisk(self._quadric, r * 0.58, r, 24, 1)
        glPopMatrix()

        glPushMatrix()
        glTranslatef(0.0, 0.0, w)
        gluDisk(self._quadric, r * 0.58, r, 24, 1)
        glPopMatrix()

        # Металевий диск і спиці
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.76, 0.79, 0.84, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.9, 0.9, 0.9, 1.0))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 72.0)

        for z_face, rot in ((w + 0.002, 0.0), (-0.002, 180.0)):
            glPushMatrix()
            glTranslatef(0.0, 0.0, z_face)
            glRotatef(rot, 1.0, 0.0, 0.0)
            gluDisk(self._quadric, 0.0, r * 0.22, 14, 1)
            gluDisk(self._quadric, r * 0.50, r * 0.58, 20, 1)
            for k in range(5):
                ang = k * 2.0 * pi / 5.0
                cx, cy = cos(ang), sin(ang)
                px, py = -cy * 0.035, cx * 0.035
                glBegin(GL_QUADS)
                glNormal3f(0.0, 0.0, 1.0)
                glVertex3f(px, py, 0.003)
                glVertex3f(-px, -py, 0.003)
                glVertex3f(cx * r * 0.54 - px, cy * r * 0.54 - py, 0.003)
                glVertex3f(cx * r * 0.54 + px, cy * r * 0.54 + py, 0.003)
                glEnd()
            glPopMatrix()

        glPopMatrix()
