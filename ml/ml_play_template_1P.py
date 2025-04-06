# ml/ml_play_P1_YourStudentID.py
import pickle
import numpy as np
import os
import random 
from ml.predict_logic import predict_pingpong_landing

class MLPlay:
    def __init__(self, ai_name, *args, **kwargs):
        """
        Constructor for the ML Player 1
        """
        self.side = "1P" # Explicitly set side
        self.player_no = int(ai_name.strip('P')) # Get player number
        self.previous_ball_position = None
        self.model = None

        # --- Load Model ---
        # ** IMPORTANT: Replace "YourStudentID" with your actual student ID **
        student_id = "F74101115"
        model_filename = f"model_{self.side}_{student_id}.pickle"
        model_path = os.path.join(os.path.dirname(__file__), model_filename)

        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            print(f"[{self.side}] Model '{model_filename}' loaded successfully.")
        except FileNotFoundError:
            print(f"[{self.side}] Error: Model file not found at '{model_path}'. Will use fallback logic.")
            self.model = None
        except Exception as e:
            print(f"[{self.side}] Error loading model: {e}. Will use fallback logic.")
            self.model = None

        self.ball_served = False # Initialize ball_served status

    def update(self, scene_info, *args, **kwargs):
        """
        Generate command based on model prediction or fallback logic.
        """
        command = "NONE"

        # 1. Check game status
        if scene_info["status"] != "GAME_ALIVE":
            # print(f"[{self.side}] Game status: {scene_info['status']}. Sending RESET.")
            return "RESET"

        # 2. Serve the ball (if not served)
        # Check using scene_info["ball_served"] which comes from the game core
        if not scene_info["ball_served"]:
            command = "SERVE_TO_LEFT" if random.random() < 0.5 else "SERVE_TO_RIGHT"
            self.previous_ball_position = None # Reset history on new serve
            return command

        # --- Ball is in play ---
        # 3. Calculate predicted landing point (needed for fallback AND potentially as a feature)
        predicted_center = predict_pingpong_landing(scene_info, self.side)
        my_platform_x = scene_info[f"platform_{self.side}"][0]
        my_platform_center = my_platform_x + 40 / 2

        # 4. Use Model or Fallback
        if self.model:
            # --- Prepare features for the model (MUST MATCH TRAINING) ---
            try:
                # 直接使用 scene_info['ball_speed']
                if "ball_speed" not in scene_info:
                     raise ValueError("'ball_speed' not in scene_info") # 如果沒有速度信息則報錯
                ball_speed_x, ball_speed_y = scene_info["ball_speed"]

                # Use calculated prediction, or fallback if None
                pred_center_feature = predicted_center if predicted_center is not None else my_platform_center

                features = [
                    scene_info["ball"][0], scene_info["ball"][1],
                    ball_speed_x, ball_speed_y,  # <--- 使用讀取的速度
                    scene_info["platform_1P"][0], scene_info["platform_2P"][0],
                    scene_info["blocker"][0] if scene_info.get("blocker") else -1,
                    pred_center_feature
                ]
                feature_vector = np.array(features).reshape(1, -1)

                # --- Predict command ---
                prediction = self.model.predict(feature_vector)[0]
                command_map = {0: "MOVE_LEFT", 1: "MOVE_RIGHT", 2: "NONE"}
                command = command_map.get(prediction, "NONE")
                # print(f"[{self.side}] Model prediction: {prediction} -> {command}")

            except Exception as e:
                 print(f"[{self.side}] Error during feature extraction or prediction: {e}. Using fallback.")
                 # Fallback logic if feature extraction/prediction fails
                 if predicted_center is not None:
                     if my_platform_center < predicted_center - 3: command = "MOVE_RIGHT"
                     elif my_platform_center > predicted_center + 3: command = "MOVE_LEFT"
                     else: command = "NONE"
                 else: # Move towards center if no prediction
                     if my_platform_center < 100 - 5: command = "MOVE_RIGHT"
                     elif my_platform_center > 100 + 5: command = "MOVE_LEFT"
                     else: command = "NONE"

        else:
            # --- Fallback logic (if model didn't load) ---
            # print(f"[{self.side}] Using fallback logic.")
            if predicted_center is not None:
                if my_platform_center < predicted_center - 3: command = "MOVE_RIGHT"
                elif my_platform_center > predicted_center + 3: command = "MOVE_LEFT"
                else: command = "NONE"
            else: # Move towards center if no prediction
                if my_platform_center < 100 - 5: command = "MOVE_RIGHT"
                elif my_platform_center > 100 + 5: command = "MOVE_LEFT"
                else: command = "NONE"


        # print(f"[{self.side}] Frame {scene_info['frame']}: Command={command}")
        return command

    def reset(self):
        """
        Reset the status.
        """
        self.ball_served = False # Reset internal flag, though game state is master
        # print(f"[{self.side}] Resetting AI state.")