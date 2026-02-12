"""
Cocktail Image Renderer

칵테일 베이스 이미지에 그라데이션을 적용해 최종 이미지를 생성한다.
"""

from PIL import Image, ImageDraw
import os
import numpy as np
from .models import GradientInfo


class CocktailImageRenderer:
    """
    칵테일 이미지 렌더링 클래스.

    베이스 이미지의 컵 영역에 감정 기반 그라데이션을 적용한다.
    텍스트는 이미지에 합성하지 않고 웹 화면에서 별도로 노출한다.
    """

    def __init__(self, output_dir: str = "output"):
        """
        렌더러 초기화.

        Args:
            output_dir: 생성 이미지를 저장할 출력 디렉터리
        """
        self.output_dir = output_dir

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 프로젝트 루트(현재 파일 상위 3단계: cocktail -> model_sample -> root) 기준 경로
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.allowed_palette = [
            "#FFB7C5",
            "#FF4500",
            "#E0FFFF",
            "#FFD700",
            "#4B0082",
            "#87CEEB",
            "#98FF98",
        ]

    def _resolve_base_image_path(self, base_image_path: str) -> str:
        """상대 경로를 프로젝트 루트 기준 절대 경로로 변환한다."""
        if os.path.isabs(base_image_path):
            return base_image_path
        return os.path.join(self.project_root, base_image_path)

    def _select_palette_colors(self, colors: list, max_colors: int = 3) -> list[str]:
        """허용 팔레트 안에서 최대 max_colors개 색상만 선택한다."""
        allowed = set(self.allowed_palette)
        selected = []

        for color in (colors or []):
            if not isinstance(color, str):
                continue
            normalized = color.strip().upper()
            if normalized in allowed and normalized not in selected:
                selected.append(normalized)
            if len(selected) >= max_colors:
                break

        if not selected:
            selected = [self.allowed_palette[0]]

        return selected

    def _get_default_base_image_path(self) -> str:
        """static/에서 기본 베이스 이미지를 찾는다."""
        static_dir = os.path.join(self.project_root, "static")
        candidates = [
            "배경제거W.png",
            "칵테일_도안_배경제거.png",
            "칵테일 도안.png",
        ]

        for name in candidates:
            full_path = os.path.join(static_dir, name)
            if os.path.exists(full_path):
                return os.path.join("static", name)

        if os.path.exists(static_dir):
            for name in os.listdir(static_dir):
                if name.lower().endswith(".png"):
                    return os.path.join("static", name)

        raise FileNotFoundError(f"static 디렉터리에서 PNG 베이스 이미지를 찾을 수 없습니다: {static_dir}")

    def hex_to_rgb(self, hex_color: str) -> tuple:
        """
        HEX 색상 코드를 RGB 튜플로 변환한다.

        Args:
            hex_color: HEX 색상 코드 (예: '#FFB7C5')

        Returns:
            tuple: (R, G, B)
        """
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    def detect_glass_region(self, image: Image.Image) -> tuple:
        """
        이미지에서 컵의 액체 영역을 추정한다.

        알파 채널을 기반으로 불투명 영역 경계를 추정하고,
        컵 테두리를 일부 제외한 내부 영역을 반환한다.

        Args:
            image: 베이스 이미지(RGBA)

        Returns:
            tuple: (left, top, right, bottom)
        """
        img_array = np.array(image)
        width, height = image.size

        if img_array.shape[2] == 4:
            alpha = img_array[:, :, 3]
            non_transparent = alpha > 50
            rows = np.any(non_transparent, axis=1)
            cols = np.any(non_transparent, axis=0)

            if rows.any() and cols.any():
                top, bottom = np.where(rows)[0][[0, -1]]
                left, right = np.where(cols)[0][[0, -1]]

                img_height = bottom - top
                liquid_top = int(top + img_height * 0.25)
                liquid_bottom = int(bottom - img_height * 0.1)

                img_width = right - left
                liquid_left = int(left + img_width * 0.3)
                liquid_right = int(right - img_width * 0.3)

                return (liquid_left, liquid_top, liquid_right, liquid_bottom)

        # 기본값: 중앙 영역
        return (
            int(width * 0.3),
            int(height * 0.3),
            int(width * 0.7),
            int(height * 0.7),
        )

    def create_glass_gradient(
        self,
        width: int,
        height: int,
        glass_region: tuple,
        gradient_info: GradientInfo,
        alpha: int = 200,
    ) -> Image.Image:
        """
        컵 내부 영역에만 적용되는 그라데이션 오버레이를 생성한다.

        Args:
            width: 이미지 너비
            height: 이미지 높이
            glass_region: 컵 내부 영역 (left, top, right, bottom)
            gradient_info: 그라데이션 정보
            alpha: 불투명도(0-255)

        Returns:
            RGBA 이미지
        """
        left, top, right, bottom = glass_region
        gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient)

        palette_colors = self._select_palette_colors(gradient_info.colors, max_colors=3)
        colors_rgb = [self.hex_to_rgb(color) for color in palette_colors]
        glass_height = bottom - top

        if len(colors_rgb) == 1:
            color = colors_rgb[0] + (alpha,)
            draw.rectangle([(left, top), (right, bottom)], fill=color)
        elif len(colors_rgb) == 2:
            stop_y = int(top + glass_height * gradient_info.stops[0])
            for y in range(top, stop_y):
                color = colors_rgb[0] + (alpha,)
                draw.line([(left, y), (right, y)], fill=color)
            for y in range(stop_y, bottom):
                progress = (y - stop_y) / (bottom - stop_y) if (bottom - stop_y) > 0 else 1
                r = int(colors_rgb[0][0] + (colors_rgb[1][0] - colors_rgb[0][0]) * progress)
                g = int(colors_rgb[0][1] + (colors_rgb[1][1] - colors_rgb[0][1]) * progress)
                b = int(colors_rgb[0][2] + (colors_rgb[1][2] - colors_rgb[0][2]) * progress)
                draw.line([(left, y), (right, y)], fill=(r, g, b, alpha))
        elif len(colors_rgb) == 3:
            stop1_y = int(top + glass_height * gradient_info.stops[0])
            stop2_y = int(top + glass_height * gradient_info.stops[1])

            for y in range(top, stop1_y):
                color = colors_rgb[0] + (alpha,)
                draw.line([(left, y), (right, y)], fill=color)

            for y in range(stop1_y, stop2_y):
                progress = (y - stop1_y) / (stop2_y - stop1_y) if (stop2_y - stop1_y) > 0 else 0
                r = int(colors_rgb[0][0] + (colors_rgb[1][0] - colors_rgb[0][0]) * progress)
                g = int(colors_rgb[0][1] + (colors_rgb[1][1] - colors_rgb[0][1]) * progress)
                b = int(colors_rgb[0][2] + (colors_rgb[1][2] - colors_rgb[0][2]) * progress)
                draw.line([(left, y), (right, y)], fill=(r, g, b, alpha))

            for y in range(stop2_y, bottom):
                progress = (y - stop2_y) / (bottom - stop2_y) if (bottom - stop2_y) > 0 else 1
                r = int(colors_rgb[1][0] + (colors_rgb[2][0] - colors_rgb[1][0]) * progress)
                g = int(colors_rgb[1][1] + (colors_rgb[2][1] - colors_rgb[1][1]) * progress)
                b = int(colors_rgb[1][2] + (colors_rgb[2][2] - colors_rgb[1][2]) * progress)
                draw.line([(left, y), (right, y)], fill=(r, g, b, alpha))

        return gradient

    def render_cocktail_with_polygon(
        self,
        gradient_colors: list,
        output_filename: str,
        base_image_path: str | None = None,
    ) -> str:
        """
        사전 정의된 폴리곤 영역에 그라데이션을 채워 칵테일 이미지를 렌더링한다.

        Args:
            gradient_colors: HEX 색상 리스트
            output_filename: 출력 파일명
            base_image_path: 베이스 이미지 경로 (None이면 기본 이미지 자동 선택)

        Returns:
            생성된 이미지 파일 경로
        """
        import logging
        logger = logging.getLogger(__name__)

        if not base_image_path:
            base_image_path = self._get_default_base_image_path()
        logger.info(f"[DEBUG] render_cocktail_with_polygon - 베이스 이미지 경로: {base_image_path}")

        resolved_base_image_path = self._resolve_base_image_path(base_image_path)
        logger.info(f"[DEBUG] resolved 베이스 이미지 경로: {resolved_base_image_path}")

        if not os.path.exists(resolved_base_image_path):
            raise FileNotFoundError(f"베이스 이미지를 찾을 수 없습니다: {resolved_base_image_path}")

        base_image = Image.open(resolved_base_image_path).convert("RGBA")
        width, height = base_image.size
        logger.info(f"[DEBUG] 로드된 이미지 크기: {width}x{height}")

        polygon_coords = [
            (335, 134), (320, 134), (304, 136), (287, 138), (270, 141),
            (258, 197), (250, 249), (250, 268), (252, 281), (256, 294),
            (259, 305), (265, 314), (269, 321), (275, 327), (280, 333),
            (287, 339), (297, 345), (308, 349), (320, 354), (332, 356),
            (343, 356), (355, 356), (367, 354), (381, 351), (393, 346),
            (404, 341), (412, 334), (420, 325), (428, 315), (434, 303),
            (439, 289), (442, 276), (444, 260), (443, 248), (442, 237),
            (432, 192), (424, 147), (408, 141), (394, 137), (379, 135),
            (367, 134), (357, 134), (346, 134),
        ]

        palette_colors = self._select_palette_colors(gradient_colors, max_colors=3)
        colors_rgb = [self.hex_to_rgb(c) for c in palette_colors]

        y_coords = [y for x, y in polygon_coords]
        min_y = min(y_coords)
        max_y = max(y_coords)

        mask = Image.new("L", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.polygon(polygon_coords, fill=255)

        gradient_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw_gradient = ImageDraw.Draw(gradient_img)

        for y in range(min_y, max_y + 1):
            progress = (y - min_y) / (max_y - min_y) if (max_y - min_y) > 0 else 0

            if len(colors_rgb) == 1:
                r, g, b = colors_rgb[0]
            elif len(colors_rgb) == 2:
                r = int(colors_rgb[0][0] + (colors_rgb[1][0] - colors_rgb[0][0]) * progress)
                g = int(colors_rgb[0][1] + (colors_rgb[1][1] - colors_rgb[0][1]) * progress)
                b = int(colors_rgb[0][2] + (colors_rgb[1][2] - colors_rgb[0][2]) * progress)
            else:
                if progress < 0.5:
                    local_progress = progress * 2
                    r = int(colors_rgb[0][0] + (colors_rgb[1][0] - colors_rgb[0][0]) * local_progress)
                    g = int(colors_rgb[0][1] + (colors_rgb[1][1] - colors_rgb[0][1]) * local_progress)
                    b = int(colors_rgb[0][2] + (colors_rgb[1][2] - colors_rgb[0][2]) * local_progress)
                else:
                    local_progress = (progress - 0.5) * 2
                    r = int(colors_rgb[1][0] + (colors_rgb[2][0] - colors_rgb[1][0]) * local_progress)
                    g = int(colors_rgb[1][1] + (colors_rgb[2][1] - colors_rgb[1][1]) * local_progress)
                    b = int(colors_rgb[1][2] + (colors_rgb[2][2] - colors_rgb[1][2]) * local_progress)

            draw_gradient.line([(0, y), (width, y)], fill=(r, g, b, 200))

        gradient_array = np.array(gradient_img)
        mask_array = np.array(mask)
        gradient_array[:, :, 3] = np.minimum(gradient_array[:, :, 3], mask_array)
        gradient_img = Image.fromarray(gradient_array, "RGBA")

        result = Image.alpha_composite(base_image, gradient_img).convert("RGB")
        output_path = os.path.join(self.output_dir, output_filename)
        result.save(output_path, "PNG", quality=95)
        return output_path

    def render_cocktail(
        self,
        base_image_path: str,
        gradient_info: GradientInfo,
        output_filename: str,
    ) -> str:
        """
        자동 컵 영역 감지 방식으로 칵테일 이미지를 렌더링한다.

        Args:
            base_image_path: 베이스 이미지 경로
            gradient_info: 그라데이션 정보
            output_filename: 출력 파일명

        Returns:
            생성된 이미지 파일 경로
        """
        resolved_base_image_path = self._resolve_base_image_path(base_image_path)
        if not os.path.exists(resolved_base_image_path):
            raise FileNotFoundError(f"베이스 이미지를 찾을 수 없습니다: {resolved_base_image_path}")

        base_image = Image.open(resolved_base_image_path).convert("RGBA")
        width, height = base_image.size

        glass_region = self.detect_glass_region(base_image)
        gradient_overlay = self.create_glass_gradient(width, height, glass_region, gradient_info, alpha=220)

        result = Image.alpha_composite(base_image, gradient_overlay).convert("RGB")
        output_path = os.path.join(self.output_dir, output_filename)
        result.save(output_path, "PNG", quality=95)
        return output_path
