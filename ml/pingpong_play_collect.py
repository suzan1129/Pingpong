# ml/pingpong_play_collect.py
import pickle
import datetime
import os
import random
import numpy as np # 引入 numpy

# 假設 predict_logic.py 在同一個 ml 資料夾下
from ml.predict_logic import predict_pingpong_landing

class MLPlay:
    def __init__(self, ai_name, *args, **kwargs):
        """
        Constructor for data collection AI
        """
        self.side = ai_name
        self.ball_served = False
        self.previous_ball_position = None
        self.data_buffer = []
        # 創建資料夾 (如果不存在)
        self.data_folder = f"pingpong_data_{self.side}"
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
        print(f"[{self.side}] Data collection AI initialized. Data will be saved to '{self.data_folder}'")

    def update(self, scene_info, *args, **kwargs):
        """
        Generate command based on prediction and collect data.
        """
        command = "NONE"
        predicted_center = None

        # 1. Check game status
        if scene_info["status"] != "GAME_ALIVE":
            # Save data if game ends (adjust win/loss condition if needed)
            # For simplicity, save data regardless of win/loss in collection phase
            if self.data_buffer:
                 timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                 filename = os.path.join(self.data_folder, f"data_{timestamp}.pickle")
                 self.save_data_to_pickle(filename)
            return "RESET"

        # 2. Serve the ball
        if not self.ball_served:
            # Randomly serve
            command = "SERVE_TO_LEFT" if random.random() < 0.5 else "SERVE_TO_RIGHT"
            self.ball_served = True
            self.previous_ball_position = scene_info["ball"] # Record position after serve potentially
            return command # Serve and exit update for this frame

        # 3. Predict and Decide Movement (if ball is served)
        predicted_center = predict_pingpong_landing(scene_info, self.previous_ball_position, self.side)

        my_platform_x = scene_info[f"platform_{self.side}"][0]
        my_platform_center = my_platform_x + 40 / 2 # Platform width is 40

        if predicted_center is not None:
            # Simple proportional control (adjust tolerance/deadzone as needed)
            if my_platform_center < predicted_center - 3: # Need to move right
                command = "MOVE_RIGHT"
            elif my_platform_center > predicted_center + 3: # Need to move left
                command = "MOVE_LEFT"
            else: # Close enough
                command = "NONE"
        else:
            # Fallback strategy if prediction fails: Move towards center or stay still
            if my_platform_center < 100 - 5: # Move towards center (100)
                 command = "MOVE_RIGHT"
            elif my_platform_center > 100 + 5:
                 command = "MOVE_LEFT"
            else:
                 command = "NONE"
            # command = "NONE" # Alternative: Just stay still if prediction fails

        # 4. Collect Data
        if self.previous_ball_position: # Only collect if we have previous position
            # Define features to collect
            features = {
                "ball_x": scene_info["ball"][0],
                "ball_y": scene_info["ball"][1],
                "ball_speed_x": scene_info["ball"][0] - self.previous_ball_position[0],
                "ball_speed_y": scene_info["ball"][1] - self.previous_ball_position[1],
                "platform_1P_x": scene_info["platform_1P"][0],
                "platform_2P_x": scene_info["platform_2P"][0],
                "blocker_x": scene_info["blocker"][0] if scene_info.get("blocker") else -1, # Use -1 if no blocker
                 # Add predicted_center as a potential feature for the model later
                "predicted_center_calc": predicted_center if predicted_center is not None else my_platform_center # Store calculated prediction
            }

            self.data_buffer.append({
                "features": features, # Store extracted features directly
                "command": command,
                "side": self.side
            })

        # 5. Update previous state for next frame
        self.previous_ball_position = scene_info["ball"]

        return command

    def reset(self):
        """
        Reset the status and clear buffer (buffer is saved when game ends).
        """
        self.ball_served = False
        self.previous_ball_position = None
        self.data_buffer = [] # Clear buffer for the new game
        # print(f"[{self.side}] Resetting AI state.")

    def save_data_to_pickle(self, filename):
        """
        Save the collected data buffer to a pickle file.
        """
        try:
            with open(filename, "wb") as f:
                pickle.dump(self.data_buffer, f)
            # print(f"[{self.side}] Data saved to {filename} ({len(self.data_buffer)} frames)")
        except Exception as e:
            print(f"[{self.side}] Error saving data to {filename}: {e}")