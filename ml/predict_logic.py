import math

# --- 常數定義 ---
SCREEN_WIDTH = 200
SCREEN_HEIGHT = 500
BALL_SIZE = 5
PLATFORM_WIDTH = 40
PLATFORM_HEIGHT = 10
BLOCKER_WIDTH = 30
BLOCKER_HEIGHT = 20
BLOCKER_Y_TOP = 240

# predict_pingpong_landing 函數 (加入側面碰撞近似處理)
def predict_pingpong_landing(scene_info, side):
    """
    預測 Pingpong 球的落點 (平台中心 X 座標) - 使用 scene_info['ball_speed']
    包含對障礙物側面碰撞的近似處理。
    """
    ball_x, ball_y = scene_info["ball"]
    platform_1P_x, platform_1P_y = scene_info["platform_1P"] # y=420
    platform_2P_x, platform_2P_y = scene_info["platform_2P"] # y=70
    blocker_pos = scene_info.get("blocker")

    if "ball_speed" not in scene_info:
        if side == "1P": return platform_1P_x + PLATFORM_WIDTH / 2
        if side == "2P": return platform_2P_x + PLATFORM_WIDTH / 2
        return None
    ball_speed_x, ball_speed_y = scene_info["ball_speed"]

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

    sim_x = float(ball_x)
    sim_y = float(ball_y)
    sim_speed_x = float(ball_speed_x)
    sim_speed_y = float(ball_speed_y)

    predicted_x_at_platform = None
    max_simulation_steps = 25 # 可以適當調整
    steps = 0

    while steps < max_simulation_steps:
        steps += 1

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
        if blocker_pos and sim_speed_y != 0:
            blocker_x, _ = blocker_pos
            blocker_y_bottom = BLOCKER_Y_TOP + BLOCKER_HEIGHT
            target_y_blocker = -1
            if sim_speed_y > 0 and sim_y < blocker_y_bottom:
                 target_y_blocker = BLOCKER_Y_TOP - BALL_SIZE
            elif sim_speed_y < 0 and sim_y > BLOCKER_Y_TOP:
                 target_y_blocker = blocker_y_bottom
            if target_y_blocker != -1:
                 dt_blocker = (target_y_blocker - sim_y) / sim_speed_y if sim_speed_y != 0 else float('inf')
                 if dt_blocker > 0.001: time_to_blocker_y = dt_blocker

        min_time = min(time_to_platform, time_to_wall_x, time_to_blocker_y)

        if min_time == float('inf') or min_time < 0:
             return my_platform_x + PLATFORM_WIDTH / 2

        sim_x += sim_speed_x * min_time
        sim_y += sim_speed_y * min_time

        epsilon = 0.01
        if abs(sim_y - platform_y_target) < epsilon or abs(min_time - time_to_platform) < epsilon:
            predicted_x_at_platform = sim_x
            break
        elif abs(min_time - time_to_wall_x) < epsilon:
            sim_speed_x *= -1
            if sim_x <= 0: sim_x = 0.01
            elif sim_x >= SCREEN_WIDTH - BALL_SIZE: sim_x = SCREEN_WIDTH - BALL_SIZE - 0.01
        elif abs(min_time - time_to_blocker_y) < epsilon:
            if blocker_pos:
                blocker_x, _ = blocker_pos
                if blocker_x - BALL_SIZE < sim_x < blocker_x + BLOCKER_WIDTH:
                    # --- 新增：檢查是否接近左右邊緣 ---
                    edge_margin = 1.5 # 邊緣判斷的容忍度 (可調整)
                    hit_side = False
                    if abs(sim_x - (blocker_x - BALL_SIZE)) < edge_margin: # 接近左邊緣
                         hit_side = True
                    elif abs(sim_x - (blocker_x + BLOCKER_WIDTH)) < edge_margin: # 接近右邊緣
                         hit_side = True

                    # 反彈邏輯
                    if hit_side: # 如果是側面碰撞 (或角落)
                         sim_speed_x *= -1 # 主要反彈 X
                    # 無論是否側面碰撞，Y 方向都發生了碰撞
                    sim_speed_y *= -1 # 反彈 Y
                    # --- 結束新增 ---

                    # 微調位置防止卡住
                    sim_x += sim_speed_x * 0.01
                    sim_y += sim_speed_y * 0.01
                # else: X 座標錯過，繼續模擬
            # else: Blocker 消失了？繼續模擬
        else:
             return my_platform_x + PLATFORM_WIDTH / 2

    if predicted_x_at_platform is not None:
        target_ball_center_x = predicted_x_at_platform + BALL_SIZE / 2
        target_platform_center_x = target_ball_center_x
        min_center = PLATFORM_WIDTH / 2
        max_center = SCREEN_WIDTH - PLATFORM_WIDTH / 2
        target_platform_center_x = max(min_center, min(target_platform_center_x, max_center))
        return target_platform_center_x
    else:
        return my_platform_x + PLATFORM_WIDTH / 2