import cv2, pygame, mediapipe as mp, random, math, sys

# --- setup ---
pygame.init()
W, H = 900, 600
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Gesture Space Shooter")
clock = pygame.time.Clock()
font  = pygame.font.SysFont("consolas", 22)

CAM_W, CAM_H = 280, 210   # camera preview size (bottom-right)

# --- mediapipe ---
mp_hands = mp.solutions.hands
hands    = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw  = mp.solutions.drawing_utils
cap      = cv2.VideoCapture(0)

# --- gesture state ---
hand_x   = 0.5
pinching = False
fisting  = False

def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

def get_gestures(frame):
    global hand_x, pinching, fisting
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = hands.process(rgb)
    if res.multi_hand_landmarks:
        lm       = res.multi_hand_landmarks[0].landmark
        hand_x   = 1 - lm[0].x
        pinching = dist(lm[4], lm[8]) < 0.07
        fisting  = all(dist(lm[t], lm[0]) < 0.30 for t in [8,12,16,20])
        mp_draw.draw_landmarks(frame, res.multi_hand_landmarks[0], mp_hands.HAND_CONNECTIONS)
    return frame

def cam_to_surface(frame):
    frame = cv2.resize(cv2.flip(frame, 1), (CAM_W, CAM_H))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return pygame.surfarray.make_surface(frame.swapaxes(0, 1))

# --- game objects ---
GAME_W = W - CAM_W   # game plays in left portion

ship  = pygame.Rect(GAME_W//2 - 20, H - 60, 40, 40)
bullets, enemies, explosions = [], [], []
score, lives, level = 0, 3, 1
spawn_timer, shoot_cd = 0, 0

def draw_ship(shield):
    pts = [(ship.centerx, ship.top), (ship.left, ship.bottom), (ship.right, ship.bottom)]
    pygame.draw.polygon(screen, (0,220,255), pts)
    if shield:
        pygame.draw.circle(screen, (0,255,100), ship.center, 34, 3)

def spawn_enemy():
    return {"rect": pygame.Rect(random.randint(0, GAME_W-40), -40, 40, 30),
            "speed": random.uniform(2, 3 + level*0.3)}

def draw_enemy(e):
    r = e["rect"]
    pygame.draw.ellipse(screen, (220,50,50), r)
    pygame.draw.ellipse(screen, (255,140,0), (r.x+8, r.y-8, r.w-16, 16))

running = True
while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # camera & gestures
    ok, frame = cap.read()
    if ok:
        frame    = get_gestures(frame)
        cam_surf = cam_to_surface(frame)

    # move ship toward hand x position
    target = int(hand_x * GAME_W)
    ship.x += max(-7, min(7, target - ship.centerx))
    ship.clamp_ip(pygame.Rect(0, 0, GAME_W, H))

    # shoot on pinch
    if shoot_cd > 0: shoot_cd -= 1
    if pinching and shoot_cd == 0:
        bullets.append(pygame.Rect(ship.centerx-2, ship.top, 4, 14))
        shoot_cd = 18

    # update bullets
    bullets = [b for b in bullets if b.top > 0]
    for b in bullets: b.y -= 10

    # spawn + update enemies
    spawn_timer += 1
    if spawn_timer > max(20, 70 - level*6):
        enemies.append(spawn_enemy())
        spawn_timer = 0
    level = score // 200 + 1
    enemies = [e for e in enemies if e["rect"].top < H]
    for e in enemies: e["rect"].y += e["speed"]

    # bullet-enemy hit
    for b in bullets[:]:
        for e in enemies[:]:
            if b.colliderect(e["rect"]):
                bullets.remove(b); enemies.remove(e)
                explosions.append({"pos": e["rect"].center, "r": 5, "life": 12})
                score += 10
                break

    # enemy hits ship (shield blocks it)
    if not fisting:
        for e in enemies[:]:
            if ship.colliderect(e["rect"]):
                enemies.remove(e); lives -= 1
                if lives <= 0: running = False

    # update explosions
    explosions = [ex for ex in explosions if ex["life"] > 0]
    for ex in explosions:
        ex["r"] += 2; ex["life"] -= 1

    # --- draw ---
    screen.fill((5, 5, 20))
    pygame.draw.line(screen, (50,50,80), (GAME_W, 0), (GAME_W, H), 2)

    for e  in enemies:    draw_enemy(e)
    for b  in bullets:    pygame.draw.rect(screen, (255,230,0), b, border_radius=2)
    for ex in explosions: pygame.draw.circle(screen, (255,100,0), ex["pos"], ex["r"])
    draw_ship(fisting)

    # HUD text
    screen.blit(font.render(f"Score: {score}   Lives: {'♥ '*lives}   Level: {level}", True, (200,200,200)), (10,10))
    if fisting:
        screen.blit(font.render("SHIELD ON", True, (0,255,100)), (10, 36))

    # camera panel (bottom-right)
    if ok:
        screen.blit(cam_surf, (GAME_W, H - CAM_H))
        pygame.draw.rect(screen, (50,50,80), (GAME_W, H-CAM_H, CAM_W, CAM_H), 2)
        screen.blit(font.render("CAMERA", True, (130,130,130)), (GAME_W+5, H-CAM_H+4))

    # gesture label above cam panel
    gesture = "PINCH → SHOOT" if pinching else ("FIST → SHIELD" if fisting else "MOVE HAND")
    color   = (255,230,0) if pinching else ((0,255,100) if fisting else (160,160,160))
    screen.blit(font.render(gesture, True, color), (GAME_W+5, H-CAM_H-26))

    pygame.display.flip()

cap.release()
pygame.quit()
sys.exit()