import random

import pygame

from mlgame.game.paia_game import PaiaGame, GameStatus, GameResultState
from mlgame.utils.enum import get_ai_name
from mlgame.view.decorator import check_game_progress, check_game_result
from mlgame.view.view_model import create_text_view_data, Scene, create_scene_progress_data
from .game_object import (
    Ball, Blocker, Platform, PlatformAction, SERVE_BALL_ACTIONS
)

DRAW_BALL_SPEED = 40


class PingPong(PaiaGame):

    def __init__(self, difficulty, game_over_score,user_num=2,init_vel=7,*args,**kwargs):
        super().__init__(user_num=user_num)
        self._difficulty = difficulty
        self._score = [0, 0]
        self._game_over_score = game_over_score
        self._frame_count = 0
        self._game_status = GameStatus.GAME_ALIVE
        self._ball_served = False
        self._ball_served_frame = 0
        self._init_vel = init_vel
        self.scene = Scene(width=200, height=500, color="#424242", bias_x=0, bias_y=0)
        self._create_init_scene()
    def _create_init_scene(self):
        self._draw_group = pygame.sprite.RenderPlain()

        enable_slice_ball = False if self._difficulty == "EASY" else True
        self._ball = Ball(pygame.Rect(0, 0, 200, 500), enable_slice_ball, self._draw_group, init_vel=self._init_vel)
        self._platform_1P = Platform((80, 420),
                                     pygame.Rect(0, 0, 200, 500), "1P", self._draw_group)
        self._platform_2P = Platform((80, 70),
                                     pygame.Rect(0, 0, 200, 500), "2P", self._draw_group)

        if self._difficulty != "HARD":
            # Put the blocker at the end of the world
            self._blocker = Blocker(1000, pygame.Rect(0, 0, 200, 500), self._draw_group)
        else:
            self._blocker = Blocker(240, pygame.Rect(0, 0, 200, 500), self._draw_group)

        # Initialize the position of the ball
        self._ball.stick_on_platform(self._platform_1P.rect, self._platform_2P.rect)

    def update(self, commands):
        ai_1p_cmd = commands[get_ai_name(0)]
        ai_2p_cmd = commands[get_ai_name(1)]
        command_1P = (PlatformAction(ai_1p_cmd)
                      if ai_1p_cmd in PlatformAction.__members__ else PlatformAction.NONE)
        command_2P = (PlatformAction(ai_2p_cmd)
                      if ai_2p_cmd in PlatformAction.__members__ else PlatformAction.NONE)

        self._frame_count += 1
        self._platform_1P.move(command_1P)
        self._platform_2P.move(command_2P)
        self._blocker.move()

        if not self._ball_served:
            self._wait_for_serving_ball(command_1P, command_2P)
        else:
            self._ball_moving()

        if self.get_game_status() != GameStatus.GAME_ALIVE:
            if self._game_over(self.get_game_status()):
                self._print_result()
                self._game_status = GameStatus.GAME_OVER
                return "QUIT"
            return "RESET"

        if not self.is_running:
            return "QUIT"

    def _game_over(self, status):
        """
        Check if the game is over
        """
        if status == GameStatus.GAME_1P_WIN:
            self._score[0] += 1
        elif status == GameStatus.GAME_2P_WIN:
            self._score[1] += 1
        else:  # Draw game
            self._score[0] += 1
            self._score[1] += 1

        is_game_over = (self._score[0] == self._game_over_score or
                        self._score[1] == self._game_over_score)

        return is_game_over

    def _print_result(self):
        """
        Print the result
        """
        if self._score[0] > self._score[1]:
            win_side = "1P"
        elif self._score[0] == self._score[1]:
            win_side = "No one"
        else:
            win_side = "2P"

        print("{} wins! Final score: {}-{}".format(win_side, *self._score))

    def _wait_for_serving_ball(self, action_1P: PlatformAction, action_2P: PlatformAction):
        self._ball.stick_on_platform(self._platform_1P.rect, self._platform_2P.rect)

        target_action = action_1P if self._ball.serve_from_1P else action_2P

        # Force to serve the ball after 150 frames
        if (self._frame_count >= 150 and
                target_action not in SERVE_BALL_ACTIONS):
            target_action = random.choice(SERVE_BALL_ACTIONS)

        if target_action in SERVE_BALL_ACTIONS:
            self._ball.serve(target_action)
            self._ball_served = True
            self._ball_served_frame = self._frame_count

    def _ball_moving(self):
        # Speed up the ball every 200 frames
        if (self._frame_count - self._ball_served_frame) % 100 == 0:
            # speed up per 100 frames
            self._ball.speed_up()

        self._ball.move()
        self._ball.check_bouncing(self._platform_1P, self._platform_2P, self._blocker)

    def get_data_from_game_to_player(self) -> dict:
        to_players_data = {}
        scene_info = {
            "frame": self._frame_count,
            "status": self.get_game_status(),
            "ball": self._ball.pos,
            "ball_speed": self._ball.speed,
            "ball_served":self._ball_served,
            "serving_side":"1P" if self._ball.serve_from_1P else "2P",
            "platform_1P": self._platform_1P.pos,
            "platform_2P": self._platform_2P.pos
        }

        if self._difficulty == "HARD":
            scene_info["blocker"] = self._blocker.pos
        else:
            scene_info["blocker"] = (0, 0)

        to_players_data[get_ai_name(0)] = scene_info
        to_players_data[get_ai_name(1)] = scene_info

        return to_players_data

    def get_game_status(self):
        if self._ball.rect.top > self._platform_1P.rect.bottom:
            self._game_status = GameStatus.GAME_2P_WIN
        elif self._ball.rect.bottom < self._platform_2P.rect.top:
            self._game_status = GameStatus.GAME_1P_WIN
        elif abs(min(self._ball.speed, key=abs)) > DRAW_BALL_SPEED:
            self._game_status = GameStatus.GAME_DRAW
        else:
            self._game_status = GameStatus.GAME_ALIVE

        return self._game_status

    def reset(self):
        print("reset pingpong")
        self._frame_count = 0
        self._game_status = GameStatus.GAME_ALIVE
        self._ball_served = False
        self._ball_served_frame = 0
        self._ball.reset()
        self._platform_1P.reset()
        self._platform_2P.reset()
        self._blocker.reset()

        # Initialize the position of the ball
        self._ball.stick_on_platform(self._platform_1P.rect, self._platform_2P.rect)

    @property
    def is_running(self):
        # print(self.get_game_status())
        return self._game_status != GameStatus.GAME_OVER

    def get_scene_init_data(self) -> dict:
        scene_init_data = {"scene": self.scene.__dict__, "assets": [

        ]}
        return scene_init_data

    @check_game_progress
    def get_scene_progress_data(self) -> dict:
        game_obj_list = [obj.get_object_data for obj in self._draw_group]

        create_1p_score = create_text_view_data("1P: " + str(self._score[0]),
                                                1,
                                                self.scene.height - 21,
                                                Platform.COLOR_1P,
                                                "18px Arial BOLD"
                                                )
        create_2p_score = create_text_view_data("2P: " + str(self._score[1]),
                                                1,
                                                4,
                                                Platform.COLOR_2P,
                                                "18px Arial BOLD"
                                                )
        create_speed_text = create_text_view_data("Speed: " + str(self._ball.speed),
                                                  self.scene.width - 120,
                                                  self.scene.height - 21,
                                                  "#FFFFFF",
                                                  "18px Arial BOLD"
                                                  )
        foreground = [create_1p_score, create_2p_score, create_speed_text]

        scene_progress = create_scene_progress_data(frame=self._frame_count, object_list=game_obj_list,
                                                    foreground=foreground)
        return scene_progress

    @check_game_result
    def get_game_result(self) -> dict:
        attachment = []
        if self._score[0] > self._score[1]:
            attachment = [
                {
                    "player": get_ai_name(0),
                    "rank": 1,
                    "score": self._score[0],
                    "status": "GAME_PASS",
                    "ball_speed": self._ball.speed,
                },
                {
                    "player": get_ai_name(1),
                    "rank": 2,
                    "score": self._score[1],
                    "status": "GAME_OVER",
                    "ball_speed": self._ball.speed,
                },

            ]
        elif self._score[0] < self._score[1]:
            attachment = [
                {
                    "player": get_ai_name(0),
                    "rank": 2,
                    "score": self._score[0],
                    "status": "GAME_OVER",
                    "ball_speed": self._ball.speed,
                },
                {
                    "player": get_ai_name(1),
                    "rank": 1,
                    "score": self._score[1],
                    "status": "GAME_PASS",
                    "ball_speed": self._ball.speed,

                },
            ]
        else:
            attachment = [
                {
                    "player": get_ai_name(0),
                    "rank": 1,
                    "score": self._score[0],
                    "status": "GAME_DRAW",
                    "ball_speed": self._ball.speed,
                },
                {
                    "player": get_ai_name(1),
                    "rank": 1,
                    "score": self._score[1],
                    "status": "GAME_DRAW",
                    "ball_speed": self._ball.speed,
                },
            ]
        return {
            "frame_used": self._frame_count,
            "state": GameResultState.FINISH,
            "attachment": attachment

        }

    def get_keyboard_command(self) -> dict:
        cmd_1P = ""
        cmd_2P = ""

        key_pressed_list = pygame.key.get_pressed()

        if key_pressed_list[pygame.K_PERIOD]:
            cmd_1P = PlatformAction.SERVE_TO_LEFT
        elif key_pressed_list[pygame.K_SLASH]:
            cmd_1P = PlatformAction.SERVE_TO_RIGHT
        elif key_pressed_list[pygame.K_LEFT]:
            cmd_1P = PlatformAction.MOVE_LEFT
        elif key_pressed_list[pygame.K_RIGHT]:
            cmd_1P = PlatformAction.MOVE_RIGHT
        else:
            cmd_1P = PlatformAction.NONE

        if key_pressed_list[pygame.K_q]:
            cmd_2P = PlatformAction.SERVE_TO_LEFT
        elif key_pressed_list[pygame.K_e]:
            cmd_2P = PlatformAction.SERVE_TO_RIGHT
        elif key_pressed_list[pygame.K_a]:
            cmd_2P = PlatformAction.MOVE_LEFT
        elif key_pressed_list[pygame.K_d]:
            cmd_2P = PlatformAction.MOVE_RIGHT
        else:
            cmd_2P = PlatformAction.NONE

        ai_1p = get_ai_name(0)
        ai_2p = get_ai_name(1)

        return {ai_1p: cmd_1P, ai_2p: cmd_2P}

