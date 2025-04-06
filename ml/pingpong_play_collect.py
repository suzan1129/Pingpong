# ml/pingpong_play_collect.py
import pickle
import datetime
import os
import random
import numpy as np
# 導入需要 blocker_current_speed_x 的預測函數
from ml.predict_logic import predict_pingpong_landing

class MLPlay:
    def __init__(self, ai_name, *args, **kwargs):
        """
        用於資料收集的 AI 建構子 (只收集獲勝局)
        """
        self.side = ai_name
        self.player_no = int(ai_name.strip('P'))
        self.data_buffer = []
        self.prev_blocker_x = None # <--- 新增: 儲存上一幀 Blocker 的 X 座標
        self.blocker_speed_x = 0   # <--- 新增: 推斷出的 Blocker 速度 (初始為 0)

        # 創建資料夾 (如果不存在)
        self.data_folder = f"pingpong_data_{self.side}"
        if not os.path.exists(self.data_folder):
            try:
                os.makedirs(self.data_folder)
            except FileExistsError:
                pass
        print(f"[{self.side}] 資料收集 AI 初始化。獲勝數據將儲存至 '{self.data_folder}'")

    def update(self, scene_info, *args, **kwargs):
        """
        根據預測生成指令並收集獲勝局的數據。
        """
        command = "NONE"
        predicted_center = None
        platform_width = 40

        # 1. 檢查遊戲狀態
        if scene_info["status"] != "GAME_ALIVE":
            # --- 只儲存獲勝局的數據 ---
            should_save = False
            if self.side == "1P" and scene_info["status"] == "GAME_1P_WIN":
                should_save = True
                print(f"[{self.side}] 遊戲獲勝！準備儲存數據...")
            elif self.side == "2P" and scene_info["status"] == "GAME_2P_WIN":
                should_save = True
                print(f"[{self.side}] 遊戲獲勝！準備儲存數據...")

            if should_save and self.data_buffer:
                 timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                 filename = os.path.join(self.data_folder, f"data_win_{timestamp}.pickle")
                 self.save_data_to_pickle(filename)
            elif self.data_buffer:
                 self.data_buffer = []
            # --- 儲存邏輯結束 ---

            return "RESET"

        # 2. 發球 (如果根據 scene_info 球未發出)
        if not scene_info["ball_served"]:
            command = "SERVE_TO_LEFT" if random.random() < 0.5 else "SERVE_TO_RIGHT"
            self.prev_blocker_x = None # 重置 Blocker 追蹤
            self.blocker_speed_x = 0   # 重置 Blocker 速度
            return command

        # --- 球已在場上 ---
        # 3. 推斷 Blocker 速度 (如果 Blocker 存在)
        current_blocker_pos = scene_info.get("blocker")
        current_blocker_x = -1
        if current_blocker_pos:
            current_blocker_x = current_blocker_pos[0]
            if self.prev_blocker_x is not None:
                 delta_x = current_blocker_x - self.prev_blocker_x
                 if delta_x > 2: # 容忍一點誤差
                      self.blocker_speed_x = 5
                 elif delta_x < -2:
                      self.blocker_speed_x = -5
                 # else: 速度為 0 或剛反彈，保持上次速度
            # 更新上一幀 Blocker 位置 (必須在推斷之後！)
            self.prev_blocker_x = current_blocker_x
        else: # 非 Hard 模式或 Blocker 不存在
             self.prev_blocker_x = None
             self.blocker_speed_x = 0 # Blocker 不存在則速度為 0

        # 4. 預測與移動決策
        my_platform_x = scene_info[f"platform_{self.side}"][0]
        my_platform_center = my_platform_x + platform_width / 2

        if "ball_speed" in scene_info:
             # 調用預測函數，傳入推斷出的 Blocker 速度
             predicted_center = predict_pingpong_landing(scene_info, self.side, self.blocker_speed_x) # <--- 傳入速度
        # else: predicted_center remains None

        if predicted_center is not None:
            # 根據預測移動 (微調容錯區間)
            if my_platform_center < predicted_center - 2:
                command = "MOVE_RIGHT"
            elif my_platform_center > predicted_center + 2:
                command = "MOVE_LEFT"
            else:
                command = "NONE"
        else: # 預測失敗的後備策略：移向中間
            if my_platform_center < 100 - 5:
                 command = "MOVE_RIGHT"
            elif my_platform_center > 100 + 5:
                 command = "MOVE_LEFT"
            else:
                 command = "NONE"

        # 5. 收集數據 (僅針對移動指令，當球已發出且有速度信息時)
        if scene_info["ball_served"] and "ball_speed" in scene_info:
            if command in ["MOVE_LEFT", "MOVE_RIGHT", "NONE"]:
                 ball_speed_x, ball_speed_y = scene_info["ball_speed"]
                 # 使用預測中心 (如果可用)，否則使用當前平台中心作為後備特徵值
                 pred_center_feature = predicted_center if predicted_center is not None else my_platform_center

                 features = {
                     "ball_x": scene_info["ball"][0],
                     "ball_y": scene_info["ball"][1],
                     "ball_speed_x": ball_speed_x,
                     "ball_speed_y": ball_speed_y,
                     "platform_1P_x": scene_info["platform_1P"][0],
                     "platform_2P_x": scene_info["platform_2P"][0],
                     "blocker_x": current_blocker_x, # 使用當前 Blocker X (如果存在)
                     "predicted_center_calc": pred_center_feature,
                     "blocker_speed_x": self.blocker_speed_x # <--- 新增: 也收集推斷出的 Blocker 速度作為特徵
                 }

                 self.data_buffer.append({
                     "features": features,
                     "command": command,
                     "side": self.side
                 })

        return command

    def reset(self):
        """
        重置狀態。數據緩衝區在遊戲非獲勝結束時已清空。
        """
        self.data_buffer = [] # 確保每次 Reset 都清空緩衝區
        self.prev_blocker_x = None # 重置 Blocker 位置追蹤
        self.blocker_speed_x = 0   # 重置 Blocker 速度推斷
        # print(f"[{self.side}] 重置 AI 狀態。")
        pass

    def save_data_to_pickle(self, filename):
        """
        將收集到的數據緩衝區儲存到 pickle 文件並打印樣本數據。
        """
        if not self.data_buffer:
             print(f"[{self.side}] 沒有要儲存的獲勝局數據 (緩衝區為空)。")
             return

        # --- 在儲存前打印一些樣本數據 ---
        print(f"[{self.side}] 儲存數據至 {filename}. 緩衝區大小: {len(self.data_buffer)}")
        print("-" * 20 + " 樣本數據 " + "-" * 20)
        sample_indices = list(range(min(5, len(self.data_buffer)))) + \
                         list(range(max(0, len(self.data_buffer)-5), len(self.data_buffer)))
        printed_indices = set()

        for i in sample_indices:
            if i not in printed_indices and i < len(self.data_buffer):
                 data_point = self.data_buffer[i]
                 if not isinstance(data_point, dict): continue
                 print(f"  index {i}:")
                 print(f"    Side: {data_point.get('side', 'N/A')}")
                 print(f"    Command: {data_point.get('command', 'N/A')}")
                 features = data_point.get('features')
                 if features and isinstance(features, dict):
                      print(f"    Features:")
                      for key, value in features.items():
                           if isinstance(value, (float, np.floating)):
                               print(f"      {key}: {value:.2f}")
                           else:
                                print(f"      {key}: {value}")
                 else:
                      print(f"    Features: 無效或缺失")
                 printed_indices.add(i)
        print("-" * (40 + len(" 樣本數據 ")))
        # --- 打印結束 ---

        # 執行儲存
        try:
            with open(filename, "wb") as f:
                pickle.dump(self.data_buffer, f)
            print(f"[{self.side}] 獲勝局數據成功儲存至 {filename}")
        except Exception as e:
            print(f"[{self.side}] 儲存數據至 {filename} 時發生錯誤: {e}")
        finally:
             self.data_buffer = [] # 儲存後清空 buffer