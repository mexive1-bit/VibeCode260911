const questions = [
  { question: '웹 페이지의 구조를 만드는 언어는 무엇일까요?', answers: ['CSS', 'HTML', 'JavaScript', 'Python'], correct: 1, hint: '태그를 사용해 제목과 문단을 표현하는 언어예요.' },
  { question: 'CSS에서 글자 색상을 바꾸는 속성은 무엇일까요?', answers: ['font-size', 'display', 'color', 'padding'], correct: 2, hint: '정답! color는 글자와 같은 요소의 색을 정합니다.' },
  { question: '버튼 클릭 같은 사용자 행동을 처리하는 언어는 무엇일까요?', answers: ['HTML', 'CSS', 'JavaScript', 'SQL'], correct: 2, hint: '정답! JavaScript로 웹 페이지에 동작을 더할 수 있어요.' }
];
let questionIndex = 0;
let score = 0;
let selected = false;
const questionNumber = document.querySelector('#question-number');
const scoreLabel = document.querySelector('#score-label');
const progressBar = document.querySelector('#progress-bar');
const questionText = document.querySelector('#question-text');
const answerList = document.querySelector('#answer-list');
const feedback = document.querySelector('#feedback');
const nextButton = document.querySelector('#next-button');

function renderQuestion() {
  const current = questions[questionIndex];
  selected = false;
  questionNumber.textContent = `QUESTION ${questionIndex + 1} / ${questions.length}`;
  scoreLabel.textContent = `SCORE ${score}`;
  progressBar.style.width = `${((questionIndex + 1) / questions.length) * 100}%`;
  questionText.textContent = current.question;
  feedback.textContent = '';
  feedback.className = 'feedback';
  nextButton.disabled = true;
  nextButton.innerHTML = questionIndex === questions.length - 1 ? '결과 보기 <span>→</span>' : '다음 문제 <span>→</span>';
  answerList.innerHTML = current.answers.map((answer, index) => `<button class="answer-button" type="button" data-index="${index}">${String.fromCharCode(65 + index)}. ${answer}</button>`).join('');
  answerList.querySelectorAll('.answer-button').forEach(button => button.addEventListener('click', () => chooseAnswer(Number(button.dataset.index))));
}

function chooseAnswer(answerIndex) {
  if (selected) return;
  selected = true;
  const current = questions[questionIndex];
  const buttons = answerList.querySelectorAll('.answer-button');
  buttons[current.correct].classList.add('correct');
  if (answerIndex === current.correct) { score++; feedback.textContent = current.hint; } else { buttons[answerIndex].classList.add('wrong'); feedback.textContent = `아쉬워요. ${current.hint}`; feedback.classList.add('wrong-text'); }
  scoreLabel.textContent = `SCORE ${score}`;
  nextButton.disabled = false;
}

nextButton.addEventListener('click', () => { if (questionIndex < questions.length - 1) { questionIndex++; renderQuestion(); } else { questionText.textContent = `총 ${questions.length}문제 중 ${score}문제를 맞혔어요!`; answerList.innerHTML = '<p class="result-copy">HTML, CSS, JavaScript의 역할을 잘 기억하고 있네요.</p>'; feedback.textContent = '학습 페이지로 돌아가 더 연습해보세요.'; nextButton.textContent = '다시 풀기'; nextButton.onclick = () => { questionIndex = 0; score = 0; nextButton.onclick = null; renderQuestion(); }; } });
renderQuestion();