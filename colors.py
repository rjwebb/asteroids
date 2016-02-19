import pygame

redColor = pygame.Color(255,0,0)
greenColor = pygame.Color(0,255,0)
darkGreenColor = pygame.Color(0,102,0)
blueColor = pygame.Color(0,0,255)
whiteColor = pygame.Color(255,255,255)
blackColor = pygame.Color(0,0,0)


nightColourPalette = { 
    "background" : blackColor, 
    "spaceship" : greenColor, 
    "asteroid" : whiteColor, 
    "bullet" : redColor,
    "display" : greenColor
}

dayColourPalette = {
    "background" : whiteColor, 
    "spaceship" : darkGreenColor, 
    "asteroid" : blueColor, 
    "bullet" : redColor,
    "display" : darkGreenColor
}



