"""AI Rock Paper Scissors - OpenCV + MediaPipe booth game."""

from __future__ import annotations

import math
import random
import time
from pathlib import Path

try:
    import winsound
except ImportError:  # winsound is available on Windows; keep a safe fallback.
    winsound = None

import cv2
import mediapipe as mp


WINDOW_NAME = "AI Rock Paper Scissors"
DISPLAY_WIDTH = 1280
DISPLAY_HEIGHT = 720

# MediaPipe analyzes a smaller frame for speed; the game window is still rendered at 720p.
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
COUNTDOWN_SECONDS = 3.0
CONFIDENCE_THRESHOLD = 0.50
STABLE_FRAMES_REQUIRED = 2
POINTS_TO_WIN = 2

GESTURE_MAP = {
    "Closed_Fist": "ROCK",
    "Open_Palm": "PAPER",
    "Victory": "SCISSORS",
}
CHOICES = ("ROCK", "PAPER", "SCISSORS")
COUNTER_MOVE = {"ROCK": "PAPER", "PAPER": "SCISSORS", "SCISSORS": "ROCK"}

# Landmark indices for index, middle, ring, and little finger.
FINGER_CHAINS = (
    (5, 6, 7, 8),
    (9, 10, 11, 12),
    (13, 14, 15, 16),
    (17, 18, 19, 20),
)


def landmark_distance(point_a, point_b) -> float:
    """Return the 3D distance between two MediaPipe landmarks."""
    return math.sqrt(
        (point_a.x - point_b.x) ** 2
        + (point_a.y - point_b.y) ** 2
        + (point_a.z - point_b.z) ** 2
    )


def joint_angle(point_a, point_b, point_c) -> float:
    """Return angle ABC in degrees; angles do not change when the hand rotates."""
    vector_ba = (
        point_a.x - point_b.x,
        point_a.y - point_b.y,
        point_a.z - point_b.z,
    )
    vector_bc = (
        point_c.x - point_b.x,
        point_c.y - point_b.y,
        point_c.z - point_b.z,
    )
    length_ba = math.sqrt(sum(value * value for value in vector_ba))
    length_bc = math.sqrt(sum(value * value for value in vector_bc))
    if length_ba < 1e-6 or length_bc < 1e-6:
        return 0.0

    cosine = sum(a * c for a, c in zip(vector_ba, vector_bc)) / (
        length_ba * length_bc
    )
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))


def finger_state(landmarks, chain: tuple[int, int, int, int]) -> str:
    """Classify one finger as extended, folded, or ambiguous."""
    mcp, pip, dip, tip = chain
    pip_angle = joint_angle(landmarks[mcp], landmarks[pip], landmarks[dip])
    dip_angle = joint_angle(landmarks[pip], landmarks[dip], landmarks[tip])

    if pip_angle >= 145.0 and dip_angle >= 140.0:
        return "extended"
    if pip_angle <= 132.0 or dip_angle <= 132.0:
        return "folded"
    return "ambiguous"


def classify_landmark_gesture(landmarks) -> str | None:
    """Recognize R/P/S from joint bends as a rotation-resistant fallback."""
    if landmarks is None or len(landmarks) < 21:
        return None

    states = [finger_state(landmarks, chain) for chain in FINGER_CHAINS]
    extended_count = states.count("extended")
    folded_count = states.count("folded")

    # A raised thumb also folds the four other fingers. Reject that shape as ROCK.
    palm_width = landmark_distance(landmarks[5], landmarks[17])
    thumb_near_palm = landmark_distance(landmarks[4], landmarks[5]) <= max(
        palm_width * 1.35, 1e-6
    )

    if folded_count >= 3 and extended_count == 0 and thumb_near_palm:
        return "ROCK"
    if extended_count >= 3 and folded_count == 0:
        return "PAPER"
    if states[0] == states[1] == "extended" and states[2:] == ["folded", "folded"]:
        return "SCISSORS"
    return None


def play_sound(kind: str) -> None:
    """Play a short non-blocking Windows system sound without extra files."""
    if winsound is None:
        return

    aliases = {
        "tick": "SystemAsterisk",
        "win": "SystemExclamation",
        "lose": "SystemHand",
        "draw": "SystemQuestion",
    }
    try:
        winsound.PlaySound(
            aliases.get(kind, "SystemAsterisk"),
            winsound.SND_ALIAS | winsound.SND_ASYNC,
        )
    except RuntimeError:
        pass


def choose_ai_move(player_history: list[str]) -> str:
    """Predict the player's recent favorite move, with some randomness kept in."""
    # The first few rounds are random while the AI collects a little history.
    if len(player_history) < 2 or random.random() < 0.35:
        return random.choice(CHOICES)

    recent_moves = player_history[-8:]
    counts = {move: recent_moves.count(move) for move in CHOICES}
    highest_count = max(counts.values())
    likely_moves = [move for move, count in counts.items() if count == highest_count]
    predicted_player_move = random.choice(likely_moves)
    return COUNTER_MOVE[predicted_player_move]


def create_particles(color: tuple[int, int, int], amount: int = 55) -> list[dict]:
    """Create a small celebration burst for round and match results."""
    particles = []
    for _ in range(amount):
        particles.append(
            {
                "x": random.randint(180, DISPLAY_WIDTH - 180),
                "y": random.randint(190, 430),
                "vx": random.uniform(-4.0, 4.0),
                "vy": random.uniform(-7.0, 1.0),
                "life": random.randint(25, 55),
                "size": random.randint(3, 8),
                "color": color,
            }
        )
    return particles


def draw_and_update_particles(frame, particles: list[dict]) -> None:
    """Draw simple OpenCV particles and discard them when they expire."""
    alive = []
    for particle in particles:
        particle["x"] += particle["vx"]
        particle["y"] += particle["vy"]
        particle["vy"] += 0.28
        particle["life"] -= 1
        if particle["life"] > 0 and particle["y"] < DISPLAY_HEIGHT:
            cv2.circle(
                frame,
                (int(particle["x"]), int(particle["y"])),
                particle["size"],
                particle["color"],
                -1,
                cv2.LINE_AA,
            )
            alive.append(particle)
    particles[:] = alive


def draw_centered_text(
    image,
    text: str,
    y: int,
    scale: float,
    color: tuple[int, int, int],
    thickness: int = 2,
) -> None:
    """Draw one line of text centered horizontally."""
    font = cv2.FONT_HERSHEY_DUPLEX
    (text_width, _), _ = cv2.getTextSize(text, font, scale, thickness)
    x = max(0, (image.shape[1] - text_width) // 2)

    # A dark outline keeps words readable over a moving camera image.
    cv2.putText(
        image,
        text,
        (x, y),
        font,
        scale,
        (0, 0, 0),
        thickness + 5,
        cv2.LINE_AA,
    )
    cv2.putText(
        image,
        text,
        (x, y),
        font,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def add_dark_panel(image, top: int, bottom: int, opacity: float = 0.65) -> None:
    """Darken part of the frame so the arcade UI stays easy to read."""
    overlay = image.copy()
    cv2.rectangle(overlay, (0, top), (image.shape[1], bottom), (8, 12, 20), -1)
    cv2.addWeighted(overlay, opacity, image, 1.0 - opacity, 0, image)


def resize_and_crop(frame, width: int, height: int):
    """Fill a 16:9 game canvas without stretching the camera image."""
    frame_height, frame_width = frame.shape[:2]
    scale = max(width / frame_width, height / frame_height)
    resized_width = int(frame_width * scale)
    resized_height = int(frame_height * scale)
    resized = cv2.resize(
        frame, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR
    )

    x = (resized_width - width) // 2
    y = (resized_height - height) // 2
    return resized[y : y + height, x : x + width].copy()


def decide_winner(player: str, computer: str) -> str:
    """Return the result text shown in the game window."""
    if player == computer:
        return "DRAW!"

    winning_pairs = {
        ("ROCK", "SCISSORS"),
        ("PAPER", "ROCK"),
        ("SCISSORS", "PAPER"),
    }
    if (player, computer) in winning_pairs:
        return "YOU WIN!"
    return "YOU LOSE!"


def draw_game_ui(
    frame,
    now: float,
    round_done: bool,
    match_done: bool,
    countdown_end: float,
    player: str | None,
    computer: str | None,
    result_text: str,
    match_text: str,
    player_score: int,
    ai_score: int,
    round_number: int,
    win_streak: int,
    best_streak: int,
    history_size: int,
) -> None:
    """Draw all player-facing information directly on the OpenCV frame."""
    height = frame.shape[0]

    add_dark_panel(frame, 0, 145, 0.74)
    add_dark_panel(frame, height - 90, height, 0.76)

    draw_centered_text(
        frame, "AI ROCK PAPER SCISSORS", 48, 1.18, (255, 220, 70), 3
    )
    draw_centered_text(
        frame,
        f"FIRST TO {POINTS_TO_WIN}     YOU  {player_score} - {ai_score}  AI     ROUND {round_number}",
        94,
        0.78,
        (255, 255, 255),
        2,
    )
    ai_status = "AI: LEARNING" if history_size < 2 else "AI: PREDICTION ACTIVE"
    draw_centered_text(
        frame,
        f"WIN STREAK x{win_streak}     BEST x{best_streak}     {ai_status}",
        132,
        0.58,
        (170, 230, 255),
        1,
    )

    if not round_done:
        if now < countdown_end:
            countdown_number = int(countdown_end - now) + 1
            draw_centered_text(frame, "GET READY", 245, 1.15, (255, 255, 255), 3)
            draw_centered_text(
                frame, str(countdown_number), 430, 4.6, (40, 230, 255), 8
            )
            draw_centered_text(
                frame, "Change your hand before SHOW!", 520, 0.85, (255, 255, 255), 2
            )
        else:
            draw_centered_text(frame, "SHOW NOW!", 330, 2.3, (70, 255, 100), 5)
            draw_centered_text(
                frame,
                "ROCK  /  PAPER  /  SCISSORS",
                415,
                1.05,
                (255, 255, 255),
                2,
            )
            if now - countdown_end >= 0.8:
                draw_centered_text(
                    frame, "Keep your hand clear and steady", 490, 0.72, (190, 220, 255), 2
                )
    else:
        add_dark_panel(frame, 165, height - 115, 0.60)
        draw_centered_text(
            frame, f"YOU: {player}        AI: {computer}", 250, 1.08, (255, 255, 255), 3
        )

        result_color = {
            "YOU WIN!": (80, 255, 100),
            "YOU LOSE!": (70, 90, 255),
            "DRAW!": (40, 230, 255),
        }.get(result_text, (255, 255, 255))
        draw_centered_text(frame, result_text, 400, 2.25, result_color, 5)

        if match_done:
            match_color = (80, 255, 100) if player_score >= POINTS_TO_WIN else (70, 90, 255)
            draw_centered_text(frame, match_text, 500, 1.45, match_color, 4)
        else:
            draw_centered_text(
                frame,
                f"MATCH SCORE: {player_score} - {ai_score}",
                500,
                0.90,
                (220, 235, 255),
                2,
            )

    if round_done:
        next_action = "SPACE - NEW MATCH" if match_done else "SPACE - NEXT ROUND"
    else:
        next_action = "GET READY TO PLAY"
    controls = f"{next_action}     R - RESET ALL     ESC - EXIT"
    draw_centered_text(frame, controls, height - 32, 0.72, (255, 255, 255), 2)


def show_startup_error(message: str) -> None:
    """Show startup errors in the game window instead of relying on a terminal."""
    error_frame = cv2.UMat(DISPLAY_HEIGHT, DISPLAY_WIDTH, cv2.CV_8UC3).get()
    error_frame[:] = (12, 16, 25)
    draw_centered_text(error_frame, "GAME CANNOT START", 285, 1.8, (70, 90, 255), 4)
    draw_centered_text(error_frame, message, 365, 0.9, (255, 255, 255), 2)
    draw_centered_text(error_frame, "Press ESC to exit", 455, 0.8, (200, 200, 200), 2)

    while True:
        cv2.imshow(WINDOW_NAME, error_frame)
        if cv2.waitKey(30) & 0xFF == 27:
            break


def show_loading_screen(message: str) -> None:
    """Paint a loading screen before slower one-time MediaPipe initialization."""
    loading_frame = cv2.UMat(DISPLAY_HEIGHT, DISPLAY_WIDTH, cv2.CV_8UC3).get()
    loading_frame[:] = (12, 16, 25)
    draw_centered_text(loading_frame, "AI ROCK PAPER SCISSORS", 285, 1.55, (255, 220, 70), 4)
    draw_centered_text(loading_frame, message, 385, 1.0, (255, 255, 255), 2)
    cv2.imshow(WINDOW_NAME, loading_frame)
    cv2.waitKey(1)


def main() -> None:
    recognizer = None
    camera = None

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, DISPLAY_WIDTH, DISPLAY_HEIGHT)

    # Fullscreen is preferred for a booth. ESC always exits safely.
    try:
        cv2.setWindowProperty(
            WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )
    except cv2.error:
        # Some OpenCV window backends do not support fullscreen; the large window remains.
        pass

    try:
        show_loading_screen("LOADING AI...")
        model_path = Path(__file__).resolve().with_name("gesture_recognizer.task")
        if not model_path.is_file():
            show_startup_error("gesture_recognizer.task was not found")
            return

        # Keep the existing MediaPipe GestureRecognizer VIDEO-mode pipeline.
        options = mp.tasks.vision.GestureRecognizerOptions(
            # Loading bytes avoids MediaPipe's Windows issue with non-ASCII paths.
            base_options=mp.tasks.BaseOptions(
                model_asset_buffer=model_path.read_bytes()
            ),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.45,
            min_hand_presence_confidence=0.45,
            min_tracking_confidence=0.45,
        )
        recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)

        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            show_startup_error("Camera is not available")
            return

        # A smaller recognition frame is much faster; OpenCV scales only the display copy.
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        camera.set(cv2.CAP_PROP_FPS, 30)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Pay MediaPipe's one-time first-frame cost before the playable countdown.
        show_loading_screen("WARMING UP CAMERA...")
        video_start = time.monotonic()
        last_timestamp_ms = -1
        for _ in range(2):
            warmup_success, warmup_frame = camera.read()
            if not warmup_success:
                show_startup_error("Camera frame could not be read")
                return
            warmup_frame = cv2.flip(warmup_frame, 1)
            warmup_rgb = cv2.cvtColor(warmup_frame, cv2.COLOR_BGR2RGB)
            warmup_image = mp.Image(
                image_format=mp.ImageFormat.SRGB, data=warmup_rgb
            )
            timestamp_ms = int((time.monotonic() - video_start) * 1000)
            timestamp_ms = max(timestamp_ms, last_timestamp_ms + 1)
            last_timestamp_ms = timestamp_ms
            recognizer.recognize_for_video(warmup_image, timestamp_ms)

        player = None
        computer = None
        result_text = ""
        match_text = ""
        round_done = False
        match_done = False
        player_score = 0
        ai_score = 0
        round_number = 1
        win_streak = 0
        best_streak = 0
        player_history: list[str] = []

        countdown_end = time.monotonic() + COUNTDOWN_SECONDS
        last_countdown_number = None
        candidate_gesture = None
        candidate_frames = 0
        particles: list[dict] = []
        flash_until = 0.0
        flash_color = (255, 255, 255)

        while True:
            success, camera_frame = camera.read()
            if not success:
                show_startup_error("Camera frame could not be read")
                break

            # Mirror first, so the player sees natural left/right movement.
            camera_frame = cv2.flip(camera_frame, 1)
            rgb_frame = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            timestamp_ms = int((time.monotonic() - video_start) * 1000)
            # VIDEO mode needs monotonically increasing timestamps.
            timestamp_ms = max(timestamp_ms, last_timestamp_ms + 1)
            last_timestamp_ms = timestamp_ms
            recognition = recognizer.recognize_for_video(mp_image, timestamp_ms)

            valid_gesture = None
            if recognition.gestures:
                top_gesture = recognition.gestures[0][0]
                if top_gesture.score >= CONFIDENCE_THRESHOLD:
                    valid_gesture = GESTURE_MAP.get(top_gesture.category_name)

            # If the canned model is unsure, use 3D joint angles as a fallback.
            # World landmarks are preferred because their scale is consistent in x/y/z.
            if valid_gesture is None:
                fallback_landmarks = None
                if recognition.hand_world_landmarks:
                    fallback_landmarks = recognition.hand_world_landmarks[0]
                elif recognition.hand_landmarks:
                    fallback_landmarks = recognition.hand_landmarks[0]
                valid_gesture = classify_landmark_gesture(fallback_landmarks)

            now = time.monotonic()
            if not round_done:
                if now < countdown_end:
                    # MediaPipe still runs during the countdown, warming up hand tracking.
                    candidate_gesture = None
                    candidate_frames = 0
                    countdown_number = int(countdown_end - now) + 1
                    if countdown_number != last_countdown_number:
                        play_sound("tick")
                        last_countdown_number = countdown_number
                else:
                    # Two matching frames are normally well below one second at 30 FPS.
                    if valid_gesture is None:
                        candidate_gesture = None
                        candidate_frames = 0
                    elif valid_gesture == candidate_gesture:
                        candidate_frames += 1
                    else:
                        candidate_gesture = valid_gesture
                        candidate_frames = 1

                    if candidate_frames >= STABLE_FRAMES_REQUIRED:
                        player = candidate_gesture
                        computer = choose_ai_move(player_history)
                        player_history.append(player)
                        result_text = decide_winner(player, computer)

                        if result_text == "YOU WIN!":
                            player_score += 1
                            effect_color = (80, 255, 100)
                            play_sound("win")
                        elif result_text == "YOU LOSE!":
                            ai_score += 1
                            effect_color = (70, 90, 255)
                            play_sound("lose")
                        else:
                            effect_color = (40, 230, 255)
                            play_sound("draw")

                        round_done = True
                        candidate_gesture = None
                        candidate_frames = 0
                        flash_color = effect_color
                        flash_until = now + 0.18
                        particles = create_particles(effect_color, 40)

                        if player_score >= POINTS_TO_WIN:
                            match_done = True
                            match_text = "YOU BEAT THE AI!"
                            win_streak += 1
                            best_streak = max(best_streak, win_streak)
                            particles.extend(create_particles((255, 220, 70), 70))
                        elif ai_score >= POINTS_TO_WIN:
                            match_done = True
                            match_text = "AI WINS THE MATCH"
                            win_streak = 0
                            particles.extend(create_particles((70, 90, 255), 55))

            game_frame = resize_and_crop(camera_frame, DISPLAY_WIDTH, DISPLAY_HEIGHT)

            if now < flash_until:
                flash = game_frame.copy()
                flash[:] = flash_color
                cv2.addWeighted(flash, 0.22, game_frame, 0.78, 0, game_frame)

            draw_and_update_particles(game_frame, particles)
            draw_game_ui(
                game_frame,
                now,
                round_done,
                match_done,
                countdown_end,
                player,
                computer,
                result_text,
                match_text,
                player_score,
                ai_score,
                round_number,
                win_streak,
                best_streak,
                len(player_history),
            )
            cv2.imshow(WINDOW_NAME, game_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            if key in (ord("r"), ord("R")):
                player = None
                computer = None
                result_text = ""
                match_text = ""
                round_done = False
                match_done = False
                player_score = 0
                ai_score = 0
                round_number = 1
                win_streak = 0
                best_streak = 0
                player_history.clear()
                candidate_gesture = None
                candidate_frames = 0
                particles.clear()
                flash_until = 0.0
                countdown_end = time.monotonic() + COUNTDOWN_SECONDS
                last_countdown_number = None
            elif key == 32 and round_done:  # SPACE
                if match_done:
                    player_score = 0
                    ai_score = 0
                    round_number = 1
                else:
                    round_number += 1
                round_done = False
                match_done = False
                player = None
                computer = None
                result_text = ""
                match_text = ""
                candidate_gesture = None
                candidate_frames = 0
                particles.clear()
                flash_until = 0.0
                countdown_end = time.monotonic() + COUNTDOWN_SECONDS
                last_countdown_number = None

    except Exception:
        # Keep the booth experience self-contained. Details are intentionally not printed.
        show_startup_error("Check the camera and gesture model, then restart")
    finally:
        if camera is not None:
            camera.release()
        if recognizer is not None:
            recognizer.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
