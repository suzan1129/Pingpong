# ml/ml_play_P1_F74101115.py
import pickle
import numpy as np
import os
import random
# 導入需要 blocker_current_speed_x 的預測函數
from ml.predict_logic import predict_pingpong_landing

class MLPlay:
    def __init__(self, ai_name, *args, **kwargs):
        """
        用於 ML 玩家 1 的建構子
        """
        self.side = "1P"
        self.player_no = int(ai_name.strip('P'))
        self.model = None
        self.prev_blocker_x = None # <--- 新增: 儲存上一幀 Blocker 的 X 座標
        self.blocker_speed_x = 0   # <--- 新增: 推斷出的 Blocker 速度 (初始為 0)

        # --- 載入模型 ---
        student_id = "F74101115" # 你的學號
        model_filename = f"model_{self.side}_{student_id}.pickle"
        model_path = os.path.join(os.path.dirname(__file__), model_filename)

        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            print(f"[{self.side}] 模型 '{model_filename}' 載入成功。")
        except FileNotFoundError:
            print(f"[{self.side}] 錯誤: 在 '{model_path}' 找不到模型檔案。將使用後備邏輯。")
            self.model = None
        except Exception as e:
            print(f"[{self.side}] 載入模型時發生錯誤: {e}。將使用後備邏輯。")
            self.model = None

    def update(self, scene_info, *args, **kwargs):
        """
        根據模型預測或後備邏輯生成指令。
        """
        command = "NONE"
        platform_width = 40

        # 1. 檢查遊戲狀態
        if scene_info["status"] != "GAME_ALIVE":
            return "RESET"

        # 2. 發球 (如果球未發出)
        if not scene_info["ball_served"]:
            command = "SERVE_TO_LEFT" if random.random() < 0.5 else "SERVE_TO_RIGHT"
            self.prev_blocker_x = None # 重置 Blocker 追蹤
            self.blocker_speed_x = 0
            return command

        # --- 球已在場上 ---
        # 3. 推斷 Blocker 速度
        current_blocker_pos = scene_info.get("blocker")
        current_blocker_x = -1
        if current_blocker_pos:
            current_blocker_x = current_blocker_pos[0]
            if self.prev_blocker_x is not None:
                 delta_x = current_blocker_x - self.prev_blocker_x
                 if delta_x > 2: self.blocker_speed_x = 5
                 elif delta_x < -2: self.blocker_speed_x = -5
            self.prev_blocker_x = current_blocker_x
        else:
             self.prev_blocker_x = None
             self.blocker_speed_x = 0

        # 4. 計算預測落點 (傳入 Blocker 速度)
        predicted_center = None
        if "ball_speed" in scene_info:
             predicted_center = predict_pingpong_landing(scene_info, self.side, self.blocker_speed_x) # <--- 傳入速度

        my_platform_x = scene_info[f"platform_{self.side}"][0]
        my_platform_center = my_platform_x + platform_width / 2

        # 5. 使用模型或後備邏輯決定指令
        if self.model:
            # --- 準備模型的特徵向量 (必須與訓練時完全一致！) ---
            try:
                if "ball_speed" not in scene_info: raise ValueError("'ball_speed' missing")
                ball_speed_x, ball_speed_y = scene_info["ball_speed"]
                pred_center_feature = predicted_center if predicted_center is not None else my_platform_center

                features = [
                    scene_info["ball"][0], scene_info["ball"][1],
                    ball_speed_x, ball_speed_y,
                    scene_info["platform_1P"][0], scene_info["platform_2P"][0],
                    current_blocker_x, # 使用當前 Blocker X
                    pred_center_feature,
                    self.blocker_speed_x # <--- 新增: 將 Blocker 速度也作為特徵
                ]
                # 確保特徵數量和順序與訓練時一致！如果不一致，模型會出錯。
                # 假設模型需要 9 個特徵
                if len(features) != 9:
                     raise ValueError(f"Incorrect number of features. Expected 9, got {len(features)}")

                feature_vector = np.array(features).reshape(1, -1)

                # --- 模型預測 ---
                prediction = self.model.predict(feature_vector)[0]
                command_map = {0: "MOVE_LEFT", 1: "MOVE_RIGHT", 2: "NONE"}
                command = command_map.get(prediction, "NONE")

            except Exception as e:
                 print(f"[{self.side}] 特徵提取或模型預測時發生錯誤: {e}。使用後備邏輯。")
                 # 後備邏輯
                 if predicted_center is not None:
                     if my_platform_center < predicted_center - 3: command = "MOVE_RIGHT"
                     elif my_platform_center > predicted_center + 3: command = "MOVE_LEFT"
                     else: command = "NONE"
                 else: # 移到中間
                     if my_platform_center < 100 - 5: command = "MOVE_RIGHT"
                     elif my_platform_center > 100 + 5: command = "MOVE_LEFT"
                     else: command = "NONE"
        else:
            # --- 後備邏輯 (如果模型未載入) ---
            if predicted_center is not None:
                if my_platform_center < predicted_center - 3: command = "MOVE_RIGHT"
                elif my_platform_center > predicted_center + 3: command = "MOVE_LEFT"
                else: command = "NONE"
            else: # 移到中間
                if my_platform_center < 100 - 5: command = "MOVE_RIGHT"
                elif my_platform_center > 100 + 5: command = "MOVE_LEFT"
                else: command = "NONE"

        return command

    def reset(self):
        """
        重置狀態。
        """
        self.prev_blocker_x = None # 重置 Blocker 追蹤
        self.blocker_speed_x = 0   # 重置 Blocker 速度推斷
        # print(f"[{self.side}] 重置 AI 狀態。")
        pass