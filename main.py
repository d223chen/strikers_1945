#!/usr/bin/env python
"""

Shows a mini game where you have to defend against enemy fighter planes.

What does it show you about pygame?

* pg.sprite, the difference between Sprite and Group.
* dirty rectangle optimization for processing for speed.
* music with pg.mixer.music, including fadeout
* sound effects with pg.Sound
* event processing, keyboard handling, QUIT handling.
* a main loop frame limited with a game clock from pg.time.Clock
* fullscreen switching.


Controls
--------

* Left and right arrows to move.
* Space bar to shoot
* f key to toggle between fullscreen.

"""

import os
import random

# import basic pygame modules
import pygame as pg
import vlc

# see if we can load more than standard BMP
if not pg.image.get_extended():
    raise SystemExit("Sorry, extended image module required")


# game constants
MAX_SHOTS = 2  # most player bullets onscreen
ENEMY_ODDS = 22  # chances a new enemy appears
BULLET_ODDS = 60  # chances a new bullet will be shot
ENEMY_RELOAD = 12  # frames between new enemies
SCREENRECT = pg.Rect(0, 0, 640, 480)
SCORE = 0

main_dir = os.path.split(os.path.abspath(__file__))[0]


def load_image(file):
    """loads an image, prepares it for play"""
    file = os.path.join(main_dir, "data", file)
    try:
        surface = pg.image.load(file)
    except pg.error:
        raise SystemExit(f'Could not load image "{file}" {pg.get_error()}')
    return surface.convert()


def load_sound(file):
    """because pygame can be be compiled without mixer."""
    if not pg.mixer:
        return None
    file = os.path.join(main_dir, "data", file)
    try:
        sound = pg.mixer.Sound(file)
        return sound
    except pg.error:
        print(f"Warning, unable to load, {file}")
    return None


# Each type of game object gets an init and an update function.
# The update function is called once per frame, and it is when each object should
# change its current position and state.
#
# The Player object actually gets a "move" function instead of update,
# since it is passed extra information about the keyboard.


class Player(pg.sprite.Sprite):
    """Representing the player as a fighter plane."""

    speed = 10
    bounce = 24
    gun_offset = -11
    images = []
    animcycle = 12

    def __init__(self):
        pg.sprite.Sprite.__init__(self, self.containers)
        self.image = self.images[0]
        self.rect = self.image.get_rect(midbottom=SCREENRECT.midbottom)
        self.reloading = 0
        self.origtop = self.rect.top
        self.facing = -1
        self.frame = 0

    def move(self, direction):
        if direction:
            self.facing = direction
        self.rect.move_ip(direction * self.speed, 0)
        self.rect = self.rect.clamp(SCREENRECT)
        if direction < 0:
            self.image = self.images[0]
        elif direction > 0:
            self.image = self.images[1]
        self.rect.top = self.origtop - (self.rect.left // self.bounce % 2)

    def gunpos(self):
        pos = self.facing * self.gun_offset + self.rect.centerx
        return pos, self.rect.top

    def update(self):
        self.frame += 1
        self.image = self.images[self.frame // self.animcycle % len(Player.images)]


class Enemy(pg.sprite.Sprite):
    """An enemy fighter plane. Moves directly down the screen"""

    speed = 5
    animcycle = 12
    images = []

    def __init__(self):
        pg.sprite.Sprite.__init__(self, self.containers)
        self.image = self.images[0]
        self.rect = self.image.get_rect(topleft=(random.random() * SCREENRECT.width, -self.image.get_height()))
        self.facing = Enemy.speed
        self.frame = 0

    def update(self):
        self.rect.move_ip(0, self.facing)
        if self.rect.top >= SCREENRECT.height:
            self.kill()
        self.frame = self.frame + 1
        self.image = self.images[self.frame // self.animcycle % len(Enemy.images)]


class Explosion(pg.sprite.Sprite):
    """An explosion. Hopefully the enemy and not the player!"""

    defaultlife = 12
    animcycle = 3
    images = []

    def __init__(self, actor):
        pg.sprite.Sprite.__init__(self, self.containers)
        self.image = self.images[0]
        self.rect = self.image.get_rect(center=actor.rect.center)
        self.life = self.defaultlife

    def update(self):
        """called every time around the game loop.

        Show the explosion surface for 'defaultlife'.
        Every game tick(update), we decrease the 'life'.

        Also we animate the explosion.
        """
        self.life = self.life - 1
        self.image = self.images[self.life // self.animcycle % 2]
        if self.life <= 0:
            self.kill()


class Shot(pg.sprite.Sprite):
    """a bullet the Player sprite fires."""

    speed = -11
    images = []

    def __init__(self, pos):
        pg.sprite.Sprite.__init__(self, self.containers)
        self.image = self.images[0]
        self.rect = self.image.get_rect(midbottom=pos)

    def update(self):
        """called every time around the game loop.

        Every tick we move the shot upwards.
        """
        self.rect.move_ip(0, self.speed)
        if self.rect.top <= -self.image.get_height():
            self.kill()


class EnemyBullet(pg.sprite.Sprite):
    """A bullet the enemy fighters shoot."""

    speed = 9
    images = []

    def __init__(self, enemy):
        pg.sprite.Sprite.__init__(self, self.containers)
        self.image = self.images[0]
        self.rect = self.image.get_rect(midbottom=enemy.rect.move(0, 5).midbottom)

    def update(self):
        """called every time around the game loop.

        Every frame we move the sprite 'rect' down.
        When it reaches the bottom we:

        - remove the bullet.
        """
        self.rect.move_ip(0, self.speed)
        if self.rect.bottom >= SCREENRECT.height:
            self.kill()


class Score(pg.sprite.Sprite):
    """to keep track of the score."""

    def __init__(self):
        pg.sprite.Sprite.__init__(self)
        self.font = pg.font.Font(None, 20)
        self.font.set_italic(1)
        self.color = "white"
        self.lastscore = -1
        self.update()
        self.rect = self.image.get_rect().move(10, 450)

    def update(self):
        """We only update the score in update() when it has changed."""
        if SCORE != self.lastscore:
            self.lastscore = SCORE
            msg = "Score: %d" % SCORE
            self.image = self.font.render(msg, 0, self.color)


def render_background(screen: pg.surface.Surface) -> pg.surface.Surface:
    bgdtile = load_image("water.png")
    background = pg.Surface(SCREENRECT.size)
    for x in range(0, SCREENRECT.width, bgdtile.get_width()):
        for y in range(0, SCREENRECT.height, bgdtile.get_height()):
            background.blit(bgdtile, (x, y))
    screen.blit(background, (0, 0))
    pg.display.flip()
    return background


def load_images():
    # Load images, assign to sprite classes
    # (do this before the classes are used, after screen setup)
    Player.images = [load_image(im) for im in ("player1.png", "player2.png", "player3.png")]
    img = load_image("explosion.gif")
    Explosion.images = [img, pg.transform.flip(img, 1, 1)]
    Enemy.images = [load_image(im) for im in ("enemy.png",)]
    EnemyBullet.images = [load_image("enemy_bullet.jpg")]
    Shot.images = [load_image("shot.png")]


def decorate_game_window():
    icon = pg.transform.scale(Enemy.images[0], (32, 32))
    pg.display.set_icon(icon)
    pg.display.set_caption("Pygame Strikers 1945")
    pg.mouse.set_visible(0)


def initialize_sounds(PLAY_MUSIC: bool):
    boom_sound = load_sound("boom.wav")
    shoot_sound = load_sound("car_door.wav")
    if PLAY_MUSIC:
        music_file = os.path.join(main_dir, "data", "in_the_name_of_strikers.mp3")
        music = vlc.MediaPlayer(music_file)
        music.play()

    return boom_sound, shoot_sound


def main(winstyle=0):
    PLAY_MUSIC = True

    # Initialize pygame
    if pg.get_sdl_version()[0] == 2:
        pg.mixer.pre_init(44100, 32, 2, 1024)
    pg.init()
    if pg.mixer and not pg.mixer.get_init():
        print("Warning, no sound")
        pg.mixer = None

    fullscreen = False
    # Set the display mode
    winstyle = 0  # |FULLSCREEN
    bestdepth = pg.display.mode_ok(SCREENRECT.size, winstyle, 32)
    screen = pg.display.set_mode(SCREENRECT.size, winstyle, bestdepth)

    load_images()
    decorate_game_window()
    background = render_background(screen)

    # load the sound effects
    boom_sound, shoot_sound = initialize_sounds(PLAY_MUSIC)

    # Initialize Game Groups
    enemies = pg.sprite.Group()
    shots = pg.sprite.Group()
    enemy_bullets = pg.sprite.Group()
    all = pg.sprite.RenderUpdates()
    lastenemy = pg.sprite.GroupSingle()

    # assign default groups to each sprite class
    Player.containers = all
    Enemy.containers = enemies, all, lastenemy
    Shot.containers = shots, all
    EnemyBullet.containers = enemy_bullets, all
    Explosion.containers = all
    Score.containers = all

    # Create Some Starting Values
    global score
    enemyreload = ENEMY_RELOAD
    clock = pg.time.Clock()

    # initialize our starting sprites
    global SCORE
    player = Player()
    Enemy()  # note, this 'lives' because it goes into a sprite group
    if pg.font:
        all.add(Score())

    # Run our main loop whilst the player is alive.
    while player.alive():

        # get input
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                return
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_f:
                    if not fullscreen:
                        print("Changing to FULLSCREEN")
                        screen_backup = screen.copy()
                        screen = pg.display.set_mode(SCREENRECT.size, winstyle | pg.FULLSCREEN, bestdepth)
                        screen.blit(screen_backup, (0, 0))
                    else:
                        print("Changing to windowed mode")
                        screen_backup = screen.copy()
                        screen = pg.display.set_mode(SCREENRECT.size, winstyle, bestdepth)
                        screen.blit(screen_backup, (0, 0))
                    pg.display.flip()
                    fullscreen = not fullscreen

        keystate = pg.key.get_pressed()

        # clear/erase the last drawn sprites
        all.clear(screen, background)

        # update all the sprites
        all.update()

        # handle player input
        direction = keystate[pg.K_RIGHT] - keystate[pg.K_LEFT]
        player.move(direction)
        firing = keystate[pg.K_SPACE]
        if not player.reloading and firing and len(shots) < MAX_SHOTS:
            Shot(player.gunpos())
            if pg.mixer:
                shoot_sound.play()
        player.reloading = firing

        # Create new enemy
        if enemyreload:
            enemyreload = enemyreload - 1
        elif not int(random.random() * ENEMY_ODDS):
            Enemy()
            enemyreload = ENEMY_RELOAD

        # shoot enemy bullets
        if lastenemy and not int(random.random() * BULLET_ODDS):
            EnemyBullet(lastenemy.sprite)

        # Detect collisions between enemies and players.
        for enemy in pg.sprite.spritecollide(player, enemies, 1):
            if pg.mixer:
                boom_sound.play()
            Explosion(enemy)
            Explosion(player)
            SCORE = SCORE + 1
            player.kill()

        # See if shots hit the enemies.
        for enemy in pg.sprite.groupcollide(enemies, shots, 1, 1).keys():
            if pg.mixer:
                boom_sound.play()
            Explosion(enemy)
            SCORE = SCORE + 1

        # See if enemy bullets hit the player.
        for enemy_bullet in pg.sprite.spritecollide(player, enemy_bullets, 1):
            if pg.mixer:
                boom_sound.play()
            Explosion(player)
            player.kill()

        # draw the scene
        dirty = all.draw(screen)
        pg.display.update(dirty)

        # cap the framerate at 40fps. Also called 40HZ or 40 times per second.
        clock.tick(40)

    if pg.mixer:
        pg.mixer.music.fadeout(1000)
    pg.time.wait(1000)


# call the "main" function if running this script
if __name__ == "__main__":
    main()
    pg.quit()
