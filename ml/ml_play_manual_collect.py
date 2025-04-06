# ml/ml_play_manual_collect.py
import pygame
import pickle
import datetime
import os
import numpy as np # 需要 numpy 來處理特徵
from ml.predict_logic import predict_pingpong_landing

class MLPlay:
    def __init__(self, ai_name, *args, **kwargs):
        """
        Constructor for Manual Play Data Collection
        """
        self.side = ai_name
        self.player_no = int(ai_name.strip('P'))
        self.data_buffer = []
        

        # 創建資料夾 (如果不存在) - 手動數據建議存到不同地方
        self.data_folder = f"pingpong_manual_data_{self.side}"
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
        print(f"[{self.side}] Manual Data Collection AI initialized. Data will be saved to '{self.data_folder}'")
        print(f"[{self.side}] Controls: Serve: Q/E (2P), ./ (1P) | Move: A/D (2P), Left/Right Arrow (1P)")


    def update(self, scene_info, keyboard=[], *args, **kwargs):
        """
        Generate command based on keyboard input and collect data.
        """
        command = "NONE"
        predicted_center = None # 先初始化

        # 1. Check game status
        if scene_info["status"] != "GAME_ALIVE":
            # --- 只儲存獲勝局的數據 ---
            should_save = False
            if self.side == "1P" and scene_info["status"] == "GAME_1P_WIN":
                should_save = True
                print(f"[{self.side}] Game Won! Preparing to save manual data...")
            elif self.side == "2P" and scene_info["status"] == "GAME_2P_WIN":
                should_save = True
                print(f"[{self.side}] Game Won! Preparing to save manual data...")

            if should_save and self.data_buffer:
                 timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                 filename = os.path.join(self.data_folder, f"manual_data_win_{timestamp}.pickle")
                 self.save_data_to_pickle(filename)
            return "RESET"

        # 2. Determine command from keyboard input
        if self.side == "1P":
            # Red 紅色 下方 (通常用方向鍵, . / 發球)
            if pygame.K_PERIOD in keyboard: # '.' key
                command = "SERVE_TO_LEFT"
            elif pygame.K_SLASH in keyboard: # '/' key
                command = "SERVE_TO_RIGHT"
            elif pygame.K_LEFT in keyboard:
                command = "MOVE_LEFT"
            elif pygame.K_RIGHT in keyboard:
                command = "MOVE_RIGHT"
            else:
                command = "NONE"
        elif self.side == "2P":
            # Blue 藍色 上方 (通常用 A/D 移動, Q/E 發球)
            if pygame.K_q in keyboard:
                command = "SERVE_TO_LEFT"
            elif pygame.K_e in keyboard:
                command = "SERVE_TO_RIGHT"
            elif pygame.K_a in keyboard:
                command = "MOVE_LEFT"
            elif pygame.K_d in keyboard:
                command = "MOVE_RIGHT"
            else:
                command = "NONE"

        # 3. Calculate predicted landing point (仍然需要計算，因為它是特徵之一)
        predicted_center = predict_pingpong_landing(scene_info, self.side)
        my_platform_x = scene_info[f"platform_{self.side}"][0]
        my_platform_center = my_platform_x + 40 / 2


        # 4. Collect Data (只在球已發出後收集移動指令相關數據)
        if scene_info["ball_served"] and "ball_speed" in scene_info: # 確保 ball_speed 存在
             if command in ["MOVE_LEFT", "MOVE_RIGHT", "NONE"]: # 只收集移動指令
                 # Define features to collect (與訓練時保持一致!)
                 # 使用 scene_info['ball_speed']
                 ball_speed_x, ball_speed_y = scene_info["ball_speed"]

                 # 計算預測中心特徵 (如果預測失敗則用當前平台中心)
                 pred_center_feature = predicted_center if predicted_center is not None else my_platform_center

                 features = {
                     "ball_x": scene_info["ball"][0],
                     "ball_y": scene_info["ball"][1],
                     "ball_speed_x": ball_speed_x, 
                     "ball_speed_y": ball_speed_y, 
                     "platform_1P_x": scene_info["platform_1P"][0],
                     "platform_2P_x": scene_info["platform_2P"][0],
                     "blocker_x": scene_info["blocker"][0] if scene_info.get("blocker") else -1, # Use -1 if no blocker
                     "predicted_center_calc": pred_center_feature
                 }

                 self.data_buffer.append({
                     "features": features,
                     "command": command, # 儲存手動指令
                     "side": self.side
                 })

 

        return command

    def reset(self):
        """
        Reset the status and clear buffer.
        """
        self.data_buffer = [] # 清空 buffer，數據在遊戲勝利時已儲存
        # print(f"[{self.side}] Resetting Manual AI state.")

    def save_data_to_pickle(self, filename):
        """
        Save the collected manual data buffer to a pickle file.
        """
        if not self.data_buffer:
             print(f"[{self.side}] No manual data to save for this round.")
             return
        try:
            with open(filename, "wb") as f:
                pickle.dump(self.data_buffer, f)
            print(f"[{self.side}] Manual data saved to {filename} ({len(self.data_buffer)} frames)")
        except Exception as e:
            print(f"[{self.side}] Error saving manual data to {filename}: {e}")