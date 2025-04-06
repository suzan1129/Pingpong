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
    """Extracts features and labels from the loaded game data for the target side."""
    features = []
    labels = []

    command_map = {"MOVE_LEFT": 0, "MOVE_RIGHT": 1, "NONE": 2}
    feature_keys = [ # Define the exact order of features
        "ball_x", "ball_y", "ball_speed_x", "ball_speed_y",
        "platform_1P_x", "platform_2P_x", "blocker_x", "predicted_center_calc"
    ]


    print(f"Preprocessing data for side: {target_side}...")
    count = 0
    for item in all_game_data:
         # Ensure the item is a dictionary and contains 'side' and 'features'
         if isinstance(item, dict) and item.get('side') == target_side and 'features' in item and 'command' in item:
            feat_dict = item['features']
            command = item['command']

            # Check if all feature keys exist
            if all(key in feat_dict for key in feature_keys):
                 # Extract features in the defined order
                feature_vector = [feat_dict[key] for key in feature_keys]
                features.append(feature_vector)

                if command in command_map:
                    labels.append(command_map[command])
                    count += 1
                # else: Ignore data points with invalid commands (like SERVE)

    if not features:
         print("Error: No valid features extracted. Check data format and feature keys.")
         return np.array([]), np.array([])

    print(f"Preprocessing complete. Extracted {count} valid data points for {target_side}.")
    return np.array(features), np.array(labels)

def train_model(features, labels, n_neighbors=5):
    """Trains a KNN model and evaluates its accuracy."""
    if features.shape[0] < n_neighbors * 2: # Need enough data for split and neighbors
        print(f"Error: Not enough data ({features.shape[0]}) to train with n_neighbors={n_neighbors}.")
        return None, 0.0

    print(f"Training KNN model with n_neighbors={n_neighbors}...")
    print(f"Feature shape: {features.shape}, Label shape: {labels.shape}")

    # Stratify might be useful if commands are imbalanced
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=0.2, random_state=42, stratify=labels
        )
    except ValueError: # Handle cases where stratification isn't possible (e.g., only one class)
         print("Warning: Could not stratify split, using regular split.")
         X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=0.2, random_state=42
        )


    print(f"Train set size: {len(X_train)}, Test set size: {len(X_test)}")
    if len(X_train) == 0 or len(X_test) == 0:
         print("Error: Training or testing set is empty after split.")
         return None, 0.0


    model = KNeighborsClassifier(n_neighbors=n_neighbors)
    model.fit(X_train, y_train)

    # Evaluate accuracy
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model training complete. Test Accuracy: {accuracy:.4f}")

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
    parser = argparse.ArgumentParser(description="Train Pingpong KNN model.")
    parser.add_argument("--data_folder", type=str, required=True,
                        help="Path to the folder containing game data pickle files (e.g., ./pingpong_data_1P).")
    parser.add_argument("--side", type=str, required=True, choices=['1P', '2P'],
                        help="Which side to train the model for (1P or 2P).")
    parser.add_argument("--output_model", type=str, required=True,
                        help="Filename for the trained model (e.g., model_P1_YourStudentID.pickle).")
    parser.add_argument("--neighbors", type=int, default=5,
                        help="Number of neighbors for KNN (default: 5).")
    args = parser.parse_args()

    # --- 1. Load Data ---
    all_game_data = load_data_from_pickle(args.data_folder)
    if not all_game_data:
        print("Exiting due to data loading issues.")
        return

    # --- 2. Preprocess Data ---
    features, labels = preprocess_data(all_game_data, args.side)
    if features.size == 0:
        print("Exiting due to preprocessing issues.")
        return

    # --- 3. Train Model ---
    model, accuracy = train_model(features, labels, n_neighbors=args.neighbors)

    # --- 4. Save Model ---
    if model:
        # Ensure the output model filename matches the side (optional check)
        if f"_{args.side}_" not in args.output_model:
             print(f"Warning: Output model name '{args.output_model}' might not match the trained side '{args.side}'.")
        save_model(model, args.output_model)
    else:
        print("Exiting because model training failed.")

if __name__ == '__main__':
    main()