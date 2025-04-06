# ml/pingpong_model_trainer.py
import pickle
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score
import os
import glob
import argparse

def load_data_from_pickle(folder_path):
    """Loads all pickle files from a specified folder."""
    all_data = []
    file_pattern = os.path.join(folder_path, "*.pickle")
    filenames = glob.glob(file_pattern)

    if not filenames:
        print(f"Warning: No pickle files found in folder '{folder_path}'.")
        return None

    print(f"Found {len(filenames)} pickle files in folder '{folder_path}'.")
    for filename in filenames:
        try:
            with open(filename, "rb") as f:
                data = pickle.load(f)
            # print(f"Data loaded from {filename}, size: {len(data)}")
            all_data.extend(data) # data is expected to be a list of dictionaries
        except Exception as e:
            print(f"Error loading data from {filename}: {e}")

    print(f"Total data loaded from {folder_path}: {len(all_data)} items")
    return all_data

def preprocess_data(all_game_data, target_side):
    """從載入的遊戲數據中為目標玩家提取特徵和標籤。"""
    features = []
    labels = []

    command_map = {"MOVE_LEFT": 0, "MOVE_RIGHT": 1, "NONE": 2}

    # --- 關鍵修改：定義包含所有 9 個特徵的鍵名和順序 ---
    feature_keys = [
        "ball_x", "ball_y", "ball_speed_x", "ball_speed_y",
        "platform_1P_x", "platform_2P_x", "blocker_x",
        "predicted_center_calc",
        "blocker_speed_x" # <--- 確保包含這個新特徵
    ]

    print(f"為玩家 {target_side} 預處理數據...")
    valid_data_count = 0
    for item in all_game_data:
         if isinstance(item, dict) and item.get('side') == target_side and 'features' in item and 'command' in item:
            feat_dict = item['features']
            command = item['command']

            # 檢查是否包含所有必需的特徵鍵
            if all(key in feat_dict for key in feature_keys):
                 # 按照 feature_keys 定義的順序提取特徵值
                 try:
                     # 確保提取的值是數值型
                     feature_vector = [float(feat_dict[key]) for key in feature_keys]
                     features.append(feature_vector)

                     if command in command_map:
                         labels.append(command_map[command])
                         valid_data_count += 1
                     # else: 忽略無效指令
                 except (TypeError, ValueError) as e:
                      print(f"警告: 提取特徵時跳過無效數據點: {e}, data={feat_dict}")
                      pass # 跳過無法轉換為 float 的數據
            # else:
            #      print(f"警告: 跳過缺失特徵的數據點: {feat_dict.keys()}")

    if not features:
         print("錯誤: 未能提取任何有效特徵。請檢查數據格式和 feature_keys。")
         return np.array([]), np.array([])

    print(f"預處理完成。為玩家 {target_side} 提取了 {valid_data_count} 個有效數據點。")
    return np.array(features), np.array(labels)


def train_model(features, labels):
    """訓練 KNN 模型並評估準確率 (使用固定的 n_neighbors=5)。"""
    N_NEIGHBORS = 5 # <--- 直接在這裡設定 K 值

    if features.shape[0] < N_NEIGHBORS * 2:
        print(f"錯誤: 數據不足 ({features.shape[0]}) 無法使用 n_neighbors={N_NEIGHBORS} 進行訓練。")
        return None, 0.0

    print(f"使用固定的 n_neighbors={N_NEIGHBORS} 訓練 KNN 模型...")
    print(f"特徵維度: {features.shape}, 標籤維度: {labels.shape}")

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=0.2, random_state=42, stratify=labels
        )
    except ValueError:
         print("警告: 無法進行分層抽樣，使用普通抽樣。")
         X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=0.2, random_state=42
        )

    print(f"訓練集大小: {len(X_train)}, 測試集大小: {len(X_test)}")
    if len(X_train) == 0 or len(X_test) == 0:
         print("錯誤: 訓練集或測試集在分割後為空。")
         return None, 0.0

    # 直接使用 N_NEIGHBORS
    model = KNeighborsClassifier(n_neighbors=N_NEIGHBORS)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"模型訓練完成。測試準確率: {accuracy:.4f}")

    return model, accuracy


def save_model(model, filename):
    """Saves the trained model to a pickle file."""
    print(f"Saving model to {filename}...")
    try:
        with open(filename, "wb") as f:
            pickle.dump(model, f)
        print(f"Model saved successfully.")
    except Exception as e:
        print(f"Error saving model: {e}")

def main():
    parser = argparse.ArgumentParser(description="訓練乒乓球 KNN 模型。")
    parser.add_argument("--data_folder", type=str, required=True,
                        help="包含遊戲數據 pickle 檔案的資料夾路徑 (例如, ./ml/pingpong_data_1P)。")
    parser.add_argument("--side", type=str, required=True, choices=['1P', '2P'],
                        help="為哪個玩家訓練模型 (1P 或 2P)。")
    parser.add_argument("--output_model", type=str, required=True,
                        help="訓練好的模型檔案名稱 (例如, ./ml/model_P1_YourStudentID.pickle)。")
    # 移除 neighbors 參數解析
    # parser.add_argument("--neighbors", type=int, default=5, help="KNN 的鄰居數量 (預設: 5)。")
    args = parser.parse_args()

    all_game_data = load_data_from_pickle(args.data_folder)
    if not all_game_data: return

    features, labels = preprocess_data(all_game_data, args.side)
    if features.size == 0: return

    # 調用修改後的 train_model，不再傳遞 neighbors 參數
    model, accuracy = train_model(features, labels)

    if model:
        save_model(model, args.output_model)

if __name__ == '__main__':
    main()