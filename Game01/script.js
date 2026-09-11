const COLS = 10;
const ROWS = 20;
const BLOCK_SIZE = 30;
const boardCanvas = document.querySelector('#game-board');
const nextCanvas = document.querySelector('#next-piece');
const boardContext = boardCanvas.getContext('2d');
const nextContext = nextCanvas.getContext('2d');
const scoreElement = document.querySelector('#score');
const linesElement = document.querySelector('#lines');
const levelElement = document.querySelector('#level');
const message = document.querySelector('#game-message');
const messageTitle = document.querySelector('#message-title');
const messageText = document.querySelector('#message-text');

const pieces = [
  { shape: [[1, 1, 1, 1]], color: '#27b8c5' },
  { shape: [[1, 1], [1, 1]], color: '#f0ba43' },
  { shape: [[0, 1, 0], [1, 1, 1]], color: '#a879d5' },
  { shape: [[1, 0, 0], [1, 1, 1]], color: '#e88b43' },
  { shape: [[0, 0, 1], [1, 1, 1]], color: '#4e7fd1' },
  { shape: [[0, 1, 1], [1, 1, 0]], color: '#63bd73' },
  { shape: [[1, 1, 0], [0, 1, 1]], color: '#df637f' }
];

let board;
let currentPiece;
let nextPiece;
let score = 0;
let lines = 0;
let level = 1;
let dropCounter = 0;
let lastTime = 0;
let dropInterval = 800;
let isPaused = false;
let isGameOver = false;

function createBoard() { return Array.from({ length: ROWS }, () => Array(COLS).fill(0)); }
function randomPiece() { const source = pieces[Math.floor(Math.random() * pieces.length)]; return { shape: source.shape.map(row => [...row]), color: source.color, x: 0, y: 0 }; }
function resetPiece(piece) { piece.x = Math.floor(COLS / 2) - Math.ceil(piece.shape[0].length / 2); piece.y = 0; }
function startGame() {
  board = createBoard(); score = 0; lines = 0; level = 1; dropInterval = 800; isPaused = false; isGameOver = false;
  currentPiece = randomPiece(); nextPiece = randomPiece(); resetPiece(currentPiece); message.classList.add('hidden'); updateStats(); drawNext();
}
function drawCell(context, x, y, color, size = BLOCK_SIZE) {
  context.fillStyle = color; context.fillRect(x * size, y * size, size, size);
  context.strokeStyle = 'rgba(23, 32, 38, .3)'; context.lineWidth = 2; context.strokeRect(x * size + 1, y * size + 1, size - 2, size - 2);
  context.fillStyle = 'rgba(255,255,255,.2)'; context.fillRect(x * size + 4, y * size + 4, size - 12, 4);
}
function drawMatrix(context, matrix, offset, color, size = BLOCK_SIZE) { matrix.forEach((row, y) => row.forEach((value, x) => { if (value) drawCell(context, x + offset.x, y + offset.y, color, size); })); }
function draw() {
  boardContext.fillStyle = '#202b31'; boardContext.fillRect(0, 0, boardCanvas.width, boardCanvas.height);
  boardContext.strokeStyle = 'rgba(255,255,255,.05)'; boardContext.lineWidth = 1;
  for (let x = 0; x <= COLS; x++) { boardContext.beginPath(); boardContext.moveTo(x * BLOCK_SIZE, 0); boardContext.lineTo(x * BLOCK_SIZE, boardCanvas.height); boardContext.stroke(); }
  for (let y = 0; y <= ROWS; y++) { boardContext.beginPath(); boardContext.moveTo(0, y * BLOCK_SIZE); boardContext.lineTo(boardCanvas.width, y * BLOCK_SIZE); boardContext.stroke(); }
  board.forEach((row, y) => row.forEach((color, x) => { if (color) drawCell(boardContext, x, y, color); }));
  if (currentPiece) drawMatrix(boardContext, currentPiece.shape, { x: currentPiece.x, y: currentPiece.y }, currentPiece.color);
}
function drawNext() {
  nextContext.fillStyle = '#f0eadf'; nextContext.fillRect(0, 0, nextCanvas.width, nextCanvas.height);
  const offset = { x: (4 - nextPiece.shape[0].length) / 2, y: (4 - nextPiece.shape.length) / 2 };
  drawMatrix(nextContext, nextPiece.shape, offset, nextPiece.color, 24);
}
function collides(piece) {
  return piece.shape.some((row, y) => row.some((value, x) => value && (piece.y + y >= ROWS || piece.x + x < 0 || piece.x + x >= COLS || board[piece.y + y][piece.x + x])));
}
function merge() { currentPiece.shape.forEach((row, y) => row.forEach((value, x) => { if (value) board[currentPiece.y + y][currentPiece.x + x] = currentPiece.color; })); }
function rotate(matrix) { return matrix[0].map((_, index) => matrix.map(row => row[index]).reverse()); }
function tryRotate() { const previous = currentPiece.shape; currentPiece.shape = rotate(currentPiece.shape); if (collides(currentPiece)) currentPiece.shape = previous; draw(); }
function move(direction) { currentPiece.x += direction; if (collides(currentPiece)) currentPiece.x -= direction; draw(); }
function drop() { currentPiece.y++; if (collides(currentPiece)) { currentPiece.y--; merge(); clearLines(); spawnPiece(); } dropCounter = 0; draw(); }
function hardDrop() { while (!collides(currentPiece)) currentPiece.y++; currentPiece.y--; drop(); }
function clearLines() {
  let cleared = 0;
  board = board.filter(row => { if (row.every(Boolean)) { cleared++; return false; } return true; });
  while (board.length < ROWS) board.unshift(Array(COLS).fill(0));
  if (cleared) { lines += cleared; score += [0, 100, 300, 500, 800][cleared] * level; level = Math.floor(lines / 10) + 1; dropInterval = Math.max(100, 800 - (level - 1) * 65); updateStats(); }
}
function spawnPiece() { currentPiece = nextPiece; nextPiece = randomPiece(); resetPiece(currentPiece); drawNext(); if (collides(currentPiece)) endGame(); }
function endGame() { isGameOver = true; messageTitle.textContent = '게임 오버'; messageText.textContent = `최종 점수 ${score.toLocaleString()}점. 다시 도전해 보세요.`; message.classList.remove('hidden'); }
function togglePause() { if (isGameOver) return; isPaused = !isPaused; messageTitle.textContent = '일시정지'; messageText.textContent = 'P 키 또는 버튼을 눌러 계속하세요.'; message.classList.toggle('hidden', !isPaused); document.querySelector('#pause-button').textContent = isPaused ? '계속하기' : '일시정지'; }
function updateStats() { scoreElement.textContent = score.toLocaleString(); linesElement.textContent = lines; levelElement.textContent = level; }
function update(time = 0) { const delta = time - lastTime; lastTime = time; if (!isPaused && !isGameOver) { dropCounter += delta; if (dropCounter > dropInterval) drop(); } draw(); requestAnimationFrame(update); }

window.addEventListener('keydown', event => {
  if (['ArrowLeft', 'ArrowRight', 'ArrowDown', 'ArrowUp', ' '].includes(event.key)) event.preventDefault();
  if (event.key === 'ArrowLeft') move(-1); else if (event.key === 'ArrowRight') move(1); else if (event.key === 'ArrowDown') drop(); else if (event.key === 'ArrowUp') tryRotate(); else if (event.key === ' ') hardDrop(); else if (event.key.toLowerCase() === 'p') togglePause();
});
document.querySelector('#restart-button').addEventListener('click', startGame);
document.querySelector('#restart-overlay').addEventListener('click', startGame);
document.querySelector('#pause-button').addEventListener('click', togglePause);
document.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => {
  const action = button.dataset.action;
  if (action === 'left') move(-1); if (action === 'right') move(1); if (action === 'rotate') tryRotate(); if (action === 'down') drop(); if (action === 'drop') hardDrop();
}));
startGame(); requestAnimationFrame(update);
