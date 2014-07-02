import random

random.seed()

class Strategy(object):
    def __init__(self):
        self._last_seen_hand = None

    def look_at(self, target):
        self._last_seen_hand = {
                    'target' : target.number,
                    'hand'   : target.hand_value()
                }

class RandomStrategy(Strategy):
    def play(self, player, game):
        hand            = player.hand()
        card_to_play    = random.randrange(0, len(hand), 1) 
        card            = hand[card_to_play]

        random_target   = random.choice(game.players()) 
        random_guess    = random.randrange(1, 8, 1)

        # The player discards the card before it takes effect.
        player._discard(game, card)

        game.log("RandomStrategy: Player " + str(player.number()) + " discarded the " + card.name() + ", target: " + str(random_target.number()) + 
                 ", guess: " + str(random_guess) + ".") 

        # This actually applies the effect of the card.
        card.discard(game   = game, 
                     player = player, 
                     target = random_target,
                     guess  = random_guess)

class Player(object):
    def __init__(self, card, number, strategy):
        self._hand = [card]
        self._discard_pile = []
        self._number = number
        self._strat  = strategy

    def play(self, game):
        drawn_card = game.deck().draw()
        self._hand.append(drawn_card)
        game.log("Player " + str(self._number) + " drew the " + drawn_card.name() + ".")
        game.log("Player " + str(self._number) + "'s hand: " + str(self._hand))

        numbers = []
        for card in self._hand:
            numbers.append(card.number())

        # Sensei must be discarded if Manipulator or Hatamoto is in the player's hand.
        if ((6 in numbers or 5 in numbers) and
            7 in numbers):
            for card in self._hand:
                if card.number() == 7:
                    self._discard(card)
                    return

        self._strat.play(self, game)

    def hand_value(self):
        return self._hand[0].number()

    def _discard(self, game, card):
        self._hand.remove(card)
        self._discard_pile.append(card)
        game.log("Player " + str(self.number()) + " discarded the " + card.name() + " card.")

    def discard_hand(self, game):
        self._discard(game, self._hand[0])
        game.log("Player " + str(self.number()) + " drew a card after discarding their hand.")
        self._hand.append(game.deck().draw())

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
    def discard(self, game, player, target, guess):
        pass

    def number(self):
        return self._number

    def name(self):
        return self._name

    def __eq__(self, other):
        return self.number() == other.number()

class Princess(Card):
    def __init__(self):
        self._number = 8
        self._name   = "Princess"

    def discard(self, game, player, target, guess):
        game.lose(player)

class Sensei(Card):
    def __init__(self):
        self._number = 7
        self._name   = "Sensei"

    def discard(self, game, player, target, guess):
        pass

class Manipulator(Card):
    def __init__(self):
        self._number = 6
        self._name   = "Manipulator"

    def discard(self, game, player, target, guess):
        player.trade(target)

class Hatamoto(Card):
    def __init__(self):
        self._number = 5
        self._name   = "Hatamoto"

    def discard(self, game, player, target, guess):
        target.discard_hand(game)

class Shugenja(Card):
    def __init__(self):
        self._number = 4
        self._name   = "Shugenja"

    def discard(self, game, player, target, guess):
        game.protect(player)

class Diplomat(Card):
    def __init__(self):
        self._number = 3
        self._name   = "Diplomat"

    def discard(self, game, player, target, guess):
        if player.hand_value() > target.hand_value(): 
            game.lose(target)
        elif target.hand_value() > player.hand_value():
            game.lose(player)

class Coutier(Card):
    def __init__(self):
        self._number = 2
        self._name   = "Coutier"

    def discard(self, game, player, target, guess):
        player.look_at(target)
        game.log("Player " + str(player.number()) + " looked at " + str(target.number()) + "'s hand.")

class Guard(Card):
    def __init__(self):
        self._number = 1
        self._name   = "Guard"

    def discard(self, game, player, target, guess):
        game.guess(target, guess)

class Deck:
    def __init__(self):
        self._cards = [
                    Princess(),
                    Sensei(),
                    Manipulator(),
                    Hatamoto(), Hatamoto(),
                    Shugenja(), Shugenja(),
                    Diplomat(), Diplomat(),
                    Coutier(),  Coutier(),
                    Guard(), Guard(), Guard(), Guard(), Guard()
                ]

    def shuffle(self):
        random.shuffle(self._cards)

    def draw(self):
        if self.size() == 0:
            return None
        return self._cards.pop(0)

    def size(self):
        return len(self._cards)

class Game:
    def __init__(self, num_players = 2):
        self._deck          = Deck()
        self._deck.shuffle()

        self._players       = []
        for n in range(num_players):
            self._players.append(Player(self._deck.draw(), n, RandomStrategy()))

        self._burn_card      = self._deck.draw()

        self._losers         = []
        self._protected      = []
        self._log            = []

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

    def do_turn(self):
        current_player = self._players.pop(0)
        self.log("Player " + str(current_player.number()) + "'s turn.")

        # Protection ends on the player's next turn.
        if current_player.number() in self._protected:
            self._protected.remove(current_player.number())
            self.log("Player " + str(current_player.number()) + "'s protection ended.")

        # Allow the current player to play.
        current_player.play(self)
        self._players.append(current_player)
        self.log("Player " + str(current_player.number()) + "'s turn ended.")

    def lose(self, loser):
        self.log("Player " + str(loser.number()) + " is out.")
        for player in self._players:
            if player.number() == loser.number():
                self._players.remove(player)
                self._losers.append(player)
                return

    def deck(self):
        return self._deck

    def protect(self, player):
        self._protected.append(player.number())

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

        output += ("Deck size: " + str(self._deck.size()) + "\n" +
                   "=== End Status ===\n")

        return output

def play_game():
    game = Game(num_players = 4)
    while not game.is_game_over():
        print game.status()
        game.do_turn()

    winner = game.winner()

play_game()
