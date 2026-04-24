const poems = [
  {
    id: "dickinson-hope",
    title: "Hope is the thing with feathers",
    author: "Emily Dickinson",
    text: `"Hope" is the thing with feathers -\nThat perches in the soul -\nAnd sings the tune without the words -\nAnd never stops - at all -\n\nAnd sweetest - in the Gale - is heard -\nAnd sore must be the storm -\nThat could abash the little Bird\nThat kept so many warm -\n\nI've heard it in the chillest land -\nAnd on the strangest Sea -\nYet - never - in Extremity,\nIt asked a crumb - of me.`,
    tags: ["hope", "resilience", "nature", "short"],
  },
  {
    id: "blake-tyger",
    title: "The Tyger",
    author: "William Blake",
    text: `Tyger Tyger, burning bright,\nIn the forests of the night;\nWhat immortal hand or eye,\nCould frame thy fearful symmetry?\n\nIn what distant deeps or skies.\nBurnt the fire of thine eyes?\nOn what wings dare he aspire?\nWhat the hand, dare seize the fire?`,
    tags: ["awe", "creation", "mystery", "rhythmic"],
  },
  {
    id: "rossetti-remember",
    title: "Remember",
    author: "Christina Rossetti",
    text: `Remember me when I am gone away,\nGone far away into the silent land;\nWhen you can no more hold me by the hand,\nNor I half turn to go yet turning stay.\nRemember me when no more day by day\nYou tell me of our future that you plann'd:\nOnly remember me; you understand\nIt will be late to counsel then or pray.`,
    tags: ["memory", "grief", "love", "sonnet"],
  },
  {
    id: "wordsworth-daffodils",
    title: "I Wandered Lonely as a Cloud",
    author: "William Wordsworth",
    text: `I wandered lonely as a cloud\nThat floats on high o'er vales and hills,\nWhen all at once I saw a crowd,\nA host, of golden daffodils;\nBeside the lake, beneath the trees,\nFluttering and dancing in the breeze.`,
    tags: ["nature", "joy", "memory", "lyrical"],
  },
  {
    id: "keats-bright-star",
    title: "Bright Star",
    author: "John Keats",
    text: `Bright star, would I were stedfast as thou art -\nNot in lone splendour hung aloft the night\nAnd watching, with eternal lids apart,\nLike nature's patient, sleepless Eremite,\nThe moving waters at their priestlike task\nOf pure ablution round earth's human shores,`,
    tags: ["love", "constancy", "night", "sonnet"],
  },
  {
    id: "shelley-mutability",
    title: "Mutability",
    author: "Percy Bysshe Shelley",
    text: `We are as clouds that veil the midnight moon;\nHow restlessly they speed, and gleam, and quiver,\nStreaking the darkness radiantly! yet soon\nNight closes round, and they are lost for ever:\n\nOr like forgotten lyres, whose dissonant strings\nGive various response to each varying blast,`,
    tags: ["change", "time", "melancholy", "philosophical"],
  },
  {
    id: "shakespeare-sonnet-18",
    title: "Sonnet 18",
    author: "William Shakespeare",
    text: `Shall I compare thee to a summer's day?\nThou art more lovely and more temperate:\nRough winds do shake the darling buds of May,\nAnd summer's lease hath all too short a date;\nSometime too hot the eye of heaven shines,\nAnd often is his gold complexion dimm'd;`,
    tags: ["love", "beauty", "summer", "sonnet"],
  },
  {
    id: "whitman-miracles",
    title: "Miracles",
    author: "Walt Whitman",
    text: `Why, who makes much of a miracle?\nAs to me I know of nothing else but miracles,\nWhether I walk the streets of Manhattan,\nOr dart my sight over the roofs of houses toward the sky,\nOr wade with naked feet along the beach just in the edge of the water,`,
    tags: ["wonder", "city", "nature", "expansive"],
  },
];

const stateKey = "poetry-tok-state-v1";
const state = loadState();
let currentPoem = chooseNextPoem();

const titleEl = document.querySelector("#poem-title");
const authorEl = document.querySelector("#poem-author");
const positionEl = document.querySelector("#poem-position");
const textEl = document.querySelector("#poem-text");
const likeButton = document.querySelector("#like-button");
const dislikeButton = document.querySelector("#dislike-button");
const nextButton = document.querySelector("#next-button");
const likedCountEl = document.querySelector("#liked-count");
const dislikedCountEl = document.querySelector("#disliked-count");
const seenCountEl = document.querySelector("#seen-count");
const tagCloudEl = document.querySelector("#tag-cloud");

render();

likeButton.addEventListener("click", () => rateCurrentPoem("liked"));
dislikeButton.addEventListener("click", () => rateCurrentPoem("disliked"));
nextButton.addEventListener("click", nextPoem);

window.addEventListener("keydown", (event) => {
  if (event.key === "ArrowDown" || event.key.toLowerCase() === "j") nextPoem();
  if (event.key.toLowerCase() === "l") rateCurrentPoem("liked");
  if (event.key.toLowerCase() === "d") rateCurrentPoem("disliked");
});

let touchStartY = null;
window.addEventListener("touchstart", (event) => {
  touchStartY = event.touches[0]?.clientY ?? null;
});
window.addEventListener("touchend", (event) => {
  if (touchStartY === null) return;
  const endY = event.changedTouches[0]?.clientY ?? touchStartY;
  if (touchStartY - endY > 70) nextPoem();
  touchStartY = null;
});

function loadState() {
  const fallback = { liked: [], disliked: [], seen: [] };
  try {
    return { ...fallback, ...JSON.parse(localStorage.getItem(stateKey)) };
  } catch {
    return fallback;
  }
}

function saveState() {
  localStorage.setItem(stateKey, JSON.stringify(state));
}

function render() {
  const index = poems.findIndex((poem) => poem.id === currentPoem.id);
  titleEl.textContent = currentPoem.title;
  authorEl.textContent = currentPoem.author;
  positionEl.textContent = `${index + 1} / ${poems.length}`;
  textEl.textContent = currentPoem.text;

  likeButton.setAttribute("aria-pressed", String(state.liked.includes(currentPoem.id)));
  dislikeButton.setAttribute("aria-pressed", String(state.disliked.includes(currentPoem.id)));
  likedCountEl.textContent = state.liked.length;
  dislikedCountEl.textContent = state.disliked.length;
  seenCountEl.textContent = state.seen.length;

  const topTags = getPreferenceTags().slice(0, 8);
  tagCloudEl.innerHTML = "";
  for (const tag of topTags) {
    const tagEl = document.createElement("span");
    tagEl.className = "tag";
    tagEl.textContent = tag;
    tagCloudEl.append(tagEl);
  }
}

function rateCurrentPoem(rating) {
  removeValue(state.liked, currentPoem.id);
  removeValue(state.disliked, currentPoem.id);
  state[rating].push(currentPoem.id);
  markSeen(currentPoem.id);
  saveState();
  nextPoem();
}

function nextPoem() {
  markSeen(currentPoem.id);
  currentPoem = chooseNextPoem();
  saveState();
  render();
}

function markSeen(poemId) {
  if (!state.seen.includes(poemId)) state.seen.push(poemId);
}

function chooseNextPoem() {
  const unseen = poems.filter((poem) => !state.seen.includes(poem.id));
  const candidates = unseen.length ? unseen : poems;
  const scored = candidates
    .map((poem) => ({ poem, score: scorePoem(poem) + Math.random() * 0.35 }))
    .sort((a, b) => b.score - a.score);
  return scored[0].poem;
}

function scorePoem(poem) {
  const likedTags = tagsFor(state.liked);
  const dislikedTags = tagsFor(state.disliked);
  const tagScore = poem.tags.reduce((score, tag) => {
    return score + (likedTags.get(tag) ?? 0) - (dislikedTags.get(tag) ?? 0) * 0.75;
  }, 0);
  const authorBoost = state.liked.some((id) => getPoem(id)?.author === poem.author) ? 0.7 : 0;
  const authorPenalty = state.disliked.some((id) => getPoem(id)?.author === poem.author) ? -0.35 : 0;
  return tagScore + authorBoost + authorPenalty;
}

function tagsFor(poemIds) {
  const tags = new Map();
  for (const poemId of poemIds) {
    for (const tag of getPoem(poemId)?.tags ?? []) {
      tags.set(tag, (tags.get(tag) ?? 0) + 1);
    }
  }
  return tags;
}

function getPreferenceTags() {
  return [...tagsFor(state.liked)]
    .sort((a, b) => b[1] - a[1])
    .map(([tag]) => tag);
}

function getPoem(poemId) {
  return poems.find((poem) => poem.id === poemId);
}

function removeValue(values, value) {
  const index = values.indexOf(value);
  if (index >= 0) values.splice(index, 1);
}
