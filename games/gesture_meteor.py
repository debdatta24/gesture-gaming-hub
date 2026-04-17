import pygame, cv2, mediapipe as mp, random, threading, sys

pygame.init()
WIDTH, HEIGHT = 900, 500
CAM_W, CAM_H  = 280, 210
GAME_W        = WIDTH - CAM_W

screen   = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Gesture Ball Reflect")
clock    = pygame.time.Clock()
FONT     = pygame.font.SysFont("Arial", 24)
BIG_FONT = pygame.font.SysFont("Arial", 52, True)

# --- camera thread ---
hand_x = 0.5; hand_visible = False; cam_surf = None
_lock  = threading.Lock()

def camera_thread():
    global hand_x, hand_visible, cam_surf
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    mp_hands = mp.solutions.hands
    hands    = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
    mp_draw  = mp.solutions.drawing_utils
    while True:
        ret, frame = cap.read()
        if not ret: continue
        frame[:] = cv2.flip(frame, 1)
        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)
        hx, hv  = 0.5, False
        if results.multi_hand_landmarks:
            lm = results.multi_hand_landmarks[0].landmark
            hx = lm[0].x; hv = True
            mp_draw.draw_landmarks(frame, results.multi_hand_landmarks[0],
                                   mp_hands.HAND_CONNECTIONS)
        small = cv2.resize(frame, (CAM_W, CAM_H))
        small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        surf  = pygame.surfarray.make_surface(small.swapaxes(0, 1))
        with _lock:
            hand_x = hx; hand_visible = hv; cam_surf = surf
    cap.release()

threading.Thread(target=camera_thread, daemon=True).start()

# --- constants ---
BASKET_W, BASKET_H = 100, 14
BASKET_Y = HEIGHT - 60
BALL_R   = 14

# --- stars ---
stars = [(random.randint(0,GAME_W), random.randint(0,HEIGHT), random.randint(1,2))
         for _ in range(80)]

def reset():
    angle = random.choice([-1, 1])
    return {
        "bx": GAME_W // 2,       # basket x
        "ball_x": GAME_W // 2,   # ball x
        "ball_y": HEIGHT // 3,   # ball y
        "vx": 3 * angle,
        "vy": 3,
        "score": 0,
        "lives": 3,
        "alive": True,
    }

g = reset()

def draw_bg():
    screen.fill((10,10,30), (0, 0, GAME_W, HEIGHT))
    for sx, sy, sr in stars:
        pygame.draw.circle(screen, (180,180,200), (sx,sy), sr)

def draw_basket(bx):
    pygame.draw.rect(screen, (60,160,220),
                     (bx - BASKET_W//2, BASKET_Y, BASKET_W, BASKET_H), border_radius=6)
    pygame.draw.rect(screen, (140,220,255),
                     (bx - BASKET_W//2, BASKET_Y, BASKET_W, 4), border_radius=6)

def draw_ball(bx, by):
    # glow
    glow = pygame.Surface((BALL_R*4, BALL_R*4), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255,180,60,60), (BALL_R*2, BALL_R*2), BALL_R*2)
    screen.blit(glow, (int(bx)-BALL_R*2, int(by)-BALL_R*2))
    pygame.draw.circle(screen, (220,140,40), (int(bx), int(by)), BALL_R)
    pygame.draw.circle(screen, (255,220,120),(int(bx)-4, int(by)-4), BALL_R//3)

running = True
while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r: g = reset()
            if event.key == pygame.K_q: running = False

    with _lock:
        hx = hand_x; hv = hand_visible; surf = cam_surf

    if g["alive"]:
        # move basket
        g["bx"] = int(hx * GAME_W)
        g["bx"] = max(BASKET_W//2, min(GAME_W - BASKET_W//2, g["bx"]))

        # move ball
        g["ball_x"] += g["vx"]
        g["ball_y"] += g["vy"]

        # wall bounce (left / right)
        if g["ball_x"] - BALL_R <= 0:
            g["ball_x"] = BALL_R; g["vx"] = abs(g["vx"])
        if g["ball_x"] + BALL_R >= GAME_W:
            g["ball_x"] = GAME_W - BALL_R; g["vx"] = -abs(g["vx"])

        # ceiling bounce
        if g["ball_y"] - BALL_R <= 0:
            g["ball_y"] = BALL_R; g["vy"] = abs(g["vy"])

        # basket bounce
        basket_rect = pygame.Rect(g["bx"] - BASKET_W//2, BASKET_Y, BASKET_W, BASKET_H)
        ball_rect   = pygame.Rect(g["ball_x"]-BALL_R, g["ball_y"]-BALL_R, BALL_R*2, BALL_R*2)
        if g["vy"] > 0 and ball_rect.colliderect(basket_rect):
            g["ball_y"] = BASKET_Y - BALL_R
            g["vy"]     = -abs(g["vy"])
            # slight angle change based on where ball hits basket
            offset      = (g["ball_x"] - g["bx"]) / (BASKET_W // 2)
            g["vx"]    += offset * 2
            g["vx"]     = max(-8, min(8, g["vx"]))  # cap speed
            g["score"] += 1
            # speed up every 5 points
            if g["score"] % 5 == 0:
                g["vy"] = min(-8, g["vy"] - 0.5)

        # ball missed — fell below basket
        if g["ball_y"] - BALL_R > HEIGHT:
            g["lives"] -= 1
            if g["lives"] <= 0:
                g["alive"] = False
            else:
                # respawn ball
                g["ball_x"] = GAME_W // 2
                g["ball_y"] = HEIGHT // 3
                g["vx"]     = 3 * random.choice([-1,1])
                g["vy"]     = 3

    # --- draw ---
    draw_bg()
    draw_ball(g["ball_x"], g["ball_y"])
    draw_basket(g["bx"])

    # HUD
    screen.blit(FONT.render(f"Score: {g['score']}", True, (255,255,255)), (10,10))
    screen.blit(FONT.render(f"Lives: {'❤ ' * g['lives']}", True, (220,80,80)), (10,38))
    if not hv:
        screen.blit(FONT.render("No hand detected", True, (220,80,80)), (10,66))

    if not g["alive"]:
        txt = BIG_FONT.render("GAME OVER", True, (220,60,60))
        screen.blit(txt, (GAME_W//2 - txt.get_width()//2, HEIGHT//2 - 50))
        txt2 = FONT.render(f"Score: {g['score']}   |   R = Retry   Q = Quit", True, (255,255,255))
        screen.blit(txt2, (GAME_W//2 - txt2.get_width()//2, HEIGHT//2 + 18))

    # divider + camera
    pygame.draw.line(screen, (50,50,80), (GAME_W,0), (GAME_W,HEIGHT), 2)
    screen.fill((10,10,20), (GAME_W, 0, CAM_W, HEIGHT-CAM_H))
    if surf:
        screen.blit(surf, (GAME_W, HEIGHT-CAM_H))
        pygame.draw.rect(screen, (50,50,80), (GAME_W, HEIGHT-CAM_H, CAM_W, CAM_H), 2)
        screen.blit(FONT.render("Move hand to steer", True, (130,130,130)),
                    (GAME_W+4, HEIGHT-CAM_H+4))

    pygame.display.update()

pygame.quit()
sys.exit()