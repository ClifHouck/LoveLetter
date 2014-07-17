import collections
import copy
import random

random.seed()

class Strategy(object):
    def __init__(self, target_strategy, guess_strategy, discard_strategy):
        self._last_seen_hand   = None
        self._target_strategy  = target_strategy
        self._guess_strategy   = guess_strategy
        self._discard_strategy = discard_strategy

    def get_target(self, player, game):
        return self._target_strategy.target(player, game)

    def get_guess(self, player, target, game):
        return self._guess_strategy.guess(player, target, game)

    def get_discard(self, player, game):
        return self._discard_strategy.get_discard(player, game)

    def look_at(self, target):
        self._last_seen_hand = {
                    'target'    : target.number,
                    'hand'      : target.hand_value(),
                    'turns_ago' : 0
                }

    def play(self, player, game):
        card = self.get_discard(player, game)
        player.discard(game, card)

        target = None
        if card.needs_target():
            target = self.get_target(player, game)

        guess = None
        if card.needs_guess():
            guess = self.get_guess(player, target, game)

        card.apply_effect(game   = game,
                          player = player,
                          target = target,
                          guess  = guess)

PLAYER_PROMPT = '-->'

class HumanTarget(object):
    def get_input(self, player, game):
        target_numbers = [p.number() for p in game.available_targets(player)]
        print "HumanTarget: Available targets: " + str(target_numbers)

        selection = raw_input(PLAYER_PROMPT)
        number = None

        try:
            number = int(selection)
        except ValueError:
            print "HumanTarget: '" + selection + "' is not a number! Try again."
            return None

        if number not in target_numbers:
            print "HumanTarget: '" + selection + "' is not a valid player to target. Try again."
            return None

        return number

    def target(self, player, game):
        selection = None
        while selection is None:
            selection = self.get_input(player, game)
        return game.player(selection)

class HumanGuess(object):
    def get_input(self, player, game):
        print "HumanGuess: State of everyone's discard pile: "

        player_input = raw_input(PLAYER_PROMPT)

        try:
            guess = int(player_input)
        except ValueError:
            print "HumanGuess: '" + player_input + "' is not a valid number! Try again."
            return None

        if guess > Card.PRINCESS_NUM or guess < Card.GUARD_NUM:
            print "HumanGuess: Guess must be a number between " + str(Card.GUARD_NUM) + " and " + str(Card.PRINCESS_NUM) + ". Try again."
            return None

        return guess

    def guess(self, player, target, game):
        guess = None
        while guess is None:
            guess = self.get_input(player, game)
        return guess

class HumanDiscard(object):
    def get_input(self, player, game):
        hand = player.hand()
        hand_str = "[" + "0 - " + str(hand[0]) + " 1 - " + str(hand[1]) + "]"
        print "HumanDiscard: Your hand: " + hand_str + ". Pick card 0 or card 1."

        player_input = raw_input(PLAYER_PROMPT)

        try:
            choice = int(player_input)
        except ValueError:
            print "HumanDiscard: '" + player_input + "' is not a valid number! Try again."
            return None

        if choice != 0 and choice != 1:
            print "HumanGuess: Choice must be either 0 or 1. Try again."
            return None

        return choice

    def get_discard(self, player, game):
        choice = None
        while choice is None:
            choice = self.get_input(player, game)
        return player.hand()[choice]


class HumanStrategy(Strategy):
    def __init__(self):
        super(HumanStrategy, self).__init__(HumanTarget(), HumanGuess(), HumanDiscard())

class RandomDiscard(object):
    def get_discard(self, player, game):
        return random.choice(player.hand())

class RandomTarget(object):
    def target(self, player, game):
        return random.choice(game.available_targets(player)) 

class RandomGuess(object):
    def guess(self, player, target, game):
        return random.randrange(2, 8, 1)

class RandomStrategy(Strategy):
    def __init__(self):
        super(RandomStrategy, self).__init__(RandomTarget(), RandomGuess(), RandomDiscard())

class ExamineDiscardedCardsGuess(object):
    def guess(self, player, target, game):
        whats_left = get_remaining_cards_counter(player, game)
        # Remove the Guard from consideration.
        del whats_left[Card.GUARD_NUM]
        guess = whats_left.most_common(1)[0][0]
        game.log("ExamineDiscardedCardsGuess: Guessing " + str(guess))
        return guess

class LowestDiscard(object):
    def get_discard(self, player, game):
        hand = player.hand()

        card = hand[1]
        if hand[1].number() > hand[0].number():
            card = hand[0]

        game.log("LowestDiscard: Discarding " + card.name() + "(" + str(card.number()) + "), since it is lowest card in the player's hand.")
        return card

class HighestDiscard(object):
    def get_discard(self, player, game):
        hand = player.hand()

        card = hand[1]
        if hand[1].number() < hand[0].number():
            card = hand[0]

        game.log("HighestDiscard: Discarding " + card.name() + "(" + str(card.number()) + "), since it is highest card in the player's hand.")
        return card

class LowestDiscardStrategy(Strategy):
    def __init__(self):
        super(LowestDiscardStrategy, self).__init__(RandomTarget(), RandomGuess(), LowestDiscard())

class HighestDiscardStrategy(Strategy):
    def __init__(self):
        super(HighestDiscardStrategy, self).__init__(RandomTarget(), RandomGuess(), HighestDiscard())

def get_remaining_cards_counter(player, game):
    all_discarded_cards = []
    for p in game.players():
        all_discarded_cards += p.discard_pile()
    all_discarded_cards += player.discard_pile()
    discarded_cards  = [card.number() for card in all_discarded_cards]
    print "get_remaining_cards_counter: " + str(discarded_cards)

    # The player's hand also gives us information.
    discarded_cards.append(player.hand()[0].number())

    whats_left = Deck.CANONICAL_DECK_COUNT - collections.Counter(discarded_cards)
    return whats_left

def num_indeterminate_cards(player, game):
    """ Returns the sum of the number of cards that a player cannot directly see, whether because they are in another player's hand,
        awaiting to be drawn, or if the burn card has not been drawn. """
    burn_card = 1 
    if game.burn_card() is None:
        burn_card = 0
    print str(game.deck().size()), str(len(game.players())), str(burn_card)
    return game.deck().size() + len(game.players()) + burn_card

def best_pure_guess(player, game):
    """ Guesses the most probable card regardless of target based only on these two criteria:
        - What cards are visible in the discard piles.
        - What card is in this player's hand.
        Returns a tuple of (set of cards with same remaining frequency, likelyhood of guessing correctly based on criteria used.)
    """
    whats_left = get_remaining_cards_counter(player, game)
    del whats_left[Card.GUARD_NUM]
    remaining_counts = whats_left.most_common()

    # There are only guards left in this case.
    if len(remaining_counts) == 0: 
        return [[1], 1]

    game.log("best_pure_guess: " + str(remaining_counts))
    best_card_numbers = []
    best_count = remaining_counts[0][1]
    for count_pair in remaining_counts:
        if count_pair[1] == best_count:
            best_card_numbers.append(count_pair[0])
        else:
            break
    game.log("best_pure_guess: " + str(best_count) + " / " + str(num_indeterminate_cards(player, game)))
    return [best_card_numbers, float(best_count) / num_indeterminate_cards(player, game)]

def sensei_discard_guess(player, target, game):
    # TODO
    return [[5, 6, 8], 0.0]

class BestGuess(object):
    """ This guessing strategy attempts to take the following into account when making a guess:
        - All seen cards = {Discarded cards} U {card in hand}
        - Seen hands 
        - Specific discarded cards: { Sensei }
    """
    def guess(self, player, target, game):
        # If we've seen the target's hand, and we're sure they still have the card, then
        # knock that sucker out!
        seen_card, target_has_seen_card = self.ponder_seen_hands(player, target, game)
        if target_has_seen_card:
            return seen_card

        # FIXME: Not sure about the pure_guess vs. sensei_discard_guess logic below.
        pure_guesses,           pure_likelyhood   = best_pure_guess(player, game)
        game.log("BestGuessStrategy: " + str(pure_guesses) + " " + str(pure_likelyhood) + "\n")
        sensei_discard_guesses, sensei_likelyhood = sensei_discard_guess(player, target, game)
        # If it seems more probable that the sensei discard was forced AND it's better than a pure guess, then use that guess.
        if sensei_likelyhood > pure_likelyhood:
            return random.choice(sensei_card_guess)
        selection = random.choice(pure_guesses)

        if selection == Card.GUARD_NUM:
            game.log("BestGuess: Only guards remain! Returning a random guess because guessing Guard is illegal.")
            return RandomGuess.guess()

        return selection

    def ponder_seen_hands(self, player, target, game):
        # TODO: fill-in, move to Player class.
        return [[1], False]

class BestGuessStrategy(Strategy):
    def __init__(self):
        super(BestGuessStrategy, self).__init__(RandomTarget(), BestGuess(), LowestDiscard())
    
class Player(object):
    def __init__(self, card, number, strategy):
        self._hand = [card]
        self._discard_pile = []
        self._number = number
        self._strat  = strategy

    def play(self, game):
        drawn_card = game.deck().draw()
        self._hand.append(drawn_card)
        game.log("Player " + str(self._number) + " drew the " + drawn_card.name() + "(" + str(drawn_card.number()) + ").")
        hand_text = "["
        for card in self._hand:
            hand_text += card.name() + "(" + str(card.number()) + ") "
        hand_text += "]"
        game.log("Player " + str(self._number) + "'s hand: " + hand_text)

        numbers = []
        for card in self._hand:
            numbers.append(card.number())

        # Sensei must be discarded if Manipulator or Hatamoto is in the player's hand.
        if ((Card.MANIPULATOR_NUM in numbers or Card.HATAMOTO_NUM in numbers) and
            Card.SENSEI_NUM in numbers):
            for card in self._hand:
                if card.number() == Card.SENSEI_NUM:
                    self.discard(game, card)
                    return

        self._strat.play(self, game)

    def hand_value(self):
        return self._hand[0].number()

    def hand_str(self):
        output = "["
        for card in self._hand:
            output += str(card) + " "
        output += "]"
        return output

    def discard(self, game, card):
        self._hand.remove(card)
        self._discard_pile.append(card)
        game.log("Player " + str(self.number()) + " discarded the " + card.name() + " card.")

    def discard_hand(self, game):
        card = self._hand[0]
        self.discard(game, card)

        # If the discarded card is the princess this player loses.
        if card.number() == 8:
            game.lose(self)
            return

        game.log("Player " + str(self.number()) + " drew a card after discarding their hand.")
        card = None
        if game.deck().size() == 0:
            card = game.draw_burn_card()
            game.log("Player " + str(self.number()) + " drew the burn card because the deck is empty.")
        else:
            card = game.deck().draw()
        self._hand.append(card)

    def discard_pile(self):
        return self._discard_pile

    def trade(self, target_player):
        self._hand, target_player._hand = target_player._hand, self._hand

    def number(self):
        return self._number

    def hand(self):
        return self._hand

    def look_at(self, target):
        self._strat.look_at(target)

    def __eq__(self, other):
        return self.number() == other.number()


class Card(object):
    PRINCESS_NUM    = 8
    SENSEI_NUM      = 7
    MANIPULATOR_NUM = 6
    HATAMOTO_NUM    = 5
    SHUGENJA_NUM    = 4
    DIPLOMAT_NUM    = 3
    COURTIER_NUM    = 2
    GUARD_NUM       = 1

    def apply_effect(self, game, player, target, guess):
        pass

    def number(self):
        return self._number

    def name(self):
        return self._name

    def needs_guess(self):
        return self._needs_guess

    def needs_target(self):
        return self._needs_target

    def __eq__(self, other):
        return self.number() == other.number()

    def __str__(self):
        return self._name + "(" + str(self._number) + ")"

class Princess(Card):
    def __init__(self):
        self._number       = 8
        self._name         = "Princess"
        self._needs_guess  = False
        self._needs_target = False

    def apply_effect(self, game, player, target, guess):
        game.lose(player)

class Sensei(Card):
    def __init__(self):
        self._number = 7
        self._name   = "Sensei"
        self._needs_guess  = False
        self._needs_target = False

class Manipulator(Card):
    def __init__(self):
        self._number = 6
        self._name   = "Manipulator"
        self._needs_guess  = False
        self._needs_target = True

    def apply_effect(self, game, player, target, guess):
        player.trade(target)

class Hatamoto(Card):
    def __init__(self):
        self._number = 5
        self._name   = "Hatamoto"
        self._needs_guess  = False
        self._needs_target = True

    def apply_effect(self, game, player, target, guess):
        target.discard_hand(game)

class Shugenja(Card):
    def __init__(self):
        self._number = 4
        self._name   = "Shugenja"
        self._needs_guess  = False
        self._needs_target = False

    def apply_effect(self, game, player, target, guess):
        game.protect(player)

class Diplomat(Card):
    def __init__(self):
        self._number = 3
        self._name   = "Diplomat"
        self._needs_guess  = False
        self._needs_target = True

    def apply_effect(self, game, player, target, guess):
        if player.hand_value() > target.hand_value(): 
            game.lose(target)
        elif target.hand_value() > player.hand_value():
            game.lose(player)

class Courtier(Card):
    def __init__(self):
        self._number = 2
        self._name   = "Courtier"
        self._needs_guess  = False
        self._needs_target = True

    def apply_effect(self, game, player, target, guess):
        player.look_at(target)
        game.log("Player " + str(player.number()) + " looked at " + str(target.number()) + "'s hand.")

class Guard(Card):
    def __init__(self):
        self._number        = 1
        self._name          = "Guard"
        self._needs_guess   = True
        self._needs_target  = True

    def apply_effect(self, game, player, target, guess):
        game.guess(target, guess)

class Deck:
    CANONICAL_DECK = [
        Princess(),
        Sensei(),
        Manipulator(),
        Hatamoto(), Hatamoto(),
        Shugenja(), Shugenja(),
        Diplomat(), Diplomat(),
        Courtier(), Courtier(),
        Guard(), Guard(), Guard(), Guard(), Guard()
    ]

    CANONICAL_DECK_COUNT = collections.Counter([card.number() for card in CANONICAL_DECK])

    # CANONICAL_DECK = [
    #     Card.PRINCESS_NUM,
    #     Card.SENSEI_NUM,
    #     Card.MANIPULATOR_NUM,
    #     Card.HATAMOTO_NUM, Card.HATAMOTO_NUM,
    #     Card.SHUGENJA_NUM, Card.SHUGENJA_NUM, 
    #     Card.DIPLOMAT_NUM, Card.DIPLOMAT_NUM, 
    #     Card.COURTIER_NUM, Card.COURTIER_NUM,
    #     Card.GUARD_NUM, Card.GUARD_NUM, Card.GUARD_NUM, Card.GUARD_NUM, Card.GUARD_NUM,
    # ]

    def __init__(self):
        self._cards = copy.deepcopy(Deck.CANONICAL_DECK)

    def shuffle(self):
        random.shuffle(self._cards)

    def draw(self):
        if self.size() == 0:
            return None
        return self._cards.pop(0)

    def size(self):
        return len(self._cards)

class Game:
    def __init__(self, players_strategies):
        self._deck          = Deck()
        self._deck.shuffle()

        self._players       = []
        for n in range(len(players_strategies)):
            self._players.append(Player(self._deck.draw(), n, players_strategies[n]))

        self._burn_card      = self._deck.draw()

        self._losers         = []
        self._protected      = []
        self._log            = []
        self._current_player_is_out = False

    # Don't call unless is_game_over confirms the game is over.
    def winner(self):
        if not self.is_game_over():
            return None

        # If the deck is empty then whoever has the highest value card in their hand wins.
        if self._deck.size() == 0:
            winner = None
            winning_card = None
            max_card_num = 0
            # Figure out who had the highest value card at the end.
            for player in self._players:
                card = player.hand()[0]
                if card.number() > max_card_num:
                    max_card_num = card.number()
                    winning_card = card
                    winner = player
            self.log("Winner by best card in hand: Player " + str(winner.number()) + " with the " + winning_card.name() + "!")
            return winner

        # Assumption is the only other way to win is to be the last player standing.
        winner = self._players[0]
        self.log("Winner by elimination: Player " + str(winner.number()) + "!")
        return winner

    # Should only be called after a turn has ended, never during a turn. 
    def is_game_over(self):
        if self._deck.size() == 0:
            return True
        if len(self._players) == 1:
            return True
        return False

    def players(self):
        return self._players

    def log(self, text):
        self._log.append(text)
        print text

    def log_error(self, text):
        error_text = "ERROR: " + text
        self._log.append(error_text)
        print error_text

    def do_turn(self):
        current_player = self._players.pop(0)
        self._current_player = current_player
        self.log("Player " + str(current_player.number()) + "'s turn.")

        # Protection ends on the player's next turn.
        if current_player.number() in self._protected:
            self._protected.remove(current_player.number())
            self.log("Player " + str(current_player.number()) + "'s protection ended.")

        # Allow the current player to play.
        current_player.play(self)

        # If the current player was knocked out, clean that up here.
        if self._current_player_is_out:
            self._losers.append(current_player)
            self._current_player_is_out = False
        else:
            self._players.append(current_player)

        self._current_player = None
        self.log("Player " + str(current_player.number()) + "'s turn ended.")


    def lose(self, loser):
        self.log("Player " + str(loser.number()) + " is out.")
        for player in self._players:
            if player.number() == loser.number():
                self.log("Found a match for the loser: " + str(player.number()))
                self._players.remove(player)
                self._losers.append(player)
                return
        self._current_player_is_out = True 

    def deck(self):
        return self._deck

    def protect(self, player):
        self._protected.append(player.number())

    def available_targets(self, current_player):
        targets = [current_player]
        for player in self._players:
            if player.number() not in self._protected:
                targets.append(player)
        return targets 

    def guess(self, target, guess):
        for card in target.hand():
            if card.number() == guess:
                self.lose(target)

    def status(self):
        output = ("=== Game Status ===\n" +
                  "Players: ")

        for player in self._players:
            output += " " + str(player.number())
        output += "\n"

        for player in self._players:
            output += " " + str(player.number()) + ": "
            for card in player.hand():
                output += str(card)

            output += " Discard pile: ["
            for card in player.discard_pile():
                output += str(card) + " "
            output += "]\n"

        output += ("Deck size: " + str(self._deck.size()) + "\n" +
                   "=== End Status ===\n")

        return output

    def draw_burn_card(self):
        if self._burn_card is None:
            game.log_error("Tried to draw a burn card, but it had already been drawn!")
            return None

        card = self._burn_card
        self._burn_card = None
        return card

    def burn_card(self):
        return self._burn_card

    def player(self, number):
        for p in self._players:
            if number == p.number():
                return p
        if number == self._current_player.number():
            return self._current_player

        self.log_error("Tried to find a player, but got None!")
        return None

def play_game():
    game = Game([LowestDiscardStrategy(),
                BestGuessStrategy()])
    while not game.is_game_over():
        print game.status()
        game.do_turn()
    return game.winner()

win_tablulation = [0, 0, 0, 0]
for n in range(10000):
    print "===== Game Begin ====="
    winner = play_game()
    win_tablulation[winner.number()] += 1
    print "=====  Game End  ====="

print win_tablulation
