import pygame, cv2, mediapipe as mp, random, os, sys, threading

pygame.init()
WIDTH, HEIGHT = 900, 400
screen   = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Gesture Controlled Dino Game")
clock    = pygame.time.Clock()
FONT     = pygame.font.SysFont("Arial", 20)
BIG_FONT = pygame.font.SysFont("Arial", 48)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
dino_img   = pygame.image.load(os.path.join(BASE_DIR,"images","pixel-dino-01.png")).convert_alpha()
cactus_img = pygame.image.load(os.path.join(BASE_DIR,"images","pixel-cactus-01.png")).convert_alpha()
dino_img   = pygame.transform.scale(dino_img,   (60, 70))
cactus_img = pygame.transform.scale(cactus_img, (40, 70))

# shared state
gesture_text   = "OPEN"
camera_surface = None
_lock          = threading.Lock()

def camera_thread():
    global gesture_text, camera_surface

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    mp_hands = mp.solutions.hands
    hands    = mp_hands.Hands(
                    max_num_hands=1,
                    model_complexity=0,
                    min_detection_confidence=0.6,
                    min_tracking_confidence=0.5)
    mp_draw  = mp.solutions.drawing_utils
    frame_n  = 0
    history  = ["OPEN", "OPEN", "OPEN"]   # last 3 readings

    def is_fist(lm):
        # all 4 fingertips below their middle knuckle = fist
        tips = [8, 12, 16, 20]
        mids = [6, 10, 14, 18]
        folded = sum(lm[t].y > lm[m].y for t, m in zip(tips, mids))
        return folded >= 3

    while True:
        ret, frame = cap.read()
        if not ret: continue
        frame_n += 1
        frame[:] = cv2.flip(frame, 1)

        # run mediapipe every 2nd frame (balance speed vs accuracy)
        if frame_n % 2 == 0:
            rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            g = "OPEN"
            if results.multi_hand_landmarks:
                lm = results.multi_hand_landmarks[0].landmark
                mp_draw.draw_landmarks(frame, results.multi_hand_landmarks[0],
                                       mp_hands.HAND_CONNECTIONS)
                g = "FIST" if is_fist(lm) else "OPEN"

            # majority vote over last 3 readings — stable, no flashing
            history.append(g)
            history.pop(0)
            stable = "FIST" if history.count("FIST") >= 2 else "OPEN"

            with _lock:
                gesture_text = stable

        # always show camera preview
        small = cv2.resize(frame, (220, 160))
        small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        surf  = pygame.surfarray.make_surface(small.swapaxes(0, 1))
        with _lock:
            camera_surface = surf

    cap.release()

t = threading.Thread(target=camera_thread, daemon=True)
t.start()

# high score
HS_FILE = os.path.join(BASE_DIR, "highscore.txt")
if not os.path.exists(HS_FILE): open(HS_FILE,"w").write("0")
def get_hs():
    return int(open(HS_FILE).read())
def save_hs(s):
    if s > get_hs(): open(HS_FILE,"w").write(str(s))

def reset_game():
    return {"x":80, "y":280, "vy":0, "jumping":False,
            "score":0, "game_over":False, "paused":False, "jump_cooldown":0}

game      = reset_game()
ground_y  = 280
gravity   = 0.7
obstacles = [{"x": WIDTH+300}, {"x": WIDTH+650}]
prev_g    = "OPEN"

running = True
while running:
    clock.tick(60)
    screen.fill((255, 255, 255))

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and not game["jumping"] and game["jump_cooldown"] == 0 and not game["game_over"]:
                game["jumping"] = True
                game["vy"]      = -13
                game["jump_cooldown"] = 15
            if event.key == pygame.K_p:
                game["paused"] = not game["paused"]
            if game["game_over"]:
                if event.key == pygame.K_r:
                    game = reset_game()
                    obstacles[0]["x"] = WIDTH+300
                    obstacles[1]["x"] = WIDTH+650
                elif event.key == pygame.K_q:
                    running = False

    with _lock:
        g    = gesture_text
        surf = camera_surface

    if not game["game_over"] and not game["paused"]:

        # jump on OPEN → FIST edge
        if g == "FIST" and prev_g == "OPEN":
            if not game["jumping"] and game["jump_cooldown"] == 0:
                game["jumping"] = True
                game["vy"]      = -13
                game["jump_cooldown"] = 15

        # physics
        if game["jumping"]:
            game["y"] += game["vy"]
            game["vy"] += gravity
            if game["y"] >= ground_y:
                game["y"] = ground_y
                game["jumping"] = False

        if game["jump_cooldown"] > 0:
            game["jump_cooldown"] -= 1

        # obstacles
        speed = 4 + game["score"] // 10
        for obs in obstacles:
            obs["x"] -= speed
            if obs["x"] < -50:
                obs["x"] = WIDTH + random.randint(250, 450)
                game["score"] += 1

        # collision
        dino_rect = pygame.Rect(game["x"]+12, game["y"]+8, 32, 52)
        for obs in obstacles:
            if dino_rect.colliderect(pygame.Rect(obs["x"], ground_y, 40, 70)):
                game["game_over"] = True
                game["jumping"]   = False
                save_hs(game["score"])

    prev_g = g

    # draw
    pygame.draw.line(screen, (0,0,0), (0,350), (WIDTH,350), 2)
    screen.blit(dino_img,  (game["x"], int(game["y"])))
    for obs in obstacles:
        screen.blit(cactus_img, (obs["x"], ground_y))

    # gesture indicator box
    gcolor = (200,0,0) if g == "FIST" else (0,150,0)
    pygame.draw.rect(screen, gcolor, (WIDTH-160, 10, 140, 30), border_radius=6)
    screen.blit(FONT.render(f"Gesture: {g}", True, (255,255,255)), (WIDTH-155, 15))

    screen.blit(FONT.render(f"Score: {game['score']}", True, (0,0,0)), (740, 50))
    screen.blit(FONT.render(f"High:  {get_hs()}",      True, (0,0,0)), (740, 75))
    screen.blit(FONT.render("Fist = Jump  |  Space = Jump", True, (100,100,100)), (240, 370))

    if surf and not game["game_over"]:
        screen.blit(surf, (10,10))
        pygame.draw.rect(screen, (0,0,0), (10,10,220,160), 2)

    if game["paused"]:
        screen.blit(BIG_FONT.render("PAUSED",    True, (0,0,200)), (350,160))
    if game["game_over"]:
        screen.blit(BIG_FONT.render("GAME OVER", True, (200,0,0)), (300,140))
        screen.blit(FONT.render("R = Retry  |  Q = Quit", True, (0,0,0)), (350,200))

    pygame.display.update()

pygame.quit()
sys.exit()