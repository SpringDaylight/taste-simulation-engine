"""
Cocktail Image Renderer

移듯뀒??踰좎씠???대?吏??洹몃씪?곗씠?섏쓣 ?곸슜?섏뿬 ?ㅼ젣 ?대?吏瑜??앹꽦?⑸땲??
"""

from PIL import Image, ImageDraw
import os
import numpy as np
from src.models import GradientInfo


class CocktailImageRenderer:
    """
    移듯뀒???대?吏 ?뚮뜑留??대옒??
    
    踰좎씠???대?吏?????곸뿭??媛먯젙 湲곕컲 洹몃씪?곗씠?섏쓣 ?곸슜?⑸땲??
    ?띿뒪?몃뒗 蹂꾨룄濡????섏씠吏?먯꽌 ?쒖떆?⑸땲??
    """
    
    def __init__(self, output_dir: str = "output"):
        """
        CocktailImageRenderer 珥덇린??
        
        Args:
            output_dir: ?앹꽦???대?吏瑜???ν븷 ?붾젆?좊━
        """
        self.output_dir = output_dir
        
        # 異쒕젰 ?붾젆?좊━ ?앹꽦
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # src ?붾젆?곕━ 湲곗? ?곸쐞(?꾨줈?앺듃 猷⑦듃) 寃쎈줈
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
        """
        踰좎씠???대?吏 寃쎈줈瑜??ㅽ뻾 ?꾩튂? 臾닿??섍쾶 ?댁꽍?쒕떎.
        """
        if os.path.isabs(base_image_path):
            return base_image_path
        return os.path.join(self.project_root, base_image_path)

    def _select_palette_colors(self, colors: list, max_colors: int = 3) -> list[str]:
        """Select up to max_colors from the allowed palette."""
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
        """Resolve a valid default base image from static/."""
        static_dir = os.path.join(self.project_root, "static")
        candidates = [
            "\ubc30\uacbd\uc81c\uac70W.png",
            "\uce75\ud14c\uc77c_\ub3c4\uc548_\ubc30\uacbd\uc81c\uac70.png",
            "\uce75\ud14c\uc77c \ub3c4\uc548.png",
        ]

        for name in candidates:
            full_path = os.path.join(static_dir, name)
            if os.path.exists(full_path):
                return os.path.join("static", name)

        if os.path.exists(static_dir):
            for name in os.listdir(static_dir):
                if name.lower().endswith(".png"):
                    return os.path.join("static", name)

        raise FileNotFoundError(f"No PNG base image found in: {static_dir}")
    
    def hex_to_rgb(self, hex_color: str) -> tuple:
        """
        HEX ?됱긽 肄붾뱶瑜?RGB ?쒗뵆濡?蹂??
        
        Args:
            hex_color: HEX ?됱긽 肄붾뱶 (?? '#FFB7C5')
            
        Returns:
            tuple: (R, G, B) ?쒗뵆
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def detect_glass_region(self, image: Image.Image) -> tuple:
        """
        ?대?吏?먯꽌 移듯뀒?????곸뿭??媛먯??⑸땲??
        
        ?щ챸???뚰뙆 梨꾨꼸)瑜?湲곕컲?쇰줈 ?붿쓽 ?꾩튂瑜?異붿젙?⑸땲??
        
        Args:
            image: 踰좎씠???대?吏 (RGBA)
            
        Returns:
            tuple: (left, top, right, bottom)
        """
        # ?대?吏瑜?numpy 諛곗뿴濡?蹂??
        img_array = np.array(image)
        width, height = image.size
        
        # ?뚰뙆 梨꾨꼸???덈뒗 寃쎌슦
        if img_array.shape[2] == 4:
            alpha = img_array[:, :, 3]
            
            # ?뚰뙆 媛믪씠 ?덈뒗 ?곸뿭 李얘린 (?щ챸?섏? ?딆? 遺遺?
            non_transparent = alpha > 50
            
            # ???곸뿭??寃쎄퀎 李얘린
            rows = np.any(non_transparent, axis=1)
            cols = np.any(non_transparent, axis=0)
            
            if rows.any() and cols.any():
                top, bottom = np.where(rows)[0][[0, -1]]
                left, right = np.where(cols)[0][[0, -1]]
                
                # ?붿쓽 ?ㅼ젣 ?≪껜 ?곸뿭 異붿젙
                # ?곷떒 20%???쒖쇅 (???뚮몢由?, ?섎떒 5%???쒖쇅
                img_height = bottom - top
                liquid_top = int(top + img_height * 0.25)
                liquid_bottom = int(bottom - img_height * 0.1)
                
                # 醫뚯슦 ?щ갚 議곗젙 (以묒븰 50% ?뺣룄留??ъ슜)
                img_width = right - left
                liquid_left = int(left + img_width * 0.3)
                liquid_right = int(right - img_width * 0.3)
                
                return (liquid_left, liquid_top, liquid_right, liquid_bottom)
        
        # 湲곕낯媛? ?대?吏 以묒븰 40%
        return (
            int(width * 0.3),
            int(height * 0.3),
            int(width * 0.7),
            int(height * 0.7)
        )
    
    def create_glass_gradient(
        self, 
        width: int, 
        height: int,
        glass_region: tuple,
        gradient_info: GradientInfo,
        alpha: int = 200
    ) -> Image.Image:
        """
        ???곸뿭?먮쭔 ?곸슜?섎뒗 洹몃씪?곗씠???앹꽦
        
        Args:
            width: ?대?吏 ?덈퉬
            height: ?대?吏 ?믪씠
            glass_region: (left, top, right, bottom) ???곸뿭 ?뺣낫
            gradient_info: 洹몃씪?곗씠???뺣낫
            alpha: ?щ챸??(0-255)
            
        Returns:
            Image.Image: 洹몃씪?곗씠???대?吏 (RGBA)
        """
        left, top, right, bottom = glass_region
        
        # ?щ챸??RGBA ?대?吏 ?앹꽦
        gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient)
        
        # ?됱긽??RGB濡?蹂??
        palette_colors = self._select_palette_colors(gradient_info.colors, max_colors=3)
        colors_rgb = [self.hex_to_rgb(color) for color in palette_colors]
        
        # ???곸뿭???믪씠
        glass_height = bottom - top
        
        # ?몃줈 諛⑺뼢 洹몃씪?곗씠???앹꽦 (???곸뿭留?
        if len(colors_rgb) == 1:
            # ?⑥깋
            color = colors_rgb[0] + (alpha,)
            draw.rectangle([(left, top), (right, bottom)], fill=color)
        
        elif len(colors_rgb) == 2:
            # 2??洹몃씪?곗씠??
            stop_y = int(top + glass_height * gradient_info.stops[0])
            
            # 泥?踰덉㎏ ?됱긽 ?곸뿭
            for y in range(top, stop_y):
                color = colors_rgb[0] + (alpha,)
                draw.line([(left, y), (right, y)], fill=color)
            
            # 洹몃씪?곗씠???꾪솚 ?곸뿭
            for y in range(stop_y, bottom):
                progress = (y - stop_y) / (bottom - stop_y) if (bottom - stop_y) > 0 else 1
                r = int(colors_rgb[0][0] + (colors_rgb[1][0] - colors_rgb[0][0]) * progress)
                g = int(colors_rgb[0][1] + (colors_rgb[1][1] - colors_rgb[0][1]) * progress)
                b = int(colors_rgb[0][2] + (colors_rgb[1][2] - colors_rgb[0][2]) * progress)
                color = (r, g, b, alpha)
                draw.line([(left, y), (right, y)], fill=color)
        
        elif len(colors_rgb) == 3:
            # 3??洹몃씪?곗씠??
            stop1_y = int(top + glass_height * gradient_info.stops[0])
            stop2_y = int(top + glass_height * gradient_info.stops[1])
            
            # 泥?踰덉㎏ ?됱긽 ?곸뿭
            for y in range(top, stop1_y):
                color = colors_rgb[0] + (alpha,)
                draw.line([(left, y), (right, y)], fill=color)
            
            # 泥?踰덉㎏ ????踰덉㎏ ?꾪솚
            for y in range(stop1_y, stop2_y):
                progress = (y - stop1_y) / (stop2_y - stop1_y) if (stop2_y - stop1_y) > 0 else 0
                r = int(colors_rgb[0][0] + (colors_rgb[1][0] - colors_rgb[0][0]) * progress)
                g = int(colors_rgb[0][1] + (colors_rgb[1][1] - colors_rgb[0][1]) * progress)
                b = int(colors_rgb[0][2] + (colors_rgb[1][2] - colors_rgb[0][2]) * progress)
                color = (r, g, b, alpha)
                draw.line([(left, y), (right, y)], fill=color)
            
            # ??踰덉㎏ ????踰덉㎏ ?꾪솚
            for y in range(stop2_y, bottom):
                progress = (y - stop2_y) / (bottom - stop2_y) if (bottom - stop2_y) > 0 else 1
                r = int(colors_rgb[1][0] + (colors_rgb[2][0] - colors_rgb[1][0]) * progress)
                g = int(colors_rgb[1][1] + (colors_rgb[2][1] - colors_rgb[1][1]) * progress)
                b = int(colors_rgb[1][2] + (colors_rgb[2][2] - colors_rgb[1][2]) * progress)
                color = (r, g, b, alpha)
                draw.line([(left, y), (right, y)], fill=color)
        
        return gradient
    
    def render_cocktail_with_polygon(
        self,
        gradient_colors: list,
        output_filename: str,
        base_image_path: str | None = None
    ) -> str:
        """
        ?대━怨?醫뚰몴瑜??ъ슜?섏뿬 移듯뀒???대?吏 ?뚮뜑留?
        
        ?뺥솗???대━怨?醫뚰몴瑜??ъ슜?섏뿬 ???대?留?洹몃씪?곗씠?섏쑝濡?梨꾩썎?덈떎.
        ?뚰뙆 留덉뒪?뱀쓣 ?듯빐 ?먯옟?댁? ?뚮몢由щ? ?쒖쇅?⑸땲??
        ?띿뒪?몃뒗 ?대?吏??異붽??섏? ?딄퀬 蹂꾨룄濡?諛섑솚?⑸땲??
        
        Args:
            gradient_colors: 洹몃씪?곗씠???됱긽 由ъ뒪??(HEX)
            output_filename: 異쒕젰 ?뚯씪紐?
            base_image_path: 踰좎씠???대?吏 寃쎈줈 (湲곕낯媛? "static/諛곌꼍?쒓굅W.png")
        
        Returns:
            str: ?앹꽦???대?吏 ?뚯씪 寃쎈줈
        """
        # 踰좎씠???대?吏 濡쒕뱶
        import logging
        logger = logging.getLogger(__name__)
        if not base_image_path:
            base_image_path = self._get_default_base_image_path()
        logger.info(f"[DEBUG] render_cocktail_with_polygon - 踰좎씠???대?吏 寃쎈줈: {base_image_path}")

        resolved_base_image_path = self._resolve_base_image_path(base_image_path)
        logger.info(f"[DEBUG] resolved 踰좎씠???대?吏 寃쎈줈: {resolved_base_image_path}")

        if not os.path.exists(resolved_base_image_path):
            raise FileNotFoundError(f"踰좎씠???대?吏瑜?李얠쓣 ???놁뒿?덈떎: {resolved_base_image_path}")

        base_image = Image.open(resolved_base_image_path).convert('RGBA')
        width, height = base_image.size
        logger.info(f"[DEBUG] 濡쒕뱶???대?吏 ?ш린: {width}x{height}")
        
        # ?대━怨?醫뚰몴 (移듯뀒?????대? ?곸뿭)
        polygon_coords = [
            (335, 134), (320, 134), (304, 136), (287, 138), (270, 141),
            (258, 197), (250, 249), (250, 268), (252, 281), (256, 294),
            (259, 305), (265, 314), (269, 321), (275, 327), (280, 333),
            (287, 339), (297, 345), (308, 349), (320, 354), (332, 356),
            (343, 356), (355, 356), (367, 354), (381, 351), (393, 346),
            (404, 341), (412, 334), (420, 325), (428, 315), (434, 303),
            (439, 289), (442, 276), (444, 260), (443, 248), (442, 237),
            (432, 192), (424, 147), (408, 141), (394, 137), (379, 135),
            (367, 134), (357, 134), (346, 134)
        ]
        
        # ?됱긽??RGB濡?蹂??
        palette_colors = self._select_palette_colors(gradient_colors, max_colors=3)
        colors_rgb = [self.hex_to_rgb(c) for c in palette_colors]
        
        # ?대━怨ㅼ쓽 Y 踰붿쐞 李얘린
        y_coords = [y for x, y in polygon_coords]
        min_y = min(y_coords)
        max_y = max(y_coords)
        
        # ?대━怨?留덉뒪???앹꽦
        mask = Image.new('L', (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.polygon(polygon_coords, fill=255)
        
        # 洹몃씪?곗씠???대?吏 ?앹꽦
        gradient_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        draw_gradient = ImageDraw.Draw(gradient_img)
        for y in range(min_y, max_y + 1):
            # Y 위치에 따른 색상 계산
            progress = (y - min_y) / (max_y - min_y) if (max_y - min_y) > 0 else 0

            if len(colors_rgb) == 1:
                r, g, b = colors_rgb[0]
            elif len(colors_rgb) == 2:
                r = int(colors_rgb[0][0] + (colors_rgb[1][0] - colors_rgb[0][0]) * progress)
                g = int(colors_rgb[0][1] + (colors_rgb[1][1] - colors_rgb[0][1]) * progress)
                b = int(colors_rgb[0][2] + (colors_rgb[1][2] - colors_rgb[0][2]) * progress)
            else:
                # 3색 그라데이션
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

            color = (r, g, b, 200)
            draw_gradient.line([(0, y), (width, y)], fill=color)
        
        # 留덉뒪???곸슜
        gradient_array = np.array(gradient_img)
        mask_array = np.array(mask)
        gradient_array[:, :, 3] = np.minimum(gradient_array[:, :, 3], mask_array)
        gradient_img = Image.fromarray(gradient_array, 'RGBA')
        
        # 踰좎씠???대?吏? ?⑹꽦
        result = Image.alpha_composite(base_image, gradient_img)
        result = result.convert('RGB')
        
        # 異쒕젰 ?뚯씪 寃쎈줈
        output_path = os.path.join(self.output_dir, output_filename)
        
        # ?대?吏 ???
        result.save(output_path, 'PNG', quality=95)
        
        return output_path
    
    def render_cocktail(
        self,
        base_image_path: str,
        gradient_info: GradientInfo,
        output_filename: str
    ) -> str:
        """
        移듯뀒???대?吏 ?뚮뜑留?(?뚰뙆 梨꾨꼸 媛먯? 諛⑹떇)
        
        踰좎씠???대?吏?????곸뿭???먮룞 媛먯??섏뿬 洹몃씪?곗씠?섏쓣 ?곸슜?⑸땲??
        ?띿뒪?몃뒗 蹂꾨룄濡????섏씠吏?먯꽌 ?쒖떆?⑸땲??
        
        Args:
            base_image_path: 踰좎씠???대?吏 寃쎈줈
            gradient_info: 洹몃씪?곗씠???뺣낫
            output_filename: 異쒕젰 ?뚯씪紐?
            
        Returns:
            str: ?앹꽦???대?吏 ?뚯씪 寃쎈줈
        """
        # 踰좎씠???대?吏 濡쒕뱶
        resolved_base_image_path = self._resolve_base_image_path(base_image_path)
        if not os.path.exists(resolved_base_image_path):
            raise FileNotFoundError(f"踰좎씠???대?吏瑜?李얠쓣 ???놁뒿?덈떎: {resolved_base_image_path}")

        base_image = Image.open(resolved_base_image_path).convert('RGBA')
        width, height = base_image.size
        
        # ???곸뿭 媛먯?
        glass_region = self.detect_glass_region(base_image)
        
        # ???곸뿭?먮쭔 洹몃씪?곗씠???앹꽦
        gradient_overlay = self.create_glass_gradient(
            width, height, glass_region, gradient_info, alpha=220
        )
        
        # 踰좎씠???대?吏? 洹몃씪?곗씠???⑹꽦
        result = Image.alpha_composite(base_image, gradient_overlay)
        
        # RGB濡?蹂??(PNG ??μ슜)
        result = result.convert('RGB')
        
        # 異쒕젰 ?뚯씪 寃쎈줈
        output_path = os.path.join(self.output_dir, output_filename)
        
        # ?대?吏 ???
        result.save(output_path, 'PNG', quality=95)
        
        return output_path

