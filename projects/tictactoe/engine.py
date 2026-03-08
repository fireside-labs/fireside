"""Tic-Tac-Toe Game Engine with AI Opponent

A complete implementation including:
- Board class with move validation and win/draw detection
- Minimax AI opponent (unbeatable)
- Random AI fallback
- Two-player human mode
"""

from enum import Enum
from typing import List, Optional, Tuple
import random
import math

class Player(Enum):
    """Game players."""
    X = "X"
    O = "O"
    EMPTY = " "

class Board:
    """Represents the 3x3 game board."""
    
    WINNING_COMBINATIONS: List[List[Tuple[int, int]]] = [
        [(0, 0), (0, 1), (0, 2)],  # Row 0
        [(1, 0), (1, 1), (1, 2)],  # Row 1
        [(2, 0), (2, 1), (2, 2)],  # Row 2
        [(0, 0), (1, 0), (2, 0)],  # Column 0
        [(0, 1), (1, 1), (2, 1)],  # Column 1
        [(0, 2), (1, 2), (2, 2)],  # Column 2
        [(0, 0), (1, 1), (2, 2)],  # Diagonal \n        [(0, 2), (1, 1), (2, 0)],  # Diagonal /
    ]
    
    def __init__(self):
        """Initialize empty board."""
        self._grid: List[List[Player]] = [
            [Player.EMPTY, Player.EMPTY, Player.EMPTY],
            [Player.EMPTY, Player.EMPTY, Player.EMPTY],
            [Player.EMPTY, Player.EMPTY, Player.EMPTY]
        ]
        self._move_count: int = 0
    
    def get(self, row: int, col: int) -> Player:
        """Get player at position."""
        return self._grid[row][col]
    
    def is_valid_move(self, row: int, col: int) -> bool:
        """Check if move location is valid and empty."""
        return (0 <= row < 3 and 0 <= col < 3 and 
                self._grid[row][col] == Player.EMPTY)
    
    def make_move(self, row: int, col: int, player: Player) -> bool:
        """Make a move. Returns True if successful."""
        if not self.is_valid_move(row, col):
            return False
        
        self._grid[row][col] = player
        self._move_count += 1
        return True
    
    def get_valid_moves(self) -> List[Tuple[int, int]]:
        """Return list of valid (row, col) moves."""
        return [
            (r, c) for r in range(3) for c in range(3)
            if self._grid[r][c] == Player.EMPTY
        ]
    
    def is_full(self) -> bool:
        """Check if board has no empty cells."""
        return self._move_count == 9
    
    def check_win(self, player: Player) -> bool:
        """Check if player has winning line."""
        for combo in self.WINNING_COMBINATIONS:
            if all(self._grid[r][c] == player for r, c in combo):
                return True
        return False
    
    def get_winner(self) -> Optional[Player]:
        """Return winner or None if no winner yet."""
        for player in [Player.X, Player.O]:
            if self.check_win(player):
                return player
        return None
    
    def is_game_over(self) -> bool:
        """Return True if game has ended (win or draw)."""
        return self.get_winner() is not None or self.is_full()
    
    def copy(self) -> 'Board':
        """Create deep copy of board."""
        new_board = Board()
        new_board._grid = [row[:] for row in self._grid]
        new_board._move_count = self._move_count
        return new_board
    
    def __str__(self) -> str:
        """String representation for terminal display."""
        lines = []
        for row in self._grid:
            lines.append(" | ".join(cell.value for cell in row))
            lines.append("-" * 5)
        return "\n".join(lines).rstrip("-\n") + "\n"


class TicTacToeAI:
    """AI opponent with minimax algorithm."""
    
    def __init__(self, player: Player, mode: str = "minimax"):
        self.player = player
        self.opponent = Player.O if player == Player.X else Player.X
        self.mode = mode  # 'minimax' or 'random'
    
    def get_best_move(self, board: Board) -> Tuple[int, int]:
        """Get best move based on current mode."""
        valid_moves = board.get_valid_moves()
        
        if not valid_moves:
            raise ValueError("No moves available")
        
        if self.mode == 'random':
            return random.choice(valid_moves)
        else:  # minimax
            best_score = -math.inf
            best_move = valid_moves[0]
            
            for row, col in valid_moves:
                board.make_move(row, col, self.player)
                score = self._minimax(board, 0, False)
                board.make_move(row, col, Player.EMPTY)  # Undo
                
                if score > best_score:
                    best_score = score
                    best_move = (row, col)
            
            return best_move
    
    def _minimax(self, board: Board, depth: int, is_maximizing: bool) -> float:
        """Minimax algorithm with alpha-beta pruning."""
        winner = board.get_winner()
        
        if winner == self.player:
            return 10 - depth
        elif winner == self.opponent:
            return depth - 10
        elif board.is_full():
            return 0
        
        if is_maximizing:
            best_score = -math.inf
            for row, col in board.get_valid_moves():
                board.make_move(row, col, self.player)
                score = self._minimax(board, depth + 1, False)
                board.make_move(row, col, Player.EMPTY)
                best_score = max(best_score, score)
            return best_score
        else:
            best_score = math.inf
            for row, col in board.get_valid_moves():
                board.make_move(row, col, self.opponent)
                score = self._minimax(board, depth + 1, True)
                board.make_move(row, col, Player.EMPTY)
                best_score = min(best_score, score)
            return best_score


class Game:
    """Main game controller."""
    
    def __init__(self, player1: str, player2: str,
                 p1_type: Optional[str] = None, p2_type: Optional[str] = None):
        """Initialize game with two players.
        
        Args:
            player1: Name of player 1 (X)
            player2: Name of player 2 (O)
            p1_type: 'human' or 'ai'
            p2_type: 'human' or 'ai'
        """
        self.board = Board()
        self.players = [
            {'name': player1, 'player': Player.X},
            {'name': player2, 'player': Player.O}
        ]
        self.player_types = [p1_type or 'human', p2_type or 'human']
        self.current_player_idx = 0
    
    def get_ai_move(self, player_idx: int) -> Tuple[int, int]:
        """Get AI move for specified player."""
        ai = TicTacToeAI(
            self.players[player_idx]['player'],
            mode='minimax'
        )
        return ai.get_best_move(self.board)
    
    def get_human_move(self, player_name: str) -> Tuple[int, int]:
        """Get and validate human move input."""
        while True:
            print(f"\n{player_name}'s turn (X or O):")
            print(self.board)
            
            try:
                row = int(input("Row (0-2): "))
                col = int(input("Col (0-2): "))
                
                if not self.board.is_valid_move(row, col):
                    print("Invalid move! Try again.")
                    continue
                
                return (row, col)
            except ValueError:
                print("Please enter numeric values (0-2).")
            except KeyboardInterrupt:
                print("\nGame interrupted.")
                raise SystemExit(0)
    
    def play(self) -> None:
        """Run the game loop."""
        try:
            while not self.board.is_game_over():
                player_info = self.players[self.current_player_idx]
                player_name = player_info['name']
                player_type = self.player_types[self.current_player_idx]
                
                if player_type == 'ai':
                    print(f"\n{player_name} is thinking...")
                    row, col = self.get_ai_move(self.current_player_idx)
                else:
                    row, col = self.get_human_move(player_name)
                
                self.board.make_move(row, col, player_info['player'])
                
                winner = self.board.get_winner()
                if winner:
                    print(f"\n{self.board}\n{player_name} wins!")
                    return
                
                if self.board.is_full():
                    print(f"\n{self.board}\nIt's a draw!")
                    return
                
                self.current_player_idx = 1 - self.current_player_idx
                
        except KeyboardInterrupt:
            print("\n\nGame interrupted.")
            raise SystemExit(0)


def play_tournament(num_games: int = 3) -> None:
    """Run a tournament between AI and human."""
    scores = {'AI': 0, 'Human': 0, 'Draws': 0}
    
    print("Tic-Tac-Toe Tournament\n")
    print("=" * 40)
    
    for game_num in range(num_games):
        print(f"\nGame {game_num + 1}/{num_games}")
        ai = TicTacToeAI(Player.X, mode='minimax')
        human = Game('Human', 'AI', p1_type='human', p2_type='ai')
        human.board = Board()  # Reset board
        
        while not human.board.is_game_over():
            # AI's turn (minimax)
            row, col = ai.get_best_move(human.board)
            human.board.make_move(row, col, Player.X)
            
            if human.board.get_winner():
                print(f"\n{human.board}\nAI wins!")
                scores['AI'] += 1
                break
            
            if human.board.is_full():
                print(f"\n{human.board}\nIt's a draw!")
                scores['Draws'] += 1
                break
            
            # Human's turn
            row, col = human.get_human_move('Human')
            human.board.make_move(row, col, Player.O)
            
            if human.board.get_winner():
                print(f"\n{human.board}\nHuman wins!")
                scores['Human'] += 1
                break
            
            if human.board.is_full():
                print(f"\n{human.board}\nIt's a draw!")
                scores['Draws'] += 1
                break
    
    print("\n" + "=" * 40)
    print("\nTournament Results:")
    for category, count in scores.items():
        print(f"  {category}: {count}")
    print("=" * 40)


if __name__ == "__main__":
    print("=" * 40)
    print("TIC-TAC-TOE GAME ENGINE")
    print("=" * 40)
    
    print("\nGame Modes:")
    print("1. Two Human Players (PvP)")
    print("2. AI vs Human (You play as O, go second)")
    print("3. Tournament: Play multiple games against unbeatable AI")
    
    while True:
        try:
            choice = input("\nSelect mode (1-3): ").strip()
            if choice in ['1', '2', '3']:
                break
            print("Invalid choice. Enter 1, 2, or 3.")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            raise SystemExit(0)
    
    if choice == '1':
        p1 = input("Player 1 name (X): ").strip() or "Player 1"
        p2 = input("Player 2 name (O): ").strip() or "Player 2"
        game = Game(p1, p2)
        print(f"\n{p1} starts first! Press Ctrl+C to quit.")
    elif choice == '2':
        p1 = input("Your name: ").strip() or "You"
        game = Game("AI", p1, p1_type='ai', p2_type='human')
        print(f"\nYou play as O and will go second.")
    else:  # choice == '3'
        num_games = 5
        try:
            input_num = input("Number of games (default 5): ").strip()
            if input_num:
                num_games = int(input_num)
        except ValueError:
            pass
        print(f"\nStarting tournament: {num_games} game(s) against unbeatable AI")
        play_tournament(num_games)
        raise SystemExit(0)
    
    try:
        game.play()
    except SystemExit:
        pass
    finally:
        print("\nThank you for playing!")
