import os
import pygame
from game.constants import SPRITE_PATH, TILES_PATH, TILE_SIZE, BASE_DIR


_spritesheet = None
_tiles_sheet = None
_separate_cache = {}


def get_spritesheet():
    global _spritesheet
    if _spritesheet is None:
        _spritesheet = pygame.image.load(SPRITE_PATH).convert_alpha()
    return _spritesheet


def get_tiles_sheet():
    global _tiles_sheet
    if _tiles_sheet is None:
        _tiles_sheet = pygame.image.load(TILES_PATH).convert_alpha()
    return _tiles_sheet


def get_tile(col, row, tile_size=TILE_SIZE, scale=3):
    sheet = get_spritesheet()
    rect = pygame.Rect(col * tile_size, row * tile_size, tile_size, tile_size)
    tile = sheet.subsurface(rect).copy()
    if scale != 1:
        tile = pygame.transform.scale(tile, (tile_size * scale, tile_size * scale))
    return tile


def get_tile_rect(x, y, w, h, scale=3):
    sheet = get_spritesheet()
    rect = pygame.Rect(x, y, w, h)
    tile = sheet.subsurface(rect).copy()
    if scale != 1:
        tile = pygame.transform.scale(tile, (w * scale, h * scale))
    return tile


def get_floor_tile(col, row, tile_size=TILE_SIZE, scale=3):
    sheet = get_tiles_sheet()
    rect = pygame.Rect(col * tile_size, row * tile_size, tile_size, tile_size)
    tile = sheet.subsurface(rect).copy()
    if scale != 1:
        tile = pygame.transform.scale(tile, (tile_size * scale, tile_size * scale))
    return tile


def get_separate_sprite(name, scale=3):
    cache_key = (name, scale)
    if cache_key not in _separate_cache:
        path = os.path.join(BASE_DIR, "assets", "office_assets", "separately_assets", name)
        img = pygame.image.load(path).convert_alpha()
        if scale != 1:
            w, h = img.get_size()
            img = pygame.transform.scale(img, (w * scale, h * scale))
        _separate_cache[cache_key] = img
    return _separate_cache[cache_key]


def draw_floor(surface, tile_col=0, tile_row=0):
    tile = get_floor_tile(tile_col, tile_row)
    tw, th = tile.get_size()
    for x in range(0, surface.get_width(), tw):
        for y in range(0, surface.get_height(), th):
            surface.blit(tile, (x, y))
