from enum import Enum
import random

class Suit(Enum):
    """
    ####### Suit.SPADES -> Suit.SPADES
    ## Suit.SPADES.name -> 'SPADES'
    # Suit.SPADES.value -> '♤'
    """
    SPADES = '♤'
    HEARTS = '♥'
    DIAMONDS = '♦'
    CLUBS = '♧'

class Card:
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

    def __str__(self):
        if not self.is_face_up:
            return '??'
        return self.short_name()
      
    def __repr__(self):
        return self.__str__()

    def can_stack_on(self, other):
        if other is None:
            return self.rank == 13
        if not other.is_face_up:
            return False
        return (
            self.rank == other.rank - 1 and
            self.is_red() != other.is_red()
        )

    def short_name(self):
        rank_map = {1:'A', 11:'J', 12:'Q', 13:'K'}
        r = rank_map.get(self.rank, str(self.rank))
        return f"{r}{self.suit.value}"

    def long_name(self):
        rank_map = {1:'ACE', 2:'TWO', 3:'THREE', 4:'FOUR', 5:'FIVE', 6:'SIX', 7:'SEVEN', 8:'EIGHT', 9:'NINE', 10:'TEN', 11:'JACK', 12:'QUEEN', 13:'KING'}
        r = rank_map[self.rank]
        return f"{r} of {self.suit.name}"

    def card_symbol(self):
        unicode_array = [
            ['🂡', '🂱', '🃁', '🃑'],
            ['🂢', '🂲', '🃂', '🃒'],
            ['🂣', '🂳', '🃃', '🃓'],
            ['🂤', '🂴', '🃄', '🃔'],
            ['🂥', '🂵', '🃅', '🃕'],
            ['🂦', '🂶', '🃆', '🃖'],
            ['🂧', '🂷', '🃇', '🃗'],
            ['🂨', '🂸', '🃈', '🃘'],
            ['🂩', '🂹', '🃉', '🃙'],
            ['🂪', '🂺', '🃊', '🃚'],
            ['🂫', '🂻', '🃋', '🃛'],
            ['🂭', '🂽', '🃍', '🃝'],
            ['🂮', '🂾', '🃎', '🃞']
        ]
        suit_index = list(Suit).index(self.suit)
        return unicode_array[self.rank - 1][suit_index]

    def is_red(self):
        return self.suit in (Suit.HEARTS, Suit.DIAMONDS)

    def is_black(self):
        return not self.is_red()

class Pile:
    """
    The Pile class is a list of Card objects that includes functions specific to manipulating lists of Card objects.
    """
    def __init__(self, cards=None):
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

    def __str__(self):
        return str(self.cards)

    def __repr__(self):
        return self.__str__()

    def copy(self):
        cards = [card.copy() for card in self.cards]
        return type(self)(cards)

    def top(self):
        if self.cards:
            return self.cards[-1]
        return None
    
    def add(self, cards):
        if isinstance(cards, Card):
            self.cards.append(cards)
        else:
            self.cards.extend(cards)

    def remove_from(self, index) -> list[Card]:
        removed = self.cards[index:]
        self.cards = self.cards[:index]
        return removed

class Tableau:
    def __init__(self, deck: list[Card]=None, piles: list[Pile]=None):
        if deck is not None:    # Tableau should usually be initialized with a deck
            if isinstance(deck, tuple):
                deck = list(deck)
            if not isinstance(deck, list):
                raise ValueError(f"Tableau() argument 'deck' must be a list of 28 Card objects, not {type(deck)}")
            if len(deck) < 28:
                raise ValueError(f"Tableau() argument 'deck' must be a list of 28 Card objects, got {len(deck)} objects")
            if not all(isinstance(c, Card) for c in deck):
                raise ValueError(f"Tableau() argument 'deck' must be a list of 28 Card objects")
            self.piles = self._init_tableau(deck)
        
        elif piles is not None:
            if isinstance(piles, tuple):
                piles = list(piles)
            if not isinstance(piles, list):
                raise ValueError(f"Tableau() argument 'piles' must be a list of Pile objects, not {type(piles)}")
            if not all(isinstance(p, Pile) for p in piles):
                raise ValueError(f"Tableau() argument 'piles' must be a list of Piles objects")
            self.piles = piles

        else:
            raise ValueError(f"Tableau() requires at least one argument, 'deck' or 'piles'. Received:\ndeck={deck}\npiles={piles}")

    def __str__(self):
        return str(self.piles)

    def __repr__(self):
        return self.__str__()

    def copy(self):
        piles = [pile.copy() for pile in self.piles]
        return type(self)(piles=piles)

    def _init_tableau(self, deck: list[Card]):
        piles = [Pile() for _ in range(7)]
        deck_idx = 0
        for col in range(7):
            for row in range(col + 1):
                card = deck[deck_idx]
                card.is_face_up = (row == col)
                piles[col].add(cards=card)
                deck_idx += 1
        return piles
    
    def _is_valid_stack(self, cards):
        for i in range(len(cards) - 1):
            if not cards[i+1].can_stack_on(cards[i]):
                return False
        return True

    def add_card2pile(self, card: Card, target_i: int):
        pile = self.piles[target_i]
        if card.can_stack_on(pile.top()):
            pile.add(card)
            return True
        return False

    def can_move_stack2stack(self, source_i, target_i):
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
    
    def move_stack2stack(self, source_i, target_i, index):
        removed = self.piles[source_i].remove_from(index)
        self.piles[target_i].add(removed)
        self.update_tableau()

    def update_tableau(self):
        for pile in self.piles:
            if len(pile.cards) > 0:
                pile.top().is_face_up = True
    
    def count_pile_hiddens(self, pile_idx):
        pile_cards = self.piles[pile_idx].cards
        count = 0
        for card in pile_cards:
            if not card.is_face_up:
                count += 1
        return count

class Stock:
    def __init__(self, deck: list[Card]=None, pile: Pile=None, wastepile: Pile=None):
        if deck is not None:    # Stock should usually be initialized with a deck
            if isinstance(deck, tuple):
                deck = list(deck)
            if not isinstance(deck, list):
                raise ValueError(f"Stock() argument 'deck' must be a list of Card objects, not {type(deck)}")
            if not all(isinstance(c, Card) for c in deck):
                raise ValueError(f"Stock() argument 'deck' must be a list of Card objects")
            self.pile = self._init_stock(deck)
            self.wastepile = Pile()
        
        elif pile is not None and wastepile is not None:
            self.pile = pile.copy()
            self.wastepile = wastepile.copy()

        else:
            raise ValueError(f"Stock() requires at least one argument 'deck', or both 'pile' and 'wastepile'. Received:\ndeck={deck}\npile={pile}\nwastepile={wastepile}")


    def __str__(self):
        return str((self.pile, self.wastepile))
    
    def __repr__(self):
        return self.__str__()
    
    def copy(self):
        return type(self)(pile=self.pile.copy(), wastepile=self.wastepile.copy())

    def _init_stock(self, deck: list[Card]):
        pile = Pile()
        for card in deck:
            card.is_face_up = False
            pile.add(card)
        return pile
    
    def update_waste(self):
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
            for card in self.wastepile.cards:
                removed = self.wastepile.remove_from(-1)
                for card in removed:
                    card.is_face_up = False
                self.pile.add(removed)
        return True

class Foundation:
    def __init__(self, piles=None):
        if piles is None:
            self.piles = {suit: Pile() for suit in Suit}
        else:
            self.piles = {suit: pile.copy() for suit, pile in piles.items()}

    def __str__(self):
        return str(self.piles)
    
    def __repr__(self):
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
    def __init__(self, deck=None, shuffle_deck:bool=True):
        self.deck = self.init_deck(deck, shuffle_deck)
        self.tableau = Tableau(self.deck[:28])
        self.stock = Stock(self.deck[28:])
        self.foundation = Foundation()
        self.score = 0
        self.moves = 0
        self.history = []

    def init_deck(self, deck: list, shuffle_deck: bool):
        bad_deck = False
        # default behavior
        if deck is None:
            return self.new_deck(shuffle_deck)
        
        # check deck is a list containing 52 Card objects
        if not isinstance(deck, list) or len(deck) != 52:
            bad_deck = True
        elif not all(isinstance(c, Card) for c in deck):
            bad_deck = True
        
        if bad_deck:
            print("Bad deck provided. Generating new deck.")
            return self.new_deck(shuffle_deck)
        
        for card in deck:
            if not card.is_face_up:
                card.is_face_up = True
        if shuffle_deck:
            random.shuffle(deck)
        return deck
    
    def new_deck(self, random_deck=True):
        deck = [Card(rank, suit) for suit in Suit for rank in range(1, 14)]
        if random_deck:
            random.shuffle(deck)
        return deck

    def copy(self):
        new_game = object.__new__(Solitaire) # bypassing __init__ (faster)

        new_game.deck = [card.copy() for card in self.deck]
        new_game.tableau = self.tableau.copy()
        new_game.stock = self.stock.copy()
        new_game.foundation = self.foundation.copy()
        new_game.score = self.score
        new_game.moves = self.moves
        new_game.history = [] # not copying history. That is deal with by load_prev_save()

        return new_game

    def add_to_history(self): 
        self.history.append(self.copy())

    def load_prev_save(self): 

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
        print(f"\n{' WELCOME TO SOLITAIRE '.center(50, '*')}")
        self.display_help_menu()
        self.display_solitaire()
        self.add_to_history()

        while True:
            user_input = input("Enter move: ")
            success = False
            if user_input.upper() in ('Q', 'QUIT'):
                break
            if user_input == ' ':
                success = self.stock.update_waste()
                if success:
                    self.add_to_history()
                    self.moves += 1
                    self.display_solitaire()
                else:
                    print("Stock and waste are empty.")
                continue
            if user_input.upper() in ('H', 'HELP'):
                self.display_help_menu()
                continue
            if user_input.upper() in ('U', 'UNDO', 'B', 'BACK'):
                valid = self.load_prev_save()
                if valid:
                    self.display_solitaire()
                continue

            try:
                source_i, target_i = tuple(user_input.split())
                source_i = int(source_i) - 1
                target_i = int(target_i) - 1
            except:
                print("Invalid input")
                continue


            # Moving from a stack in the tableau to another stack in the tableau
            if (0 <= source_i <= 6) and (0 <= target_i <= 6):
                valid, idx = self.tableau.can_move_stack2stack(source_i, target_i)
                if valid:
                    success = True
                    premove_hidden_count = self.tableau.count_pile_hiddens(source_i)
                    self.tableau.move_stack2stack(source_i, target_i, idx)
                    postmove_hidden_count = self.tableau.count_pile_hiddens(source_i)
                    if postmove_hidden_count < premove_hidden_count:
                        # +5 Score if move reveals a hidden card
                        self.score += 5
            
            # TODO: Moving from a stack in the tableau to the foundation
            if (0 <= source_i <= 6) and (target_i == 7):
                premove_hidden_count = self.tableau.count_pile_hiddens(source_i)
                success = self.move_tableau2foundation(source_i)
                postmove_hidden_count = self.tableau.count_pile_hiddens(source_i)
                if success:
                    if postmove_hidden_count < premove_hidden_count:
                        # +20 Score if move reveals a hidden card
                        self.score += 20
                    else:
                        # +15 Score if card moves from tableau to foundation without revealing a new card in the tableau
                        self.score += 15

            # TODO: Moving from the foundation to a stack in the tableau
            # - Score is reset to 15 if this move is made
            # - Since this is text-based, if there are two valid moves to be made from the foundation to a
            #   stack in the tableau I will need to ask the user which suit of the valid suits to pull from

            # TODO: Moving from the waste to a stack in the tableau
            if (source_i == -1) and (0 <= target_i <= 6):
                success = self.move_waste2tableau(target_i)
                if success:
                    # +5 score if card is moved from waste to tableau
                    self.score += 5

            # TODO: Moving from the waste to the foundation
            if (source_i == -1) and (target_i == 7):
                success = self.move_waste2foundation()
                if success:
                    # +10 score if card moves from waste to foundation
                    self.score += 10

            # Display results of move
            if success:
                self.moves += 1
                self.add_to_history()
                self.display_solitaire()
                if self.display_win_screen():
                    break
            else:
                print("Can't move any cards there...")

    def is_win(self):
        for suit in self.foundation.piles:
            if not len(self.foundation.piles[suit].cards) == 13:
                return False
        return True

    def move_tableau2foundation(self, source_i):
        card = self.tableau.piles[source_i].top()
        valid = self.foundation.add(card)
        if valid:
            self.tableau.piles[source_i].remove_from(-1)
            self.tableau.update_tableau()
            return True
        return False
    
    def move_waste2tableau(self, target_i):
        card = self.stock.wastepile.top()
        valid = self.tableau.add_card2pile(card, target_i)
        if valid:
            self.stock.wastepile.remove_from(-1)
            return True
        return False
    
    def move_waste2foundation(self):
        card = self.stock.wastepile.top()
        valid = self.foundation.add(card)
        if valid:
            self.stock.wastepile.remove_from(-1)
            return True
        return False

    def display_solitaire(self):
        score_str = f"Score: {str(self.score).ljust(4)} Moves: {str(self.moves).ljust(4)}"
        print(f"\n{score_str.center(50, ' ')}")
        print(' 0   |    1    2    3    4    5    6    7   |    8')
        for row in range( max(max(len(pile.cards) for pile in self.tableau.piles), 4) ):
            # stock piles
            waste_stack = self.stock.wastepile.cards[-3:]
            if row == 0:
                if self.stock.pile.cards:
                    print(f"{'??'.ljust(5)}|  ", end=' ')
                else:
                    print(f"{'  '.ljust(5)}|  ", end=' ')
            elif row < len(waste_stack)+1:
                print(f"{str(waste_stack[row-1]).ljust(5)}|  ", end=' ')
            else:
                print('     |  ', end=' ')

            # tableau piles
            for pile in self.tableau.piles:
                if row < len(pile.cards):
                    print(str(pile.cards[row]).ljust(4), end=' ')
                else:
                    print('    ', end=' ')
            
            # foundation piles
            if row < len(self.foundation.piles):
                suit = list(self.foundation.piles)[row]
                pile = self.foundation.piles[suit]
                if not pile.cards:
                    print(f"|   {(suit.value*2).ljust(4)}", end=' ')
                else:
                    print(f"|   {str(pile.top()).ljust(4)}", end=' ')
            else:
                print('|   ', end=' ')
            print()
        print()

    def display_win_screen(self):
        if self.is_win():
            print(f"{' !!! !!! YOU WIN !!! !!! '.center(50, '*')}")
            print(f"Final Score: {str(self.score).ljust(6)} Total Moves: {str(self.moves).ljust(6)}\n")
            return True
        return False

    def display_help_menu(self):
        print("Move options:\n1. <source> <target> (e.g., '3 5')\n2. ' ' to update waste from stock\n3. 'U', 'B', 'UNDO', or 'BACK' to undo a move\n4. 'H' or 'HELP' to display this menu again\n5. 'Q' or 'QUIT' to quit")

# Play game
if __name__ == '__main__':
    solitaire = Solitaire(shuffle_deck=True)
    solitaire.play()
