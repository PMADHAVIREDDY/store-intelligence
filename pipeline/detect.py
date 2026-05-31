import argparse
import cv2
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ultralytics import YOLO

from pipeline.emit import append_event, emit_event


def parse_args():
    parser = argparse.ArgumentParser(description="Process CCTV video and emit events")
    parser.add_argument("--video", required=True, help="Path to mp4 video file")
    parser.add_argument("--store-id", required=True, help="Store ID")
    parser.add_argument("--camera-id", required=True, help="Camera ID")
    parser.add_argument("--camera-type", required=True, choices=["entry", "floor", "billing"], help="Camera type")
    parser.add_argument("--output", required=True, help="Output .jsonl file path")
    parser.add_argument("--clip-start-time", required=True, help="ISO-8601 UTC timestamp for frame 0")
    return parser.parse_args()


def is_staff_uniform(frame: np.ndarray, bbox: Tuple[float, float, float, float]) -> bool:
    """Detect if person is wearing blue staff uniform via HSV analysis."""
    x1, y1, x2, y2 = [int(v) for v in bbox]
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(frame.shape[1], x2)
    y2 = min(frame.shape[0], y2)

    if x2 <= x1 or y2 <= y1:
        return False

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0 or crop.shape[0] < 20 or crop.shape[1] < 20:
        return False

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    blue_mask = cv2.inRange(hsv,
        np.array([100, 80, 80]), np.array([130, 255, 255]))
    total_pixels = crop.shape[0] * crop.shape[1]
    blue_ratio = np.sum(blue_mask > 0) / total_pixels
    return blue_ratio > 0.60


def get_zone(cx: float, cy: float, frame_width: int, frame_height: int, camera_type: str) -> str:
    """Determine zone based on position and camera type."""
    if camera_type == "billing":
        return "CASH_COUNTER"
    elif camera_type == "floor":
        if cx < frame_width * 0.3:
            return "FRAGRANCE"
        elif cx < frame_width * 0.6:
            return "FOH"
        else:
            return "MAKEUP_UNIT"
    return "UNKNOWN"


def main():
    args = parse_args()

    clip_start_time = datetime.fromisoformat(args.clip_start_time.replace("Z", "+00:00"))

    model = YOLO("yolov8n.pt")

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error: Could not open video {args.video}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    visitor_positions: Dict[int, List[float]] = {}
    visitor_zones: Dict[int, Tuple[str, datetime]] = {}
    visitor_dwell: Dict[int, Tuple[str, datetime, Optional[datetime]]] = {}
    exited_visitors: Dict[int, datetime] = {}
    session_seq: Dict[int, int] = {}
    previous_tracks: Set[int] = set()

    frame_num = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1

        if frame_num % 3 != 0:
            continue

        if frame_num % 100 == 0:
            print(f"Processing frame {frame_num}/{total_frames}")

        frame_time = clip_start_time + timedelta(seconds=frame_num / fps)

        results = model.track(frame, persist=True, classes=[0], conf=0.4, tracker="bytetrack.yaml")

        current_tracks: Set[int] = set()

        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            track_ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else []

            for idx, track_id in enumerate(track_ids):
                box = boxes.xyxy[idx].cpu().numpy()
                x1, y1, x2, y2 = box
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                conf = float(boxes.conf[idx])
                bbox = (x1, y1, x2, y2)

                current_tracks.add(track_id)

                is_staff = is_staff_uniform(frame, bbox)
                visitor_id = f"VIS_{track_id:06d}"

                if track_id not in visitor_positions:
                    visitor_positions[track_id] = []
                    session_seq[track_id] = 1
                else:
                    session_seq[track_id] = len(visitor_positions[track_id]) // 5 + 1

                prev_cy = visitor_positions[track_id][-1] if visitor_positions[track_id] else None
                visitor_positions[track_id].append(cy)

                threshold_y = frame_height * 0.5

                if args.camera_type == "entry":
                    if prev_cy is not None:
                        if prev_cy < threshold_y and cy >= threshold_y:
                            session_seq[track_id] += 1
                            if track_id in exited_visitors:
                                exit_time = exited_visitors[track_id]
                                if frame_time - exit_time <= timedelta(minutes=30):
                                    event = emit_event(
                                        store_id=args.store_id,
                                        camera_id=args.camera_id,
                                        visitor_id=visitor_id,
                                        event_type="REENTRY",
                                        timestamp=frame_time,
                                        is_staff=is_staff,
                                        confidence=conf,
                                        session_seq=session_seq[track_id],
                                    )
                                    append_event(event, args.output)
                                    del exited_visitors[track_id]
                                else:
                                    event = emit_event(
                                        store_id=args.store_id,
                                        camera_id=args.camera_id,
                                        visitor_id=visitor_id,
                                        event_type="ENTRY",
                                        timestamp=frame_time,
                                        is_staff=is_staff,
                                        confidence=conf,
                                        session_seq=session_seq[track_id],
                                    )
                                    append_event(event, args.output)
                            else:
                                event = emit_event(
                                    store_id=args.store_id,
                                    camera_id=args.camera_id,
                                    visitor_id=visitor_id,
                                    event_type="ENTRY",
                                    timestamp=frame_time,
                                    is_staff=is_staff,
                                    confidence=conf,
                                    session_seq=session_seq[track_id],
                                )
                                append_event(event, args.output)

                        elif prev_cy >= threshold_y and cy < threshold_y:
                            event = emit_event(
                                store_id=args.store_id,
                                camera_id=args.camera_id,
                                visitor_id=visitor_id,
                                event_type="EXIT",
                                timestamp=frame_time,
                                is_staff=is_staff,
                                confidence=conf,
                                session_seq=session_seq[track_id],
                            )
                            append_event(event, args.output)
                            exited_visitors[track_id] = frame_time

                zone = get_zone(cx, cy, frame_width, frame_height, args.camera_type)

                if args.camera_type in ["floor", "billing"]:
                    if track_id not in visitor_zones:
                        visitor_zones[track_id] = (zone, frame_time)
                        visitor_dwell[track_id] = (zone, frame_time, None)
                        event = emit_event(
                            store_id=args.store_id,
                            camera_id=args.camera_id,
                            visitor_id=visitor_id,
                            event_type="ZONE_ENTER",
                            timestamp=frame_time,
                            zone_id=zone,
                            is_staff=is_staff,
                            confidence=conf,
                            session_seq=session_seq[track_id],
                        )
                        append_event(event, args.output)

                        if args.camera_type == "billing":
                            queue_depth = len(current_tracks)
                            event = emit_event(
                                store_id=args.store_id,
                                camera_id=args.camera_id,
                                visitor_id=visitor_id,
                                event_type="BILLING_QUEUE_JOIN",
                                timestamp=frame_time,
                                queue_depth=queue_depth,
                                is_staff=is_staff,
                                confidence=conf,
                                session_seq=session_seq[track_id],
                            )
                            append_event(event, args.output)

                    else:
                        current_zone, entry_time = visitor_zones[track_id]
                        dwell_zone, dwell_start, last_emit = visitor_dwell[track_id]

                        dwell_duration = (frame_time - entry_time).total_seconds()
                        if dwell_duration >= 30:
                            if last_emit is None or (frame_time - last_emit).total_seconds() >= 30:
                                dwell_ms = int(dwell_duration * 1000)
                                event = emit_event(
                                    store_id=args.store_id,
                                    camera_id=args.camera_id,
                                    visitor_id=visitor_id,
                                    event_type="ZONE_DWELL",
                                    timestamp=frame_time,
                                    zone_id=zone,
                                    dwell_ms=dwell_ms,
                                    is_staff=is_staff,
                                    confidence=conf,
                                    session_seq=session_seq[track_id],
                                )
                                append_event(event, args.output)
                                visitor_dwell[track_id] = (dwell_zone, dwell_start, frame_time)

        exited_tracks = previous_tracks - current_tracks
        for track_id in exited_tracks:
            if args.camera_type == "floor" and track_id in visitor_zones:
                zone, entry_time = visitor_zones[track_id]
                visitor_id = f"VIS_{track_id:06d}"
                event = emit_event(
                    store_id=args.store_id,
                    camera_id=args.camera_id,
                    visitor_id=visitor_id,
                    event_type="ZONE_EXIT",
                    timestamp=frame_time,
                    zone_id=zone,
                    is_staff=False,
                    confidence=1.0,
                    session_seq=session_seq.get(track_id, 1),
                )
                append_event(event, args.output)
                del visitor_zones[track_id]

            if args.camera_type == "billing" and track_id in visitor_zones:
                visitor_id = f"VIS_{track_id:06d}"
                event = emit_event(
                    store_id=args.store_id,
                    camera_id=args.camera_id,
                    visitor_id=visitor_id,
                    event_type="BILLING_QUEUE_ABANDON",
                    timestamp=frame_time,
                    is_staff=False,
                    confidence=1.0,
                    session_seq=session_seq.get(track_id, 1),
                )
                append_event(event, args.output)
                del visitor_zones[track_id]

        previous_tracks = current_tracks

    cap.release()
    print(f"Processing complete. Events saved to {args.output}")


if __name__ == "__main__":
    main()
