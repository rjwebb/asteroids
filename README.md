asteroids
=========

An Asteroids clone written in Python with Pygame.

Press up/down/left/right to move around and A to fire.

Teleo-reactive programming
--------------------------

If you have QuLog and Pedro installed, you can write a teleo-reactive program that plays the game for you.

Unfortunately, due to the fact that it's a simple asteroids game the kinds of percepts that you get are a bit boring (stuff like 'I can see an asteroid 100 pixels in front of the ship').
An example QuLog program is included (asteroids.qlg), but if you want to learn more about QuLog and Pedro you should check out the website: http://staff.itee.uq.edu.au/pjr/HomePages/QulogHome.html

To run asteroids in TR mode:

1. Open a shell, run 'pedro'
2. Open another shell in this directory, run 'python asteroids.py'
3. Open another shell in this directory, run 'qulog'
    1. A prompt should appear. Enter the command 'consult asteroids.'
    2. Enter the command 'teleor.' (to begin teleo-reactive mode).
    3. Enter the command 'go().' (to start the actual TR program).

DISCLAIMER: this is all a work-in-progress, run at your own risk