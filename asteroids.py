#!/bin/python
# Asteroids game!!

"""

Percepts:
see(Thing, Direction, Distance)
Thing is only going to be "asteroid" in this case
Direction can be left, right, centre or dead_centre
Distance is how far away the thing is

facing_direction(Direction)
the absolute direction that the spaceship is facing in (in radians)

speed(Speed)
the velocity at which the spaceship is travelling, in the direction given by facing_direction

"""

# game stuff
import pygame
from pygame.locals import *
import sys
import math
import random
import numpy as np

# pedro stuff
import pedroclient

import threading
import Queue 



# constants
FRAMES_PER_SECOND = 50

pygame.init()

fpsClock = pygame.time.Clock()

redColor = pygame.Color(255,0,0)
greenColor = pygame.Color(0,255,0)
darkGreenColor = pygame.Color(0,102,0)
blueColor = pygame.Color(0,0,255)
whiteColor = pygame.Color(255,255,255)
blackColor = pygame.Color(0,0,0)

windowSurfObj = pygame.display.set_mode((640,480))

pygame.display.set_caption("Asteroids")

windowSurfObj.fill(blackColor)

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

CURRENT_COLOURS = dayColourPalette
#CURRENT_COLOURS = nightColourPalette

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

def myround(x, prec=2, base=.05):
  return round(base * round(float(x)/base),prec)

def format_percept( (functor, args) ):
    arg_str = ",".join([str(a) for a in args])
    return functor + "(" + arg_str + ")"

class Game(object):
    def __init__(self,surface,easyMode=False, splashScreen=True):
        self.surface = surface
        self.easyMode = easyMode
        self.splashScreen = splashScreen

        if self.splashScreen:
            self.currentWorld = IntroWorld(self,self.surface)
        else:
            self.currentWorld = GameWorld(self,self.surface,easyMode=self.easyMode)

    def startGame(self):
        self.currentWorld = GameWorld(self,self.surface,easyMode=self.easyMode)

    def youWin(self):
        if self.splashScreen:
            self.currentWorld = YouWinWorld(self,self.surface)
        else:
            self.currentWorld = GameWorld(self,self.surface,easyMode=self.easyMode)

    def youLose(self):
        if self.splashScreen:
            self.currentWorld = YouLoseWorld(self,self.surface)
        else:
            self.currentWorld = GameWorld(self,self.surface,easyMode=self.easyMode)

class PausedWorld(object):
    def __init__(self,game,surface):
        self.game = game
        self.surface = surface

    def handleEvents(self,events, actions):
        for event in events:
            if event.type == QUIT:
                actions.add("quit")
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.event.post(pygame.event.Event(QUIT))
                actions.add("start_game")

        return actions

    def handleActions(self,actions):
        if "quit" in actions:
            pygame.quit()
            sys.exit()
        
        if "start_game" in actions:
            self.game.startGame()


    def update(self):
        pass

class TitleWorld(PausedWorld):
    def __init__(self,game,surface,text):
        super(TitleWorld,self).__init__(game,surface)

        self.titleFont = pygame.font.Font(None,36)
        self.drawTitle(text)

    def drawTitle(self,text):
        self.surface.blit(self.titleFont.render(text, False, CURRENT_COLOURS["display"]),(200,200))

class IntroWorld(TitleWorld):
    def __init__(self,game,surface):
        super(IntroWorld,self).__init__(game,surface,"Asteroids! By Bob Webb")


class YouLoseWorld(TitleWorld):
    def __init__(self,game,surface):
        super(YouLoseWorld,self).__init__(game,surface,"You Lose!")

class YouWinWorld(TitleWorld):
    def __init__(self,game,surface):
        super(YouWinWorld,self).__init__(game,surface,"You Win! Congratulations.")

class GameWorld(object):
    DEAD_CENTRE_THRESHOLD = math.pi / 64
    CENTRE_THRESHOLD = math.pi / 16
    #SIDE_THRESHOLD = math.pi / 6
    SIDE_THRESHOLD = math.pi / 4

    def __init__(self,game,surface, easyMode=False):
        self.game = game
        self.surface = surface
        self.easyMode = easyMode

        self.spaceship = Spaceship(self,(320,240))
        self.bullets = []
        self.asteroids = []
        if not self.easyMode:
            self.populateAsteroids()
        self.points = 0

        self.scoreFont = pygame.font.Font(None, 18)

        self.justInstantiated = True

    def populateAsteroids(self):
        numAsteroids = 5
        for _ in range(numAsteroids):
            x = random.randint(0,self.surface.get_width())
            y = random.randint(0,self.surface.get_height())

            size = 30

            self.addAsteroid( Asteroid(self, (x, y), size) )

    def addBullet(self,bullet):
        self.bullets.append(bullet)

    def addAsteroid(self,asteroid):
        self.asteroids.append(asteroid)

    def handleEvents(self, events, actions):
        if self.justInstantiated:
            actions = set([])
            self.justInstantiated = False

        for event in events:
            if event.type == QUIT:
                actions.add("quit")
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.event.post(pygame.event.Event(QUIT))
                elif event.key == K_LEFT:
                    actions.add("turn_left")
                elif event.key == K_RIGHT:
                    actions.add("turn_right")
                elif event.key == K_UP:
                    actions.add("move_forward")
                elif event.key == K_DOWN:
                    actions.add("move_backward")
                elif event.key == K_a:
                    actions.add("shoot")
                elif event.key == K_c:
                    actions.add("clear")
            elif event.type == KEYUP:
                if event.key == K_LEFT:
                    actions.discard("turn_left")
                elif event.key == K_RIGHT:
                    actions.discard("turn_right")
                elif event.key == K_UP:
                    actions.discard("move_forward")
                elif event.key == K_DOWN:
                    actions.discard("move_backward")
                elif event.key == K_a:
                    actions.discard("shoot")
                elif event.key == K_c:
                    actions.discard("clear")
        return actions

    def handleActions(self, actions):
        if "quit" in actions:
            pygame.quit()
            sys.exit()

        if "turn_left" in actions:
            self.spaceship.isRotatingAntiClockwise = True
            self.spaceship.isRotatingClockwise = False
        elif "turn_right" in actions:
            self.spaceship.isRotatingAntiClockwise = False
            self.spaceship.isRotatingClockwise = True    
        else:
            self.spaceship.isRotatingAntiClockwise = False
            self.spaceship.isRotatingClockwise = False

        if "move_forward" in actions:
            self.spaceship.isMovingForwards = True
            self.spaceship.isMovingBackwards = False
        elif "move_backward" in actions:
            self.spaceship.isMovingForwards = False
            self.spaceship.isMovingBackwards = True
        else:
            self.spaceship.isMovingForwards = False
            self.spaceship.isMovingBackwards = False

        if "shoot" in actions:
            self.spaceship.isShooting = True
        else:
            self.spaceship.isShooting = False


    def update(self):
        self.surface.fill(CURRENT_COLOURS["background"])

        self.spaceship.update()

        self.surface.blit(self.scoreFont.render("Current points: "+str(self.points), False, CURRENT_COLOURS["display"]),(20,20))

        for i,v in enumerate(self.spaceship.shape):
            for j,a in enumerate(self.asteroids):
                dist = math.sqrt((v[0]+self.spaceship.x-a.x)**2+(v[1]+self.spaceship.y-a.y)**2)
                if dist < a.size:
                    #print "YOU LOOOOSE"
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

        if self.asteroids == [] and not self.easyMode:
            self.game.youWin()
        else:
            for i,x in enumerate(self.asteroids):
                x.update()

    def sense(self):
        # generate percepts for QuLog or the like
        percepts = set()
        ship_direction = self.spaceship.direction
        speed = myround(self.spaceship.getSpeed(), base=0.1)

        for j,a in enumerate(self.asteroids):
            dx = a.x - self.spaceship.x
            dy = a.y - self.spaceship.y

            dist = math.sqrt((dx)**2+(dy)**2)

            asteroid_direction = np.arctan2(dy, dx) % (math.pi * 2)
            relative_direction = (asteroid_direction - ship_direction) % (math.pi * 2)

            # can the spaceship see the asteroid?
            if dist > 300 or \
               (relative_direction > GameWorld.SIDE_THRESHOLD and relative_direction < math.pi * 2 - GameWorld.SIDE_THRESHOLD):
                # behind / not seen
                pass
            else:
                # then it is seen
                # translate these pi values into something more human-readable
                if ( relative_direction <= GameWorld.DEAD_CENTRE_THRESHOLD and relative_direction >= 0) or \
                    (relative_direction >= math.pi * 2 - GameWorld.DEAD_CENTRE_THRESHOLD and relative_direction < math.pi * 2):
                    # dead centre
                    percept_direction = "dead_centre"
                elif ( relative_direction <= GameWorld.CENTRE_THRESHOLD and relative_direction >= 0) or \
                    (relative_direction >= math.pi * 2 - GameWorld.CENTRE_THRESHOLD and relative_direction < math.pi * 2):
                    # centre
                    percept_direction = "centre"
                elif relative_direction > GameWorld.CENTRE_THRESHOLD and relative_direction <= GameWorld.SIDE_THRESHOLD:
                    # right
                    percept_direction = "right"
                elif relative_direction < math.pi * 2 - GameWorld.CENTRE_THRESHOLD and relative_direction >= math.pi * 2 - GameWorld.SIDE_THRESHOLD:
                    # left
                    percept_direction = "left"

                percepts.add( ("see", ("asteroid", percept_direction, int(dist))) )
                # add percept

        percepts.add( ("facing_direction",(ship_direction,)) )
        percepts.add( ("speed", (speed,)) )

        return percepts


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
        self.rads = math.pi/20
        self.direction = 1.5*math.pi
        self.isRotatingClockwise = False
        self.isRotatingAntiClockwise = False
        self.clockwiseRotMatrix = [[math.cos(self.rads),-math.sin(self.rads)],
                              [math.sin(self.rads), math.cos(self.rads)]]

        self.antiClockwiseRotMatrix = [[math.cos(-self.rads),-math.sin(-self.rads)],
                               [math.sin(-self.rads), math.cos(-self.rads)]]

        self.isShooting = False

        self.calcAcceleration()

    def draw(self):
        pygame.draw.polygon(self.world.surface,CURRENT_COLOURS["spaceship"],translateVectors(self.shape,self.x,self.y),0)

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

    def getSpeed(self):
        return math.sqrt(self.vx * self.vx + self.vy * self.vy)

    def rotClockwise(self):
        self.rotateWithMatrix(self.clockwiseRotMatrix)
        self.direction = (self.direction + self.rads) % (math.pi * 2)
        self.calcAcceleration()

    def rotAntiClockwise(self):
        self.rotateWithMatrix(self.antiClockwiseRotMatrix)
        self.direction = (self.direction - self.rads) % (math.pi * 2)
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
    BULLET_AGE = 20
    BULLET_LENGTH = 10

    def __init__(self,world,(x,y),direction):
        super(Bullet,self).__init__(world,(x,y),(18 + random.random() * 2,direction))

        self.age = Bullet.BULLET_AGE
        self.length = Bullet.BULLET_LENGTH

    def draw(self):
        pygame.draw.line(self.world.surface, CURRENT_COLOURS["bullet"], (self.x,self.y),(self.x + self.length * math.cos(self.direction), self.y + self.length * math.sin(self.direction)))

    def update(self):
        super(Bullet,self).update()
        self.age -= 1


class Asteroid(Actor):
    def __init__(self,world,(x,y),size):
        super(Asteroid,self).__init__(world,(x,y),(1,random.uniform(0,math.pi*2)))
        self.size = size

    def draw(self):
        pygame.draw.circle(self.world.surface, CURRENT_COLOURS["asteroid"], (int(self.x),int(self.y)),self.size,1)


DELAY = 500

# In this case we want to respond in some way immediately a message arrives
# We do this below using a thread. Depending on the application this might
# instead create an event.
# The other approach (see Pedro documentation on Python API) is to set up
# the connection for async comms and then use notification_ready() to
# see if there are message to process 
class MessageThread(threading.Thread):
    def __init__(self, parent):
        self.running = True
        self.parent = parent
        threading.Thread.__init__(self)
        self.daemon = True
        
    def run(self):
        while self.running:
            p2pmsg = self.parent.client.get_term()[0]
            # get the message
            message = p2pmsg.args[2]
            print message
            if str(message) == 'initialise_':
                # get the sender address
                percepts_addr = p2pmsg.args[1]
                self.parent.set_client(percepts_addr)
            self.parent.message_queue.put(str(message)+'\n')
            
    def stop(self):
        self.running = False


def send_message(client, addr, percept_text):
    if addr is None:
#        print "No agent connected"
        pass
    else:
        # send percepts
        if client.p2p(addr, percept_text) == 0:
            print "Illegal percepts message"

def main(using_pedro=False):
    splashScreen = not using_pedro

    game = Game(windowSurfObj,easyMode=False, splashScreen=splashScreen)

    percepts = set()

    if using_pedro:
        host = "localhost"
        shell_name = "asteroids"

        client = pedroclient.PedroClient()
        c = client.register(shell_name)
        print "registered?  "+ str(c)
    
        tr_client_addr = None

        percept_actions = set()

    user_actions = set()

    while True:
        if type(game.currentWorld) is GameWorld:
            user_actions.discard("start_game")

        if using_pedro and type(game.currentWorld) is GameWorld:
            # sense
            new_percepts = game.currentWorld.sense()
            percepts = new_percepts
            
            percept_string = "[" + ",".join(map(format_percept, percepts)) + "]"
            print percept_string
            send_message(client, tr_client_addr, percept_string)

            if client.notification_ready():
                m = client.get_term()
                p2pmsg = m[0]
                message = p2pmsg.args[2]
                if str(message) == 'initialise_':
                    # get the sender address
                    percepts_addr = p2pmsg.args[1]
                    tr_client_addr = percepts_addr
                    percept_actions = set()

                elif str(message.functor) == 'controls': # was sent actions to perform
                    r = message.args[0]
                    
                    if type(r) == pedroclient.PList:
                        rec_actions = r.toList()
                        for action in rec_actions:
                            a = str(action.args[0])

                            if str(action.functor) == 'start_':
                                percept_actions.add(a)
                            elif str(action.functor) == 'stop_':
                                percept_actions.discard(a)
                    elif type(r) == pedroclient.PAtom:
                        pass
                    else:
                        raise Exception("invalid message received")

        user_actions = game.currentWorld.handleEvents(pygame.event.get(), user_actions)

        if "clear" in user_actions:
            percept_actions = set()

        if using_pedro:
            actions = percept_actions | user_actions
        else:
            actions = user_actions

        game.currentWorld.handleActions(actions)
        game.currentWorld.update()
        pygame.display.update()
        fpsClock.tick(FRAMES_PER_SECOND)

if __name__ == '__main__':
    main(using_pedro=True)
