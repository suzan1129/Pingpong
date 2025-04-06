import math

def predict_pingpong_landing(scene_info, previous_ball_position, side):
    """
    預測 Pingpong 球的落點 (平台中心 X 座標)
    Args:
        scene_info: 遊戲當前狀態
        previous_ball_position: 上一幀球的位置 (用於計算速度)
        side: "1P" 或 "2P"
    Returns:
        預測的平台中心目標 X 座標，如果無法預測則返回 None
    """
    ball_x, ball_y = scene_info["ball"]
    platform_1P_x, platform_1P_y = scene_info["platform_1P"] # y = 420
    platform_2P_x, platform_2P_y = scene_info["platform_2P"] # y = 70
    blocker_info = scene_info.get("blocker") # HARD 模式才有 (x, 240)
    screen_width = 200
    screen_height = 500
    ball_size = 5
    platform_width = 40
    blocker_width = 30
    blocker_height = 20

    # --- 計算球的速度 ---
    if previous_ball_position:
        prev_x, prev_y = previous_ball_position
        ball_speed_x = ball_x - prev_x
        ball_speed_y = ball_y - prev_y
    else:
        # 如果沒有上一幀資訊，嘗試從 scene_info 讀取 (如果 MLGame 版本支援)
        # 否則無法預測
        if "ball_speed" in scene_info:
             ball_speed_x, ball_speed_y = scene_info["ball_speed"]
        else:
             return None # 無法計算速度

    # --- 根據 side 決定目標 Y 和檢查方向 ---
    if side == "1P":
        platform_y_target = platform_1P_y # 球拍頂部 Y
        my_platform_x = platform_1P_x
        if ball_speed_y <= 0: # 球沒往下走
            return None
    elif side == "2P":
        platform_y_target = platform_2P_y + 10 # 球拍底部 Y
        my_platform_x = platform_2P_x
        if ball_speed_y >= 0: # 球沒往上走
            return None
    else:
        return None # 無效 side

    if ball_speed_y == 0: # 避免除以零
        return None

    # --- 模擬球的移動與預測 ---
    sim_ball_x = ball_x
    sim_ball_y = ball_y
    sim_speed_x = ball_speed_x
    sim_speed_y = ball_speed_y

    predicted_x_at_platform = None

    while True:
        # 計算到達目標 Y 或邊界的時間
        time_to_platform = float('inf')
        if sim_speed_y != 0:
            dt_platform = (platform_y_target - sim_ball_y) / sim_speed_y
            if dt_platform > 0.001: # 需要正向時間
                 time_to_platform = dt_platform

        time_to_hit_wall_x = float('inf')
        if sim_speed_x > 0: # 往右
            dt_wall_x = (screen_width - ball_size - sim_ball_x) / sim_speed_x if sim_speed_x != 0 else float('inf')
        elif sim_speed_x < 0: # 往左
            dt_wall_x = (0 - sim_ball_x) / sim_speed_x if sim_speed_x != 0 else float('inf')
        else: # x 速度為 0
             dt_wall_x = float('inf')

        if dt_wall_x <= 0.001: dt_wall_x = float('inf') # 忽略過小或負時間

        # --- 檢查是否撞到障礙物 (HARD 模式) ---
        time_to_blocker = float('inf')
        hit_blocker_this_step = False
        if blocker_info and sim_speed_y != 0:
            blocker_x, blocker_y_top = blocker_info # y=240
            blocker_y_bottom = blocker_y_top + blocker_height # y=260

            # 檢查是否朝障礙物移動
            if sim_speed_y > 0 and sim_ball_y < blocker_y_bottom: # 向下且在障礙物之上
                 time_to_hit_blocker_top = (blocker_y_top - ball_size - sim_ball_y) / sim_speed_y if sim_speed_y != 0 else float('inf')
                 if time_to_hit_blocker_top > 0.001: time_to_blocker = time_to_hit_blocker_top
            elif sim_speed_y < 0 and sim_ball_y > blocker_y_top: # 向上且在障礙物之下
                 time_to_hit_blocker_bottom = (blocker_y_bottom - sim_ball_y) / sim_speed_y if sim_speed_y != 0 else float('inf')
                 if time_to_hit_blocker_bottom > 0.001: time_to_blocker = time_to_hit_blocker_bottom

            if time_to_blocker <= 0.001: time_to_blocker = float('inf')


        # --- 找出最早發生的事件 ---
        min_time = min(time_to_platform, time_to_hit_wall_x, time_to_blocker)

        if min_time == float('inf') or min_time <= 0:
            # 無法預測或卡住
             # print(f"[{side}] Prediction failed: min_time={min_time}")
            return None # 或回傳目前平台中心

        # 更新球的位置到事件發生點
        sim_ball_x += sim_speed_x * min_time
        sim_ball_y += sim_speed_y * min_time

        # --- 處理事件 ---
        if min_time == time_to_platform:
            # 到達目標平台 Y
            predicted_x_at_platform = sim_ball_x
            break # 預測完成

        elif min_time == time_to_hit_wall_x:
            # 撞到左右牆壁
            sim_speed_x *= -1 # 反彈
             # 微調位置避免卡牆
            if sim_ball_x <= 0: sim_ball_x = 0
            elif sim_ball_x >= screen_width - ball_size: sim_ball_x = screen_width - ball_size


        elif min_time == time_to_blocker:
            # 撞到障礙物
            # 檢查 X 位置是否真的在障礙物範圍內
            blocker_x, _ = blocker_info
            if blocker_x - ball_size < sim_ball_x < blocker_x + blocker_width:
                # 真的撞到了
                 # print(f"[{side}] Hit Blocker predicted at x={sim_ball_x:.1f}, y={sim_ball_y:.1f}")
                sim_speed_y *= -1 # 只反彈 Y 方向
                 # 稍微移開避免重複碰撞
                sim_ball_y += sim_speed_y * 0.01
                # *** 簡化策略：直接放棄精確預測，讓板子回中間 ***
                # 你可以在這裡 return 100 (中間) 或 my_platform_x + platform_width/2 (目前位置)
                # return 100
                # 或者繼續模擬反彈後路徑 (如下)
            # else: # 雖然時間到了，但 X 座標錯過了障礙物，繼續模擬
                 # print(f"[{side}] Blocker time reached but missed at x={sim_ball_x:.1f}")
                pass # 繼續下一輪 while

        else: # 不應該發生
             # print(f"[{side}] Unexpected min_time case")
             return None


    # --- 計算最終目標平台中心 X ---
    if predicted_x_at_platform is not None:
        target_ball_center_x = predicted_x_at_platform + ball_size / 2
        target_platform_center_x = target_ball_center_x

        # 限制平台中心在可移動範圍內
        min_center = platform_width / 2
        max_center = screen_width - platform_width / 2
        target_platform_center_x = max(min_center, min(target_platform_center_x, max_center))

        # print(f"[{side}] Predicted target platform center: {target_platform_center_x:.1f}")
        return target_platform_center_x
    else:
        # print(f"[{side}] Prediction loop finished without result")
        return None # 無法預測