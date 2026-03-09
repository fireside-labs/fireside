// Game state
let currentPlayer = 'X';nconst cells = document.querySelectorAll('.cell');
let gameActive = true;
let board = ['', '', '', '', '', '', '', '', ''];
let scores = { X: 0, O: 0, draw: 0 };

// Winning combinations (rows, columns, diagonals)
const winningConditions = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8], // rows
    [0, 3, 6], [1, 4, 7], [2, 5, 8], // columns
    [0, 4, 8], [2, 4, 6]              // diagonals
];

// DOM elements
const status = document.getElementById('status');
const resetBtn = document.getElementById('resetBtn');
const scoreX = document.getElementById('scoreX');
const scoreO = document.getElementById('scoreO');
const scoreDraw = document.getElementById('scoreDraw');

// Handle cell click
function handleCellClick(event) {
    const cell = event.target;
    const index = cell.dataset.index;

    // Ignore if cell is taken or game is over
    if (board[index] !== '' || !gameActive) return;

    // Update board and cell
    board[index] = currentPlayer;
    cell.textContent = currentPlayer;
    cell.classList.add('taken', currentPlayer.toLowerCase());

    // Check for win or draw
    checkResult();

    // Switch player if game continues
    if (gameActive) {
        currentPlayer = currentPlayer === 'X' ? 'O' : 'X';
        status.textContent = `Player ${currentPlayer}'s turn`;
    }
}

// Check for win or draw
function checkResult() {
    let roundWon = false;
    let winningLine = null;

    // Check all winning conditions
    for (let i = 0; i < winningConditions.length; i++) {
        const [a, b, c] = winningConditions[i];
        if (board[a] && board[a] === board[b] && board[a] === board[c]) {
            roundWon = true;
            winningLine = [a, b, c];
            break;
        }
    }

    if (roundWon) {
        status.textContent = `🎉 Player ${currentPlayer} wins!`;
        gameActive = false;
        scores[currentPlayer]++;
        updateScoreboard();
        highlightWinningCells(winningLine);
        return;
    }

    // Check for draw
    if (!board.includes('')) {
        status.textContent = "🤝 It's a draw!";
        gameActive = false;
        scores.draw++;
        updateScoreboard();
        return;
    }
}

// Highlight winning cells
function highlightWinningCells(indices) {
    indices.forEach(index => {
        cells[index].classList.add('winning');
    });
}

// Update scoreboard display
function updateScoreboard() {
    scoreX.textContent = scores.X;
    scoreO.textContent = scores.O;
    scoreDraw.textContent = scores.draw;
}

// Reset the game
function resetGame() {
    board = ['', '', '', '', '', '', '', '', ''];
    gameActive = true;
    currentPlayer = 'X';
    status.textContent = "Player X's turn";

    cells.forEach(cell => {
        cell.textContent = '';
        cell.classList.remove('taken', 'x', 'o', 'winning');
    });
}

// Event listeners
cells.forEach(cell => cell.addEventListener('click', handleCellClick));
resetBtn.addEventListener('click', resetGame);
