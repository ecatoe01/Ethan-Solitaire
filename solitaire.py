from enum import Enum
import random
import re
import sys

RESET = "\033[0m"
ANSI_ESCAPE = re.compile(r'\033\[[0-9;]*m')

def visible_len(s: str) -> int:
    '''
    Returns the length of a string with ANSI-formatted coloring, not counting the formatting characters
    '''
    return len(ANSI_ESCAPE.sub('', s))

def slice_visible(s: str, max_visible: int) -> str:
    """
    Slice a string to a maximum visible length, preserveing ANSI codes.
    """
    result = []
    visible_count = 0
    i = 0

    while i < len(s) and visible_count < max_visible:
        if s[i] == '\033':  # start of ANSI code
            match = ANSI_ESCAPE.match(s, i)
            if match:
                result.append(match.group())
                i = match.end()
                continue
        
        result.append(s[i])
        visible_count += 1
        i += 1
    
    return ''.join(result)

def repeat_fill(fillchar: str, target_visible_len: int) -> str:
    """
    Repeat fillchar until reaching target visible length,
    then truncate cleanly if needed.
    """
    fill_visible = visible_len(fillchar)
    if fill_visible == 0:
        raise ValueError("fillchar must have visible length > 0")
    
    result = ''
    current_len = 0

    while current_len + fill_visible <= target_visible_len:
        result += fillchar
        current_len += fill_visible

    remaining = target_visible_len - current_len
    if remaining > 0:
        result += slice_visible(fillchar, remaining)

    return result

def center_ansi(s: str, width: int, fillchar: str = ' ') -> str:
    vis_len = visible_len(s)

    if vis_len >= width:
        return s
    
    total_padding = width - vis_len
    left_padding = total_padding // 2
    right_padding = total_padding - left_padding

    left = repeat_fill(fillchar, left_padding)
    right = repeat_fill(fillchar, right_padding)

    return left + s + right + RESET

def ljust_ansi(s: str, width: int, fillchar: str = ' ') -> str:
    vis_len = visible_len(s)

    if vis_len >= width:
        return s + RESET

    padding = width - vis_len
    right = repeat_fill(fillchar, padding)

    return s + right + RESET

def rjust_ansi(s: str, width: int, fillchar: str = ' ') -> str:
    vis_len = visible_len(s)

    if vis_len >= width:
        return s + RESET

    padding = width - vis_len
    left = repeat_fill(fillchar, padding)

    return left + s + RESET

class Suit(Enum):
    """
    A class to represent playing card suits.
    Utilizes ANSI-formatting for displaying the color of the suit (Red or Blue).

    Examples of behavior when printed:
        Suit.SPADES -> '\033[34m♠\033[0m'
        Suit.SPADES.name -> 'SPADES'
        Suit.SPADES.value -> ('♠', '\033[34m♠\033[0m')
        Suit.SPADES.symbol -> '♠'
        Suit.SPADES.ansi_symbol -> '\033[34m♠\033[0m'
    """
    SPADES = ('♠', '\033[34m♠\033[0m')
    HEARTS = ('♥', '\033[31m♥\033[0m')
    DIAMONDS = ('♦', '\033[31m♦\033[0m')
    CLUBS = ('♣', '\033[34m♣\033[0m')

    def __init__(self, symbol: str, ansi_symbol: str):
        self.symbol = symbol
        self.ansi_symbol = ansi_symbol

    def __str__(self) -> str:
        return self.ansi_symbol

class Card:
    """
    A class to represent a playing card.
    
    Attributes:
        rank (int): The rank of the card 1-13. Face cards have numeric values Ace=1, Jack=11, Queen=12, King=13.
        suit (Suit): The suit of the card. Spades, Hearts, Diamonds, Clubs.
        is_face_up (bool): Represents whether the rank and suit is visible to the user.
    """
    def __init__(self, rank: int, suit: Suit, is_face_up: bool=True):
        if not isinstance(rank, int) or not (1 <= rank <= 13):
            raise ValueError("Card() argument 'rank' must be a number 1-13")
        if not isinstance(suit, Suit):
            raise ValueError(f"Card() argument 'suit' must be a Suit object, not {type(suit)}")
        self.rank = rank
        self.suit = suit
        self.is_face_up = is_face_up
    
    def copy(self):
        return type(self)(self.rank, self.suit, self.is_face_up)

    def __str__(self) -> str:
        if not self.is_face_up:
            return '\033[35m??\033[0m'
        return self.short_name()
      
    def __repr__(self) -> str:
        return self.__str__()

    def can_stack_on(self, other) -> bool:
        # Ex: 4♥ can_stack_on(5♤) = True
        if other is None:
            return self.rank == 13
        if not other.is_face_up:
            return False
        return (
            self.rank == other.rank - 1 and
            self._is_red() != other._is_red()
        )

    def short_name(self) -> str:
        rank_map = {1:'A', 11:'J', 12:'Q', 13:'K'}
        r = rank_map.get(self.rank, str(self.rank))
        return f"{r}{self.suit}"

    def _is_red(self) -> bool:
        return self.suit in (Suit.HEARTS, Suit.DIAMONDS)

    def _is_black(self) -> bool:
        return not self._is_red()
    
class Pile:
    """
    A class to represent/manipulate a list of Card objects.

    Attributes:
        cards (list[Card]): A list of Card objects.
    """
    def __init__(self, cards: list[Card] | None = None):
        if cards is None:
            self.cards = []

        else:
            if isinstance(cards, tuple):
                cards = list(cards)
            if not isinstance(cards, list):
                raise ValueError(f"Pile() argument must be a list of Card objects, not {type(cards)}")
            if not all(isinstance(c, Card) for c in cards):
                raise ValueError(f"Pile() argument must be a list of Card objects")
            self.cards = cards.copy()

    def __str__(self) -> str:
        return str(self.cards)

    def __repr__(self) -> str:
        return self.__str__()

    def copy(self):
        cards = [card.copy() for card in self.cards]
        return type(self)(cards)

    def top(self) -> Card | None:
        if self.cards:
            return self.cards[-1]
        return None
    
    def add(self, cards: list[Card]):
        if isinstance(cards, Card):
            self.cards.append(cards)
        else:
            self.cards.extend(cards)

    def remove_from(self, index: int) -> list[Card]:
        removed = self.cards[index:]
        self.cards = self.cards[:index]
        return removed

class Tableau:
    """
    A class to represent the Tableau in a game of Solitaire.

    Attributes:
        piles (list[Pile]): A list of seven piles of cards representing the seven columns on the Tableau.
    """
    def __init__(self, deck: list[Card]):
        self.piles = self._init_tableau(deck)

    def __str__(self) -> str:
        return str(self.piles)

    def __repr__(self) -> str:
        return self.__str__()

    def copy(self):
        # bypass __init__ to avoid providing a deck
        new_tableau = object.__new__(Tableau)

        # explicitly set class variable outside of __init__
        new_tableau.piles = [pile.copy() for pile in self.piles]

        return new_tableau

    def _init_tableau(self, deck: list[Card]) -> list[Pile]:
        if not len(deck) == 28:
            raise ValueError(f"Tableau() argument 'deck' must be a list of 28 Card objects")
        piles = [Pile() for _ in range(7)]
        deck_idx = 0
        for col in range(7):
            for row in range(col + 1):
                card = deck[deck_idx]
                card.is_face_up = (row == col)
                piles[col].add(cards=card)
                deck_idx += 1
        return piles
    
    def _is_valid_stack(self, cards: list[Card]) -> bool:
        for i in range(len(cards) - 1):
            if not cards[i+1].can_stack_on(cards[i]):
                return False
        return True

    def add_card_to_pile(self, card: Card, target_i: int) -> bool:
        pile = self.piles[target_i]
        if card.can_stack_on(pile.top()):
            pile.add(card)
            return True
        return False

    def can_move_stack_to_stack(self, source_i: int, target_i: int) -> tuple[bool, int | None]:
        source_cards = self.piles[source_i].cards
        target_card = self.piles[target_i].top()
        if source_cards:
            for card_idx, moving_card in enumerate(source_cards):
                if not moving_card.is_face_up:
                    continue
                if moving_card.can_stack_on(target_card):
                    if self._is_valid_stack(source_cards[card_idx:]):
                        return True, card_idx
        return False, None
    
    def move_stack_to_stack(self, source_i: int, target_i: int, index: int):
        removed = self.piles[source_i].remove_from(index)
        self.piles[target_i].add(removed)
        self.update_tableau()

    def update_tableau(self):
        for pile in self.piles:
            if len(pile.cards) > 0:
                pile.top().is_face_up = True
    
    def count_pile_hiddens(self, pile_idx: int) -> int:
        pile_cards = self.piles[pile_idx].cards
        count = 0
        for card in pile_cards:
            if not card.is_face_up:
                count += 1
        return count

class Stock:
    """
    A class to represent the Stock and Waste piles in a game of Solitaire.

    Atrributes:
        pile (Pile): The Stock pile of face-down playing cards to be iterated through.
        wastepile (Pile): The Waste pile of face-up playing cards that can be moved on to the Tableau or Foundation.
    """
    def __init__(self, deck: list[Card]):
        self.pile = self._init_stock(deck)
        self.wastepile = Pile()

    def __str__(self) -> str:
        return str((self.pile, self.wastepile))
    
    def __repr__(self) -> str:
        return self.__str__()

    def copy(self):
        # bypass __init__ to avoid providing a deck
        new_stock = object.__new__(Stock)

        # explicitly set class variables outside of __init__
        new_stock.pile = self.pile.copy() 
        new_stock.wastepile = self.wastepile.copy()

        return new_stock

    def _init_stock(self, deck: list[Card]) -> Pile:
        pile = Pile()
        for card in deck:
            card.is_face_up = False
            pile.add(card)
        return pile
    
    def update_waste(self) -> bool:
        if (not self.pile.cards) and (not self.wastepile.cards):
            # nothing to update if stock and waste are both empty
            return False

        # Face-Up waste
        if len(self.pile.cards) > 0:
            for i in range(min(3, len(self.pile.cards))):
                removed = self.pile.remove_from(-1)
                for card in removed:
                    card.is_face_up = True
                self.wastepile.add(removed)

        # Waste moved to Face-Down stock
        else:
            recycled = list(reversed(self.wastepile.cards))
            for card in recycled:
                card.is_face_up = False
            self.pile.cards = recycled
            self.wastepile.cards = []

        return True

class Foundation:
    """
    A class to represent the Foundation in a game of Solitaire.

    Atrributes:
        piles (dict): A dictionary of Pile objects keyed by Suit objects to represent piles of cards organized by suit.
    """
    def __init__(self, piles: dict[Suit, Pile] | None = None):
        if piles is None:
            self.piles = {suit: Pile() for suit in Suit}
        else:
            self.piles = {suit: pile.copy() for suit, pile in piles.items()}

    def __str__(self) -> str:
        return str(self.piles)
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def copy(self):
        new_piles = {suit: pile.copy() for suit, pile in self.piles.items()}
        return type(self)(piles=new_piles)

    def can_add(self, card: Card) -> bool:
        if not isinstance(card, Card):
            return False
        pile = self.piles[card.suit]
        top = pile.top()

        # Card can be added to pile if
        #   pile is empty AND
        #   card is Ace
        if top is None:
            return card.rank == 1   # Ace
        
        # Card can be added to pile if 
        #   suit matches pile's AND
        #   rank is one higher than card at top of pile
        return (
            card.suit == top.suit and
            card.rank == top.rank + 1
        )
    
    def add(self, card: Card):
        if not self.can_add(card):
            return False
        self.piles[card.suit].add(card)
        return True
    
    def top(self, suit: Suit):
        return self.piles[suit].top()

class Solitaire:
    def __init__(self, deck: list[Card] | None = None, shuffle_deck: bool = True):
        self.deck = self._init_deck(deck, shuffle_deck)
        self.tableau = Tableau(self.deck[:28])
        self.stock = Stock(self.deck[28:])
        self.foundation = Foundation()
        self.score = 0
        self.moves = 0
        self.history = []
        self._add_to_history()

    def _init_deck(self, deck: list[Card] | None, shuffle_deck: bool) -> list[Card]:
        # default behavior
        if deck is None:
            return self._new_deck(shuffle_deck)
        
        # check deck is a list containing 52 Card objects
        if len(deck) != 52:
            print("Bad deck provided. Generating new deck.")
            return self._new_deck(shuffle_deck)
        
        for card in deck:
            if not card.is_face_up:
                card.is_face_up = True
        if shuffle_deck:
            random.shuffle(deck)
        return deck
    
    def _new_deck(self, random_deck: bool = True) -> list[Card]:
        deck = [Card(rank, suit) for suit in Suit for rank in range(1, 14)]
        if random_deck:
            random.shuffle(deck)
        return deck

    def copy(self):
        # bypassing __init__ (faster)
        new_game = object.__new__(Solitaire)

        # explicitly set class variables outside of __init__
        new_game.deck = [card.copy() for card in self.deck]
        new_game.tableau = self.tableau.copy()
        new_game.stock = self.stock.copy()
        new_game.foundation = self.foundation.copy()
        new_game.score = self.score
        new_game.moves = self.moves
        new_game.history = [] # not copying history. That is deal with by _load_prev_save()

        return new_game

    def _add_to_history(self): 
        self.history.append(self.copy())

    def _load_prev_save(self) -> bool: 

        # Triggers if user is at first state in history. Nothing to reload.
        if len(self.history) == 1:
            print("No moves to undo.")
            return False
        
        current_state = self.history.pop()  # Deleting current state from hsitory
        prev_state = self.history[-1]       # Previous (new) state is used to redefine game variables

        # Restore state
        self.tableau = prev_state.tableau.copy()
        self.stock = prev_state.stock.copy()
        self.foundation = prev_state.foundation.copy()
        self.score = prev_state.score
        self.moves = prev_state.moves

        return True

    def play(self):
        print("\n\n\nTo learn how to play, enter '\033[32mH\033[0m' or '\033[32mHELP\033[0m' to view the Help Menu.")
        welcome_banner = center_ansi('\033[33m WELCOME TO SOLITAIRE \033[0m', 51, '\033[34m*\033[31m*\033[0m')
        print(f"\n{welcome_banner}")
        
        self.display_solitaire(show_title=False)

        while True:
            user_input = input("Enter move: \033[32m")
            sys.stdout.write(RESET)
            sys.stdout.flush()
            success = False
            points = 0

            if user_input.upper() in ('', ' ', 'SPACE'):
                user_input = '0 0'
            elif user_input.upper() in ('H', 'HELP'):
                self.display_help_menu()
                continue
            elif user_input.upper() in ('U', 'UNDO', 'B', 'BACK'):
                valid = self._load_prev_save()
                if valid:
                    self.display_solitaire()
                continue
            elif user_input.upper() in ('Q', 'QUIT'):
                break

            elif len(user_input.strip()) == 1:
                try:
                    user_int = int(user_input)
                    if not (0 <= user_int <= 7):
                        raise ValueError()
                except:
                    print("Invalid input. For more information on valid inputs, Enter '\033[32mH\033[0m' to view the Help Menu.")
                    continue
                if user_int > 0: # user wants to move a card from the tableau to the foundation
                    user_input = f"{user_input.strip()} 8"
                else:   # Otherwise the user wants to move from the waste to the tableau or foundation.
                    # Try automatic move waste to tableau
                    for i in range (0, 7):
                        success, temp_points = self._move_waste_to_tableau(i)
                        if success:
                            user_input = '9 9'
                            points = temp_points
                            break
                    # Try automatic move waste to foundation
                    if not success:
                        success, temp_points = self._move_waste_to_foundation()
                        if success:
                            user_input = '9 9'
                            points = temp_points

            # Past this point user input should be '<0-8> <0-8>' ('9 9' if automatic move made)
            try:
                source_i, target_i = tuple(user_input.split())
                source_i = int(source_i) - 1
                target_i = int(target_i) - 1
            except:
                print("Invalid input. For more information on valid inputs, Enter '\033[32mH\033[0m' to view the Help Menu.")
                continue

            # Updating waste from stock
            if (source_i == -1) and (target_i == -1) and not success:
                success = self.stock.update_waste()
                if not success:
                    print("Stock and waste are empty.")
                    continue

            # Moving from a stack in the tableau to another stack in the tableau
            if (0 <= source_i <= 6) and (0 <= target_i <= 6) and not success:
                success, points = self._move_tableau_to_tableau(source_i, target_i)
            
            # Moving from a stack in the tableau to the foundation
            if (0 <= source_i <= 6) and (target_i == 7) and not success:
                success, points = self._move_tableau_to_foundation(source_i)

            # Moving from the waste to a stack in the tableau
            if (source_i == -1) and (0 <= target_i <= 6) and not success:
                success, points = self._move_waste_to_tableau(target_i)

            # Moving from the waste to the foundation
            if (source_i == -1) and (target_i == 7) and not success:
                success, points = self._move_waste_to_foundation()

            # Moving from the foundation to a stack in the tableau
            if (source_i == 7) and (0 <= target_i <= 6) and not success:
                success, points = self._move_foundation_to_tableau(target_i)

            # Display results of successful move
            if success:
                self.score += points
                self.moves += 1
                self._add_to_history()
                self.display_solitaire()
                if self._display_win_screen():
                    break
            else:
                print("Can't move any cards there...")

    def _is_win(self, force_win: bool = False) -> bool:
        if not force_win:
            for suit in self.foundation.piles:
                if not len(self.foundation.piles[suit].cards) == 13:
                    return False
        return True

    def _move_tableau_to_tableau(self, source_i: int, target_i: int) -> tuple[bool, int]:
        """
        Consolidating the methods in Tableau into one for Solitaire.
        This is to make it so moving cards between stacks in the tableau
        is as streamlined as the other moves.
        Returns (success:bool, points:int)
        """
        points = 0
        success, idx = self.tableau.can_move_stack_to_stack(source_i, target_i)
        if success:
            premove_hidden_count = self.tableau.count_pile_hiddens(source_i)
            self.tableau.move_stack_to_stack(source_i, target_i, idx)
            postmove_hidden_count = self.tableau.count_pile_hiddens(source_i)
            if postmove_hidden_count < premove_hidden_count:
                # +5 Score if move reveals a hidden card
                points = 5
        return (success, points)

    def _move_tableau_to_foundation(self, source_i: int) -> tuple[bool, int]:
        points = 0
        premove_hidden_count = self.tableau.count_pile_hiddens(source_i)
        card = self.tableau.piles[source_i].top()
        success = self.foundation.add(card)
        if success:
            self.tableau.piles[source_i].remove_from(-1)
            self.tableau.update_tableau()
            postmove_hidden_count = self.tableau.count_pile_hiddens(source_i)
            if postmove_hidden_count < premove_hidden_count:
                points = 20 # +20 Score if move reveals a hidden card
            else:                
                points = 15 # +15 Score if card moves from tableau to foundation without revealing a new card in the tableau
        return (success, points)
    
    def _move_waste_to_tableau(self, target_i: int) -> tuple[bool, int]:
        success = False
        points = 0

        card = self.stock.wastepile.top()
        if card is not None:
            success = self.tableau.add_card_to_pile(card, target_i)
            if success:
                self.stock.wastepile.remove_from(-1)
                points = 5      # +5 score if card is moved from waste to tableau
        return (success, points)
    
    def _move_waste_to_foundation(self) -> tuple[bool, int]:
        success = False
        points = 0

        card = self.stock.wastepile.top()
        if card is not None:
            success = self.foundation.add(card)
            if success:
                self.stock.wastepile.remove_from(-1)
                points = 10     # +10 score if card moves from waste to foundation
        return (success, points)

    def _move_foundation_to_tableau(self, target_i: int) -> tuple[bool, int]:
        # - Score is reset to 15 if this move is made
        # - Since this is text-based, if there are two valid moves to be made from the foundation to a
        #   stack in the tableau I will need to ask the user which suit of the valid suits to pull from
        success = False
        points = 0
        found_suit_order = [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]
        tab_card = self.tableau.piles[target_i].top()
        choice_list = []
        for suit in found_suit_order:
            valid = False
            found_card = self.foundation.piles[suit].top()
            if found_card:
                valid = found_card.can_stack_on(tab_card)
            if valid:
                success = True
                choice_list.append(found_card)
        
        if success:
            # will probably need to use self.foundation.piles[found_card.suit] to get foundation pile I'm removing from
            # then .remove_from() Pile method
            if len(choice_list) == 1:
                # remove card from foundation and add it to tableau
                success = self.tableau.add_card_to_pile(choice_list[0], target_i)
                self.foundation.piles[choice_list[0].suit].remove_from(-1)
            else:   # len(choice_list) should be 2 here
                # ask user which card in the foundation they intended to move
                # then remove card from foundation and add it tableau
                print("Multiple valid moves detected. Select card to move from Foundation to Tableau:")
                for i, found_card in enumerate(choice_list):
                    print(f"{i+1}. {found_card}")
                valid_input = False
                while not valid_input:
                    user_input = input(f"Enter a number (\033[32m1\033[0m-\033[32m{len(choice_list)}\033[0m): \033[32m")
                    sys.stdout.write(RESET)
                    sys.stdout.flush()
                    try:
                        choice = int(user_input) - 1
                        if not (0 <= choice <= len(choice_list) - 1):
                            raise ValueError
                        valid_input = True
                    except ValueError:
                        print(f"Invalid selection. Please enter an integer \033[32m1\033[0m-\033[32m{len(choice_list)}\033[0m.")
                success = self.tableau.add_card_to_pile(choice_list[choice], target_i)
                self.foundation.piles[choice_list[choice].suit].remove_from(-1)

            # calculate what 'points' should be to bring self.score down to 15
            if success:
                points = 15 - self.score
                if self.score + points < 0: # fail-safe so that self.score is never negative
                    points = -1 * self.score # if somehow it goes negative, score will be brought to 0
        
        return (success, points)

    def display_solitaire(self, show_title: bool = True):
        if show_title:
            title = center_ansi('\033[33m SOLITAIRE \033[0m', 51, '\033[34m*\033[31m*')
            print(f"\n\n\n\n{title}")
        print('\n\033[4;30m 0   |    1    2    3    4    5    6    7   |    8 \033[0m')
        waste_stack = self.stock.wastepile.cards[-3:]
        for row in range( max(max(len(pile.cards) for pile in self.tableau.piles), 4) ):
            # stock piles
            if row == 0:
                if self.stock.pile.cards:
                    s = ljust_ansi('\033[35m??\033[0m', 5)
                    print(f"{s}|  ", end=' ')
                else:
                    print(f"{'  '.ljust(5)}|  ", end=' ')
            elif row < len(waste_stack)+1:
                s = ljust_ansi(str(waste_stack[row-1]), 5)
                print(f"{s}|  ", end=' ')
            else:
                print('     |  ', end=' ')

            # tableau piles
            for pile in self.tableau.piles:
                if row < len(pile.cards):
                    print(ljust_ansi(str(pile.cards[row]), 4), end=' ')
                else:
                    print('    ', end=' ')
            
            # foundation piles
            if row < len(self.foundation.piles):
                displayed_suit_order = [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]
                suit = displayed_suit_order[row]
                pile = self.foundation.piles[suit]
                if not pile.cards:
                    s = ljust_ansi(suit.ansi_symbol*2, 4)
                    print(f"|   {s}", end=' ')
                    # print(f"|   {ljust_ansi(suit*2, 4)}", end=' ')
                else:
                    s = ljust_ansi(str(pile.top()), 4)
                    print(f"|   {s}", end=' ')
            else:
                print('|   ', end=' ')
            print()
        # score_str = f"Score: {str(self.score).ljust(4)} Moves: {str(self.moves).ljust(4)}"
        score_str = f"{' '*15}Score: {str(self.score).ljust(4)} Moves: {str(self.moves)}"
        print(f"\n\033[33m{score_str}\033[0m")
        print()

    def _display_win_screen(self, force_win: bool = False) -> bool:
        if self._is_win(force_win=force_win):
            uwin = ' \033[34m!\033[31m!\033[34m! \033[31m!\033[34m!\033[31m! \033[33mYOU WIN \033[34m!\033[31m!\033[34m! \033[31m!\033[34m!\033[31m! \033[0m'
            pad = "\033[34m*\033[31m*\033[0m"
            s = center_ansi(uwin, 50, pad)
            print(f"\n{s}")
            stats = f"Final Score: {str(self.score).ljust(6)} Total Moves: {str(self.moves).ljust(6)}"
            s = center_ansi(f"\033[33m{stats}\033[0m", 50)
            print(f"\n{s}\n")
            return True
        return False

    def display_help_menu(self):
        title = center_ansi('\033[33m SOLITAIRE HELP MENU \033[0m', 51, '\033[34m*\033[31m*\033[0m')
        print(f"\n\n\n\n{title}")
        print("\n1. '\033[32msource #\033[0m' '\033[32mtarget #\033[0m' (e.g., '\033[32m3 5\033[0m' moves an eligible card from column 3 to column 5)")
        print("2. \033[32mSPACE\033[0m ' ' to update waste from stock")
        print("3. '\033[32mU\033[0m', '\033[32mB\033[0m', '\033[32mUNDO\033[0m', or '\033[32mBACK\033[0m' to undo a move")
        print("4. '\033[32mH\033[0m' or '\033[32mHELP\033[0m' to display this menu again")
        print("5. '\033[32mQ\033[0m' or '\033[32mQUIT\033[0m' to quit")

        # TODO: While loop for user to select options and learn more details about each section.
        print("\nEnter anything to return to \033[33mSOLITAIRE\033[0m.")
        user_input = input("Enter move: \033[32m")
        sys.stdout.write(RESET)
        sys.stdout.flush()
        self.display_solitaire()

# Play game
if __name__ == '__main__':
    sys.stdout.write(RESET)
    sys.stdout.flush()

    solitaire = Solitaire(shuffle_deck=True)
    solitaire.play()

    while True:
        user_input = input("Play again? (Y/N): \033[32m")
        sys.stdout.write(RESET)
        sys.stdout.flush()
        if user_input.upper() not in ('Y', 'N'):
            print("Invalid input. Enter either '\033[32mY\033[0m' or '\033[32mN\033[0m'")
            continue
        if user_input.upper() == 'Y':
            solitaire = Solitaire(shuffle_deck=True)
            solitaire.play()
        if user_input.upper() == 'N':
            print("\nThank you for playing!")
            break

    sys.stdout.write(RESET)
    sys.stdout.flush()

