# 乒乓球

<img src="https://raw.githubusercontent.com/PAIA-Playful-AI-Arena/pingpong/main/asset/logo.svg" alt="logo" width="100"/> 

![pygame](https://img.shields.io/github/v/tag/PAIA-Playful-AI-Arena/pingpong)
[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![MLGame](https://img.shields.io/badge/MLGame->9.5.3-<COLOR>.svg)](https://github.com/PAIA-Playful-AI-Arena/MLGame)
[![pygame](https://img.shields.io/badge/pygame-2.0.1-<COLOR>.svg)](https://github.com/pygame/pygame/releases/tag/2.0.1)

想要體驗一場有趣且刺激的乒乓球遊戲嗎？操控發球及反擊的時機讓對手無路可逃，喜歡快節奏的你一定要來體驗看看！

<img src="https://raw.githubusercontent.com/PAIA-Playful-AI-Arena/pingpong/main/asset/github/%E6%89%93%E4%B9%92%E4%B9%93.gif" height="500"/>

---

# 基礎介紹

## 啟動方式

- 直接啟動 [main.py](main.py) 即可執行

### 遊戲參數設定

```python
# main.py 
game = PingPong(difficulty="EASY", game_over_score=5,user_num=2,init_vel=7)

```

- `difficulty`：遊戲難度
    - `EASY`：簡單的乒乓球遊戲
    - `NORMAL`：加入切球機制
    - `HARD`：加入切球機制與障礙物
- `game_over_score`：指定遊戲結束的分數。當任一方得到指定的分數時，就結束遊戲。預設是 `3`，但如果啟動遊戲時有指定 `-1`
  選項，則結束分數會是 `1`。
- `init_vel`：設定初始球的 `X` 與 `Y` 速度。 預設為 `7`。

## 玩法

- 將球發往左邊/右邊
    - 1P:  `.`、`/`
    - 2P:  `Q`、`E`
- 移動板子
    - 1P: 左右方向鍵
    - 2P: `A`、`D`

1P 在下半部，2P 在上半部

## 目標

1. 讓對手沒接到球

### 通關條件

1. 自己的分數達到 `game_over_score`。

### 失敗條件

1. 對手的分數達到 `game_over_score`。

### 平手條件

1. 球速超過 `40`

## 遊戲系統

1. 遊戲物件
    - 球
        - 綠色正方形
        - 每場遊戲開始時，都是由 1P 先發球，之後每個回合輪流發球
        - 球由板子的位置發出，可以選擇往左或往右發球。如果沒有在 150 影格內發球，則會自動往隨機一個方向發球
        - 初始球速是每個影格 (±7, ±7)，發球後每 100 影格增加 1

    - 板子
        - 矩形，1P 是紅色的，2P 是藍色的
        - 板子移動速度是每個影格 (±5, 0)
        - 1P 板子的初始位置在 (80, 420)，2P 則在 (80, 70)

    - 障礙物
        - 黃色矩形
        - x 初始位置在 0 到 180 之間，每 20 為一單位隨機決定，y 初始位置固定在 240，移動速度為每影格 (±5, 0)
        - 障礙物會往復移動，初始移動方向是隨機決定的
        - 障礙物不會切球，球撞到障礙物會保持球的速度

      障礙物加入在 `HARD` 難度中。

2. 行動機制

   左右移動板子，每次移動 5px

3. 座標系統 (物件座標皆為左上角座標)
    - 螢幕大小 200 x 500
    - 板子 40 x 10
    - 球 5 x 5
    - 障礙物 30 x 20
      <img src="https://raw.githubusercontent.com/PAIA-Playful-AI-Arena/pingpong/main/asset/github/%E6%89%93%E4%B9%92%E4%B9%93-%E5%BA%A7%E6%A8%99%E5%9C%96.png" height="500"/>

4. 切球機制

   在板子接球時，球的 x 方向速度會因為板子的移動而改變：

    - 如果板子與球往同一個方向移動時，球的 x 方向速度會增加 3 (只增加一次)
    - 如果板子沒有移動，則球的 x 方向速度會恢復為目前的基礎速度
    - 如果板子與球往相反方向移動時，球會被打回原來過來的方向，其 x 方向速度恢復為目前的基礎速度

   切球機制加入在 `NORMAL` 與 `HARD` 難度中。

---

# 進階說明

## 使用ＡＩ玩遊戲

```bash
# 在 pingpong 資料夾中打開終端機 
python -m mlgame -i ./ml/ml_play_template_1P.py -i ./ml/ml_play_template_2P.py  ./ --difficulty HARD --game_over_score 3  --init_vel 10
```

## ＡＩ範例

```python

class MLPlay:
    def __init__(self, ai_name, *args, **kwargs):
        """
        Constructor

        @param ai_name A string "1P" or "2P" indicates that the `MLPlay` is used by
               which side.
        """
        self.ball_served = False
        self.side = ai_name
        print(kwargs)

    def update(self, scene_info, *args, **kwargs):
        """
        Generate the command according to the received scene information
        """
        if scene_info["status"] != "GAME_ALIVE":
            return "RESET"

        if not self.ball_served:
            self.ball_served = True
            return "SERVE_TO_RIGHT"
        else:
            return "MOVE_LEFT"

    def reset(self):
        """
        Reset the status
        """
        print("reset " + self.side)
        self.ball_served = False

```

#### 初始化參數

- ai_name: 字串。其值只會是 `"1P"` 或 `"2P"`，代表這個程式被哪一邊使用。
- kwargs: 字典。裡面會包含遊戲初始化的參數
  ```json

    {"game_params": 
      {
        "difficulty": "HARD",
        "game_over_score": 3
      }
    }

    ```

## 遊戲資訊

- scene_info 的資料格式如下

```json
{
  "frame": 24,
  "status": "GAME_ALIVE",
  "ball": [
    63,
    241
  ],
  "ball_speed": [
    7,
    7
  ],
  "ball_served": true,
  "serving_side": "2P",
  "platform_1P": [
    0,
    420
  ],
  "platform_2P": [
    0,
    70
  ],
  "blocker": [
    140,
    240
  ]
}

```

- `frame`：遊戲畫面更新的編號
- `status`：字串。目前的遊戲狀態，會是以下的值其中之一：
    - `GAME_ALIVE`：遊戲正在進行中
    - `GAME_1P_WIN`：這回合 1P 獲勝
    - `GAME_2P_WIN`：這回合 2P 獲勝
    - `GAME_DRAW`：這回合平手
- `ball` `(x, y)` tuple。球的位置。
- `ball_speed`：`(x, y)` tuple。目前的球速。
- `ball_served`：`true` or `false` 布林值 boolean。表示是否已經發球。
- `serving_side`：`1P` or `2P`  字串 string。表示發球方。
- `platform_1P`：`(x, y)` tuple。1P 板子的位置。
- `platform_2P`：`(x, y)` tuple。2P 板子的位置。
- `blocker`：`(x, y)` tuple。障礙物的位置。如果選擇的難度不是 `HARD`，則其值為 `None`。

## 動作指令

- 在 update() 最後要回傳一個字串，主角物件即會依照對應的字串行動，一次只能執行一個行動。
    - `SERVE_TO_LEFT`：將球發向左邊
    - `SERVE_TO_RIGHT`：將球發向右邊
    - `MOVE_LEFT`：將板子往左移
    - `MOVE_RIGHT`：將板子往右移
    - `NONE`：無動作

## 遊戲結果

- 最後結果會顯示在 console 介面中，若是 PAIA 伺服器上執行，會回傳下列資訊到平台上。

```json
{
  "frame_used": 54,
  "state": "FINISH",
  "attachment": [
    {
      "player": "ml_1P",
      "rank": 1,
      "score": 1,
      "status": "GAME_PASS",
      "ball_speed": [
        7,
        -7
      ]
    },
    {
      "player": "ml_2P",
      "rank": 2,
      "score": 0,
      "status": "GAME_OVER",
      "ball_speed": [
        7,
        -7
      ]
    }
  ]
}
```

- `frame_used`：表示使用了多少個 frame
- `state`：表示遊戲結束的狀態
    - `FAIL`：遊戲結束
    - `FINISH`：遊戲完成
- `attachment`：紀錄遊戲各個玩家的結果與分數等資訊
    - `player`：玩家編號
    - `rank`：排名
    - `score`：各玩家獲勝的次數
    - `status`：玩家的狀態
        - `GAME_PASS`：該玩家獲勝
        - `GAME_OVER`：該玩家失敗
        - `GAME_DRAW`：雙方平手
    - `ball_speed`：球的速度

## 關於球的物理

球在移動中，下一幀會穿牆的時候，會移動至球的路徑與碰撞表面的交點。
<img src="https://raw.githubusercontent.com/PAIA-Playful-AI-Arena/pingpong/main/asset/github/%E6%89%93%E4%B9%92%E4%B9%93-%E7%90%83%E7%9A%84%E7%89%A9%E7%90%86.png" height="500"/>

---
