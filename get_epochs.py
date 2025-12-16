#!/usr/bin/env python3
"""
Script to fetch epoch data from Gonka.ai API and generate a CSV report.
Gets the current epoch and processes the last N epochs with their start/end times.
"""

import json
import csv
import requests
from datetime import datetime
from typing import Optional, Dict, List

# Configuration
AMOUNT_EPOCH = 10  # Number of recent epochs to process
API_BASE_URL = "http://node2.gonka.ai:8000"
BLOCKCHAIN_API_URL = "http://node2.gonka.ai:26657"


def get_current_epoch() -> int:
    """Get the current epoch ID from the API."""
    url = f"{API_BASE_URL}/v1/epochs/current/participants"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        # epoch_id is inside active_participants
        epoch_id = data.get("active_participants", {}).get("epoch_id")
        if epoch_id is None:
            raise ValueError("epoch_id not found in response")
        print(f"Current epoch ID: {epoch_id}")
        return epoch_id
    except requests.RequestException as e:
        print(f"Error fetching current epoch: {e}")
        raise
    except (KeyError, ValueError) as e:
        print(f"Error parsing current epoch data: {e}")
        raise


def get_epoch_start_block(epoch_id: int) -> Optional[int]:
    """Get the start block height for a specific epoch."""
    url = f"{API_BASE_URL}/v1/epochs/{epoch_id}/participants"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        block_height = data.get("active_participants", {}).get("poc_start_block_height")
        if block_height is None:
            print(f"Warning: Could not find start block for epoch {epoch_id}")
            return None
        return block_height
    except requests.RequestException as e:
        print(f"Error fetching epoch {epoch_id} data: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Error parsing epoch {epoch_id} data: {e}")
        return None


def get_block_timestamp(block_height: int) -> Optional[datetime]:
    """Get the timestamp for a specific block height."""
    url = f"{BLOCKCHAIN_API_URL}/block?height={block_height}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        time_str = data.get("result", {}).get("block", {}).get("header", {}).get("time")
        if time_str is None:
            print(f"Warning: Could not find timestamp for block {block_height}")
            return None
        # Parse ISO format timestamp: "2025-11-24T03:42:11.812952356Z" or "2025-11-14T14:31:23.908096665+00:00"
        # Handle nanoseconds by truncating to microseconds (6 digits)
        if "." in time_str:
            # Split on decimal point
            parts = time_str.split(".")
            if len(parts) == 2:
                # Truncate nanoseconds to microseconds
                decimal_part = parts[1]
                # Remove timezone suffix if present
                if "+" in decimal_part:
                    decimal_part, tz = decimal_part.split("+", 1)
                    time_str = f"{parts[0]}.{decimal_part[:6]}+{tz}"
                elif "Z" in decimal_part:
                    decimal_part = decimal_part.replace("Z", "")
                    time_str = f"{parts[0]}.{decimal_part[:6]}Z"
                else:
                    time_str = f"{parts[0]}.{decimal_part[:6]}"
        
        # Replace Z with +00:00 for fromisoformat
        if time_str.endswith("Z"):
            time_str = time_str[:-1] + "+00:00"
        
        dt = datetime.fromisoformat(time_str)
        return dt
    except requests.RequestException as e:
        print(f"Error fetching block {block_height} data: {e}")
        return None
    except (ValueError, KeyError) as e:
        print(f"Error parsing block {block_height} timestamp: {e}")
        return None


def format_datetime(dt: datetime) -> str:
    """Format datetime as YYYY-MM-DD HH:MM."""
    return dt.strftime("%Y-%m-%d %H:%M")


def format_duration(start: datetime, end: datetime) -> str:
    """Format duration as HH:MM:SS."""
    delta = end - start
    total_seconds = int(delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def process_epochs(amount_epoch: int) -> List[Dict]:
    """Process the last N epochs and return their data."""
    current_epoch = get_current_epoch()
    
    # Calculate epoch range
    first_epoch = max(1, current_epoch - amount_epoch + 1)
    last_epoch = current_epoch
    
    print(f"Processing epochs from {first_epoch} to {last_epoch}")
    
    epochs_data = []
    
    # Get start blocks and timestamps for all epochs in range
    epoch_timestamps = {}
    for epoch_id in range(first_epoch, last_epoch + 1):
        print(f"Fetching data for epoch {epoch_id}...")
        block_height = get_epoch_start_block(epoch_id)
        if block_height is None:
            continue
        
        timestamp = get_block_timestamp(block_height)
        if timestamp is None:
            continue
        
        epoch_timestamps[epoch_id] = timestamp
        print(f"  Epoch {epoch_id}: block {block_height}, timestamp {timestamp}")
    
    # Build the data list
    for epoch_id in range(first_epoch, last_epoch + 1):
        if epoch_id not in epoch_timestamps:
            continue
        
        start_time = epoch_timestamps[epoch_id]
        
        # End time is the start time of the next epoch, or None for the last epoch
        if epoch_id + 1 in epoch_timestamps:
            end_time = epoch_timestamps[epoch_id + 1]
        else:
            # For the last epoch, we don't have an end time yet
            # We could get the current block, but for now we'll leave it empty
            end_time = None
        
        if end_time:
            duration = format_duration(start_time, end_time)
            end_time_str = format_datetime(end_time)
        else:
            duration = "N/A"
            end_time_str = "N/A"
        
        epochs_data.append({
            "epoch": epoch_id,
            "start_datetime": format_datetime(start_time),
            "end_datetime": end_time_str,
            "duration": duration
        })
    
    return epochs_data, first_epoch, last_epoch


def write_csv(data: List[Dict], first_epoch: int, last_epoch: int):
    """Write the epoch data to a CSV file."""
    filename = f"gonka_{first_epoch}-{last_epoch}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['epoch', 'start_datetime', 'end_datetime', 'duration']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in data:
            writer.writerow({
                'epoch': row['epoch'],
                'start_datetime': row['start_datetime'],
                'end_datetime': row['end_datetime'],
                'duration': row['duration']
            })
    
    print(f"\nData written to {filename}")
    print(f"Total epochs processed: {len(data)}")


def main():
    """Main function."""
    print("Gonka.ai Epoch Data Fetcher")
    print("=" * 40)
    
    try:
        data, first_epoch, last_epoch = process_epochs(AMOUNT_EPOCH)
        write_csv(data, first_epoch, last_epoch)
        print("\nDone!")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

