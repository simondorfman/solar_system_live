#!/usr/bin/env python3

import argparse
import calendar
import datetime
import json
import pathlib
import subprocess
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def calculate_age(birth_date: datetime.datetime, current_date: datetime.datetime):
    """Calculate age in years, months, and days."""
    if birth_date is None:
        return None, None, None

    years = current_date.year - birth_date.year
    months = current_date.month - birth_date.month
    days = current_date.day - birth_date.day

    if days < 0:
        months -= 1
        if current_date.month == 1:
            prev_month = 12
            prev_year = current_date.year - 1
        else:
            prev_month = current_date.month - 1
            prev_year = current_date.year
        # Get number of days in the previous month
        days_in_prev_month = calendar.monthrange(prev_year, prev_month)[1]
        days += days_in_prev_month

    if months < 0:
        years -= 1
        months += 12

    return years, months, days


# Approximate sidereal orbital periods (days)
ORBITAL_PERIODS_DAYS = {
    "Mercury": 87.969,
    "Venus": 224.701,
    "Earth": 365.256,
    "Mars": 686.980,
    "Jupiter": 4332.59,
    "Saturn": 10759.22,
    "Uranus": 30685.4,
    "Neptune": 60189.0,
    "Pluto": 90560.0,
}

EARTH_PERIOD = ORBITAL_PERIODS_DAYS["Earth"]

# Precompute synodic periods (days) relative to Earth
SYNODIC_INNER = {}
for name in ["Mercury", "Venus"]:
    p = ORBITAL_PERIODS_DAYS[name]
    SYNODIC_INNER[name] = 1.0 / abs((1.0 / p) - (1.0 / EARTH_PERIOD))

SYNODIC_OUTER = {}
for name in ["Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]:
    p = ORBITAL_PERIODS_DAYS[name]
    SYNODIC_OUTER[name] = 1.0 / abs((1.0 / EARTH_PERIOD) - (1.0 / p))


def compute_lap_counts(elapsed_days: float):
    """Compute how many times Earth was lapped by inner planets and how many times
    Earth lapped outer planets, based on synodic periods."""
    inner = {
        name: int(elapsed_days / SYNODIC_INNER[name])
        for name in SYNODIC_INNER
    }
    outer = {
        name: int(elapsed_days / SYNODIC_OUTER[name])
        for name in SYNODIC_OUTER
    }
    return inner, outer


def main():
    parser = argparse.ArgumentParser(
        description="Generate Solar System Live frames and build a video with text overlays"
    )
    parser.add_argument(
        "birth_date",
        type=str,
        help="Birth/start date in YYYY-MM-DD format (e.g., 1975-01-01)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End date in YYYY-MM-DD format (default: today's date)",
    )
    parser.add_argument(
        "--step-days",
        type=int,
        default=3,
        help="Number of days to step forward between frames (default: 3)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="",
        help="Name to display in age text (optional)",
    )
    args = parser.parse_args()

    # Parse the birth/start date (time will be set to midnight)
    try:
        start_date = datetime.datetime.strptime(args.birth_date, "%Y-%m-%d")
        start = start_date.replace(hour=0, minute=0, second=0)
    except ValueError:
        print(f"Error: Invalid date format '{args.birth_date}'. Expected YYYY-MM-DD (e.g., 1975-01-01)", file=sys.stderr)
        sys.exit(1)

    # Parse the end date (defaults to today if not provided)
    if args.end_date:
        try:
            end_date = datetime.datetime.strptime(args.end_date, "%Y-%m-%d")
            end = end_date.replace(hour=0, minute=0, second=0)
        except ValueError:
            print(f"Error: Invalid end date format '{args.end_date}'. Expected YYYY-MM-DD (e.g., 2026-01-20)", file=sys.stderr)
            sys.exit(1)
    else:
        # Default to today at midnight
        today = datetime.datetime.now()
        end = today.replace(hour=0, minute=0, second=0, microsecond=0)

    # Step size in days
    if args.step_days <= 0:
        print(f"Error: Step days must be positive (got {args.step_days})", file=sys.stderr)
        sys.exit(1)
    step = datetime.timedelta(days=args.step_days)

    # Birth date is the start date
    birth_date = start

    # Output directory: project_root/frames
    project_root = pathlib.Path(__file__).resolve().parents[1]
    out_dir = project_root / "frames"
    out_dir.mkdir(exist_ok=True)

    t = start
    i = 0

    print(f"Generating frames into: {out_dir}")
    print(f"From {start.isoformat()} to {end.isoformat()} (step {step})")

    while t <= end:
        i += 1
        utc_str = t.strftime("%Y/%m/%d %H:%M:%S")

        url = (
            "http://localhost:8080/cgi-bin/Solar"
            f"?date=1&utc={utc_str.replace(' ', '+')}"
            "&img=-k1&sys=-Sf&imgsize=1024&dynimg=y"
        )

        out_path = out_dir / f"frame_{i:05d}.gif"

        print(f"[{i}] {utc_str} -> {out_path}")
        try:
            subprocess.run(
                ["curl", "-sS", url, "-o", str(out_path)],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error fetching frame {i} at {utc_str}: {e}", file=sys.stderr)
            # Stop on first failure so the problem is visible
            sys.exit(1)

        # Check if next step would exceed end date
        next_date = t + step
        if next_date > end and t < end:
            # Generate final frame at exact end date
            i += 1
            utc_str = end.strftime("%Y/%m/%d %H:%M:%S")
            
            url = (
                "http://localhost:8080/cgi-bin/Solar"
                f"?date=1&utc={utc_str.replace(' ', '+')}"
                "&img=-k1&sys=-Sf&imgsize=1024&dynimg=y"
            )
            
            out_path = out_dir / f"frame_{i:05d}.gif"
            
            print(f"[{i}] {utc_str} -> {out_path} (final frame at end date)")
            try:
                subprocess.run(
                    ["curl", "-sS", url, "-o", str(out_path)],
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                print(f"Error fetching final frame {i} at {utc_str}: {e}", file=sys.stderr)
                sys.exit(1)
            break
        
        t = next_date

    # Write metadata file (for reference)
    metadata = {
        "start_date": start.strftime("%Y-%m-%d"),
        "step_days": args.step_days,
        "total_frames": i,
        "name": args.name,
        "birth_date": birth_date.strftime("%Y-%m-%d"),
    }

    metadata_path = project_root / "frames_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata written to: {metadata_path}")

    # Add text overlays to frames using PIL
    if not HAS_PIL:
        print("Error: PIL/Pillow is required for text overlays. Install it with: pip install Pillow", file=sys.stderr)
        sys.exit(1)
    
    print("Adding text overlays to frames...")
    try:
        # Try to load Helvetica font
        font_path = "/System/Library/Fonts/Helvetica.ttc"
        try:
            # Slightly smaller font so all lines fit within 1080px height
            font = ImageFont.truetype(font_path, 40)
        except (OSError, IOError):
            # Fallback to default font
            print(f"Warning: Could not load font from {font_path}, using default font", file=sys.stderr)
            font = ImageFont.load_default()
    except Exception as e:
        print(f"Warning: Could not load font, using default: {e}", file=sys.stderr)
        font = ImageFont.load_default()
    
    # Create directory for video frames with text overlays
    video_frames_dir = project_root / "video_frames"
    video_frames_dir.mkdir(exist_ok=True)
    
    # Process each frame to add text overlay
    for frame_num in range(1, i + 1):
        frame_path = out_dir / f"frame_{frame_num:05d}.gif"
        if not frame_path.exists():
            continue
        
        current_date = start + datetime.timedelta(days=(frame_num - 1) * args.step_days)
        year = current_date.year
        month = f"{current_date.month:02d}"
        day = f"{current_date.day:02d}"

        # Age since birth date
        years, months, days = calculate_age(birth_date, current_date)

        # Relative orbital laps since start date
        elapsed_days = (current_date - start).days
        inner_laps, outer_laps = compute_lap_counts(elapsed_days)

        if args.name:
            heading = f"{args.name}'s age in:"
            subject = args.name
        else:
            heading = "Age in:"
            subject = "Earth"
        
        # Load the GIF frame
        img = Image.open(frame_path)
        # Convert to RGB if needed (GIFs might be palette mode)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Create a new image: 1920x1080 black background
        video_frame = Image.new('RGB', (1920, 1080), color='black')
        
        # Scale the original image to 1024 width, maintaining aspect ratio
        img_width = 1024
        aspect_ratio = img.height / img.width
        img_height = int(img_width * aspect_ratio)
        img_scaled = img.resize((img_width, img_height), Image.Resampling.LANCZOS)
        
        # Paste the scaled image on the right side, vertically centered
        x_offset = 1920 - img_width
        y_offset = (1080 - img_height) // 2
        video_frame.paste(img_scaled, (x_offset, y_offset))
        
        # Add text overlay on the left side
        draw = ImageDraw.Draw(video_frame)
        text_lines = [
            f"year – {year}",
            f"month – {month}",
            f"day – {day}",
            "",
            heading,
            f"years – {years}",
            f"months – {months}",
            f"days – {days}",
            "",
            f"Number of times {subject} was lapped by:",
            f"Mercury – {inner_laps['Mercury']}",
            f"Venus – {inner_laps['Venus']}",
            "",
            f"Number of times {subject} lapped:",
            f"Mars – {outer_laps['Mars']}",
            f"Jupiter – {outer_laps['Jupiter']}",
            f"Saturn – {outer_laps['Saturn']}",
            f"Uranus – {outer_laps['Uranus']}",
            f"Neptune – {outer_laps['Neptune']}",
            f"Pluto – {outer_laps['Pluto']}",
        ]
        
        y_pos = 50
        line_height = 45
        for line in text_lines:
            if line:  # Skip empty lines
                draw.text((50, y_pos), line, fill='white', font=font)
            y_pos += line_height
        
        # Save the frame with text overlay as PNG (better quality for video encoding)
        # Save to a temporary directory for video frames
        video_frames_dir = project_root / "video_frames"
        video_frames_dir.mkdir(exist_ok=True)
        video_frame_path = video_frames_dir / f"frame_{frame_num:05d}.png"
        video_frame.save(video_frame_path, 'PNG')
        
        if frame_num % 100 == 0:
            print(f"  Processed {frame_num}/{i} frames...")
    
    print("Text overlays added to all frames.")

    # Create concat file for ffmpeg (use video_frames with text overlays)
    concat_file = project_root / "frames_list.txt"
    print("Creating concat file for ffmpeg...")
    with open(concat_file, "w") as f:
        for idx in range(1, i + 1):
            frame_path = video_frames_dir / f"frame_{idx:05d}.png"
            if frame_path.exists():
                f.write(f"file '{frame_path.resolve()}'\n")

    # Build video with ffmpeg (no drawtext needed, text is already in frames)
    # Frames are already 1920x1080, just need to ensure proper format
    filter_complex = "format=yuv420p"

    output_file = project_root / "solar_timelapse.mp4"

    print("Building video with text overlays...")
    print(f"Output: {output_file}")

    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-r", "30",
        "-i", str(concat_file),
        "-vf", filter_complex,
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "slow",
        "-y",
        str(output_file),
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"Video created successfully: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error running ffmpeg: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Clean up helper files
        if concat_file.exists():
            concat_file.unlink()
        # Optionally clean up video_frames directory (uncomment if desired)
        # import shutil
        # if video_frames_dir.exists():
        #     shutil.rmtree(video_frames_dir)

    print(f"Done. Generated {i} frame(s) and video {output_file}.")


if __name__ == "__main__":
    main()

