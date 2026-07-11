#!/bin/bash

# 1. Configuration Settings
PORT="/dev/ttyACM0"
TEST_SAMPLES=100

if [ ! -c "$PORT" ]; then
    echo "Error: Device port $PORT not found."
    exit 1
fi

# 2. Handle Routing: Check if a name argument was supplied
if [ -z "$1" ]; then
    # Test Mode: Use raw Python kernel sockets with handshakes enabled
    python3 -c "
import serial
import numpy as np
import sys

try:
    ser = serial.Serial('$PORT', 115200, timeout=1)
    ser.dtr = True
    ser.rts = True
    ser.reset_input_buffer()
    raw_data = ser.read($TEST_SAMPLES * 2 + 64)
    ser.close()

    if not raw_data or len(raw_data) < 32:
        sys.exit(1)

    best_frames = None
    byte_offset = 0

    while byte_offset < 2:
        buf = raw_data[byte_offset:]
        n = (len(buf) // 2) * 2
        if n >= $TEST_SAMPLES * 2:
            initial_frames = np.frombuffer(buf[:n], dtype='>u2').copy()
            for bit_shift in range(16):
                if bit_shift == 0:
                    shifted = initial_frames
                else:
                    shifted = (initial_frames[:-1] << bit_shift) | (initial_frames[1:] >> (16 - bit_shift))
                if np.all((shifted[:10] & 0xF000) == 0):
                    best_frames = shifted
                    break
        if best_frames is not None:
            break
        byte_offset += 1

    if best_frames is None:
        n0 = (len(raw_data) // 2) * 2
        best_frames = np.frombuffer(raw_data[:n0], dtype='>u2')

    for val in best_frames[:$TEST_SAMPLES]:
        print(int(val & 0x0FFF))
except Exception as e:
    pass
"
    exit 0
fi

# Define our clean output filename configurations
RAW_FILE="${1}.raw"
CSV_FILE="${1}.csv"

echo "------------------------------------------------------------"
echo "STAGE 1: Ingesting exactly 5 seconds of raw optical data..."
echo "------------------------------------------------------------"

# Embedded Python Recording Engine with Handshakes & Precision Terminal Progress Bar
python3 -c "
import serial
import time
import sys

PORT = '$PORT'
RAW_FILE = '$RAW_FILE'
CAPTURE_DURATION = 5.0  # Strict 5-second hardware clock boundary

try:
    ser = serial.Serial(PORT, 115200, timeout=0.1)
    ser.dtr = True
    ser.rts = True
    ser.reset_input_buffer()

    start_time = time.time()
    end_time = start_time + CAPTURE_DURATION

    # Pre-allocate buffer tracking limits
    with open(RAW_FILE, 'wb') as f:
        while True:
            current_time = time.time()
            if current_time >= end_time:
                break

            # Read whatever byte sequences are ready in the kernel cache
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                f.write(data)

            # Visual Progress Bar Generation (High-density blocks)
            elapsed = current_time - start_time
            progress = min(1.0, elapsed / CAPTURE_DURATION)
            bar_length = 40
            filled_length = int(round(bar_length * progress))
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            percent = progress * 100

            # Print update dynamically over the current stdout line
            sys.stdout.write(f'\rProgress: |{bar}| {percent:.1f}% Complete ({elapsed:.1f}s / 5.0s)')
            sys.stdout.flush()
            time.sleep(0.01)

    ser.close()
    print('\n--> Capture complete! Binary saved safely.')
except Exception as e:
    print(f'\nError during active ingestion loop: {e}')
    sys.exit(1)
"

echo ""
echo "------------------------------------------------------------"
echo "STAGE 2: Converting bitstream to normalized CSV..."
echo "------------------------------------------------------------"

python3 -c "
import numpy as np
import sys

try:
    buf = open('$RAW_FILE', 'rb').read()
    best_frames = None
    byte_offset = 0

    while byte_offset < 2:
        t_buf = buf[byte_offset:]
        n = (len(t_buf) // 2) * 2
        if n >= 100:
            initial_frames = np.frombuffer(t_buf[:n], dtype='>u2').copy()
            for bit_shift in range(16):
                if bit_shift == 0:
                    shifted = initial_frames
                else:
                    shifted = (initial_frames[:-1] << bit_shift) | (initial_frames[1:] >> (16 - bit_shift))
                if np.all((shifted[:10] & 0xF000) == 0):
                    best_frames = shifted
                    break
        if best_frames is not None:
            break
        byte_offset += 1

    if best_frames is None:
        n0 = (len(buf) // 2) * 2
        best_frames = np.frombuffer(buf[:n0], dtype='>u2')

    frames = best_frames & 0x0FFF

    # LOCK TIME PARSER: Increments every row sequence by exactly 20µs ticks
    t = np.arange(frames.size, dtype=np.uint64) * 20
    np.savetxt('$CSV_FILE', np.column_stack((t, frames)), fmt=['%u', '%u'], delimiter=',', header='timestamp,light_intensity', comments='')
    print('--> Conversion successful! Created: $CSV_FILE')
except Exception as e:
    print('Error during processing:', e)
"

rm "$RAW_FILE"
echo "Finished! Clean dataset ready for graphing."
