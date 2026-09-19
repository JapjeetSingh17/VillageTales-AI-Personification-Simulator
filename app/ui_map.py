"""
Village Tales — Map Rendering & NPC Proximity Detection
Handles the Duskendale village map with NPC spatial positions and avatar portrait rendering.
"""

import os
import math
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont

from .graph import NPC_ROSTER

MAP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "map.jpg"))
AVATAR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "avatars"))

MAP_WIDTH = 2400
MAP_HEIGHT = 1750

DEFAULT_PLAYER_POS = (1065, 925)  # Crossroads Well / Town Square
PROXIMITY_THRESHOLD = 175

# In-memory caches for high-speed map generation (< 20ms)
_base_map_cache: Optional[Image.Image] = None
_avatar_cache: Dict[str, Image.Image] = {}
_circular_mask_cache: Dict[int, Image.Image] = {}


def get_base_map() -> Image.Image:
    """Load and cache the base map at the optimized 2400x1750 resolution."""
    global _base_map_cache
    if _base_map_cache is None:
        if os.path.exists(MAP_PATH):
            full_img = Image.open(MAP_PATH)
            _base_map_cache = full_img.resize((MAP_WIDTH, MAP_HEIGHT), Image.Resampling.LANCZOS).convert("RGBA")
        else:
            _base_map_cache = Image.new("RGBA", (MAP_WIDTH, MAP_HEIGHT), color=(30, 41, 59, 255))
    return _base_map_cache


def get_circular_mask(diameter: int) -> Image.Image:
    """Cache circular alpha masks for avatar tokens."""
    if diameter not in _circular_mask_cache:
        mask = Image.new("L", (diameter, diameter), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, diameter, diameter), fill=255)
        _circular_mask_cache[diameter] = mask
    return _circular_mask_cache[diameter]


def get_avatar_token(filename: str, diameter: int) -> Optional[Image.Image]:
    """Load, scale, and mask an avatar image into a circular portrait."""
    cache_key = f"{filename}_{diameter}"
    if cache_key in _avatar_cache:
        return _avatar_cache[cache_key]

    path = os.path.join(AVATAR_DIR, filename)
    if not os.path.exists(path):
        return None

    try:
        av = Image.open(path).convert("RGBA")
        av = av.resize((diameter, diameter), Image.Resampling.LANCZOS)
        mask = get_circular_mask(diameter)
        circular_av = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
        circular_av.paste(av, (0, 0), mask)
        _avatar_cache[cache_key] = circular_av
        return circular_av
    except Exception as e:
        print(f"[Avatar Load Error] {filename}: {e}")
        return None


def get_closest_npc(player_pos: Tuple[int, int]):
    """Find the closest NPC to the player within PROXIMITY_THRESHOLD distance."""
    px, py = player_pos
    closest_npc = None
    min_dist = float("inf")

    for npc_id, npc in NPC_ROSTER.items():
        nx, ny = npc["pos"]
        dist = math.hypot(px - nx, py - ny)
        if dist < min_dist:
            min_dist = dist
            closest_npc = (npc_id, npc, dist)

    if closest_npc and min_dist <= PROXIMITY_THRESHOLD:
        return closest_npc[0], closest_npc[1], min_dist
    return None, None, min_dist


def render_game_map(player_pos: Tuple[int, int]) -> Image.Image:
    """
    Render the Duskendale map with authentic NPC avatar portrait tokens,
    proximity range rings, name badges, and the player compass marker.
    """
    base = get_base_map()
    img = base.copy()
    draw = ImageDraw.Draw(img, "RGBA")

    # Fonts
    try:
        font_large = ImageFont.truetype("Arial.ttf", 26)
        font_name = ImageFont.truetype("Arial.ttf", 22)
        font_badge = ImageFont.truetype("Arial.ttf", 16)
    except Exception:
        font_large = ImageFont.load_default()
        font_name = font_large
        font_badge = font_large

    active_npc_id, _, _ = get_closest_npc(player_pos)

    # Avatar Token Dimensions
    AVATAR_RADIUS = 54
    AVATAR_DIAMETER = AVATAR_RADIUS * 2
    PROXIMITY_RADIUS = PROXIMITY_THRESHOLD

    for npc_id, npc in NPC_ROSTER.items():
        nx, ny = npc["pos"]
        color = npc.get("color", "#6366f1")
        is_active = (npc_id == active_npc_id)

        # 1. Proximity range ring
        if is_active:
            # Active NPC has glowing multi-layered proximity circle
            draw.ellipse(
                [nx - PROXIMITY_RADIUS, ny - PROXIMITY_RADIUS, nx + PROXIMITY_RADIUS, ny + PROXIMITY_RADIUS],
                outline="#facc15",
                width=4
            )
        else:
            # Subtle interaction zone
            draw.ellipse(
                [nx - PROXIMITY_RADIUS, ny - PROXIMITY_RADIUS, nx + PROXIMITY_RADIUS, ny + PROXIMITY_RADIUS],
                outline=color,
                width=2
            )

        # 2. Outer backing shadow / bezel
        bezel_extra = 7 if is_active else 5
        outer_outline = "#facc15" if is_active else color
        outer_width = 5 if is_active else 3
        draw.ellipse(
            [nx - AVATAR_RADIUS - bezel_extra, ny - AVATAR_RADIUS - bezel_extra,
             nx + AVATAR_RADIUS + bezel_extra, ny + AVATAR_RADIUS + bezel_extra],
            fill=(10, 15, 30, 220),
            outline=outer_outline,
            width=outer_width
        )

        # 3. Render circular NPC Avatar
        avatar_img = get_avatar_token(npc.get("avatar", ""), AVATAR_DIAMETER)
        if avatar_img:
            img.paste(avatar_img, (nx - AVATAR_RADIUS, ny - AVATAR_RADIUS), avatar_img)
        else:
            # Fallback if avatar file is missing
            draw.ellipse(
                [nx - AVATAR_RADIUS, ny - AVATAR_RADIUS, nx + AVATAR_RADIUS, ny + AVATAR_RADIUS],
                fill=color,
                outline="#ffffff",
                width=2
            )

        # 4. Ring highlight over the avatar edge
        inner_ring_color = "#facc15" if is_active else "#ffffff"
        draw.ellipse(
            [nx - AVATAR_RADIUS, ny - AVATAR_RADIUS, nx + AVATAR_RADIUS, ny + AVATAR_RADIUS],
            outline=inner_ring_color,
            width=2
        )

        # 5. Name tag pill
        label = npc["name"]
        bbox = draw.textbbox((0, 0), label, font=font_name)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        pad_x = 16
        pad_y = 6
        pill_w = tw + pad_x * 2
        pill_h = th + pad_y * 2

        px1 = nx - pill_w // 2
        py1 = ny + AVATAR_RADIUS + 8
        px2 = px1 + pill_w
        py2 = py1 + pill_h

        pill_bg = (15, 23, 42, 235) if not is_active else (30, 27, 75, 245)
        pill_border = "#facc15" if is_active else color
        draw.rounded_rectangle([px1, py1, px2, py2], radius=10, fill=pill_bg, outline=pill_border, width=2)
        draw.text((px1 + pad_x, py1 + pad_y - 2), label, fill="#ffffff", font=font_name)

        # 6. Active indicator badge if currently in range
        if is_active:
            active_text = "✨ IN RANGE — TALK"
            abbox = draw.textbbox((0, 0), active_text, font=font_badge)
            atw = abbox[2] - abbox[0]
            ath = abbox[3] - abbox[1]
            apx1 = nx - atw // 2 - 10
            apy1 = ny - AVATAR_RADIUS - ath - 18
            apx2 = nx + atw // 2 + 10
            apy2 = apy1 + ath + 10
            draw.rounded_rectangle([apx1, apy1, apx2, apy2], radius=8, fill=(234, 179, 8, 240), outline="#ffffff", width=2)
            draw.text((apx1 + 10, apy1 + 4), active_text, fill="#0f172a", font=font_badge)

    # ==================== Player Marker ====================
    px, py = player_pos
    PLAYER_R = 30

    # Glow ring
    draw.ellipse([px - PLAYER_R - 5, py - PLAYER_R - 5, px + PLAYER_R + 5, py + PLAYER_R + 5],
                 fill=(10, 25, 18, 210), outline="#22c55e", width=4)
    # Main token
    draw.ellipse([px - PLAYER_R, py - PLAYER_R, px + PLAYER_R, py + PLAYER_R],
                 fill="#22c55e", outline="#ffffff", width=3)
    # Center core
    draw.ellipse([px - 9, py - 9, px + 9, py + 9], fill="#ffffff")

    # Player label badge - position away from closest NPC to prevent overlap
    p_label = "YOU (PLAYER)"
    p_bbox = draw.textbbox((0, 0), p_label, font=font_badge)
    ptw = p_bbox[2] - p_bbox[0]
    pth = p_bbox[3] - p_bbox[1]

    # If player is below an active/close NPC, position badge below the player token
    badge_below = False
    if active_npc_id and active_npc_id in NPC_ROSTER:
        active_ny = NPC_ROSTER[active_npc_id]["pos"][1]
        if py > active_ny:
            badge_below = True

    if badge_below:
        b_y1 = py + PLAYER_R + 8
        b_y2 = b_y1 + pth + 12
    else:
        b_y2 = py - PLAYER_R - 8
        b_y1 = b_y2 - pth - 12

    b_x1 = px - ptw // 2 - 12
    b_x2 = px + ptw // 2 + 12

    draw.rounded_rectangle(
        [b_x1, b_y1, b_x2, b_y2],
        radius=8,
        fill=(34, 197, 94, 240),
        outline="#ffffff",
        width=2
    )
    draw.text((px - ptw // 2, b_y1 + 5), p_label, fill="#ffffff", font=font_badge)

    return img
