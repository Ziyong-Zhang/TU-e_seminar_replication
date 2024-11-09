import pandas as pd
import threading
import random
from datetime import datetime, timedelta

number = 500 # number of boxes: 1000 1500 2000
number_name = 1 # 1 2 3 4
# Locks to ensure stations are accessed by one box at a time
fill_station_lock = threading.Lock()
seal_station_lock = threading.Lock()

df_lock = threading.Lock()

# DataFrame to log events
event_log_df = pd.DataFrame(columns=['idx', 'eventId', 'activity', 'timestamp', 'timestampVar', 'box', 'batchPosition', 'equipment', 'log'])

# Define the sequence of activities
box_process_steps = ['LoadFS', 'Fill', 'UnloadFS', 'LoadSS', 'Seal', 'UnloadSS']

# Function to log a box's activities through the assembly line
def log_box_process(batch_pos: str, box_id: str, equipment_id: int, event_counter: list, timestamp: datetime):
    global event_log_df

    # Process the box through the Fill Station
    with fill_station_lock:
        for activity in box_process_steps[:3]:  # LoadFS, Fill, UnloadFS
            event_counter[0] += 1
            if activity == 'Fill':
                with df_lock:
                    event_log_df.loc[len(event_log_df)] = [
                    len(event_log_df), f"e{event_counter[0]}", activity, timestamp.strftime('%d/%m/%Y %H:%M:%S'), f"t{event_counter[0]}",
                    "", "", equipment_id, "GeneratedExample"
                ]
            else:
                with df_lock:
                    event_log_df.loc[len(event_log_df)] = [
                    len(event_log_df), f"e{event_counter[0]}", activity, timestamp.strftime('%d/%m/%Y %H:%M:%S'), f"t{event_counter[0]}",
                    "", batch_pos, equipment_id, "GeneratedExample"
                ]
            timestamp += timedelta(seconds=1)

    # Process the box through the Seal Station
    with seal_station_lock:
        for activity in box_process_steps[3:]:  # LoadSS, Seal, UnloadSS
            event_counter[0] += 1
            if activity == 'Seal':
                with df_lock:
                    event_log_df.loc[len(event_log_df)] = [
                    len(event_log_df), f"e{event_counter[0]}", activity, timestamp.strftime('%d/%m/%Y %H:%M:%S'), f"t{event_counter[0]}",
                    box_id, "", equipment_id, "GeneratedExample"
                ]
            else:
                with df_lock:
                    event_log_df.loc[len(event_log_df)] = [
                    len(event_log_df), f"e{event_counter[0]}", activity, timestamp.strftime('%d/%m/%Y %H:%M:%S'), f"t{event_counter[0]}",
                    "", batch_pos, equipment_id, "GeneratedExample"
                ]
            timestamp += timedelta(seconds=1)
    return timestamp


# Simulating the Assembly Line process with multiple batches and boxes
def generate_process_log():
    counter = 1
    event_counter = [0]
    batch_positions = ['x', 'y', 'z']
    # equipment_ids = [random.choice([1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 1111, 2111, 3111, 4111, 5111, 6111, 7111, 8111, 9111])]
    # equipment_id = random.choice([1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 1111, 2111, 3111, 4111, 5111, 6111, 7111, 8111, 9111])
    
    start_time = datetime(2024, 10, 1, 9, 0, 0)

    global number
    while counter < number:
        # Load a tray of boxes into the assembly line (LoadAL)
        equipment_id = random.choice([1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 1111, 2111, 3111, 4111, 5111, 6111, 7111, 8111, 9111])

        event_log_df.loc[len(event_log_df)] = [
                len(event_log_df), f"e{event_counter[0] + 1}", 'LoadAL', start_time.strftime('%d/%m/%Y %H:%M:%S'), f't{event_counter[0] + 1}',
                "", "", equipment_id, "GeneratedExample"
            ]
        start_time += timedelta(seconds=1)
        event_counter[0] += 1
        
        random.shuffle(batch_positions)
        
        # Start threading to simulate boxes moving through the assembly line
        threads = []
        for i in range(3):  # Three boxes per tray (batch)
            box_id = f'b{counter + i}'
            thread = threading.Thread(target=log_box_process, args=(batch_positions[i], box_id, equipment_id, event_counter, start_time))
            threads.append(thread)
            thread.start()
            start_time += timedelta(seconds=6)  # Adjust time increment for each box's total processing time (6 steps)

        for thread in threads:
            thread.join()

        # Unload the tray from the assembly line (UnloadAL)
        event_counter[0] += 1
        event_log_df.loc[len(event_log_df)] = [
            len(event_log_df), f"e{event_counter[0]}", 'UnloadAL', start_time.strftime('%d/%m/%Y %H:%M:%S'), f't{event_counter[0]}',
            "", "", equipment_id, "GeneratedExample"
        ]
        start_time += timedelta(seconds=1)
        counter += 3

# Generate the log data
generate_process_log()

# Save the event log to a CSV file
event_log_df.to_csv(f'./box_process_data/event_data_generated_{number_name}.csv', index=False)
