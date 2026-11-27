from pathlib import Path
import cv2
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from car import Car


class DatasetExporter:
    def __init__(self, output_dir: str = "dataset"):
        self.base_dir = Path(output_dir)
        self.images_dir = self.base_dir / "images"
        self.labels_dir = self.base_dir / "labels"
        self.preview_dir = self.base_dir / "preview"
        for d in (self.images_dir, self.labels_dir, self.preview_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.frame_idx = self._next_index()

    def _next_index(self) -> int:
        existing = sorted(self.images_dir.glob("frame_*.png"))
        if not existing:
            return 0
        last = existing[-1].stem.split("_")[-1]
        return int(last) + 1 if last.isdigit() else len(existing)

    def capture(self, width: int, height: int, cars: list[Car]) -> tuple[Path, int]:
        raw = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
        img = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
        img = np.flipud(img)
        bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)

        yolo_lines: list[str] = []
        preview = bgr.copy()

        for car in cars:
            xs, ys = [], []
            visible = True
            for wx, wy, wz in car.get_world_bbox():
                sx, sy, sz = gluProject(wx, wy, wz, modelview, projection, viewport)
                if sz < 0.0 or sz > 1.0:
                    visible = False
                    break
                xs.append(sx)
                ys.append(height - sy)

            if not visible:
                continue

            x_min = max(0.0, min(xs))
            x_max = min(float(width), max(xs))
            y_min = max(0.0, min(ys))
            y_max = min(float(height), max(ys))

            bw = x_max - x_min
            bh = y_max - y_min
            if bw < 28 or bh < 28:
                continue

            xc = ((x_min + x_max) * 0.5) / width
            yc = ((y_min + y_max) * 0.5) / height
            nw = bw / width
            nh = bh / height
            yolo_lines.append(f"0 {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}")

            p1 = (int(x_min), int(y_min))
            p2 = (int(x_max), int(y_max))
            cv2.rectangle(preview, p1, p2, (0, 220, 0), 2)
            cv2.putText(
                preview,
                "car",
                (p1[0], max(15, p1[1] - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 220, 0),
                2,
            )

        stem = f"frame_{self.frame_idx:04d}"
        img_path = self.images_dir / f"{stem}.png"
        lbl_path = self.labels_dir / f"{stem}.txt"
        prev_path = self.preview_dir / f"{stem}.png"

        cv2.imwrite(str(img_path), bgr)
        cv2.imwrite(str(prev_path), preview)
        lbl_path.write_text("\n".join(yolo_lines), encoding="utf-8")

        self.frame_idx += 1
        return img_path, len(yolo_lines)
