# ml/pingpong_play_collect.py
import pickle
import datetime
import os
import random
import numpy as np # 引入 numpy 以便後續處理特徵

# 導入預測邏輯函數 (假設 predict_logic.py 在同一個 ml 資料夾下)
# 這個函數預期接收 scene_info 和 side 作為參數
from ml.predict_logic import predict_pingpong_landing

class MLPlay:
    def __init__(self, ai_name, *args, **kwargs):
        """
        用於 Pingpong 數據收集的 AI 類別。
        - 會根據 ai_name ('1P' 或 '2P') 區分玩家。
        - 使用 predict_pingpong_landing 函數來決定移動策略。
        - 只收集並儲存 AI 獲勝那一局的數據。
        - 將數據儲存到獨立的資料夾 (pingpong_data_1P 或 pingpong_data_2P)。

        Args:
            ai_name (str): MLGame 傳入的玩家標識 ("1P" 或 "2P")。
        """
        self.side = ai_name                               
        self.player_no = int(ai_name.strip('P'))          
        self.data_buffer = []                             # 空的 list 來暫存一局中的數據

        # 根據 side 創建數據儲存資料夾 (如果不存在)
        self.data_folder = f"pingpong_data_{self.side}"
        if not os.path.exists(self.data_folder):
            try:
                # 嘗試創建資料夾
                os.makedirs(self.data_folder)
            except FileExistsError:
                # 如果在極小的時間差內，另一個進程也創建了資料夾，忽略這個錯誤
                pass
        print(f"[{self.side}] Data collection AI initialized. Win data will be saved to '{self.data_folder}'")

    def update(self, scene_info, *args, **kwargs):
        """
        每一幀被 MLGame 呼叫，根據遊戲狀態決定動作並收集數據。

        Args:
            scene_info (dict): 包含當前遊戲狀態信息的字典。

        Returns:
            str: 要執行的遊戲指令 ("MOVE_LEFT", "MOVE_RIGHT", "NONE", "SERVE_TO_LEFT", "SERVE_TO_RIGHT", "RESET")。
        """
        # --- 1. 檢查遊戲是否結束 ---
        if scene_info["status"] != "GAME_ALIVE":  
            # --- 1.1 判斷是否為獲勝局 ---
            should_save = False                           
            if self.side == "1P" and scene_info["status"] == "GAME_1P_WIN": # 1P 獲勝
                should_save = True
                print(f"[{self.side}] Game Won! Preparing to save data...")
            elif self.side == "2P" and scene_info["status"] == "GAME_2P_WIN": # 2P 獲勝
                should_save = True
                print(f"[{self.side}] Game Won! Preparing to save data...")

            # --- 1.2 如果是獲勝局且 buffer 中有數據，則儲存 ---
            if should_save and self.data_buffer:
                 timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                 filename = os.path.join(self.data_folder, f"data_win_{timestamp}.pickle")
                 # 儲存
                 self.save_data_to_pickle(filename)

            # --- 1.3 無論是否儲存，遊戲結束都要返回 "RESET" ---
            return "RESET"

        # --- 2. 檢查是否需要發球 ---
        if not scene_info["ball_served"]:   # 球未發出
            command = "SERVE_TO_LEFT" if random.random() < 0.5 else "SERVE_TO_RIGHT"
            return command

        # --- 如果遊戲進行中且球已發出 ---

        # --- 3. 預測球的落點並決定移動指令 ---
        command = "NONE"                                  # 預設指令為不移動
        predicted_center = None                           # 初始化預測結果為空

        # 確保 scene_info 中有 'ball_speed' 才能進行預測
        if "ball_speed" in scene_info:
             # 呼叫預測函數，傳入當前場景信息和自己是哪一方 (1P/2P)
             predicted_center = predict_pingpong_landing(scene_info, self.side)
        # else:
        #     print(f"[{self.side}] Warning: 'ball_speed' not found. Cannot predict.")

        # 我方球拍的當前 X 座標和中心點 X 座標
        my_platform_x = scene_info[f"platform_{self.side}"][0]
        my_platform_center = my_platform_x + 40 / 2       # 球拍寬度為 40

        # --- 3.1 根據預測結果決定移動方向 ---
        if predicted_center is not None:                  # 如果成功預測到落點
            # 設置一個小的容忍區間 (deadzone)，避免在目標點附近頻繁抖動
            tolerance = 3
            # 如果當前中心比目標中心偏左超過容忍值
            if my_platform_center < predicted_center - tolerance:
                command = "MOVE_RIGHT"                    # 需要向右移動
            # 如果當前中心比目標中心偏右超過容忍值
            elif my_platform_center > predicted_center + tolerance:
                command = "MOVE_LEFT"                     # 需要向左移動
            # 否則 (在容忍區間內)，保持不動
            else:
                command = "NONE"
        # --- 3.2 如果預測失敗 (predicted_center 為 None) ---
        else:
            # 採取後備策略：讓球拍移向畫面中心 (x=100)
            center_target = 100
            center_tolerance = 5
            if my_platform_center < center_target - center_tolerance:
                 command = "MOVE_RIGHT"
            elif my_platform_center > center_target + center_tolerance:
                 command = "MOVE_LEFT"
            else:
                 command = "NONE"


        # --- 4. 收集特徵和標籤數據 ---
        if scene_info["ball_served"] and "ball_speed" in scene_info:
            if command in ["MOVE_LEFT", "MOVE_RIGHT", "NONE"]:
                 # --- 4.1 提取需要的特徵 ---
                 ball_speed_x, ball_speed_y = scene_info["ball_speed"]

                 # 如果預測落點計算失敗，使用當前平台中心作為特徵值
                 pred_center_feature = predicted_center if predicted_center is not None else my_platform_center

                 # 將 Feature 和 Command 整理
                 features = {
                     "ball_x": scene_info["ball"][0],
                     "ball_y": scene_info["ball"][1],
                     "ball_speed_x": ball_speed_x,
                     "ball_speed_y": ball_speed_y,
                     "platform_1P_x": scene_info["platform_1P"][0],
                     "platform_2P_x": scene_info["platform_2P"][0],
                     # 如果沒有障礙物，給定一個特殊值 (例如 -1)
                     "blocker_x": scene_info["blocker"][0] if scene_info.get("blocker") else -1,
                     "predicted_center_calc": pred_center_feature # 儲存計算出的預測中心
                 }

                 # --- 4.2 將 (特徵, 指令, side) 加入暫存 buffer ---
                 self.data_buffer.append({
                     "features": features,   # 儲存提取的特徵字典
                     "command": command,     # 儲存這一幀實際執行的移動指令
                     "side": self.side        # 記錄這條數據是屬於 1P 還是 2P
                 })

        # --- 5. 返回最終決定的指令 ---
        return command

    def reset(self):
        """
        當一局遊戲結束並重置時被 MLGame 呼叫。
        主要工作是清空 data_buffer，為下一局做準備。
        (數據儲存已在 update 檢測到遊戲勝利時完成)
        """
        self.data_buffer = [] # 清空暫存的數據
        pass 

    def save_data_to_pickle(self, filename):
        """
        將 data_buffer 中的數據序列化並儲存到指定的 pickle 文件。

        Args:
            filename (str): 要儲存的文件路徑和名稱。
        """
        if not self.data_buffer:
             print(f"[{self.side}] No data in buffer to save for file: {filename}")
             return
        try:
            with open(filename, "wb") as f:
                # 將整個 data_buffer (一個 list of dictionaries) 寫入文件
                pickle.dump(self.data_buffer, f)
            print(f"[{self.side}] Win data saved successfully to {filename} ({len(self.data_buffer)} frames)")
        except Exception as e:
            print(f"[{self.side}] Error saving data to {filename}: {e}")