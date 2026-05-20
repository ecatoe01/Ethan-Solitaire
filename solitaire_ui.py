import pygame
import sys
import time
from solitaire import Solitaire, Suit, Card

pygame.init()

# === Layout constants ===
SCREEN_W, SCREEN_H = 1050, 600 # 7:4 ratio 1050, 600
CARD_W           = SCREEN_W * 0.06
CARD_H           = CARD_W * 1.4
HEADER_H         = SCREEN_H / 8
SIDES_W          = SCREEN_W * 0.09
H_GAP            = CARD_W * 1.9     # horizontal space between tableau columns
V_GAP            = CARD_H * 1.3     # vertical space between cards in stock and foundation areas
TABLEAU_X        = (SCREEN_W - (CARD_W + 6 * H_GAP)) / 2       # x of first tableau column
TABLEAU_Y        = SCREEN_H * 0.16  # y where tableau starts
FACE_UP_OFFSET   = 25               # vertical gap between face-up cards in a pile
FACE_DOWN_OFFSET = 15               # vertical gap between face-down cards
STOCK_X, STOCK_Y = (SIDES_W - CARD_W) / 2, TABLEAU_Y
WASTE_X, WASTE_Y = STOCK_X, TABLEAU_Y + V_GAP
FOUND_X, FOUND_Y = SCREEN_W - SIDES_W + (SIDES_W - CARD_W) / 2, TABLEAU_Y
FOUND_GAP        = CARD_H
FOOTER_H         = SCREEN_H * 0.08
FOOTER_Y         = SCREEN_H - FOOTER_H
BUTTON_W         = CARD_W * 2
BUTTON_H         = FOOTER_H * 0.6
UNDO_RECT    = pygame.Rect(TABLEAU_X + H_GAP - CARD_W / 2, FOOTER_Y + (FOOTER_H - BUTTON_H) / 2, BUTTON_W, BUTTON_H)
NEWGAME_RECT = pygame.Rect(TABLEAU_X + 5 * H_GAP - CARD_W / 2, FOOTER_Y + (FOOTER_H - BUTTON_H) / 2, BUTTON_W, BUTTON_H)

# === Font and Colors === #
font = pygame.font.SysFont('Segoe UI', 20, bold=True)
button_font = pygame.font.SysFont('Segoe UI Symbol', 18, bold=True)
GREEN       = ( 67, 161,  75)
DARK_GREEN  = ( 53, 122,  60)
WHITE       = (255, 255, 255)
BLACK       = (  0,   0,   0)
GRAY        = (159, 161, 164)
DARK_GRAY   = ( 49,  49,  49)
RED         = (200,   0,   0)

# === Setup === #
game = Solitaire(shuffle_deck=True)
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Solitaire")
clock = pygame.time.Clock()
RANK_MAP = {1: 'A', 11: 'J', 12: 'Q', 13: 'K'}
drag = {
    'active': False,
    'cards': [],        # the Card objects being dragged
    'source_pile': None,# which tableau column they came from
    'source_idx': None, # index within that pile
    'offset': (0, 0),   # cursor offset from card top-left
    'x': 0, 'y': 0      # current draw position
}
last_click = {'time': 0, 'pos': None, 'region_clicked': None, 'col': None, 'card': None}
START_TIME = time.time()
F_SUIT_ORDER = [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]

# ========== FUNCTIONS ========== #
def success_update(game: Solitaire, points):
    game.score += points
    game.moves += 1
    game._add_to_history()

def get_rank_str(rank):
    return RANK_MAP.get(rank, str(rank))

def get_suit_color(suit):
    return RED if suit in (Suit.HEARTS, Suit.DIAMONDS) else BLACK

def get_time_str(secs):
    secs = round(secs)
    hours = int(secs // 3600)
    minutes = int((secs - hours * 3600) // 60)
    seconds = int(round(secs - hours * 3600 - minutes * 60))

    result = ''
    result += f"{'0' if hours < 10 else ''}{str(hours)}:"
    result += f"{'0' if minutes < 10 else ''}{str(minutes)}:"
    result += f"{'0' if seconds < 10 else ''}{str(seconds)}"

    return result

def get_waste_y(stock):
    y = WASTE_Y
    if stock.wastepile.cards:
        y = WASTE_Y + min(2, len(stock.wastepile.cards) - 1) * FACE_UP_OFFSET
    return y

def draw_card(surface, rank_str, suit_str, x, y,
              suit_color=BLACK, face_up_color=WHITE,
              face_down_color=GRAY, face_up_border_color=BLACK,
              face_down_border_color=BLACK, face_up=True
              ):
    """Draw a single card at (x, y)."""
    rect = pygame.Rect(x, y, CARD_W, CARD_H)

    if face_up:
        # Card background + border
        pygame.draw.rect(surface=surface, color=face_up_color, rect=rect, border_radius=6)
        pygame.draw.rect(surface=surface, color=face_up_border_color, rect=rect, width=2, border_radius=6)

        # Rank + suit in lop-left
        label = font.render(f"{rank_str}{suit_str}", True, suit_color)
        surface.blit(label, (x + CARD_W * 0.09, y))
    else:
        # Card background + border
        pygame.draw.rect(surface=surface, color=face_down_color, rect=rect, border_radius=6)
        pygame.draw.rect(surface=surface, color=face_down_border_color, rect=rect, width=2, border_radius=6)

def draw_board(surface, score, moves):
    # -- Tableau Area --
    screen.fill(GREEN)
    for i in range(7):
        x = TABLEAU_X + i * H_GAP
        y = TABLEAU_Y
        draw_empty_slot(surface, x, y)

    # -- Stock/Waste Area --
    rect = pygame.Rect(0, 0, SIDES_W, SCREEN_H)
    pygame.draw.rect(surface, color=DARK_GREEN, rect=rect)
    draw_empty_slot(surface, STOCK_X, STOCK_Y)
    draw_empty_slot(surface, WASTE_X, WASTE_Y)

    # -- Foundation Area --
    rect = pygame.Rect(SCREEN_W - SIDES_W, 0, SIDES_W, SCREEN_H)
    pygame.draw.rect(surface, color=DARK_GREEN, rect=rect)
    for i, suit in enumerate(F_SUIT_ORDER):
        y = FOUND_Y + i * V_GAP
        draw_card(surface, '', suit.symbol, FOUND_X, y, suit_color=(0, 60, 0), face_up_color=(0, 80, 0), face_up_border_color=(0, 60, 0), face_up=True)

    # -- Header --
    rect = pygame.Rect(0, 0, SCREEN_W, HEADER_H)
    pygame.draw.rect(surface, color=DARK_GRAY, rect=rect)
    # Time
    time_str = get_time_str(time.time() - START_TIME)
    label = font.render(time_str, True, WHITE)
    label_rect = label.get_rect(center=(TABLEAU_X + H_GAP + CARD_W / 2, HEADER_H / 2))
    surface.blit(label, label_rect)
    # Score
    score_str = "Score " + str(score).rjust(4)
    label = font.render(score_str, True, WHITE)
    label_rect = label.get_rect(center=(TABLEAU_X + 3 * H_GAP + CARD_W / 2, HEADER_H / 2))
    surface.blit(label, label_rect)
    # Moves
    move_str = "Moves " + str(moves).rjust(4)
    label = font.render(move_str, True, WHITE)
    label_rect = label.get_rect(center=(TABLEAU_X + 5 * H_GAP + CARD_W / 2, HEADER_H / 2))
    surface.blit(label, label_rect)
    # TODO: Add mute button (maybe?) and X to exit

    # -- Footer --
    # TODO: Add undo button and New Game button
    mouse_pos = pygame.mouse.get_pos()
    draw_button(surface, UNDO_RECT, "↩ Undo", hovered=UNDO_RECT.collidepoint(mouse_pos))
    draw_button(surface, NEWGAME_RECT, "★ New Game", hovered=NEWGAME_RECT.collidepoint(mouse_pos))

def draw_empty_slot(surface, x, y):
    """Dotted outline showing an empty pile slot."""
    rect = pygame.Rect(x, y, CARD_W, CARD_H)
    pygame.draw.rect(surface, (0, 80, 0), rect, border_radius=6)            # (0, 80, 0) Light-Dark Green
    pygame.draw.rect(surface, (0, 60, 0), rect, width=2, border_radius=6)   # (0, 60, 0) Dark Green

def draw_tableau(surface, tableau, drag):
    for col_i, pile in enumerate(tableau.piles):
        x = TABLEAU_X + col_i * H_GAP
        y = TABLEAU_Y

        if not pile.cards:
            # draw_empty_slot(surface, x, y)
            continue

        for card_i, card in enumerate(pile.cards):
            # skip cards currently being dragged
            if drag['active'] and col_i == drag['source_pile'] and card_i >= drag['source_idx']:
                break
            draw_card(surface, get_rank_str(card.rank), card.suit.symbol, x, y, suit_color=get_suit_color(card.suit), face_up=card.is_face_up)
            y += FACE_UP_OFFSET if card.is_face_up else FACE_DOWN_OFFSET

def draw_stock(surface, stock):
    # Stock pile (face-down stock)
    if stock.pile.cards:
        draw_card(surface,'', '', STOCK_X, STOCK_Y, face_up=False)
    
    # Waste pile (NOTE: show top card only for now)
    if stock.wastepile.cards:
        y = WASTE_Y
        if len(stock.wastepile.cards) > 3:
            card4 = stock.wastepile.cards[-4]
            draw_card(surface, get_rank_str(card4.rank), card4.suit.symbol, WASTE_X, y, suit_color=get_suit_color(card4.suit), face_up=True)
        if len(stock.wastepile.cards) >= 3:
            card3 = stock.wastepile.cards[-3]
            draw_card(surface, get_rank_str(card3.rank), card3.suit.symbol, WASTE_X, y, suit_color=get_suit_color(card3.suit), face_up=True)
            y += FACE_UP_OFFSET
        if len(stock.wastepile.cards) >= 2:
            card2 = stock.wastepile.cards[-2]
            draw_card(surface, get_rank_str(card2.rank), card2.suit.symbol, WASTE_X, y, suit_color=get_suit_color(card2.suit), face_up=True)
            y += FACE_UP_OFFSET
        if not (drag['active'] and drag['source_pile'] == 'waste'):
            top = stock.wastepile.top()
            draw_card(surface, get_rank_str(top.rank), top.suit.symbol, WASTE_X, y, suit_color=get_suit_color(top.suit), face_up=True)
    # else:
    #     draw_empty_slot(surface, WASTE_X, WASTE_Y)

def draw_foundation(surface, foundation):
    for i, suit in enumerate(F_SUIT_ORDER):
        y = FOUND_Y + i * V_GAP
        top = foundation.top(suit)
        if top:
            draw_card(surface, get_rank_str(top.rank), top.suit.symbol, FOUND_X, y, suit_color=get_suit_color(top.suit), face_up=True)
        # else:
        #     draw_empty_slot(surface, FOUND_X, y)

def draw_drag(surface, drag):
    if not drag['active']:
        return
    x, y = drag['x'], drag['y']
    for card in drag['cards']:
        draw_card(surface, get_rank_str(card.rank), card.suit.symbol, x, y, suit_color=get_suit_color(card.suit), face_up=True)
        y += FACE_UP_OFFSET

def draw_button(surface, rect, text, hovered=False):
    color = (80, 80, 80) if hovered else (60, 60, 60)
    pygame.draw.rect(surface, color, rect, border_radius=5)
    pygame.draw.rect(surface, WHITE, rect, width=1, border_radius=5)
    label = button_font.render(text, True, WHITE)
    lx = rect.x + (rect.width - label.get_width())   / 2
    ly = rect.y + (rect.height - label.get_height()) / 2
    surface.blit(label, (lx, ly))

def card_at_tableau_pos(pos, tableau):
    """Returns (pile_index, card_index, region) or (None, None, None)."""
    mx, my = pos
    for col_i, pile in enumerate(tableau.piles):
        x = TABLEAU_X + col_i * H_GAP
        y = TABLEAU_Y
        for card_i, card in enumerate(pile.cards):
            offset = FACE_UP_OFFSET if card.is_face_up else FACE_DOWN_OFFSET
            next_y = y + offset
            card_rect = pygame.Rect(x, y, CARD_W, offset if card_i < len (pile.cards) - 1 else CARD_H)
            if card_rect.collidepoint(mx, my) and card.is_face_up:
                return col_i, card_i, 'tableau'
            y = next_y
    return None, None, None

def card_at_waste_pos(pos, stock):
    """Returns (pile_index, card_index, region) or (None, None, None)."""
    mx, my = pos
    if stock.wastepile.cards:
        waste_top_rect = pygame.Rect(WASTE_X, get_waste_y(stock), CARD_W, CARD_H)
        if waste_top_rect.collidepoint(mx, my):
            return 'w', -1, 'waste'
    return None, None, None

while True:
    # --- EVENT HANDLER --- #
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            now = time.time()
            print("MOUSEBUTTONDOWN")
            
            # -- Button Clicks --
            if UNDO_RECT.collidepoint(event.pos):
                if len(game.history) > 1:
                    game._load_prev_save()
            elif NEWGAME_RECT.collidepoint(event.pos):
                game = Solitaire(shuffle_deck=True)
                START_TIME = time.time()
                drag['active'] = False
                drag['cards'] = []
            else:
                # -- Double Click --
                col_i, card_i, clicked_region = card_at_tableau_pos(event.pos, game.tableau)
                if clicked_region is None:
                    col_i, card_i, clicked_region = card_at_waste_pos(event.pos, game.stock)

                is_double_click = (
                    now - last_click['time'] < 0.3 and
                    last_click['col'] == col_i and
                    last_click['card'] == card_i and
                    last_click['region_clicked'] == clicked_region
                )

                if is_double_click and clicked_region == 'tableau':
                    success, points = game._move_tableau_to_foundation(col_i)
                    if success:
                        success_update(game, points)
                elif is_double_click and clicked_region == 'waste':
                    success = False
                    for target_i in range(7):
                        success, points = game._move_waste_to_tableau(target_i)
                        if success:
                            success_update(game, points)
                            break
                    if not success:
                        success, points = game._move_waste_to_foundation()
                        if success:
                            success_update(game, points)

                # -- Single Click --
                else:
                    last_click = {'time': now, 'pos': event.pos, 'region_clicked': clicked_region, 'col': col_i, 'card': card_i}

                    # Stock click Check (Clicking Stock to update Waste)
                    stock_rect = pygame.Rect(STOCK_X, STOCK_Y, CARD_W, CARD_H)
                    if stock_rect.collidepoint(event.pos):
                        game.stock.update_waste()
                        game._add_to_history()
                    
                    # Waste click Check (picking up card from Waste)
                    top_waste_y = get_waste_y(game.stock)
                    waste_rect = pygame.Rect(WASTE_X, top_waste_y, CARD_W, CARD_H)
                    if game.stock.wastepile.cards and waste_rect.collidepoint(event.pos):
                        drag['active'] = True
                        drag['cards'] = [game.stock.wastepile.top()]
                        drag['source_pile'] = 'waste'
                        drag['source_idx'] = None
                        drag['offset'] = (event.pos[0] - WASTE_X, event.pos[1] - top_waste_y)
                        drag['x'], drag['y'] = WASTE_X, top_waste_y

                    # Tableau click Check (picking up card(s) from Tableau)
                    if clicked_region == 'tableau':
                        pile = game.tableau.piles[col_i]
                        card_x = TABLEAU_X + col_i * H_GAP
                        card_y = TABLEAU_Y  # calculate actual y from card_i here
                        for i in range(card_i):
                            card_y += FACE_UP_OFFSET if pile.cards[i].is_face_up else FACE_DOWN_OFFSET
                        drag['active'] = True
                        drag['cards'] = pile.cards[card_i:]
                        drag['source_pile'] = col_i
                        drag['source_idx'] = card_i
                        drag['offset'] = (event.pos[0] - card_x, event.pos[1] - card_y)
                        drag['x'], drag['y'] = card_x, card_y

        if event.type == pygame.MOUSEMOTION and drag['active']:
            print("MOUSEMOTION")
            drag['x'] = event.pos[0] - drag['offset'][0]
            drag['y'] = event.pos[1] - drag['offset'][1]

        if event.type == pygame.MOUSEBUTTONUP and drag['active']:
            print("MOUSEBUTTONUP")
            dropped = False
            # drag_card_rect = pygame.Rect(drag['x'], drag['y'] + (len(drag['cards']) - 1) * FACE_UP_OFFSET, CARD_W, CARD_H)
            drag_card_rect = pygame.Rect(drag['x'], drag['y'], CARD_W, CARD_H)

            if drag['source_pile'] == 'waste':
                # -- Drop waste onto tableau --
                for target_i in range(7):
                    tx = TABLEAU_X + target_i * H_GAP
                    target_pile = game.tableau.piles[target_i]
                    ty = TABLEAU_Y
                    if target_pile.cards:
                        for card in target_pile.cards:
                            ty += FACE_UP_OFFSET if card.is_face_up else FACE_DOWN_OFFSET
                        ty -= FACE_UP_OFFSET
                    target_rect = pygame.Rect(tx, ty, CARD_W, CARD_H)
                    overlap_left  = max(drag_card_rect.left, target_rect.left)
                    overlap_right = min(drag_card_rect.right, target_rect.right)
                    h_overlap = overlap_right - overlap_left
                    if h_overlap > CARD_W / 2 and drag_card_rect.colliderect(target_rect):
                        success, points = game._move_waste_to_tableau(target_i)
                        if success:
                            success_update(game, points)
                        dropped = True
                        break
                
                # -- Drop waste onto foundation --
                if not dropped:
                    for f_i, suit in enumerate(F_SUIT_ORDER):
                        fy = FOUND_Y + f_i * V_GAP
                        target_rect = pygame.Rect(FOUND_X, fy, CARD_W, CARD_H)
                        overlap_left  = max(drag_card_rect.left, target_rect.left)
                        overlap_right = min(drag_card_rect.right, target_rect.right)
                        h_overlap = overlap_right - overlap_left
                        if h_overlap > CARD_W / 2 and drag_card_rect.colliderect(target_rect):
                            success, points = game._move_waste_to_foundation()
                            if success:
                                success_update(game, points)
                            dropped = True
                            break
                
            else:
                # -- Drop onto tableau pile --
                for target_i in range(7):
                    if target_i == drag['source_pile']:
                        continue
                    tx = TABLEAU_X + target_i * H_GAP
                    target_pile = game.tableau.piles[target_i]

                    # Target rect is the top card of the pile (or empty slot)
                    if target_pile.cards:
                        ty = TABLEAU_Y
                        for card in target_pile.cards:
                            ty += FACE_UP_OFFSET if card.is_face_up else FACE_DOWN_OFFSET
                        ty -= FACE_UP_OFFSET # back up to where the top card actually starts
                    else:
                        ty = TABLEAU_Y
                    
                    target_rect = pygame.Rect(tx, ty, CARD_W, CARD_H)

                    # Overlap check: horizontal overlap must exceed half of CARD_W
                    overlap_left  = max(drag_card_rect.left, target_rect.left)
                    overlap_right = min(drag_card_rect.right, target_rect.right)
                    h_overlap = overlap_right - overlap_left

                    if h_overlap > CARD_W / 2 and drag_card_rect.colliderect(target_rect):
                        success, points = game._move_tableau_to_tableau(drag['source_pile'], target_i)
                        if success:
                            success_update(game, points)
                        dropped = True
                        break

                # -- Drop onto foundation --
                if not dropped:
                    for f_i, suit in enumerate(F_SUIT_ORDER):
                        fy = FOUND_Y + f_i * V_GAP
                        target_rect = pygame.Rect(FOUND_X, fy, CARD_W, CARD_H)

                        # Overlap check: horizontal overlap must exceed hald of CARD_W
                        overlap_left  = max(drag_card_rect.left, target_rect.left)
                        overlap_right = min(drag_card_rect.right, target_rect.right)
                        h_overlap = overlap_right - overlap_left

                        if h_overlap > CARD_W / 2 and drag_card_rect.colliderect(target_rect):
                            success, points = False, 0
                            if len(drag['cards']) == 1: # Can not move more than one card at a time to the foundation
                                success, points = game._move_tableau_to_foundation(drag['source_pile'])
                            if success:
                                success_update(game, points)
                            dropped = True
                            break

            drag['active'] = False
            drag['cards'] = []

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                game._load_prev_save()

    # Draw background
    draw_board(screen, game.score, game.moves)

    draw_stock(screen, game.stock)
    draw_foundation(screen, game.foundation)
    draw_tableau(screen, game.tableau, drag)
    draw_drag(screen, drag)     # always drawn last or "on top"

    pygame.display.flip()   # flip() is preferred over update() for full-screen redraws
    clock.tick(60)
