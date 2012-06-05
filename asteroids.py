# Asteroids game!!
import pygame, sys, math, random
from pygame.locals import *

pygame.init()
fpsClock = pygame.time.Clock()

redColor = pygame.Color(255,0,0)
greenColor = pygame.Color(0,255,0)
blueColor = pygame.Color(0,0,255)
blackColor = pygame.Color(0,0,0)

windowSurfObj = pygame.display.set_mode((640,480))

pygame.display.set_caption("Asteroids!")

windowSurfObj.fill(blackColor)

def translateVectors(vec,x,y):
    return [[v[0]+x,v[1]+y] for v in vec]

def mult2DVecAndMatrix(vec,matrix):
    x,y = vec
    return [matrix[0][0]*vec[0] + matrix[0][1]*vec[1], matrix[1][0]*vec[0] + matrix[1][1]*vec[1]]

def check (font, name):
    bold = "not bold"
    if font.get_bold ():
        bold = "bold"
    print "%s at %s is %s" % (name, font, bold)

class Game(object):
    def __init__(self,surface):
        self.surface = surface
        self.currentWorld = IntroWorld(self,self.surface)

    def startGame(self):
        self.currentWorld = GameWorld(self,self.surface)

    def youWin(self):
        self.currentWorld = YouWinWorld(self,self.surface)

    def youLose(self):
        self.currentWorld = YouLoseWorld(self,self.surface)

class PausedWorld(object):
    def __init__(self,game,surface):
        self.game = game
        self.surface = surface

    def handleEvents(self,events):
        for event in events:
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                self.game.startGame()

    def update(self):
        pass

class TitleWorld(PausedWorld):
    def __init__(self,game,surface,text):
        super(TitleWorld,self).__init__(game,surface)
        
        self.titleFont = pygame.font.Font(None,36)
        self.drawTitle(text)

    def drawTitle(self,text):
        self.surface.blit(self.titleFont.render(text, False, greenColor),(200,200))

class IntroWorld(TitleWorld):
    def __init__(self,game,surface):
        super(IntroWorld,self).__init__(game,surface,"Asteroids!! By Bob Webb")
        

class YouLoseWorld(TitleWorld):
    def __init__(self,game,surface):
        super(YouLoseWorld,self).__init__(game,surface,"You Lose!!! Loser. :D")

class YouWinWorld(TitleWorld):
    def __init__(self,game,surface):
        super(YouWinWorld,self).__init__(game,surface,"You Win!!! Yay.")

class GameWorld(object):
    def __init__(self,game,surface):
        self.game = game
        self.surface = surface
        self.spaceship = Spaceship(self,(320,240))
        self.bullets = []
        self.asteroids = []
        self.populateAsteroids()
        self.points = 0

        self.scoreFont = pygame.font.Font(None, 14)


    def populateAsteroids(self):
        numAsteroids = 10
        for x in range(numAsteroids):
            self.addAsteroid(Asteroid(self,(random.randint(0,self.surface.get_width()),random.randint(0,self.surface.get_height())),30))
    
    def addBullet(self,bullet):
        self.bullets.append(bullet)

    def addAsteroid(self,asteroid):
        self.asteroids.append(asteroid)

    def handleEvents(self,events):
        for event in events:
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.event.post(pygame.event.Event(QUIT))
                elif event.key == K_LEFT:
                    self.spaceship.isRotatingAntiClockwise = True
                elif event.key == K_RIGHT:
                    self.spaceship.isRotatingClockwise = True
                elif event.key == K_UP:
                    self.spaceship.isMovingForwards = True
                elif event.key == K_DOWN:
                    self.spaceship.isMovingBackwards = True
                elif event.key == K_a:
                    self.spaceship.isShooting = True
            elif event.type == KEYUP:
                if event.key == K_LEFT:
                    self.spaceship.isRotatingAntiClockwise = False
                elif event.key == K_RIGHT:
                    self.spaceship.isRotatingClockwise = False
                elif event.key == K_UP:
                    self.spaceship.isMovingForwards = False
                elif event.key == K_DOWN:
                    self.spaceship.isMovingBackwards = False
                elif event.key == K_a:
                    self.spaceship.isShooting = False

    def update(self):
        self.surface.fill(blackColor)
        
        self.spaceship.update()

        self.surface.blit(self.scoreFont.render("Current points: "+str(self.points), False, greenColor),(20,20))
        
        for i,v in enumerate(self.spaceship.shape):
            for j,a in enumerate(self.asteroids):
                dist = math.sqrt((v[0]+self.spaceship.x-a.x)**2+(v[1]+self.spaceship.y-a.y)**2)
                if dist < a.size:
                    print "YOU LOOOOSE"
                    self.game.youLose()
        
        for i,b in enumerate(self.bullets):
            if b.age == 0:
                self.bullets.remove(b)
            else:            
                for j,a in enumerate(self.asteroids):
                    dist = math.sqrt((b.x-a.x)**2+(b.y-a.y)**2)
                    if dist < a.size: # asteroid hit!!!!
                        self.bullets.remove(b)
                        self.points += 10
                        if a.size > 10:
                            for x in range(3):
                                self.addAsteroid(Asteroid(self,(a.x,a.y),a.size/2))
                        self.asteroids.remove(a)
                        self.points += 10
                        break
                b.update()

        if self.asteroids == []:
            self.game.youWin()
        else:
            for i,x in enumerate(self.asteroids):
                x.update()


class Actor(object):
    def __init__(self,world,(x,y),(speed,direction)):
        self.world = world
        self.x = x
        self.y = y

        self.speed = speed
        self.direction = direction

        self.vx = self.speed * math.cos(self.direction)
        self.vy = self.speed * math.sin(self.direction)

    def draw(self):
        raise NotImplementedError()

    def update(self):
        self.move()
        self.draw()

    def move(self):
        self.x = (self.x + self.vx) % self.world.surface.get_width()
        self.y = (self.y + self.vy) % self.world.surface.get_height()


class Spaceship(object):
    def __init__(self,world, (x,y)):
        self.world = world
        self.x = x
        self.y = y

        self.vx = 0
        self.vy = 0

        self.ax = 0
        self.ay = 0
        
        self.shape =    [[ 10.0 , 10.0],
                         [-10.0 , 10.0],
                         [ 0.0  ,-20.0]]
        
        # code for handling translation!
        self.acc = 0.2
        self.isMovingForwards = False
        self.isMovingBackwards = False
        self.decelRatio = 0.99
        
        # code for handling rotation!
        self.rads = math.pi/40
        self.direction = 1.5*math.pi
        self.isRotatingClockwise = False
        self.isRotatingAntiClockwise = False
        self.clockwiseRotMatrix = [[math.cos(self.rads),-math.sin(self.rads)],
                              [math.sin(self.rads), math.cos(self.rads)]]

        self.antiClockwiseRotMatrix = [[math.cos(-self.rads),-math.sin(-self.rads)],
                               [math.sin(-self.rads), math.cos(-self.rads)]]

        self.isShooting = False
        
    def draw(self):
        pygame.draw.polygon(self.world.surface,greenColor,translateVectors(self.shape,self.x,self.y),1)
    
    def update(self):
        if self.isRotatingClockwise:
            self.rotClockwise()
        elif self.isRotatingAntiClockwise:
            self.rotAntiClockwise()
        
        if self.isMovingForwards:
            self.forwardsForce()
        elif self.isMovingBackwards:
            self.backwardsForce()

        if self.isShooting:
            self.shoot()

        self.decelerate()
        
        self.move()
        self.draw()
        
        
    def rotClockwise(self):
        self.rotateWithMatrix(self.clockwiseRotMatrix)
        self.direction += self.rads
        self.calcAcceleration()
        
    def rotAntiClockwise(self):
        self.rotateWithMatrix(self.antiClockwiseRotMatrix)
        self.direction -= self.rads
        self.calcAcceleration()

    def calcAcceleration(self):
        self.ax = self.acc * math.cos(self.direction)
        self.ay = self.acc * math.sin(self.direction)

    def forwardsForce(self):
        self.vx += self.ax
        self.vy += self.ay

    def backwardsForce(self):
        self.vx -= self.ax
        self.vy -= self.ay

    def decelerate(self):
        self.vx = self.vx * self.decelRatio
        self.vy = self.vy * self.decelRatio

    def move(self):
        self.x = (self.x + self.vx) % self.world.surface.get_width()
        self.y = (self.y + self.vy) % self.world.surface.get_height()

    def shoot(self):
        self.world.addBullet(Bullet(self.world,(self.x,self.y),self.direction))

    def rotateWithMatrix(self, matrix):
        self.shape = [mult2DVecAndMatrix(x,matrix) for x in self.shape]


class Bullet(Actor):
    def __init__(self,world,(x,y),direction):
        super(Bullet,self).__init__(world,(x,y),(15,direction))

        self.age = 20
        self.length = 10

    def draw(self):
        pygame.draw.line(self.world.surface, redColor, (self.x,self.y),(self.x + self.length * math.cos(self.direction), self.y + self.length * math.sin(self.direction)))

    def update(self):
        super(Bullet,self).update()
        self.age -= 1


class Asteroid(Actor):
    def __init__(self,world,(x,y),size):
        super(Asteroid,self).__init__(world,(x,y),(1,random.uniform(0,math.pi*2)))
        
        self.size = size

    def draw(self):
        pygame.draw.circle(self.world.surface, blueColor, (int(self.x),int(self.y)),self.size,1)

game = Game(windowSurfObj)

while True:
    game.currentWorld.handleEvents(pygame.event.get())
                
    
    game.currentWorld.update()
    
    pygame.display.update()
    fpsClock.tick(60)
