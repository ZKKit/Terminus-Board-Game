import pygame
import sys
import copy
import time

# --- CONSTANTS & CONFIG ---
SQ_SIZE = 50
ROWS, COLS = 12, 12
OFFSET = 40  
BOARD_SIZE = ROWS * SQ_SIZE
UI_WIDTH = 340

WIDTH = BOARD_SIZE + (OFFSET * 2) + UI_WIDTH
HEIGHT = BOARD_SIZE + (OFFSET * 2)

# Redesigned Color Palette
MENU_BG = (18, 20, 26)      
GAME_BG = (22, 25, 31)      
SIDEBAR_COLOR = (28, 31, 38)
GRID_COLOR = (45, 50, 60)
HIGHLIGHT_COLOR = (80, 180, 120, 100)
CAPTURE_COLOR = (220, 70, 70, 120)
HOVER_COLOR = (255, 255, 255, 15)
SELECT_COLOR = (80, 130, 240, 140)
TEXT_COLOR = (240, 245, 255)
COORD_COLOR = (120, 125, 135)
BTN_COLOR = (45, 50, 60)
GREY_UI = (50, 55, 65) 

# Piece States
EMPTY = 0
B_PAWN, W_PAWN = 1, 2
B_BOUND, W_BOUND = 3, 4
B_TRAP, W_TRAP = 5, 6

def copy_to_clipboard(text):
    pygame.scrap.init()
    pygame.scrap.put(pygame.SCRAP_TEXT, text.encode('utf-8'))

class Button:
    def __init__(self, x, y, w, h, text, font, color=BTN_COLOR, text_col=TEXT_COLOR):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.color = color
        self.text_col = text_col
        self.hovered = False

    def draw(self, screen):
        c = (min(self.color[0]+30, 255), min(self.color[1]+30, 255), min(self.color[2]+30, 255)) if self.hovered else self.color
        pygame.draw.rect(screen, c, self.rect, border_radius=8)
        pygame.draw.rect(screen, (70, 75, 85), self.rect, 2, border_radius=8)
        txt = self.font.render(self.text, True, self.text_col)
        screen.blit(txt, (self.rect.centerx - txt.get_width()//2, self.rect.centery - txt.get_height()//2))

    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)
        return self.hovered

class TerminusGame:
    def __init__(self, time_limit, increment):
        self.board = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]
        self.current_player = B_PAWN
        self.history = set()
        self.move_log = []
        self.winner = None
        self.win_reason = ""
        self.flipped = False
        self.timers = {B_PAWN: float(time_limit) if time_limit else None, 
                       W_PAWN: float(time_limit) if time_limit else None}
        self.increment = increment
        self.last_tick = time.time()
        self.setup_board()

    def setup_board(self):
        for r in [10, 11]:
            for c in range(COLS): self.board[r][c] = B_PAWN
        for r in [0, 1]:
            for c in range(COLS): self.board[r][c] = W_PAWN
        for r in [8, 9]:
            for c in list(range(0, 4)) + list(range(8, 12)): self.board[r][c] = B_PAWN
        for r in [2, 3]:
            for c in list(range(0, 4)) + list(range(8, 12)): self.board[r][c] = W_PAWN
        self.save_state()

    def save_state(self):
        self.history.add((tuple(tuple(row) for row in self.board), self.current_player))

    def update_timers(self):
        if self.winner or self.timers[self.current_player] is None: return
        now = time.time()
        # Cap dt to 0.1s to prevent window drag lag from instantly timing out the player
        dt = min(now - self.last_tick, 0.1) 
        self.timers[self.current_player] -= dt
        self.last_tick = now
        if self.timers[self.current_player] <= 0:
            self.timers[self.current_player] = 0
            self.winner = "White" if self.current_player == B_PAWN else "Black"
            self.win_reason = "Time Out"

    def get_friendly_states(self, player):
        return {B_PAWN, B_BOUND, B_TRAP} if player == B_PAWN else {W_PAWN, W_BOUND, W_TRAP}

    def has_orthogonal_support(self, r, c, player):
        friendly = self.get_friendly_states(player)
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                if self.board[nr][nc] in friendly: return True
        return False

    def get_legal_moves(self, r, c):
        moves = []
        player = self.board[r][c]
        if player not in (B_PAWN, W_PAWN): return moves
        has_support = self.has_orthogonal_support(r, c, player)
        
        for dr in [-1,0,1]:
            for dc in [-1,0,1]:
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < ROWS and 0 <= nc < COLS:
                    target = self.board[nr][nc]
                    move_type = None
                    if target == EMPTY: move_type = "shift"
                    elif (player == B_PAWN and target == W_PAWN) or (player == W_PAWN and target == B_PAWN):
                        if has_support: move_type = "capture"
                    
                    if move_type and not self.violates_superko(r, c, nr, nc, move_type, player):
                        moves.append((nr, nc, move_type))
        return moves

    def violates_superko(self, r1, c1, r2, c2, move_type, player):
        temp_board = [list(row) for row in self.board]
        temp_board[r2][c2] = (B_BOUND if player == B_PAWN else W_BOUND) if move_type == "capture" else player
        temp_board[r1][c1] = EMPTY
        
        # Only run isolation on captures to save immense CPU cycles
        if move_type == "capture":
            temp_board = self.resolve_isolation(temp_board)
            
        next_p = W_PAWN if player == B_PAWN else B_PAWN
        return (tuple(tuple(row) for row in temp_board), next_p) in self.history

    def make_move(self, r1, c1, r2, c2, move_type):
        cols = "ABCDEFGHIJKL"
        p_name = "Black" if self.current_player == B_PAWN else "White"
        self.move_log.append(f"{p_name}: {cols[c1]}{12-r1} > {cols[c2]}{12-r2}")
        
        player = self.board[r1][c1]
        self.board[r2][c2] = (B_BOUND if player == B_PAWN else W_BOUND) if move_type == "capture" else player
        self.board[r1][c1] = EMPTY
        
        if move_type == "capture":
            self.board = self.resolve_isolation(self.board)
            
        if self.timers[self.current_player] is not None:
            self.timers[self.current_player] += self.increment
            
        self.current_player = W_PAWN if self.current_player == B_PAWN else B_PAWN
        self.last_tick = time.time()
        self.save_state()
        self.check_win()

    def resolve_isolation(self, board):
        visited = set()
        new_board = [list(row) for row in board]
        for r in range(ROWS):
            for c in range(COLS):
                if board[r][c] not in (B_BOUND, W_BOUND) and (r, c) not in visited:
                    part, b_mob, w_mob = [], 0, 0
                    q = [(r, c)]; visited.add((r, c))
                    while q:
                        cr, cc = q.pop(0); part.append((cr, cc))
                        s = board[cr][cc]
                        if s == B_PAWN: b_mob += 1
                        if s == W_PAWN: w_mob += 1
                        for dr in [-1,0,1]:
                            for dc in [-1,0,1]:
                                nr, nc = cr+dr, cc+dc
                                if 0 <= nr < ROWS and 0 <= nc < COLS and (nr,nc) not in visited and board[nr][nc] not in (B_BOUND, W_BOUND):
                                    visited.add((nr,nc)); q.append((nr,nc))
                    if b_mob > 0 and w_mob == 0:
                        for pr, pc in part: 
                            if new_board[pr][pc] == B_PAWN: new_board[pr][pc] = B_TRAP
                    elif w_mob > 0 and b_mob == 0:
                        for pr, pc in part:
                            if new_board[pr][pc] == W_PAWN: new_board[pr][pc] = W_TRAP
        return new_board

    def check_win(self):
        b_m = sum(row.count(B_PAWN) for row in self.board)
        w_m = sum(row.count(W_PAWN) for row in self.board)
        if b_m == 0 and w_m == 0:
            b_s, w_s = self.calc_territory()
            self.winner = "Black" if b_s > w_s else ("White" if w_s > b_s else "Draw")
            self.win_reason = f"Score {b_s}-{w_s}"
            return
        curr_m = b_m if self.current_player == B_PAWN else w_m
        if curr_m == 0:
            self.winner = "White" if self.current_player == B_PAWN else "Black"
            self.win_reason = "Mobile Extinction"
        elif not self.has_any_move():
            self.winner = "White" if self.current_player == B_PAWN else "Black"
            self.win_reason = "Mobility Starvation"

    def has_any_move(self):
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] == self.current_player and self.get_legal_moves(r, c): return True
        return False

    def calc_territory(self):
        b_s, w_s, visited = 0, 0, set()
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] not in (B_BOUND, W_BOUND) and (r, c) not in visited:
                    part, b_t, w_t = [], 0, 0
                    q = [(r, c)]; visited.add((r, c))
                    while q:
                        cr, cc = q.pop(0); part.append((cr, cc))
                        if self.board[cr][cc] == B_TRAP: b_t += 1
                        if self.board[cr][cc] == W_TRAP: w_t += 1
                        for dr in [-1,0,1]:
                            for dc in [-1,0,1]:
                                nr, nc = cr+dr, cc+dc
                                if 0<=nr<ROWS and 0<=nc<COLS and (nr,nc) not in visited and self.board[nr][nc] not in (B_BOUND, W_BOUND):
                                    visited.add((nr,nc)); q.append((nr,nc))
                    if b_t > 0 and w_t == 0: b_s += len(part)
                    elif w_t > 0 and b_t == 0: w_s += len(part)
        return b_s, w_s

def format_time(seconds):
    if seconds is None: return "∞"
    s = int(max(0, seconds % 60))
    m = int(max(0, seconds // 60))
    return f"{m:02}:{s:02}"

def draw_piece(screen, state, cx, cy):
    radius = SQ_SIZE // 2 - 8
    if state in (B_PAWN, B_TRAP):
        pygame.draw.circle(screen, (25, 28, 35), (cx, cy), radius)
        pygame.draw.circle(screen, (100, 105, 120), (cx, cy), radius, 2)
    elif state in (W_PAWN, W_TRAP):
        pygame.draw.circle(screen, (230, 235, 245), (cx, cy), radius)
        pygame.draw.circle(screen, (150, 155, 165), (cx, cy), radius, 2)
    
    if state in (B_TRAP, W_TRAP):
        # Trapped overlay pattern
        pygame.draw.line(screen, (200, 60, 60), (cx-radius+4, cy-radius+4), (cx+radius-4, cy+radius-4), 3)
        pygame.draw.line(screen, (200, 60, 60), (cx+radius-4, cy-radius+4), (cx-radius+4, cy+radius-4), 3)

    if state == B_BOUND:
        rect = pygame.Rect(cx-radius, cy-radius, radius*2, radius*2)
        pygame.draw.rect(screen, (25, 28, 35), rect, border_radius=4)
        pygame.draw.rect(screen, (80, 85, 100), rect, 3, border_radius=4)
        pygame.draw.rect(screen, (40, 45, 55), rect.inflate(-8, -8), border_radius=2)
    elif state == W_BOUND:
        rect = pygame.Rect(cx-radius, cy-radius, radius*2, radius*2)
        pygame.draw.rect(screen, (200, 205, 215), rect, border_radius=4)
        pygame.draw.rect(screen, (120, 125, 135), rect, 3, border_radius=4)
        pygame.draw.rect(screen, (160, 165, 175), rect.inflate(-8, -8), border_radius=2)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("TERMINUS")
    
    f_s = pygame.font.SysFont("Inter, Times New Roman", 18)
    f_xs = pygame.font.SysFont("Inter, Times New Roman", 14, bold=True)
    f_m = pygame.font.SysFont("Inter, Times New Roman", 22, bold=True)
    f_l = pygame.font.SysFont("Inter, Times New Roman", 36, bold=True)
    clock = pygame.time.Clock()

    while True: 
        menu_active = True
        time_opts = [("15+0", 900, 0), ("30+20", 1800, 20), ("60+30", 3600, 30), ("No Limit", 0, 0)]
        sel_time = 0
        custom_min, custom_inc = "5", "3"
        active_input = None 
        confirm_app_quit = False

        while menu_active:
            screen.fill(MENU_BG)
            m_pos = pygame.mouse.get_pos()
            title = f_l.render("TERMINUS", True, TEXT_COLOR)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, 60))
            
            t_btns = []
            for i, (name, _, _) in enumerate(time_opts):
                col = (60, 100, 180) if sel_time == i else BTN_COLOR
                b = Button(WIDTH//2 - 150 + (i%2)*160, 180 + (i//2)*60, 140, 45, name, f_m, col)
                t_btns.append(b)
            
            col_c = (60, 100, 180) if sel_time == 4 else BTN_COLOR
            custom_btn = Button(WIDTH//2 - 150, 300, 140, 45, "Custom", f_m, col_c)
            min_rect = pygame.Rect(WIDTH//2 + 10, 300, 60, 45)
            inc_rect = pygame.Rect(WIDTH//2 + 80, 300, 60, 45)
            pygame.draw.rect(screen, (70,75,85) if active_input=='min' else (30,35,40), min_rect, border_radius=6)
            pygame.draw.rect(screen, (70,75,85) if active_input=='inc' else (30,35,40), inc_rect, border_radius=6)
            screen.blit(f_m.render(custom_min, True, TEXT_COLOR), (min_rect.x+10, min_rect.y+10))
            screen.blit(f_m.render(custom_inc, True, TEXT_COLOR), (inc_rect.x+10, inc_rect.y+10))
            screen.blit(f_xs.render("mins", True, (140, 145, 155)), (min_rect.x, min_rect.bottom + 4))
            screen.blit(f_xs.render("inc (secs)", True, (140, 145, 155)), (inc_rect.x, inc_rect.bottom + 4))

            start_btn = Button(WIDTH//2 - 100, 420, 200, 50, "PLAY GAME", f_m, (50, 160, 100))
            exit_prog_btn = Button(WIDTH//2 - 100, 490, 200, 50, "EXIT", f_m, (180, 60, 80))

            for b in t_btns + [custom_btn, start_btn, exit_prog_btn]:
                b.check_hover(m_pos); b.draw(screen)

            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if confirm_app_quit:
                        if pygame.Rect(WIDTH//2-110, HEIGHT//2+20, 100, 40).collidepoint(event.pos): pygame.quit(); sys.exit()
                        if pygame.Rect(WIDTH//2+10, HEIGHT//2+20, 100, 40).collidepoint(event.pos): confirm_app_quit = False
                        continue
                    active_input = None
                    if start_btn.rect.collidepoint(event.pos): menu_active = False
                    if exit_prog_btn.rect.collidepoint(event.pos): confirm_app_quit = True
                    for i, b in enumerate(t_btns):
                        if b.rect.collidepoint(event.pos): sel_time = i
                    if custom_btn.rect.collidepoint(event.pos): sel_time = 4
                    if min_rect.collidepoint(event.pos): active_input, sel_time = 'min', 4
                    if inc_rect.collidepoint(event.pos): active_input, sel_time = 'inc', 4
                
                if event.type == pygame.KEYDOWN and active_input:
                    if event.key == pygame.K_BACKSPACE:
                        if active_input == 'min': custom_min = custom_min[:-1]
                        else: custom_inc = custom_inc[:-1]
                    elif event.unicode.isdigit():
                        if active_input == 'min' and len(custom_min) < 3: custom_min += event.unicode
                        elif active_input == 'inc' and len(custom_inc) < 3: custom_inc += event.unicode

            if confirm_app_quit:
                s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); s.fill((10,12,16,220)); screen.blit(s,(0,0))
                pygame.draw.rect(screen, GREY_UI, (WIDTH//2-125, HEIGHT//2-60, 250, 120), border_radius=12)
                screen.blit(f_m.render("QUIT PROGRAM?", True, TEXT_COLOR), (WIDTH//2-85, HEIGHT//2-30))
                pygame.draw.rect(screen, (60, 140, 80), (WIDTH//2-110, HEIGHT//2+20, 100, 40), border_radius=6)
                pygame.draw.rect(screen, (180, 60, 80), (WIDTH//2+10, HEIGHT//2+20, 100, 40), border_radius=6)
                screen.blit(f_s.render("YES", True, TEXT_COLOR), (WIDTH//2-75, HEIGHT//2+30))
                screen.blit(f_s.render("NO", True, TEXT_COLOR), (WIDTH//2+50, HEIGHT//2+30))
            
            pygame.display.flip()
            clock.tick(60)

        if sel_time < 4: t_limit, t_inc = time_opts[sel_time][1], time_opts[sel_time][2]
        else: t_limit, t_inc = int(custom_min or 5)*60, int(custom_inc or 0)
        
        game = TerminusGame(t_limit, t_inc)
        sel_pos, valid_moves = None, []
        confirm_resign_who = None 
        confirm_exit_to_menu = False
        game_running = True

        while game_running:
            game.update_timers()
            m_pos = pygame.mouse.get_pos()
            screen.fill(GAME_BG)

            col_labels = "ABCDEFGHIJKL"
            for i in range(12):
                val = i + 1 if game.flipped else 12 - i
                txt = f_xs.render(str(val), True, COORD_COLOR)
                screen.blit(txt, (OFFSET // 2 - txt.get_width() // 2, i * SQ_SIZE + OFFSET + SQ_SIZE//2 - txt.get_height() // 2))
                char = col_labels[11-i] if game.flipped else col_labels[i]
                txt = f_xs.render(char, True, COORD_COLOR)
                screen.blit(txt, (i * SQ_SIZE + OFFSET + SQ_SIZE//2 - txt.get_width()//2, BOARD_SIZE + OFFSET + (OFFSET // 2 - txt.get_height()//2)))
                screen.blit(txt, (i * SQ_SIZE + OFFSET + SQ_SIZE//2 - txt.get_width()//2, OFFSET // 2 - txt.get_height() // 2))

            for r in range(ROWS):
                for c in range(COLS):
                    dr, dc = (11-r, 11-c) if game.flipped else (r, c)
                    rect = pygame.Rect(dc * SQ_SIZE + OFFSET, dr * SQ_SIZE + OFFSET, SQ_SIZE, SQ_SIZE)
                    
                    # Hover effect
                    if rect.collidepoint(m_pos) and not confirm_resign_who and not confirm_exit_to_menu:
                        s = pygame.Surface((SQ_SIZE, SQ_SIZE), pygame.SRCALPHA)
                        s.fill(HOVER_COLOR); screen.blit(s, rect.topleft)
                        
                    pygame.draw.rect(screen, GRID_COLOR, rect, 1)
                    
                    if sel_pos and r == sel_pos[0] and c == sel_pos[1]:
                        s = pygame.Surface((SQ_SIZE, SQ_SIZE), pygame.SRCALPHA); s.fill(SELECT_COLOR); screen.blit(s, rect.topleft)
                    for mr, mc, mt in valid_moves:
                        if r == mr and c == mc:
                            s = pygame.Surface((SQ_SIZE, SQ_SIZE), pygame.SRCALPHA)
                            s.fill(CAPTURE_COLOR if mt == "capture" else HIGHLIGHT_COLOR); screen.blit(s, rect.topleft)
                            
                    state = game.board[r][c]
                    if state != EMPTY:
                        draw_piece(screen, state, rect.centerx, rect.centery)

            sidebar_x = BOARD_SIZE + (OFFSET * 2)
            pygame.draw.rect(screen, SIDEBAR_COLOR, (sidebar_x, 0, UI_WIDTH, HEIGHT))
            
            # Timers
            pygame.draw.rect(screen, (35, 40, 48), (sidebar_x+20, OFFSET, 300, 100), border_radius=10)
            screen.blit(f_s.render("WHITE", True, TEXT_COLOR), (sidebar_x+40, OFFSET+15))
            screen.blit(f_l.render(format_time(game.timers[W_PAWN]), True, TEXT_COLOR), (sidebar_x+180, OFFSET+10))
            screen.blit(f_s.render("BLACK", True, TEXT_COLOR), (sidebar_x+40, OFFSET+55))
            screen.blit(f_l.render(format_time(game.timers[B_PAWN]), True, TEXT_COLOR), (sidebar_x+180, OFFSET+50))
            
            # Status Box
            stat_rect = pygame.Rect(sidebar_x + 20, OFFSET + 120, 300, 100)
            pygame.draw.rect(screen, (45, 50, 60), stat_rect, border_radius=10)
            if game.winner:
                screen.blit(f_m.render(f"{game.winner.upper()} WINS", True, (120, 240, 140)), (stat_rect.x+20, stat_rect.y+20))
                screen.blit(f_s.render(game.win_reason, True, (200, 205, 215)), (stat_rect.x+20, stat_rect.y+50))
            else:
                curr_turn = "BLACK'S TURN" if game.current_player == B_PAWN else "WHITE'S TURN"
                color_t = (180, 190, 200) if game.current_player == B_PAWN else (255, 255, 255)
                screen.blit(f_m.render(curr_turn, True, color_t), (stat_rect.x+20, stat_rect.y+35))
                
            by = OFFSET + 240
            btn_res_w = Button(sidebar_x+20, by, 300, 45, "WHITE RESIGN", f_m, (70, 75, 85))
            btn_res_b = Button(sidebar_x+20, by+55, 300, 45, "BLACK RESIGN", f_m, (40, 45, 55))
            btn_flip = Button(sidebar_x+20, by+120, 145, 40, "FLIP BOARD", f_s)
            btn_copy = Button(sidebar_x+175, by+120, 145, 40, "COPY LOG", f_s)
            btn_exit = Button(sidebar_x+20, by+175, 300, 45, "NEW GAME" if game.winner else "EXIT TO MENU", f_m)
            
            game_btns = [btn_flip, btn_copy, btn_exit]
            if not game.winner: game_btns += [btn_res_w, btn_res_b]
            for b in game_btns: b.check_hover(m_pos); b.draw(screen)

            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if confirm_resign_who or confirm_exit_to_menu:
                        if pygame.Rect(WIDTH//2-110, HEIGHT//2+20, 100, 40).collidepoint(event.pos):
                            if confirm_resign_who: 
                                game.winner = "Black" if confirm_resign_who == "White" else "White"
                                game.win_reason = f"{confirm_resign_who} Resigned"
                            if confirm_exit_to_menu: game_running = False
                            confirm_resign_who = confirm_exit_to_menu = False
                        elif pygame.Rect(WIDTH//2+10, HEIGHT//2+20, 100, 40).collidepoint(event.pos):
                            confirm_resign_who = confirm_exit_to_menu = False
                        continue
                        
                    if OFFSET < event.pos[0] < BOARD_SIZE + OFFSET and OFFSET < event.pos[1] < BOARD_SIZE + OFFSET and not game.winner:
                        c, r = (event.pos[0] - OFFSET) // SQ_SIZE, (event.pos[1] - OFFSET) // SQ_SIZE
                        if game.flipped: r, c = 11 - r, 11 - c
                        move_found = False
                        for mr, mc, mt in valid_moves:
                            if r == mr and c == mc:
                                game.make_move(sel_pos[0], sel_pos[1], r, c, mt)
                                sel_pos, valid_moves, move_found = None, [], True; break
                        if not move_found:
                            if game.board[r][c] == game.current_player: sel_pos, valid_moves = (r, c), game.get_legal_moves(r, c)
                            else: sel_pos, valid_moves = None, []
                    else:
                        if not game.winner:
                            if btn_res_w.rect.collidepoint(event.pos): confirm_resign_who = "White"
                            if btn_res_b.rect.collidepoint(event.pos): confirm_resign_who = "Black"
                        if btn_flip.rect.collidepoint(event.pos): game.flipped = not game.flipped
                        if btn_copy.rect.collidepoint(event.pos): copy_to_clipboard("\n".join(game.move_log))
                        if btn_exit.rect.collidepoint(event.pos): confirm_exit_to_menu = True

            if confirm_resign_who or confirm_exit_to_menu:
                s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); s.fill((10,12,16,220)); screen.blit(s,(0,0))
                pygame.draw.rect(screen, GREY_UI, (WIDTH//2-135, HEIGHT//2-60, 270, 120), border_radius=12)
                msg = "EXIT TO MENU?" if not confirm_resign_who else f"{confirm_resign_who.upper()} RESIGN?"
                if game.winner and confirm_exit_to_menu: msg = "NEW GAME?"
                screen.blit(f_m.render(msg, True, TEXT_COLOR), (WIDTH//2-90, HEIGHT//2-30))
                pygame.draw.rect(screen, (60, 140, 80), (WIDTH//2-110, HEIGHT//2+20, 100, 40), border_radius=6)
                pygame.draw.rect(screen, (180, 60, 80), (WIDTH//2+10, HEIGHT//2+20, 100, 40), border_radius=6)
                screen.blit(f_s.render("YES", True, TEXT_COLOR), (WIDTH//2-75, HEIGHT//2+30))
                screen.blit(f_s.render("NO", True, TEXT_COLOR), (WIDTH//2+50, HEIGHT//2+30))
                
            pygame.display.flip()
            clock.tick(60)

if __name__ == "__main__":
    main()
