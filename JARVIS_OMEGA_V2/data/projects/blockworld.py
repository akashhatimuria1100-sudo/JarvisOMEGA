import pygame
import numpy as np

# Initialize Pygame
pygame.init()

# Set up some constants
WIDTH, HEIGHT = 640, 480
BLOCK_SIZE = 20

# Set up the display
screen = pygame.display.set_mode((WIDTH, HEIGHT))

# Set up the clock
clock = pygame.time.Clock()

# Set up the block data
blocks = np.zeros((WIDTH // BLOCK_SIZE, HEIGHT // BLOCK_SIZE))

# Game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    # Draw everything
    screen.fill((0, 0, 0))
    for x in range(WIDTH // BLOCK_SIZE):
        for y in range(HEIGHT // BLOCK_SIZE):
            if blocks[x, y] == 1:
                pygame.draw.rect(screen, (255, 0, 0), (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
    pygame.display.flip()
    clock.tick(60)
