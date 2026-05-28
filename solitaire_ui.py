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
UNDO_RECT    = pygame.Rect(TABLEAU_X + H_GAP - CARD_W / 2, FOOTER_Y + (FOOTER_H - BUTTON_H) / 2, BUTTON_W * 0.7, BUTTON_H)
NEWGAME_RECT = pygame.Rect(TABLEAU_X + 5 * H_GAP - CARD_W / 2, FOOTER_Y + (FOOTER_H - BUTTON_H) / 2, BUTTON_W, BUTTON_H)
NEWGAME_WIN_RECT = pygame.Rect(TABLEAU_X + 5 * H_GAP - CARD_W / 2, FOOTER_Y + (FOOTER_H - BUTTON_H) / 2, BUTTON_W, BUTTON_H)

SPEED = 2500 # pixels/second


# === Font and Colors === #
font = pygame.font.SysFont('Segoe UI', 20, bold=True)
win_font = pygame.font.SysFont('Segoe UI', 50, bold=True)
button_font = pygame.font.SysFont('Segoe UI Symbol', 18, bold=True)
BLUE        = (  0,   0, 200)
GREEN       = ( 67, 161,  75)
DARK_GREEN  = ( 53, 122,  60)
WHITE       = (255, 255, 255)
BLACK       = (  0,   0,   0)
LIGHT_GRAY  = (220, 220, 220)
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
    'source_suit': None,# suit of top card
    'offset': (0, 0),   # cursor offset from card top-left
    'x': 0, 'y': 0      # current draw position
}
START_TIME = time.time()
F_SUIT_ORDER = [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]
button_pressed = {'active': False, 'undo': False, 'new_game': False, 'win_new_game': False}
last_click = {'time': 0, 'pos': None, 'region_clicked': None, 'col': None, 'card': None}
can_undo = False
force_win = False
game_is_won = False
time_played = 0

# ========== ANIMATION SYSTEM ========== #
animations = []     # list of active animation dicts

def ease(t):
    """
    Cubic ease-in-out, t is 0.0 to 1.0.
    Returns eased value 0.0 to 1.0.
    Short ease-in, fast middle, short ease-out.
    """
    return t * t * (3 - 2 * t)

def update_animations():
    """
    Advance all active animations by one frame.
    Returns True if any animations are still running.
    """
    now = time.time()
    still_running = []
    for anim in animations:
        t = (now - anim['start_time']) / anim['duration']
        t = min(t, 1.0)
        anim['t'] = ease(t)
        if t < 1.0:
            still_running.append(anim)
        else:
            # Animation is finished, run it's completion callback if it has one
            if anim.get('on_complete'):
                anim['on_complete']()
    animations.clear()
    animations.extend(still_running)
    return len(animations) > 0

def get_distance(start_xy, end_xy):
    sx, sy = start_xy
    ex, ey = end_xy

    return ( (ex - sx)**2 + (ey - sy)**2 )**0.5

def start_animation(card, start_xy, end_xy, duration=None, max_duration=None, min_duration=None, on_complete=None, accept_zero_distance=False):
    distance = get_distance(start_xy, end_xy)

    if round(distance, 3) == 0 and not accept_zero_distance:
        # no animation needed. Implemented to avoid "fake animations" from blocking input during a double click
        return

    max_duration = 0.4 if max_duration is None else max_duration
    min_duration = 0.3 if min_duration is None else min_duration

    if duration is None:
        duration = min(max_duration, max(min_duration, distance / SPEED)) # cap between 200ms and 300ms

    animations.append({
        'card': card,
        'start_xy': start_xy,
        'end_xy': end_xy,
        'start_time': time.time(),
        'duration': duration,
        't': 0.0,
        'on_complete': on_complete
    })

def get_anim_pos(anim):
    """Interpolate current x,y position for an animation."""
    sx, sy = anim['start_xy']
    ex, ey = anim['end_xy']
    t = anim['t']
    return sx + (ex - sx) * t, sy + (ey - sy) * t

def draw_animations(surface):
    for anim in animations:
        x, y = get_anim_pos(anim)
        if 'card' in anim:
            card = anim['card']
            draw_card(surface, get_rank_str(card.rank), card.suit.symbol, x, y, suit_color=get_suit_color(card.suit), face_up=card.is_face_up)
        if 'win_screen' in anim:
            progress = 128 * (time.time() - anim['start_time']) / anim['duration']
            if anim['retreat']:
                trans = 128 - progress
            else:
                trans = progress
            draw_win_screen(surface, x, y, anim['time_played'], anim['score'], anim['moves'], transparency=trans)

def start_win_screen_animation(time_played, score, moves, duration=0.5, retreat=False, on_complete=None):
    if retreat:
        start_xy = (SCREEN_W / 2, SCREEN_H / 2)
        end_xy   = (SCREEN_W / 2, - SCREEN_H)
    else:
        start_xy = (SCREEN_W / 2, - SCREEN_H)
        end_xy   = (SCREEN_W / 2, SCREEN_H / 2)
    
    animations.append({
        'win_screen': True,
        'retreat': retreat,
        'start_xy': start_xy,
        'end_xy': end_xy,
        'start_time': time.time(),
        'duration': duration,
        't': 0.0,
        'time_played': time_played,
        'score': score,
        'moves': moves,
        'on_complete': on_complete
    })

def start_waste_slide_animation(stock, duration=0.3):
    """
    Animate the visible waste cards sliding into their new positions
    after the top waste card has already been removed from the pile.
    """
    cards = stock.wastepile.cards
    if not len(cards) >= 3:
        return  # nothing to slide

    # After the top card is gone, up to 3 cards are visible.
    # Calculate where they were and where they need to go.
    # Before removal there were N+1 cards; the visible ones started at these y positions:
    n = len(cards)  # count AFTER removal

    # Where each card was before (when there was one more card on top)
    def old_y(slot):
        # slot 0 = bottom of visible stack, slot 2 = was the top
        old_count = n + 1
        visible_before = min(2, old_count)
        bottom_slot = visible_before - 1
        return WASTE_Y + (bottom_slot - slot) * FACE_UP_OFFSET

    # Where each card needs to end up now
    def new_y(slot):
        visible_after = min(3, n)
        bottom_slot = visible_after - 1
        return WASTE_Y + (bottom_slot - slot) * FACE_UP_OFFSET

    # Animate up to 3 cards (the newly visible stack)
    visible = min(2, n)
    for i in range(visible):
        card = cards[n - visible + i]   # bottom to top of visible stack
        slot = visible - 1 - i          # 0 = bottom slot
        sy = old_y(slot)
        ey = new_y(slot)
        if sy != ey:
            start_animation(card, (WASTE_X, sy), (WASTE_X, ey), duration=duration) 

def start_stock_to_waste_slide_animation(stock, moved_count, duration=0.3):
    waste_cards = stock.wastepile.cards

    # Moving stock to waste
    if moved_count > 0:
        animation_list = []
        original_waste = waste_cards[:len(waste_cards) - moved_count]
        original_visible_waste = original_waste[-3:]
        new_visible_waste = waste_cards[-3:]
        print(original_visible_waste)
        print(new_visible_waste)
        for i, card in enumerate(original_visible_waste):
            # Moving cards that were already in the waste and will no longer be visible
            if card not in new_visible_waste:
                animation_list.append({
                    'card': card,
                    'sx': WASTE_X,
                    'sy': WASTE_Y + i * FACE_UP_OFFSET,
                    'ex': WASTE_X,
                    'ey': WASTE_Y
                    })
            # Moving cards that were in waste and will remain visible
            else: 
                animation_list.append({
                    'card': card,
                    'sx': WASTE_X,
                    'sy': WASTE_Y + i * FACE_UP_OFFSET,
                    'ex': WASTE_X,
                    'ey': WASTE_Y + (i - moved_count) * FACE_UP_OFFSET
                    })
        for i, card in enumerate(new_visible_waste):
            # Moving cards that were in stock to the waste
            if card not in original_visible_waste:
                animation_list.append({
                    'card': card,
                    'sx': STOCK_X,
                    'sy': STOCK_Y,
                    'ex': WASTE_X,
                    'ey': WASTE_Y + i * FACE_UP_OFFSET
                    })
        for anim in animation_list:
            start_animation(anim['card'], (anim['sx'], anim['sy']), (anim['ex'], anim['ey']), duration=duration, accept_zero_distance=True)

    # Moving waste to stock
    else:
        quick_dict = {0: 2, 1: 1, 2: 0}
        visible_waste_before = min(3, len(stock.pile.cards))
        if visible_waste_before:
            for i in range(visible_waste_before - 1, -1, -1):
                card = stock.pile.cards[i]
                sy = WASTE_Y + (quick_dict[i]) * FACE_UP_OFFSET
                ey = STOCK_Y
                start_animation(card, (WASTE_X, sy), (STOCK_X, ey), duration=duration, accept_zero_distance=True)

def start_drop_snap_tableau_animation(cards, target_i, duration=None, max_duration=None, min_duration=None):
    """
    Animate dropped card(s) snapping from their current drag position
    to their correct position in the target tableau pile.
    """
    ty = TABLEAU_Y
    target_pile = game.tableau.piles[target_i]
    for card in target_pile.cards[:len(target_pile.cards) - len(cards)]:
        ty += FACE_UP_OFFSET if card.is_face_up else FACE_DOWN_OFFSET
    
    for i, card in enumerate(cards):
        start_xy = (drag['x'], drag['y'] + i * FACE_UP_OFFSET)
        end_xy   = (TABLEAU_X + target_i * H_GAP, ty)
        start_animation(card, start_xy, end_xy, duration=duration, max_duration=max_duration, min_duration=min_duration)
        ty += FACE_UP_OFFSET

def start_drop_snap_foundation_animation(card: Card, duration=None):
    """
    Animate dropped card snapping from their current drag position
    to their correct position in the target foundation pile.
    """
    start_xy = (drag['x'], drag['y'])
    f_i = F_SUIT_ORDER.index(card.suit)
    end_xy   = (FOUND_X, FOUND_Y + f_i * V_GAP)
    start_animation(card, start_xy, end_xy, duration=duration)

def start_deal_animation(duration=0.4):
    start_xy = (STOCK_X, STOCK_Y)
    for row in range(7):
        y = TABLEAU_Y + row * FACE_DOWN_OFFSET
        for col in range(7):
            x = TABLEAU_X + col * H_GAP
            pile = game.tableau.piles[col]
            if row < len(pile.cards):
                card = pile.cards[row]
                card1 = card.copy()
                card1.is_face_up = False
                start_animation(card, start_xy, (x, y), duration=duration)

def start_redeal_animation(duration=0.4):
    animation_list = []

    # Waste
    visible_waste = game.stock.wastepile.cards[-3:]
    for i, card in enumerate(visible_waste):
        x = WASTE_X
        y = WASTE_Y + i * FACE_UP_OFFSET
        animation_list.append({'card': card, 'start_xy': (x, y), 'end_xy': (STOCK_X, STOCK_Y)})

    # Tableau
    for row in range(7):
        for col in range(7):
            if row >= len(game.tableau.piles[col].cards):
                continue
            card = game.tableau.piles[col].cards[row]
            x = TABLEAU_X + col * H_GAP
            y = TABLEAU_Y
            for row_i in range(row):
                y += FACE_UP_OFFSET if game.tableau.piles[col].cards[row_i].is_face_up else FACE_DOWN_OFFSET
            animation_list.append({'card': card, 'start_xy': (x, y), 'end_xy': (STOCK_X, STOCK_Y)})

    for i, suit in enumerate(F_SUIT_ORDER):
        if game.foundation.piles[suit].top() is not None:
            card = game.foundation.piles[suit].top()
            x = FOUND_X
            y = FOUND_Y + i * V_GAP
            animation_list.append({'card': card, 'start_xy': (x, y), 'end_xy': (STOCK_X, STOCK_Y)})

    for a in animation_list:
        start_animation(a['card'], a['start_xy'], a['end_xy'], duration=duration, on_complete=start_deal_animation)

# TODO:
# UNDO ANIMATIONS, NEW GAME END ANIMATION (all cards to stock), NEW GAME START ANIMATION (all cards from stock to their positions)

# ========== HELPER FUNCTIONS ========== #
def success_update(game: Solitaire, points):
    game.score += points
    game.moves += 1

def get_time_played():
    return time.time() - START_TIME if not game_is_won else time_played

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

def get_tableau_pile_top_y(tableau, col_i):
    y = TABLEAU_Y
    if tableau.piles[col_i].cards:
        for card in tableau.piles[col_i].cards:
            y += FACE_UP_OFFSET if card.is_face_up else FACE_DOWN_OFFSET
        y -= FACE_UP_OFFSET
    return y

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

# ========== DRAW FUNCTIONS ========== #
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

def draw_board(surface, score, moves, button_pressed, can_undo=True):
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
    time_str = get_time_str(time_played)
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
    # TODO: Add mute button (maybe? if/when sound effects are added)

    # -- Footer --
    mouse_pos = pygame.mouse.get_pos()
    undo_hover = UNDO_RECT.collidepoint(mouse_pos)
    newgame_hover = NEWGAME_RECT.collidepoint(mouse_pos)
    undo_base_colors, undo_press_colors = ([WHITE, WHITE], [LIGHT_GRAY, LIGHT_GRAY]) if can_undo else ([WHITE, LIGHT_GRAY], [WHITE, LIGHT_GRAY])
    draw_button2(surface, UNDO_RECT,    ["↩ ", "Undo"], undo_base_colors, undo_press_colors, button_pressed['undo'],     hovered=undo_hover)
    draw_button2(surface, NEWGAME_RECT, ["★ New Game"], [WHITE],          [LIGHT_GRAY],      button_pressed['new_game'], hovered=newgame_hover)
    if not game_is_won:
        if (undo_hover and can_undo) or newgame_hover:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

def draw_empty_slot(surface, x, y):
    """Dotted outline showing an empty pile slot."""
    rect = pygame.Rect(x, y, CARD_W, CARD_H)
    pygame.draw.rect(surface, (0, 80, 0), rect, border_radius=6)            # (0, 80, 0) Light-Dark Green
    pygame.draw.rect(surface, (0, 60, 0), rect, width=2, border_radius=6)   # (0, 60, 0) Dark Green

def draw_tableau(surface, tableau, drag):
    animating_cards = {id(a['card']) for a in animations if 'card' in a}
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
            if id(card) in animating_cards:
                break
            draw_card(surface, get_rank_str(card.rank), card.suit.symbol, x, y, suit_color=get_suit_color(card.suit), face_up=card.is_face_up)
            y += FACE_UP_OFFSET if card.is_face_up else FACE_DOWN_OFFSET

def draw_stock(surface, stock):
    animating_cards = {id(a['card']) for a in animations if 'card' in a}

    draw_stock_pile = True if stock.pile.cards else False
    if draw_stock_pile:
        for a in animations:
            if a['end_xy'] == (STOCK_X, STOCK_Y):
                draw_stock_pile = False
    if draw_stock_pile:
        draw_card(surface, '', '', STOCK_X, STOCK_Y, face_up=False)

    if stock.wastepile.cards:
        y = WASTE_Y
        cards = stock.wastepile.cards
        n = len(cards)

        if n > 3:
            card4 = cards[-4]
            if id(card4) not in animating_cards:
                draw_card(surface, get_rank_str(card4.rank), card4.suit.symbol,
                          WASTE_X, y, suit_color=get_suit_color(card4.suit), face_up=True)
        if n >= 3:
            card3 = cards[-3]
            if id(card3) not in animating_cards:
                draw_card(surface, get_rank_str(card3.rank), card3.suit.symbol,
                          WASTE_X, y, suit_color=get_suit_color(card3.suit), face_up=True)
            y += FACE_UP_OFFSET
        if n >= 2:
            card2 = cards[-2]
            if id(card2) not in animating_cards:
                draw_card(surface, get_rank_str(card2.rank), card2.suit.symbol,
                          WASTE_X, y, suit_color=get_suit_color(card2.suit), face_up=True)
            y += FACE_UP_OFFSET
        if not (drag['active'] and drag['source_pile'] == 'waste'):
            top = stock.wastepile.top()
            if id(top) not in animating_cards:
                draw_card(surface, get_rank_str(top.rank), top.suit.symbol,
                          WASTE_X, y, suit_color=get_suit_color(top.suit), face_up=True)

def draw_foundation(surface, foundation):
    animating_cards = {id(a['card']) for a in animations if 'card' in a}
    for i, suit in enumerate(F_SUIT_ORDER):
        y = FOUND_Y + i * V_GAP
        top = foundation.top(suit)
        if top:
            # Being dragged or animated
            if (drag['active'] and drag['source_pile'] == 'foundation' and drag['source_suit'] == suit) or id(top) in animating_cards:
                # Draw card under top if the top card is being dragged or animated
                if len(foundation.piles[suit].cards) > 1:
                    card = foundation.piles[suit].cards[-2]
                    draw_card(surface, get_rank_str(card.rank), card.suit.symbol, FOUND_X, y, suit_color=get_suit_color(card.suit), face_up=True)
                # Do not draw a card if there isn't a card under the top to be drawn
                else:
                    pass
            else:
                draw_card(surface, get_rank_str(top.rank), top.suit.symbol, FOUND_X, y, suit_color=get_suit_color(top.suit), face_up=True)

def draw_drag(surface, drag):
    if not drag['active']:
        return
    x, y = drag['x'], drag['y']
    for card in drag['cards']:
        draw_card(surface, get_rank_str(card.rank), card.suit.symbol, x, y, suit_color=get_suit_color(card.suit), face_up=True)
        y += FACE_UP_OFFSET

def draw_button(surface, rect, text, hovered=False):
    color = (80, 80, 80) if hovered else (60, 60, 60)
    if hovered:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
    else:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    pygame.draw.rect(surface, color, rect, border_radius=5)
    pygame.draw.rect(surface, WHITE, rect, width=1, border_radius=5)
    label = button_font.render(text, True, WHITE)
    lx = rect.x + (rect.width - label.get_width())   / 2
    ly = rect.y + (rect.height - label.get_height()) / 2
    surface.blit(label, (lx, ly))

def draw_button2(surface, rect, texts, base_colors=(WHITE), pressed_colors=(LIGHT_GRAY), button_pressed=False, hovered=False):
    pygame.draw.rect(surface, GREEN, rect)
    full_str = ''.join(texts)
    label = button_font.render(full_str, True, WHITE)
    lx = rect.x + (rect.width - label.get_width()) / 2
    ly = rect.y + (rect.height - label.get_height()) / 2
    for i, text in enumerate(texts):
        label = button_font.render(text, True, pressed_colors[i]) if button_pressed else button_font.render(text, True, base_colors[i])
        surface.blit(label, (lx, ly))
        lx += label.get_width()

def draw_win_screen(surface, x, y, time_played, score, moves, transparency=128):
    shadow_screen = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    shadow_screen.fill((0, 0, 0, transparency))

    width = SCREEN_W / 2
    height = SCREEN_H / 2

    rect0 = pygame.Rect(0, 0, width + 5, height + 5)
    rect0.center = (x, y)
    rect1 = pygame.Rect(0, 0, width, height)
    rect1.center = (x, y)
    rect2 = pygame.Rect(0, 0, width - 20, height - 20)
    rect2.center = (x, y)
    rect3 = pygame.Rect(0, 0, width - 40, height - 40)
    rect3.center = (x, y)

    surface.blit(shadow_screen, (0, 0))
    pygame.draw.rect(surface=surface, color=BLACK, rect=rect0, border_radius=30)
    pygame.draw.rect(surface=surface, color=RED  , rect=rect1, border_radius=28)
    pygame.draw.rect(surface=surface, color=BLUE , rect=rect2, border_radius=24)
    pygame.draw.rect(surface=surface, color=GREEN, rect=rect3, border_radius=20)
    
    label = win_font.render("YOU WIN!", True, WHITE)
    label_rect = label.get_rect(center=(x, y - 75))
    surface.blit(label, label_rect)

    x_offset = 150
    label = font.render("Time", True, WHITE)
    label_rect = label.get_rect(center=(x - x_offset, y))
    surface.blit(label, label_rect)
    label = font.render("Score", True, WHITE)
    label_rect = label.get_rect(center=(x, y))
    surface.blit(label, label_rect)
    label = font.render("Moves", True, WHITE)
    label_rect = label.get_rect(center=(x + x_offset, y))
    surface.blit(label, label_rect)

    y_offset = label_rect.height
    label = button_font.render(get_time_str(time_played), True, LIGHT_GRAY)
    label_rect = label.get_rect(center=(x - x_offset, y + y_offset))
    surface.blit(label, label_rect)
    label = button_font.render(str(score), True, LIGHT_GRAY)
    label_rect = label.get_rect(center=(x, y + y_offset))
    surface.blit(label, label_rect)
    label = button_font.render(str(moves), True, LIGHT_GRAY)
    label_rect = label.get_rect(center=(x + x_offset, y + y_offset))
    surface.blit(label, label_rect)

    new_game_button = NEWGAME_WIN_RECT
    new_game_button.center = (x, y + 90)
    mouse_pos = pygame.mouse.get_pos()
    newgame_hover = new_game_button.collidepoint(mouse_pos)
    draw_button2(surface, new_game_button, ["★ New Game"], [WHITE],          [LIGHT_GRAY],      button_pressed['win_new_game'], hovered=newgame_hover)
    if newgame_hover:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
    else:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

# ========== GAME FUNCTIONS ========== #
# -- MOUSE BUTTON DOWN -- #
def register_click_timing(pos):
    """
    Checks whether the current click is a double click
    based on the previous click state
    """
    global last_click
    global game

    now = time.time()
    clicked_region = None
    col_i, card_i, clicked_region = card_at_tableau_pos(pos, game.tableau)

    if clicked_region is None:
        col_i, card_i, clicked_region = card_at_waste_pos(pos, game.stock)

    is_double_click = (
        now - last_click['time'] < 0.3 and
        last_click['col'] == col_i and
        last_click['card'] == card_i and
        last_click['region_clicked'] == clicked_region
    )

    # Debug prints
    # print(f"time delta: {now - last_click['time']:.3f}s")
    # print(
    #     now - last_click['time'] < 0.3,
    #     last_click['col'] == col_i,
    #     last_click['card'] == card_i,
    #     last_click['region_clicked'] == clicked_region
    # )
    # print(f"col_i={col_i} card_i={card_i} clicked_region={clicked_region}")

    # Update last_click AFTER detection
    last_click = {
        'time': now,
        'pos': pos,
        'region_clicked': clicked_region,
        'col': col_i,
        'card': card_i
    }

    return col_i, card_i, clicked_region, is_double_click

def check_undo_click(pos):
    if UNDO_RECT.collidepoint(pos):
        button_pressed['active'] = True
        button_pressed['undo']   = True
        return True
    return False

def execute_undo():
    game._load_prev_move()

def check_newgame_click(pos):
    if NEWGAME_RECT.collidepoint(pos) and not game_is_won:
        button_pressed['active']   = True
        button_pressed['new_game'] = True
        return True
    if NEWGAME_WIN_RECT.collidepoint(pos) and game_is_won:
        button_pressed['active']       = True
        button_pressed['win_new_game'] = True
        return True
    return False

def execute_newgame():
    global game
    global START_TIME
    global drag
    global button_pressed
    global last_click
    global can_undo
    global force_win
    global game_is_won
    global time_played

    if game_is_won:
        start_win_screen_animation(time_played, game.score, game.moves, retreat=True)

    game = Solitaire(shuffle_deck=True)
    START_TIME = time.time()
    drag['active'] = False
    drag['cards']  = []
    last_click = {'time': 0, 'pos': None, 'region_clicked': None, 'col': None, 'card': None}
    can_undo = False
    force_win = False
    game_is_won = False
    time_played = 0
    start_deal_animation()
    # TODO: Trigger NEW GAME END ANIMATION (all cards to stock) which then triggers start animation on_complete

def check_double_click_tableau(col_i, card_i, is_double_click, clicked_region):
    global game

    if is_double_click and clicked_region == 'tableau':
        card = game.tableau.piles[col_i].top()
        if not game.tableau.piles[col_i].cards[card_i] == card:
            return False
        
        start_xy = (TABLEAU_X + col_i * H_GAP, get_tableau_pile_top_y(game.tableau, col_i))
        f_i = F_SUIT_ORDER.index(card.suit)
        end_xy = (FOUND_X, FOUND_Y + f_i * V_GAP)

        success, points = game._move_tableau_to_foundation(col_i)
        if success:
            success_update(game, points)
            start_animation(card, start_xy, end_xy)

        return True
    return False

def check_double_click_waste(col_i, card_i, is_double_click, clicked_region):
    global game

    if is_double_click and clicked_region == 'waste':
        card = game.stock.wastepile.top()
        start_xy = (WASTE_X, get_waste_y(game.stock))
        success = False

        # Try tableau first and find which column it should land on
        for target_i in range(7):
            can_place = card.can_stack_on(game.tableau.piles[target_i].top())
            if can_place:
                # calculate destination y
                ty = TABLEAU_Y
                for c in game.tableau.piles[target_i].cards:
                    ty += FACE_UP_OFFSET if c.is_face_up else FACE_DOWN_OFFSET
                end_xy = (TABLEAU_X + target_i * H_GAP, ty)
                success, points = game._move_waste_to_tableau(target_i)
                if success:
                    success_update(game, points)
                    start_waste_slide_animation(game.stock)
                    start_animation(card, start_xy, end_xy)
                    break
        
        # Try foundation if tableau didn't work
        if not success:
            f_i = F_SUIT_ORDER.index(card.suit)
            end_xy = (FOUND_X, FOUND_Y + f_i * V_GAP)

            success, points = game._move_waste_to_foundation()
            if success:
                success_update(game, points)
                start_waste_slide_animation(game.stock)
                start_animation(card, start_xy, end_xy)

        return True
    return False

def check_stock_click(pos):
    global game

    stock_rect = pygame.Rect(STOCK_X, STOCK_Y, CARD_W, CARD_H)
    if stock_rect.collidepoint(pos):
        stock_before = len(game.stock.pile.cards)
        record = game.stock.update_waste()
        if record is not None:
            game.moves += 1
            game.move_history.append(record)
            moved_count = stock_before - len(game.stock.pile.cards)
            if moved_count:
                start_stock_to_waste_slide_animation(game.stock, moved_count)
        return True
    return False

def check_waste_click(pos):
    global game
    global drag

    top_waste_y = get_waste_y(game.stock)
    waste_rect = pygame.Rect(WASTE_X, top_waste_y, CARD_W, CARD_H)
    if game.stock.wastepile.cards and waste_rect.collidepoint(pos):
        drag['active'] = True
        drag['cards'] = [game.stock.wastepile.top()]
        drag['source_pile'] = 'waste'
        drag['source_idx'] = None
        drag['offset'] = (pos[0] - WASTE_X, pos[1] - top_waste_y)
        drag['x'], drag['y'] = WASTE_X, top_waste_y
        return True
    return False

def check_tableau_click(col_i, card_i, clicked_region, pos):
    global game
    global drag

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
        drag['offset'] = (pos[0] - card_x, pos[1] - card_y)
        drag['x'], drag['y'] = card_x, card_y
        return True
    return False

def check_foundation_click(pos):
    global game
    global drag
    success = False

    for f_i, suit in enumerate(F_SUIT_ORDER):
        fy = FOUND_Y + f_i * V_GAP
        found_rect = pygame.Rect(FOUND_X, fy, CARD_W, CARD_H)
        if found_rect.collidepoint(pos):
            success = True
            top = game.foundation.top(suit)
            if top:
                drag['active'] = True
                drag['cards'] = [top]
                drag['source_pile'] = 'foundation'
                drag['source_suit'] = suit
                drag['offset'] = (pos[0] - FOUND_X, pos[1] - fy)
                drag['x'], drag['y'] = FOUND_X, fy
            break
    return success

# -- MOUSE BUTTON UP DROP -- #
def check_drop_to_tableau(drag_card_rect: pygame.Rect):
    global game
    global drag

    for target_i in range(7):
        if target_i == drag['source_pile']:
            continue
        tx = TABLEAU_X + target_i * H_GAP
        ty = get_tableau_pile_top_y(game.tableau, target_i)
        target_rect = pygame.Rect(tx, ty, CARD_W, CARD_H)
        overlap_left  = max(drag_card_rect.left, target_rect.left)
        overlap_right = min(drag_card_rect.right, target_rect.right)
        h_overlap = overlap_right - overlap_left
        if h_overlap > CARD_W / 2 and drag_card_rect.colliderect(target_rect):
            return True, target_i
    return False, None

def check_drop_to_foundation(drag_card_rect: pygame.Rect):
    global game

    for f_i, suit in enumerate(F_SUIT_ORDER):
        fy = FOUND_Y + f_i * V_GAP
        target_rect = pygame.Rect(FOUND_X, fy, CARD_W, CARD_H)
        overlap_left  = max(drag_card_rect.left, target_rect.left)
        overlap_right = min(drag_card_rect.right, target_rect.right)
        h_overlap = overlap_right - overlap_left
        if h_overlap > CARD_W / 2 and drag_card_rect.colliderect(target_rect):
            return True
    return False

start_deal_animation()
while True:
    time_played = get_time_played()
    was_won = game_is_won
    game_is_won = game._is_win(force_win=force_win)
    if game_is_won and not was_won:
        start_win_screen_animation(time_played, game.score, game.moves)
    animating = update_animations()

    # --- EVENT HANDLER --- #
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if animating:
            continue
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            col_i, card_i, clicked_region, is_double_click = register_click_timing(event.pos)

            if game_is_won:
                check_newgame_click(event.pos)
                continue
            
            # -- Button Clicks --
            if check_undo_click(event.pos): ...
            elif check_newgame_click(event.pos): ...

            # -- Double Clicks --
            elif check_double_click_tableau(col_i, card_i, is_double_click, clicked_region): ...
            elif check_double_click_waste(col_i, card_i, is_double_click, clicked_region): ...

            # -- Single Clicks --
            else:
                # Stock click Check (Clicking Stock to update Waste)
                if check_stock_click(event.pos): ...                    
                # Waste click Check (picking up card from Waste)
                elif check_waste_click(event.pos): ...
                # Tableau click Check (picking up card(s) from Tableau)
                elif check_tableau_click(col_i, card_i, clicked_region, event.pos): ...                    
                # Foundation click check (picking up card from Foundation)
                elif check_foundation_click(event.pos): ...

        if event.type == pygame.MOUSEMOTION and drag['active']:
            drag['x'] = event.pos[0] - drag['offset'][0]
            drag['y'] = event.pos[1] - drag['offset'][1]

        if event.type == pygame.MOUSEBUTTONUP and drag['active']:
            dropped = False
            successful_drop = False
            drag_card_rect = pygame.Rect(drag['x'], drag['y'], CARD_W, CARD_H)

            # --- Check if dropped to tableau --
            dropped, target_i = check_drop_to_tableau(drag_card_rect)
            if dropped:
                # -- Waste to tableau --
                if drag['source_pile'] == 'waste':
                    success, points = game._move_waste_to_tableau(target_i)
                    if success:
                        successful_drop = True
                        success_update(game, points)
                        start_drop_snap_tableau_animation([game.tableau.piles[target_i].top()], target_i)
                        start_waste_slide_animation(game.stock)
                # -- Foundation to tableau --
                elif drag['source_pile'] == 'foundation':
                    success, points = game._move_foundation_to_tableau(target_i, drag['source_suit'])
                    if success:
                        successful_drop = True
                        success_update(game, points)
                # -- Tableau to tableau --
                else:
                    success, points = game._move_tableau_to_tableau(drag['source_pile'], target_i, force_idx=drag['source_idx'])
                    if success:
                        successful_drop = True
                        cards = game.tableau.piles[target_i].cards[-len(drag['cards']):]
                        success_update(game, points)
                        print("start_drop_snap_tableau_animation, Tableau to tableau", cards)
                        start_drop_snap_tableau_animation(cards, target_i)

            # --- Check if dropped to foundation ---
            dropped = check_drop_to_foundation(drag_card_rect)
            if dropped:
                # -- Waste to foundation --
                if drag['source_pile'] == 'waste':
                    success, points = game._move_waste_to_foundation()
                    if success:
                        successful_drop = True
                        success_update(game, points)
                        start_drop_snap_foundation_animation(drag['cards'][0])
                        start_waste_slide_animation(game.stock)
                # -- Tableau to foundation --
                else:
                    success, points = False, 0
                    if len(drag['cards']) == 1: # Can not move more than one card at a time to the foundation
                        success, points = game._move_tableau_to_foundation(drag['source_pile'])
                    if success:
                        successful_drop = True
                        success_update(game, points)
                        start_drop_snap_foundation_animation(drag['cards'][0])
            
            # --- Animate card(s) moving back to original position if not successfully dropped ---
            if not successful_drop:
                pos = (drag['x'], drag['y'])
                if drag['source_pile'] == 'waste':
                    start_animation(drag['cards'][0], pos, (WASTE_X, get_waste_y(game.stock)), min_duration=0.1)
                elif drag['source_pile'] == 'foundation':
                    fy = FOUND_Y + F_SUIT_ORDER.index(drag['cards'][0].suit)
                    start_animation(drag['cards'][0], pos, (FOUND_X, fy), min_duration=0.1)
                else:
                    start_drop_snap_tableau_animation(drag['cards'], drag['source_pile'], min_duration=0.1)

            drag['active'] = False
            drag['cards'] = []
        
        if event.type == pygame.MOUSEBUTTONUP:
            if button_pressed['active']:
                if button_pressed['new_game'] or button_pressed['win_new_game']:
                    execute_newgame()
                elif button_pressed['undo']:
                    execute_undo()
                button_pressed = {'active': False, 'undo': False, 'new_game': False, 'win_new_game': False}

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                game._load_prev_move()
            elif event.key == pygame.K_w:
                force_win = True

    can_undo = True if game.move_history else False

    # Draw background
    draw_board(screen, game.score, game.moves, button_pressed, can_undo)
    draw_stock(screen, game.stock)
    draw_foundation(screen, game.foundation)
    draw_tableau(screen, game.tableau, drag)
    draw_drag(screen, drag)
    if game_is_won and not any('win_screen' in a for a in animations):
        draw_win_screen(screen, SCREEN_W / 2, SCREEN_H / 2, time_played, game.score, game.moves)
    draw_animations(screen)     # always on top after everything else

    pygame.display.flip()   # flip() is preferred over update() for full-screen redraws
    clock.tick(60)
