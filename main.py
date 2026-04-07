import pygame
from game.scene_manager import SceneManager
from game.constants import WIDTH, HEIGHT, FPS, TITLE


def main():
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    # Musica de fondo
    import os
    music_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "musica.mp3")
    if os.path.exists(music_path):
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(0.3)
        pygame.mixer.music.play(-1)
    clock = pygame.time.Clock()

    manager = SceneManager(screen)
    manager.load_scene("intro")

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                running = False
            manager.handle_event(event)

        manager.update(dt)
        manager.draw()
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
