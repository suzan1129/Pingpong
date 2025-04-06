import math

import math

# --- 常數定義 ---
SCREEN_WIDTH = 200
BALL_SIZE = 5
PLATFORM_WIDTH = 40
BLOCKER_WIDTH = 30
BLOCKER_HEIGHT = 20
BLOCKER_Y_TOP = 240 # Blocker 固定 Y 座標

def predict_pingpong_landing(scene_info: dict, side: str):
    """
    預測 Pingpong 球的落點 (返回目標平台中心 X 座標 或 None)
    """
    ball_x, ball_y = scene_info["ball"]
    # --- 安全地獲取速度和 Blocker ---
    if "ball_speed" not in scene_info: return None
    ball_speed_x, ball_speed_y = scene_info["ball_speed"]
    blocker_pos = scene_info.get("blocker") # 使用 get 避免 KeyError

    # --- 設置目標和檢查方向 ---
    if side == "1P":
        platform_y_target = 415 # 1P 接球目標 Y (可微調)
        if ball_speed_y <= 0: return None # 球沒往下走，1P 不需預測
        platform_x_current = scene_info["platform_1P"][0]
    elif side == "2P":
        platform_y_target = 80  # 2P 接球目標 Y (球拍下緣附近)
        if ball_speed_y >= 0: return None # 球沒往上走，2P 不需預測
        platform_x_current = scene_info["platform_2P"][0]
    else:
        raise ValueError("Invalid player side. Use '1P' or '2P'.")

    if ball_speed_y == 0: return None # 水平移動無法到達

    # --- 初始化模擬 ---
    sim_x = float(ball_x) # 使用浮點數進行模擬
    sim_y = float(ball_y)
    sim_speed_x = float(ball_speed_x)
    sim_speed_y = float(ball_speed_y)

    max_steps = 300 # 增加模擬步數上限，防止無限循環
    steps = 0

    # --- 模擬循環 ---
    while steps < max_steps:
        steps += 1

        # 計算到達目標 Y 的時間 (如果 Y 速度不變)
        time_to_target_y = float('inf')
        if sim_speed_y != 0:
            dt = (platform_y_target - sim_y) / sim_speed_y
            # 只考慮未來的時間 (允許非常小的負值以處理剛過目標的情況)
            if dt > -0.01:
                time_to_target_y = max(0, dt)

        # 計算撞左右牆的時間
        time_to_wall_x = float('inf')
        if sim_speed_x > 0:
            dt_wall = (SCREEN_WIDTH - BALL_SIZE - sim_x) / sim_speed_x if sim_speed_x != 0 else float('inf')
            if dt_wall > 0.001: time_to_wall_x = dt_wall
        elif sim_speed_x < 0:
            dt_wall = (0 - sim_x) / sim_speed_x if sim_speed_x != 0 else float('inf')
            if dt_wall > 0.001: time_to_wall_x = dt_wall

        # 計算撞 Blocker 的時間
        time_to_blocker_y = float('inf')
        blocker_hit_surface_y = -1
        if blocker_pos and sim_speed_y != 0:
            blocker_x, _ = blocker_pos # Blocker Y 固定為 BLOCKER_Y_TOP
            blocker_y_bottom = BLOCKER_Y_TOP + BLOCKER_HEIGHT

            # 球向下運動，可能撞 Blocker 頂部
            if sim_speed_y > 0 and sim_y < blocker_y_bottom:
                target_y = BLOCKER_Y_TOP - BALL_SIZE # 球頂撞 Blocker 頂
                dt_blocker = (target_y - sim_y) / sim_speed_y if sim_speed_y != 0 else float('inf')
                if dt_blocker > 0.001:
                    time_to_blocker_y = dt_blocker
                    blocker_hit_surface_y = BLOCKER_Y_TOP
            # 球向上運動，可能撞 Blocker 底部
            elif sim_speed_y < 0 and sim_y > BLOCKER_Y_TOP:
                target_y = blocker_y_bottom # 球底撞 Blocker 底
                dt_blocker = (target_y - sim_y) / sim_speed_y if sim_speed_y != 0 else float('inf')
                if dt_blocker > 0.001:
                    time_to_blocker_y = dt_blocker
                    blocker_hit_surface_y = blocker_y_bottom

        # 找出最短時間
        min_time = min(time_to_target_y, time_to_wall_x, time_to_blocker_y)

        # 如果無法到達任何地方或時間異常
        if min_time == float('inf') or min_time < 0:
            # 返回當前平台中心作為後備
            return platform_x_current + PLATFORM_WIDTH / 2

        # --- 更新位置 ---
        sim_x += sim_speed_x * min_time
        sim_y += sim_speed_y * min_time

        # --- 處理事件 ---
        epsilon = 0.001
        # 到達目標 Y?
        if abs(min_time - time_to_target_y) < epsilon:
            landing_x = sim_x
            # --- 計算並返回目標平台中心 ---
            target_platform_center_x = landing_x + BALL_SIZE / 2
            min_center = PLATFORM_WIDTH / 2
            max_center = SCREEN_WIDTH - PLATFORM_WIDTH / 2
            target_platform_center_x = max(min_center, min(target_platform_center_x, max_center))
            return target_platform_center_x # <--- 返回數值

        # 撞牆?
        elif abs(min_time - time_to_wall_x) < epsilon:
            sim_speed_x *= -1
            # 微調防止卡牆
            if sim_x <= 0: sim_x = 0.01
            elif sim_x >= SCREEN_WIDTH - BALL_SIZE: sim_x = SCREEN_WIDTH - BALL_SIZE - 0.01

        # 撞 Blocker?
        elif abs(min_time - time_to_blocker_y) < epsilon:
            if blocker_pos: # 再次確認 Blocker 存在
                blocker_x, _ = blocker_pos
                # 檢查 X 範圍 (考慮球寬)
                if blocker_x - BALL_SIZE < sim_x < blocker_x + BLOCKER_WIDTH:
                     sim_speed_y *= -1 # 只反彈 Y
                     # 微調防止卡住
                     sim_y += sim_speed_y * 0.01
                     # 可以選擇在這裡 return 100 或 platform_x_current + PLATFORM_WIDTH / 2 作為保守策略
                     # return 100
                # else: X 座標沒撞到，繼續模擬
            # else: Blocker 不存在了？繼續模擬

        else: # 未知情況
             return platform_x_current + PLATFORM_WIDTH / 2 # 返回後備值

    # 如果循環結束還沒返回 (可能超過 max_steps)
    return platform_x_current + PLATFORM_WIDTH / 2 # 返回後備值