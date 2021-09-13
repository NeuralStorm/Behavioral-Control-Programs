from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, ListProperty
from kivy.vector import Vector
from kivy.clock import Clock
from random import randint

### Adding comment, as example git change

class PongGame(Widget):
    ball = ObjectProperty(None)
    player1 = ObjectProperty(None)
    player2 = ObjectProperty(None)

    def serve_ball(self, vel=(4, 0)):
        self.ball.center = self.center
        self.ball.velocity = vel

    def update(self, dt):
        self.ball.move()

        # Paddle bounce: 
        self.player1.bounce_ball(self.ball)
        self.player2.bounce_ball(self.ball)

        if (self.ball.y < 0) or (self.ball.top > self.height):
            self.ball.velocity_y *= -1

        if self.ball.x < self.x:
            self.player2.score += 1
            self.serve_ball(vel=(4, 0))
        
        if self.ball.x > self.width:
            self.player1.score += 1
            self.serve_ball(vel=(-4, 0))

    def on_touch_move(self, touch):
        if touch.x < self.width / 3.:
            self.player1.center_y = touch.y
        if touch.x > self.width - self.width / 3.:
            self.player2.center_y = touch.y

    def on_touch_down(self, touch):
        if touch.x < self.width / 3.:
            self.player1.center_y = touch.y
        if touch.x > self.width - self.width / 3.:
            self.player2.center_y = touch.y        

class PongPaddle(Widget):
    score = NumericProperty(0)
    color =  ListProperty([0.5, 0.5, 0.5, 1.])

    def bounce_ball(self, ball):
        if self.collide_widget(ball):
            speedup  = 1.1
            offset = 0.02 * Vector(0, ball.center_y-self.center_y)
            ball.velocity =  speedup * (offset - ball.velocity)
            self.color[0] = self.color[0] + 0.1
            self.color[1] = self.color[1] - 0.1

class PongApp(App):
    
    def build(self):
        game = PongGame()
        game.serve_ball()
        Clock.schedule_interval(game.update, 1.0/60.0)
        return game

class PongBall(Widget):

    # velocity of the ball on x and y axis
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)

    # referencelist property so we can use ball.velocity as
    # a shorthand, just like e.g. w.pos for w.x and w.y
    velocity = ReferenceListProperty(velocity_x, velocity_y)

    # ``move`` function will move the ball one step. This
    #  will be called in equal intervals to animate the ball
    color = ListProperty([0.5, 0.5, 0.5, 1.])
    def move(self):
        self.pos = Vector(*self.velocity) + self.pos

    def set_color(self, color):
        self.color = color


if __name__ == '__main__':
    PongApp().run()