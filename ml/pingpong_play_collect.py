# ml/pingpong_play_collect.py
import pickle
import datetime
import os
import random
import numpy as np # 需要 numpy
from ml.predict_logic import predict_pingpong_landing

class MLPlay:
    def __init__(self, ai_name, *args, **kwargs):
        """
        Constructor for data collection AI (collects only wins)
        """
        self.side = ai_name
        self.player_no = int(ai_name.strip('P'))
        # self.previous_ball_position = None # 不再需要
        self.data_buffer = []

        # 創建資料夾 (如果不存在)
        self.data_folder = f"pingpong_data_{self.side}"
        if not os.path.exists(self.data_folder):
            try:
                os.makedirs(self.data_folder)
            except FileExistsError: # 處理可能的並發創建問題
                pass
        print(f"[{self.side}] Data collection AI initialized. Win data will be saved to '{self.data_folder}'")

    def update(self, scene_info, *args, **kwargs):
        """
        Generate command based on prediction and collect data for winning rounds.
        """
        command = "NONE"
        predicted_center = None
        platform_width = 40 # 球拍寬度，用於計算中心

        # 1. Check game status
        if scene_info["status"] != "GAME_ALIVE":
            # --- 只儲存獲勝局的數據 ---
            should_save = False
            if self.side == "1P" and scene_info["status"] == "GAME_1P_WIN":
                should_save = True
                print(f"[{self.side}] Game Won! Preparing to save data...")
            elif self.side == "2P" and scene_info["status"] == "GAME_2P_WIN":
                should_save = True
                print(f"[{self.side}] Game Won! Preparing to save data...")

            if should_save and self.data_buffer:
                 timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                 filename = os.path.join(self.data_folder, f"data_win_{timestamp}.pickle")
                 self.save_data_to_pickle(filename) # <--- 修改: 調用包含打印功能的函數
            elif self.data_buffer:
                 self.data_buffer = [] # 清空 buffer
            # --- 修改結束 ---

            return "RESET"

        # 2. Serve the ball (if not served according to scene_info)
        if not scene_info["ball_served"]:
            command = "SERVE_TO_LEFT" if random.random() < 0.5 else "SERVE_TO_RIGHT"
            return command

        # --- Ball is in play ---
        # 3. Predict and Decide Movement
        my_platform_x = scene_info[f"platform_{self.side}"][0]
        my_platform_center = my_platform_x + platform_width / 2

        if "ball_speed" in scene_info:
             predicted_center = predict_pingpong_landing(scene_info, self.side)
        # else: predicted_center remains None

        if predicted_center is not None:
            if my_platform_center < predicted_center - 2:
                command = "MOVE_RIGHT"
            elif my_platform_center > predicted_center + 2:
                command = "MOVE_LEFT"
            else:
                command = "NONE"
        else: # Fallback if prediction fails
            if my_platform_center < 100 - 5:
                 command = "MOVE_RIGHT"
            elif my_platform_center > 100 + 5:
                 command = "MOVE_LEFT"
            else:
                 command = "NONE"

        # 4. Collect Data (only for movement commands when ball is served and speed exists)
        if scene_info["ball_served"] and "ball_speed" in scene_info:
            if command in ["MOVE_LEFT", "MOVE_RIGHT", "NONE"]:
                 ball_speed_x, ball_speed_y = scene_info["ball_speed"]
                 # Use predicted_center if available, otherwise current center as fallback feature value
                 pred_center_feature = predicted_center if predicted_center is not None else my_platform_center

                 features = {
                     "ball_x": scene_info["ball"][0],
                     "ball_y": scene_info["ball"][1],
                     "ball_speed_x": ball_speed_x,
                     "ball_speed_y": ball_speed_y,
                     "platform_1P_x": scene_info["platform_1P"][0],
                     "platform_2P_x": scene_info["platform_2P"][0],
                     "blocker_x": scene_info["blocker"][0] if scene_info.get("blocker") else -1,
                     "predicted_center_calc": pred_center_feature
                 }

                 self.data_buffer.append({
                     "features": features,
                     "command": command,
                     "side": self.side
                 })

        return command

    def reset(self):
        """
        Reset the status. Buffer is cleared when game ends if it wasn't a win.
        """
        self.data_buffer = [] # Ensure buffer is cleared on reset
        pass

    def save_data_to_pickle(self, filename):
        """
        Save the collected data buffer to a pickle file and print sample data.
        """
        if not self.data_buffer:
             print(f"[{self.side}] No data to save for this winning round (buffer empty).")
             return

        # --- 在儲存前打印一些樣本數據 ---
        print(f"[{self.side}] Saving data to {filename}. Buffer size: {len(self.data_buffer)}")
        print("-" * 20 + " Sample Data " + "-" * 20)
        # 打印前 5 筆 和 最後 5 筆數據看看
        sample_indices = list(range(min(5, len(self.data_buffer)))) + \
                         list(range(max(0, len(self.data_buffer)-5), len(self.data_buffer)))
        printed_indices = set() # 避免重複打印

        for i in sample_indices:
            if i not in printed_indices and i < len(self.data_buffer): # 增加索引範圍檢查
                 data_point = self.data_buffer[i]
                 # 確保 data_point 是字典
                 if not isinstance(data_point, dict):
                      print(f"  Index {i}: Invalid data format - not a dictionary")
                      continue

                 print(f"  Index {i}:")
                 print(f"    Side: {data_point.get('side', 'N/A')}") # 使用 get 更安全
                 print(f"    Command: {data_point.get('command', 'N/A')}")
                 features = data_point.get('features')
                 if features and isinstance(features, dict):
                      print(f"    Features:")
                      # 逐一打印特徵，方便看格式和值
                      for key, value in features.items():
                           # 對浮點數進行格式化
                           if isinstance(value, (float, np.floating)): # 包含 numpy 浮點數
                               print(f"      {key}: {value:.2f}")
                           elif isinstance(value, (int, np.integer)): # 包含 numpy 整數
                                print(f"      {key}: {value}")
                           else: # 其他類型直接打印
                                print(f"      {key}: {value}")
                 else:
                      print(f"    Features: Invalid or Missing")
                 printed_indices.add(i)
        print("-" * (40 + len(" Sample Data ")))
        # --- 打印結束 ---

        # 執行儲存
        try:
            with open(filename, "wb") as f:
                pickle.dump(self.data_buffer, f)
            print(f"[{self.side}] Win data saved successfully to {filename}")
        except Exception as e:
            print(f"[{self.side}] Error saving data to {filename}: {e}")
        finally:
             # 儲存後清空 buffer，避免重複儲存或佔用記憶體
             self.data_buffer = []