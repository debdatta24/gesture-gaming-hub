import cv2, pygame, mediapipe as mp, math, sys

# --- setup ---
pygame.init()
W, H = 900, 600
screen   = pygame.display.set_mode((W, H))
pygame.display.set_caption("Gesture Tic Tac Toe")
clock    = pygame.time.Clock()
font     = pygame.font.SysFont("consolas", 22)
font_big = pygame.font.SysFont("consolas", 52, bold=True)

CAM_W, CAM_H = 280, 210
GAME_W = W - CAM_W

# --- mediapipe ---
mp_hands = mp.solutions.hands
hands    = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw  = mp.solutions.drawing_utils
cap      = cv2.VideoCapture(0)

# --- gesture state ---
finger_x, finger_y = 0.5, 0.5
pinching   = False
prev_pinch = False

def get_gestures(frame):
    global finger_x, finger_y, pinching
    frame[:] = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = hands.process(rgb)
    if res.multi_hand_landmarks:
        lm = res.multi_hand_landmarks[0].landmark
        finger_x = lm[8].x
        finger_y = lm[8].y
        pinching = math.hypot(lm[4].x - lm[8].x, lm[4].y - lm[8].y) < 0.07
        mp_draw.draw_landmarks(frame, res.multi_hand_landmarks[0], mp_hands.HAND_CONNECTIONS)

        # draw fingertip dot
        fx = int(finger_x * frame.shape[1])
        fy = int(finger_y * frame.shape[0])
        cv2.circle(frame, (fx, fy), 10, (0,255,255), -1)

        # draw 3x3 zone grid on camera so user knows where they're pointing
        fh, fw = frame.shape[:2]
        for i in range(1, 3):
            cv2.line(frame, (fw*i//3, 0), (fw*i//3, fh), (100,100,255), 1)
            cv2.line(frame, (0, fh*i//3), (fw, fh*i//3), (100,100,255), 1)

        # highlight current cell on camera
        col = min(int(finger_x * 3), 2)
        row = min(int(finger_y * 3), 2)
        x1, y1 = col * fw//3, row * fh//3
        x2, y2 = x1 + fw//3, y1 + fh//3
        cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,255), 2)
    return frame

def cam_to_surface(frame):
    frame = cv2.resize(frame, (CAM_W, CAM_H))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return pygame.surfarray.make_surface(frame.swapaxes(0, 1))

# --- finger → cell (directly from normalised coords, no pixel math) ---
def finger_to_cell():
    col = min(int(finger_x * 3), 2)
    row = min(int(finger_y * 3), 2)
    return row * 3 + col

# --- board ---
BOARD_SIZE = 420
CELL_SIZE  = BOARD_SIZE // 3
BOARD_X    = (GAME_W - BOARD_SIZE) // 2
BOARD_Y    = (H      - BOARD_SIZE) // 2

board  = [""] * 9
turn   = "X"        # X = human, O = AI
winner = None
win_cells  = None
result_msg = ""
pinch_cd   = 0
ai_delay   = 0      # small pause before AI moves so it feels natural
hover_cell = 0

def check_winner(b):
    lines = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    for a,bb,c in lines:
        if b[a] and b[a] == b[bb] == b[c]:
            return b[a], (a,bb,c)
    if all(b): return "Draw", None
    return None, None

# --- minimax AI (~20 lines) ---
def minimax(b, is_max):
    w, _ = check_winner(b)
    if w == "O": return  1
    if w == "X": return -1
    if all(b):   return  0
    scores = []
    for i in range(9):
        if b[i] == "":
            b[i] = "O" if is_max else "X"
            scores.append(minimax(b, not is_max))
            b[i] = ""
    return max(scores) if is_max else min(scores)

def ai_move(b):
    best, pick = -9, 0
    for i in range(9):
        if b[i] == "":
            b[i] = "O"
            s = minimax(b, False)
            b[i] = ""
            if s > best:
                best, pick = s, i
    return pick

def reset():
    global board, turn, winner, win_cells, result_msg, hover_cell, ai_delay
    board = [""] * 9
    turn  = "X"; winner = None; win_cells = None
    result_msg = ""; hover_cell = 0; ai_delay = 0

def cell_rect(i):
    r, c = divmod(i, 3)
    return pygame.Rect(BOARD_X + c*CELL_SIZE, BOARD_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)

def draw_board():
    pygame.draw.rect(screen, (20,20,35),
                     (BOARD_X-4, BOARD_Y-4, BOARD_SIZE+8, BOARD_SIZE+8), border_radius=8)
    for i in range(9):
        r  = cell_rect(i)
        bg = (40,40,70) if i == hover_cell and not board[i] and not winner else (25,25,45)
        pygame.draw.rect(screen, bg, r, border_radius=6)
        pygame.draw.rect(screen, (60,60,100), r, 2, border_radius=6)
        cx, cy = r.centerx, r.centery
        d = CELL_SIZE // 3
        if board[i] == "X":
            pygame.draw.line(screen, (80,180,255), (cx-d,cy-d), (cx+d,cy+d), 5)
            pygame.draw.line(screen, (80,180,255), (cx+d,cy-d), (cx-d,cy+d), 5)
        elif board[i] == "O":
            pygame.draw.circle(screen, (255,100,100), (cx,cy), d, 5)

def draw_win_line():
    if not win_cells: return
    r1, r2 = cell_rect(win_cells[0]), cell_rect(win_cells[2])
    pygame.draw.line(screen, (255,220,0), r1.center, r2.center, 6)

def draw_finger():
    # show which cell the finger is on as a label on game area
    r   = cell_rect(hover_cell)
    col = (255,220,0) if pinching else (0,220,255)
    pygame.draw.rect(screen, col, r, 3, border_radius=6)

# --- main loop ---
running = True
while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            reset()

    ok, frame = cap.read()
    if ok:
        frame    = get_gestures(frame)
        cam_surf = cam_to_surface(frame)

    hover_cell = finger_to_cell()

    pinch_just_pressed = pinching and not prev_pinch
    if pinch_cd > 0: pinch_cd -= 1

    # human turn
    if turn == "X" and not winner:
        if pinch_just_pressed and pinch_cd == 0 and board[hover_cell] == "":
            board[hover_cell] = "X"
            winner, win_cells = check_winner(board)
            result_msg = ("X Wins!" if winner=="X" else "Draw!") if winner else ""
            if not winner: turn = "O"; ai_delay = 40
            pinch_cd = 25

    # AI turn
    if turn == "O" and not winner:
        if ai_delay > 0: ai_delay -= 1
        else:
            move = ai_move(board)
            board[move] = "O"
            winner, win_cells = check_winner(board)
            result_msg = "O Wins!" if winner == "O" else ("Draw!" if winner else "")
            if not winner: turn = "X"

    prev_pinch = pinching

    # --- draw ---
    screen.fill((10,10,20))
    draw_board()
    draw_win_line()
    if not winner: draw_finger()
    pygame.draw.line(screen, (50,50,80), (GAME_W,0), (GAME_W,H), 2)

    # HUD
    if not winner:
        msg = "Your turn — point & pinch" if turn=="X" else "AI thinking..."
        screen.blit(font.render(msg, True, (180,180,180)), (10,10))
    else:
        txt = font_big.render(result_msg, True, (255,220,0))
        screen.blit(txt, (GAME_W//2 - txt.get_width()//2, 18))
        screen.blit(font.render("Press R to restart", True, (150,150,150)),
                    (GAME_W//2 - 95, 78))

    label = "PINCHING ✓" if pinching else f"CELL {hover_cell+1}"
    color = (255,220,0) if pinching else (0,220,255)
    screen.blit(font.render(label, True, color), (10, H-36))

    if ok:
        screen.blit(cam_surf, (GAME_W, H-CAM_H))
        pygame.draw.rect(screen, (50,50,80), (GAME_W, H-CAM_H, CAM_W, CAM_H), 2)
        screen.blit(font.render("CAMERA — point in zone", True, (130,130,130)),
                    (GAME_W+4, H-CAM_H+4))

    pygame.display.flip()

cap.release()
pygame.quit()
sys.exit()