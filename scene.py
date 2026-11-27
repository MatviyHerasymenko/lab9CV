from OpenGL.GL import *
from OpenGL.GLU import *


CAMERA_PRESETS = [
    {"name": "CCTV Overview", "yaw": -35.0, "pitch": 24.0, "dist": 23.0, "target": (0.0, 0.8, 0.0)},
    {"name": "Roadside Side", "yaw": 0.0, "pitch": 11.0, "dist": 18.0, "target": (0.0, 0.8, 0.0)},
    {"name": "Low Angle", "yaw": -64.0, "pitch": 8.0, "dist": 16.5, "target": (0.0, 0.9, 0.0)},
    {"name": "Top-Down", "yaw": 0.0, "pitch": 68.0, "dist": 25.0, "target": (0.0, 0.0, 0.0)},
]


class SceneEnvironment:
    def __init__(self, road_half_length: float = 42.0, road_half_width: float = 4.6):
        self.road_half_length = road_half_length
        self.road_half_width = road_half_width
        self.day_mode = True
        self._quadric = gluNewQuadric()

    def apply_lighting(self) -> None:
        if self.day_mode:
            sky = (0.53, 0.78, 0.95, 1.0)
            ambient = (0.36, 0.36, 0.39, 1.0)
            diffuse = (0.95, 0.93, 0.88, 1.0)
            specular = (0.85, 0.85, 0.85, 1.0)
            light_pos = (14.0, 26.0, 14.0, 1.0)
        else:
            sky = (0.07, 0.10, 0.17, 1.0)
            ambient = (0.14, 0.16, 0.22, 1.0)
            diffuse = (0.42, 0.45, 0.56, 1.0)
            specular = (0.4, 0.4, 0.5, 1.0)
            light_pos = (-10.0, 18.0, 10.0, 1.0)

        glClearColor(*sky)
        glFogfv(GL_FOG_COLOR, sky)
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glLightfv(GL_LIGHT0, GL_AMBIENT, ambient)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, diffuse)
        glLightfv(GL_LIGHT0, GL_SPECULAR, specular)

    def draw(self) -> None:
        L = self.road_half_length
        W = self.road_half_width

        # Газон
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.22, 0.42, 0.20, 1.0))
        glBegin(GL_QUADS)
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(-L, -0.04, -36.0)
        glVertex3f(L, -0.04, -36.0)
        glVertex3f(L, -0.04, 36.0)
        glVertex3f(-L, -0.04, 36.0)
        glEnd()

        # Асфальт
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.19, 0.20, 0.22, 1.0))
        glBegin(GL_QUADS)
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(-L, 0.0, -W)
        glVertex3f(L, 0.0, -W)
        glVertex3f(L, 0.0, W)
        glVertex3f(-L, 0.0, W)
        glEnd()

        # Тротуари та бордюри
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.58, 0.58, 0.56, 1.0))
        for sign in (-1, 1):
            z_in = sign * W
            z_out = sign * (W + 1.8)
            z_min, z_max = min(z_in, z_out), max(z_in, z_out)
            glBegin(GL_QUADS)
            glNormal3f(0.0, 1.0, 0.0)
            glVertex3f(-L, 0.11, z_min)
            glVertex3f(L, 0.11, z_min)
            glVertex3f(L, 0.11, z_max)
            glVertex3f(-L, 0.11, z_max)
            glEnd()

            glBegin(GL_QUADS)
            glNormal3f(0.0, 0.0, -sign)
            glVertex3f(-L, 0.0, z_in)
            glVertex3f(L, 0.0, z_in)
            glVertex3f(L, 0.11, z_in)
            glVertex3f(-L, 0.11, z_in)
            glEnd()

        # Дорожня розмітка
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.94, 0.94, 0.94, 1.0))
        for z_edge in (-W + 0.25, W - 0.25):
            glBegin(GL_QUADS)
            glNormal3f(0.0, 1.0, 0.0)
            glVertex3f(-L, 0.008, z_edge - 0.07)
            glVertex3f(L, 0.008, z_edge - 0.07)
            glVertex3f(L, 0.008, z_edge + 0.07)
            glVertex3f(-L, 0.008, z_edge + 0.07)
            glEnd()

        x = -L + 1.0
        while x < L - 1.0:
            glBegin(GL_QUADS)
            glNormal3f(0.0, 1.0, 0.0)
            glVertex3f(x, 0.008, -0.08)
            glVertex3f(x + 2.2, 0.008, -0.08)
            glVertex3f(x + 2.2, 0.008, 0.08)
            glVertex3f(x, 0.008, 0.08)
            glEnd()
            x += 4.5

        # Пішохідний перехід
        for pz in range(-4, 5):
            z_center = pz * 0.95
            glBegin(GL_QUADS)
            glNormal3f(0.0, 1.0, 0.0)
            glVertex3f(-1.4, 0.009, z_center - 0.24)
            glVertex3f(1.4, 0.009, z_center - 0.24)
            glVertex3f(1.4, 0.009, z_center + 0.24)
            glVertex3f(-1.4, 0.009, z_center + 0.24)
            glEnd()

        # Ліхтарні стовпи та дерева
        for px in range(-35, 38, 14):
            self._draw_street_lamp(float(px), -W - 1.2)
            self._draw_tree(float(px) + 7.0, -W - 3.6)
            self._draw_tree(float(px) + 3.5, W + 3.8)

    def _draw_street_lamp(self, x: float, z: float) -> None:
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.35, 0.37, 0.40, 1.0))
        glPushMatrix()
        glTranslatef(x, 0.0, z)
        glRotatef(-90.0, 1.0, 0.0, 0.0)
        gluCylinder(self._quadric, 0.1, 0.07, 4.9, 10, 1)
        glPopMatrix()

        glPushMatrix()
        glTranslatef(x, 4.85, z)
        gluCylinder(self._quadric, 0.06, 0.06, 1.3, 8, 1)
        glPopMatrix()

        if not self.day_mode:
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.95, 0.85, 0.5, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.95, 0.9, 0.7, 1.0))
        glPushMatrix()
        glTranslatef(x, 4.8, z + 1.25)
        gluSphere(self._quadric, 0.18, 10, 10)
        glPopMatrix()
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))

    def _draw_tree(self, x: float, z: float) -> None:
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.36, 0.24, 0.14, 1.0))
        glPushMatrix()
        glTranslatef(x, 0.0, z)
        glRotatef(-90.0, 1.0, 0.0, 0.0)
        gluCylinder(self._quadric, 0.22, 0.14, 2.2, 8, 1)
        glPopMatrix()

        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.16, 0.42, 0.18, 1.0))
        for dy, r in ((2.7, 1.25), (3.5, 0.95)):
            glPushMatrix()
            glTranslatef(x, dy, z)
            gluSphere(self._quadric, r, 10, 10)
            glPopMatrix()
