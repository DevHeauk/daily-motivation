"""앱 아이콘 PNG 생성 스크립트.

다크 배경(#0f172a) + 떠오르는 태양(Dawn) 컨셉.
반원형 태양(accent #f472b6) + 광선(primary #38bdf8) + 수평선.
"매일 동기부여" — 매일 아침 새로운 명언이 떠오른다는 의미.
Android mipmap 크기별 + Play Store용 512x512 생성.
"""

from PIL import Image, ImageDraw
import math
import os

# 컬러
BG_COLOR = (15, 23, 42)          # #0f172a
PRIMARY_COLOR = (56, 189, 248)   # #38bdf8 — 광선, 수평선
ACCENT_COLOR = (244, 114, 182)   # #f472b6 — 태양
ACCENT_GLOW = (244, 114, 182, 60)  # #f472b6 25% — 태양 글로우

# Android mipmap 크기
SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

PLAY_STORE_SIZE = 512
MASTER_SIZE = 1024


def _draw_dawn(draw: "ImageDraw.Draw", img: "Image.Image", size: int):
    """떠오르는 태양(Dawn) 심볼을 그린다."""
    cx = size // 2
    horizon_y = int(size * 0.62)  # 수평선 위치

    # --- 태양 글로우 (큰 반원, 반투명) ---
    glow_r = int(size * 0.28)
    glow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.ellipse(
        [cx - glow_r, horizon_y - glow_r, cx + glow_r, horizon_y + glow_r],
        fill=ACCENT_GLOW,
    )
    # 수평선 아래 부분을 지우기 위해 검은 사각형으로 덮기
    glow_draw.rectangle(
        [0, horizon_y, size, size],
        fill=(0, 0, 0, 0),
    )
    img_temp = Image.alpha_composite(img, glow_layer)

    # --- 태양 본체 (작은 반원, 불투명) ---
    sun_r = int(size * 0.16)
    # 반원만 그리기 위해 pieslice 사용
    draw_on = ImageDraw.Draw(img_temp)
    draw_on.pieslice(
        [cx - sun_r, horizon_y - sun_r, cx + sun_r, horizon_y + sun_r],
        start=180,
        end=360,
        fill=ACCENT_COLOR,
    )

    # --- 광선 (위쪽으로 퍼지는 선들) ---
    ray_count = 7
    ray_inner = int(size * 0.20)   # 광선 시작점 (태양 중심에서)
    ray_outer = int(size * 0.38)   # 광선 끝점
    ray_width = max(1, int(size * 0.015))

    for i in range(ray_count):
        # 180도(왼쪽)~360도(오른쪽) 사이에 균등 배분
        angle = math.pi + (math.pi / (ray_count + 1)) * (i + 1)
        x_inner = cx + int(ray_inner * math.cos(angle))
        y_inner = horizon_y + int(ray_inner * math.sin(angle))
        x_outer = cx + int(ray_outer * math.cos(angle))
        y_outer = horizon_y + int(ray_outer * math.sin(angle))

        # 광선 알파 — 중앙이 밝고 양쪽이 약간 어두움
        center_idx = ray_count // 2
        dist = abs(i - center_idx)
        alpha = max(100, 220 - dist * 30)
        ray_color = PRIMARY_COLOR + (alpha,)

        ray_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ray_draw = ImageDraw.Draw(ray_layer)
        ray_draw.line(
            [(x_inner, y_inner), (x_outer, y_outer)],
            fill=ray_color,
            width=ray_width,
        )
        img_temp = Image.alpha_composite(img_temp, ray_layer)

    # --- 수평선 ---
    line_y = horizon_y
    line_x1 = int(size * 0.15)
    line_x2 = int(size * 0.85)
    line_width = max(2, int(size * 0.02))

    horizon_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    horizon_draw = ImageDraw.Draw(horizon_layer)
    horizon_draw.line(
        [(line_x1, line_y), (line_x2, line_y)],
        fill=PRIMARY_COLOR + (200,),
        width=line_width,
    )
    img_temp = Image.alpha_composite(img_temp, horizon_layer)

    # --- 작은 장식 점 3개 (수평선 아래, 명언의 "점점점" 느낌) ---
    dot_r = max(1, int(size * 0.012))
    dot_y = int(size * 0.74)
    dot_gap = int(size * 0.06)
    dots_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dots_draw = ImageDraw.Draw(dots_layer)
    for offset in [-dot_gap, 0, dot_gap]:
        dx = cx + offset
        dots_draw.ellipse(
            [dx - dot_r, dot_y - dot_r, dx + dot_r, dot_y + dot_r],
            fill=PRIMARY_COLOR + (140,),
        )
    img_temp = Image.alpha_composite(img_temp, dots_layer)

    return img_temp


APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
RES_DIR = os.path.join(APP_DIR, "android", "app", "src", "main", "res")


def draw_icon(size: int, round_mask: bool = False) -> Image.Image:
    """아이콘 이미지를 생성한다."""
    img = Image.new("RGBA", (size, size), BG_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    # 떠오르는 태양 그리기
    img = _draw_dawn(draw, img, size)

    # 라운드 마스크
    if round_mask:
        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, size - 1, size - 1], fill=255)
        bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        img = Image.composite(img, bg, mask)
    else:
        # 둥근 모서리 (크기의 22%)
        corner_radius = int(size * 0.22)
        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=corner_radius, fill=255)
        bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        img = Image.composite(img, bg, mask)

    return img


def main():
    # Android mipmap 디렉토리에 저장
    for dir_name, size in SIZES.items():
        dir_path = os.path.join(RES_DIR, dir_name)
        os.makedirs(dir_path, exist_ok=True)

        # 일반 아이콘
        icon = draw_icon(size, round_mask=False)
        icon.save(os.path.join(dir_path, "ic_launcher.png"), "PNG")

        # 라운드 아이콘
        icon_round = draw_icon(size, round_mask=True)
        icon_round.save(os.path.join(dir_path, "ic_launcher_round.png"), "PNG")

        print(f"  {dir_name}: {size}x{size} px")

    # Play Store용 512x512
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(docs_dir, exist_ok=True)
    store_icon = draw_icon(PLAY_STORE_SIZE, round_mask=False)
    store_icon.save(os.path.join(docs_dir, "icon_512.png"), "PNG")
    print(f"  Play Store: 512x512 px")

    # 마스터 1024x1024
    master_icon = draw_icon(MASTER_SIZE, round_mask=False)
    master_icon.save(os.path.join(docs_dir, "icon_1024.png"), "PNG")
    print(f"  Master: 1024x1024 px")

    print("\nDone!")


if __name__ == "__main__":
    main()
