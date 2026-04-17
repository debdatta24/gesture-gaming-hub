import cv2, pygame, mediapipe as mp, math, random, sys

# --- setup ---
pygame.init()
W, H = 900, 600
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Gesture Snake")
clock = pygame.time.Clock()
font  = pygame.font.SysFont("consolas", 22)
font_big = pygame.font.SysFont("consolas", 48, bold=True)

CAM_W, CAM_H = 280, 210
GAME_W = W - CAM_W   # snake plays in left area
CELL   = 20          # grid cell size

# --- mediapipe ---
mp_hands = mp.solutions.hands
hands    = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw  = mp.solutions.drawing_utils
cap      = cv2.VideoCapture(0)

# --- direction from index finger angle ---
direction = (1, 0)   # (dx, dy) — starts moving right

def get_direction(frame):
    global direction
    frame[:] = cv2.flip(frame, 1)              # flip before processing
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = hands.process(rgb)
    if res.multi_hand_landmarks:
        lm  = res.multi_hand_landmarks[0].landmark
        tip = lm[8]; base = lm[5]
        dx  = tip.x - base.x                   # natural — no negation needed
        dy  = tip.y - base.y        # y increases downward in image
        angle = math.degrees(math.atan2(dy, dx))   # -180 to 180

        # map angle to 4 directions
        if   -45  <= angle <  45:   new_dir = (1,  0)   # right
        elif  45  <= angle < 135:   new_dir = (0,  1)   # down
        elif -135 <= angle < -45:   new_dir = (0, -1)   # up
        else:                       new_dir = (-1, 0)   # left

        # don't allow reversing
        if (new_dir[0] != -direction[0]) or (new_dir[1] != -direction[1]):
            direction = new_dir

        # draw arrow on frame to show detected direction
        arrow_labels = {(1,0):"RIGHT", (-1,0):"LEFT", (0,-1):"UP", (0,1):"DOWN"}
        cv2.putText(frame, arrow_labels[direction], (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        mp_draw.draw_landmarks(frame, res.multi_hand_landmarks[0], mp_hands.HAND_CONNECTIONS)
    return frame

def cam_to_surface(frame):
    frame = cv2.resize(frame, (CAM_W, CAM_H))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return pygame.surfarray.make_surface(frame.swapaxes(0, 1))

# --- snake helpers ---
COLS = GAME_W // CELL
ROWS = H      // CELL

def random_food(snake):
    while True:
        pos = (random.randint(2, COLS-3), random.randint(2, ROWS-3))
        if pos not in snake:
            return pos

def reset():
    cx, cy = COLS//2, ROWS//2
    snake = [(cx - i, cy) for i in range(5)]   # start with 5 cells
    food  = random_food(snake)
    return snake, food, 0

def draw_snake(snake):
    for i, (cx, cy) in enumerate(snake):
        color = (0, 220, 100) if i == 0 else (0, 160, 70)
        pygame.draw.rect(screen, color, (cx*CELL+1, cy*CELL+1, CELL-2, CELL-2), border_radius=4)

glow_tick = 0

def draw_food(food):
    fx, fy = food
    cx, cy = fx*CELL + CELL//2, fy*CELL + CELL//2
    # pulsing glow rings
    glow_r = int(CELL * 0.8 + math.sin(glow_tick * 0.15) * 4)
    for i, alpha in [(glow_r+8, 40), (glow_r+4, 80), (glow_r, 160)]:
        glow_surf = pygame.Surface((i*2, i*2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (220, 50, 50, alpha), (i, i), i)
        screen.blit(glow_surf, (cx - i, cy - i))
    pygame.draw.circle(screen, (255, 80, 80), (cx, cy), CELL//2 - 1)

# --- game state ---
snake, food, score = reset()
move_timer  = 0
MOVE_EVERY  = 8   # frames between snake steps (lower = faster)
game_over   = False

running = True
while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                snake, food, score = reset()
                direction = (1, 0)
                game_over = False

    # camera
    ok, frame = cap.read()
    if ok:
        frame    = get_direction(frame)
        cam_surf = cam_to_surface(frame)

    if not game_over:
        move_timer += 1
        if move_timer >= MOVE_EVERY:
            move_timer = 0

            # new head position
            hx, hy = snake[0]
            nx, ny = hx + direction[0], hy + direction[1]

            # wall collision
            if not (0 <= nx < COLS and 0 <= ny < ROWS):
                game_over = True
            # self collision
            elif (nx, ny) in snake[:-1]:
                game_over = True
            else:
                snake.insert(0, (nx, ny))
                if (nx, ny) == food:
                    score += 10
                    food = random_food(snake)
                else:
                    snake.pop()

    # --- draw ---
    screen.fill((10, 10, 20))

    # grid (subtle)
    for x in range(0, GAME_W, CELL):
        pygame.draw.line(screen, (20,20,35), (x,0), (x,H))
    for y in range(0, H, CELL):
        pygame.draw.line(screen, (20,20,35), (0,y), (GAME_W,y))

    glow_tick += 1
    draw_snake(snake)
    draw_food(food)

    # divider
    pygame.draw.line(screen, (50,50,80), (GAME_W,0), (GAME_W,H), 2)

    # HUD
    screen.blit(font.render(f"Score: {score}", True, (200,200,200)), (10,10))

    # direction arrow indicator
    arrows = {(1,0):"→", (-1,0):"←", (0,-1):"↑", (0,1):"↓"}
    screen.blit(font.render(f"Dir: {arrows[direction]}", True, (0,220,100)), (10,36))

    # game over overlay
    if game_over:
        txt = font_big.render("GAME OVER", True, (220,50,50))
        screen.blit(txt, (GAME_W//2 - txt.get_width()//2, H//2 - 50))
        txt2 = font.render("Press R to restart", True, (200,200,200))
        screen.blit(txt2, (GAME_W//2 - txt2.get_width()//2, H//2 + 20))

    # camera panel
    if ok:
        screen.blit(cam_surf, (GAME_W, H - CAM_H))
        pygame.draw.rect(screen, (50,50,80), (GAME_W, H-CAM_H, CAM_W, CAM_H), 2)
        screen.blit(font.render("CAMERA", True, (130,130,130)), (GAME_W+5, H-CAM_H+4))

    # gesture label
    dir_labels = {(1,0):"POINT RIGHT →", (-1,0):"← POINT LEFT",
                  (0,-1):"↑ POINT UP",   (0,1): "POINT DOWN ↓"}
    screen.blit(font.render(dir_labels[direction], True, (0,220,100)), (GAME_W+5, H-CAM_H-26))

    pygame.display.flip()

cap.release()
pygame.quit()
sys.exit()
