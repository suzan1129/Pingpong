# ml/ml_play_P2_F74101115.py
import pickle
import numpy as np
import os
import random
# --- 常數定義 ---
SCREEN_WIDTH = 200
SCREEN_HEIGHT = 500
BALL_SIZE = 5
PLATFORM_WIDTH = 40
PLATFORM_HEIGHT = 10
BLOCKER_WIDTH = 30
BLOCKER_HEIGHT = 20
BLOCKER_Y_TOP = 240

# predict_pingpong_landing 
def predict_pingpong_landing(scene_info, side, blocker_current_speed_x=0): # 新增 blocker_current_speed_x 參數
    """
    預測 Pingpong 球的落點 (平台中心 X 座標) - 使用 scene_info['ball_speed']
    整合了 Blocker 的當前水平移動速度進行預測。
    Args:
        scene_info: 遊戲當前狀態 (必須包含 'ball_speed')
        side: "1P" 或 "2P"
        blocker_current_speed_x: Blocker 當前的水平速度 (+5, -5, 或 0) - 由 MLPlay 類推斷傳入
    Returns:
        預測的平台中心目標 X 座標，如果無法預測則返回後備值 (當前平台中心)
    """
    # --- 1. 初始化和讀取基本資訊 ---
    ball_x, ball_y = scene_info["ball"]
    platform_1P_x, platform_1P_y = scene_info["platform_1P"]
    platform_2P_x, platform_2P_y = scene_info["platform_2P"]
    blocker_pos = scene_info.get("blocker") # Blocker 當前位置

    # --- 2. 獲取球的速度 ---
    if "ball_speed" not in scene_info:
        if side == "1P": return platform_1P_x + PLATFORM_WIDTH / 2
        if side == "2P": return platform_2P_x + PLATFORM_WIDTH / 2
        return None
    ball_speed_x, ball_speed_y = scene_info["ball_speed"]

    # --- 3. 根據玩家 (side) 決定目標和檢查條件 ---
    if side == "1P":
        platform_y_target = platform_1P_y - BALL_SIZE
        my_platform_x = platform_1P_x
        if ball_speed_y <= 0: return None
    elif side == "2P":
        platform_y_target = platform_2P_y + PLATFORM_HEIGHT
        my_platform_x = platform_2P_x
        if ball_speed_y >= 0: return None
    else:
        raise ValueError("Invalid player side. Use '1P' or '2P'.")

    if ball_speed_y == 0: return None

    # --- 4. 初始化模擬變數 ---
    sim_x = float(ball_x)
    sim_y = float(ball_y)
    sim_speed_x = float(ball_speed_x)
    sim_speed_y = float(ball_speed_y)
    # Blocker 的模擬位置和速度也需要
    sim_blocker_x = float(blocker_pos[0]) if blocker_pos else -100 # Blocker 初始 X
    sim_blocker_speed_x = float(blocker_current_speed_x) # 使用傳入的 Blocker 速度

    predicted_x_at_platform = None

    # --- 5. 開始模擬循環 ---
    max_simulation_steps = 30 # 可以根據需要調整
    steps = 0

    while steps < max_simulation_steps:
        steps += 1

        # --- 5.1 計算到各個邊界/物體的「預計時間」---
        time_to_platform = float('inf')
        if sim_speed_y != 0:
            dt = (platform_y_target - sim_y) / sim_speed_y
            if dt > -0.001: time_to_platform = max(0, dt)

        time_to_wall_x = float('inf')
        if sim_speed_x > 0:
            dt_wall = (SCREEN_WIDTH - BALL_SIZE - sim_x) / sim_speed_x if sim_speed_x != 0 else float('inf')
            if dt_wall > 0.001: time_to_wall_x = dt_wall
        elif sim_speed_x < 0:
            dt_wall = (0 - sim_x) / sim_speed_x if sim_speed_x != 0 else float('inf')
            if dt_wall > 0.001: time_to_wall_x = dt_wall

        time_to_blocker_y = float('inf')
        blocker_y_bottom = BLOCKER_Y_TOP + BLOCKER_HEIGHT
        if blocker_pos and sim_speed_y != 0: # 只在 Blocker 存在且球 Y 有速度時計算
            target_y_blocker = -1
            if sim_speed_y > 0 and sim_y < blocker_y_bottom:
                 target_y_blocker = BLOCKER_Y_TOP - BALL_SIZE
            elif sim_speed_y < 0 and sim_y > BLOCKER_Y_TOP:
                 target_y_blocker = blocker_y_bottom

            if target_y_blocker != -1:
                 dt_blocker = (target_y_blocker - sim_y) / sim_speed_y if sim_speed_y != 0 else float('inf')
                 if dt_blocker > 0.001: time_to_blocker_y = dt_blocker

        # --- 5.2 找出最早發生的事件 ---
        min_time = min(time_to_platform, time_to_wall_x, time_to_blocker_y)

        # --- 5.3 處理無法預測或卡住的情況 ---
        if min_time == float('inf') or min_time < 0:
             return my_platform_x + PLATFORM_WIDTH / 2

        # --- 5.4 更新模擬球和 Blocker 的位置 ---
        # Blocker 的位置也需要根據 min_time 更新
        next_sim_blocker_x = sim_blocker_x + sim_blocker_speed_x * min_time
        # Blocker 撞牆反彈 (在更新後的位置判斷)
        if next_sim_blocker_x <= 0 or next_sim_blocker_x >= SCREEN_WIDTH - BLOCKER_WIDTH:
             sim_blocker_speed_x *= -1 # 反轉 Blocker 速度
             # 修正 Blocker 位置到邊界內
             next_sim_blocker_x = max(0, min(next_sim_blocker_x, SCREEN_WIDTH - BLOCKER_WIDTH))

        # 更新球的位置
        sim_x += sim_speed_x * min_time
        sim_y += sim_speed_y * min_time
        # 更新 Blocker 的最終位置
        sim_blocker_x = next_sim_blocker_x

        # --- 5.5 根據發生的事件更新狀態 ---
        epsilon = 0.01
        # a) 到達平台?
        if abs(sim_y - platform_y_target) < epsilon or abs(min_time - time_to_platform) < epsilon:
            predicted_x_at_platform = sim_x
            break
        # b) 撞牆?
        elif abs(min_time - time_to_wall_x) < epsilon:
            sim_speed_x *= -1
            if sim_x <= 0: sim_x = 0.01
            elif sim_x >= SCREEN_WIDTH - BALL_SIZE: sim_x = SCREEN_WIDTH - BALL_SIZE - 0.01
        # c) 撞 Blocker?
        elif abs(min_time - time_to_blocker_y) < epsilon:
            if blocker_pos: # 確保 Blocker 存在
                # 使用更新後的 sim_blocker_x 進行碰撞判斷
                if sim_blocker_x - BALL_SIZE < sim_x < sim_blocker_x + BLOCKER_WIDTH:
                    edge_margin = 1.5
                    hit_side = False
                    if abs(sim_x - (sim_blocker_x - BALL_SIZE)) < edge_margin or \
                       abs(sim_x - (sim_blocker_x + BLOCKER_WIDTH)) < edge_margin:
                         hit_side = True

                    if hit_side:
                         sim_speed_x *= -1 # 側面碰撞反彈 X
                    sim_speed_y *= -1 # 上下碰撞反彈 Y

                    # 微調位置防止卡住
                    sim_x += sim_speed_x * 0.01
                    sim_y += sim_speed_y * 0.01
                # else: X 座標錯過 Blocker，繼續模擬
            # else: Blocker 消失了？繼續模擬
        else:
             return my_platform_x + PLATFORM_WIDTH / 2

    # --- 6. 計算最終返回的目標平台中心 X ---
    if predicted_x_at_platform is not None:
        target_ball_center_x = predicted_x_at_platform + BALL_SIZE / 2
        target_platform_center_x = target_ball_center_x
        min_center = PLATFORM_WIDTH / 2
        max_center = SCREEN_WIDTH - PLATFORM_WIDTH / 2
        target_platform_center_x = max(min_center, min(target_platform_center_x, max_center))
        return target_platform_center_x
    else:
        # 循環結束仍未預測成功
        return my_platform_x + PLATFORM_WIDTH / 2
    
class MLPlay:
    def __init__(self, ai_name, *args, **kwargs):
        """
        用於 ML 玩家 2 的建構子
        """
        self.side = "2P"
        self.player_no = int(ai_name.strip('P'))
        self.model = None
        self.prev_blocker_x = None # <--- 儲存上一幀 Blocker 的 X 座標
        self.blocker_speed_x = 0   # <--- 推斷出的 Blocker 速度 (初始為 0)

        # --- 載入模型 ---
        student_id = "F74101115" 
        model_filename = f"model_{self.side}_{student_id}.pickle"

        # 因為檔名問題
        if self.side == "1P":
            side_prefix = "P1"
        elif self.side == "2P":
            side_prefix = "P2"
        else: # 理論上不應該發生
            side_prefix = self.side
        model_filename = f"model_{side_prefix}_{student_id}.pickle"

        model_path = os.path.join(os.path.dirname(__file__), model_filename)

        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            print(f"[{self.side}] 模型 '{model_filename}' 載入成功。") 
        except FileNotFoundError:
            print(f"[{self.side}] 錯誤: 在 '{model_path}' 找不到模型檔案。")
            self.model = None
        except Exception as e:
            print(f"[{self.side}] 載入模型時發生錯誤: {e}。")
            self.model = None

    def update(self, scene_info, *args, **kwargs):
        """
        根據模型預測或備用邏輯生成指令。
        """
        command = "NONE"
        platform_width = 40

        # 1. 檢查遊戲狀態
        if scene_info["status"] != "GAME_ALIVE":
            return "RESET"

        # 2. 發球
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
             predicted_center = predict_pingpong_landing(scene_info, self.side, self.blocker_speed_x) 

        my_platform_x = scene_info[f"platform_{self.side}"][0]
        my_platform_center = my_platform_x + platform_width / 2

        # 5. 使用模型或備用邏輯決定指令
        if self.model:
            # --- 準備模型的特徵向量  ---
            try:
                if "ball_speed" not in scene_info: raise ValueError("'ball_speed' missing")
                ball_speed_x, ball_speed_y = scene_info["ball_speed"]
                pred_center_feature = predicted_center if predicted_center is not None else my_platform_center

                features = [
                    scene_info["ball"][0], scene_info["ball"][1],
                    ball_speed_x, ball_speed_y,
                    scene_info["platform_1P"][0], scene_info["platform_2P"][0],
                    current_blocker_x,
                    pred_center_feature,
                    self.blocker_speed_x # <--- 將 Blocker 速度也作為特徵
                ]
                # 確保特徵數量和順序與訓練時一致！
                if len(features) != 9:
                     raise ValueError(f"Incorrect number of features. Expected 9, got {len(features)}")

                feature_vector = np.array(features).reshape(1, -1)

                # --- 模型預測 ---
                prediction = self.model.predict(feature_vector)[0]
                command_map = {0: "MOVE_LEFT", 1: "MOVE_RIGHT", 2: "NONE"}
                command = command_map.get(prediction, "NONE")

            except Exception as e:
                 print(f"[{self.side}] 特徵提取或模型預測時發生錯誤: {e}。使用備用邏輯。")
                 # 備用邏輯
                 if predicted_center is not None:
                     if my_platform_center < predicted_center - 3: command = "MOVE_RIGHT"
                     elif my_platform_center > predicted_center + 3: command = "MOVE_LEFT"
                     else: command = "NONE"
                 else: # 移到中間
                     if my_platform_center < 100 - 5: command = "MOVE_RIGHT"
                     elif my_platform_center > 100 + 5: command = "MOVE_LEFT"
                     else: command = "NONE"
        else:
            # --- 備用邏輯 (如果模型未載入) ---
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