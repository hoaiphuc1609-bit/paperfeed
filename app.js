function isRecent(paper, maxAgeDays = 7) {
  if (!paper.publication_date_iso) return true;
  const date = new Date(paper.publication_date_iso);
  if (Number.isNaN(date.getTime())) return true;

  const now = new Date();
  const maxAgeMs = maxAgeDays * 24 * 60 * 60 * 1000;
  return now.getTime() - date.getTime() <= maxAgeMs;
}

function titleCaseTopic(topic) {
  return (topic || '')
    .split(' ')
    .map((word) => {
      if (!word) return word;
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(' ');
}

function buildTab(topic, activeTopic, onClick) {
  const button = document.createElement('button');
  button.className = `topic-tab${topic === activeTopic ? ' active' : ''}`;
  button.textContent = titleCaseTopic(topic);
  button.type = 'button';
  button.addEventListener('click', () => onClick(topic));
  return button;
}

function cleanText(value) {
  return (value || '').replace(/\s+/g, ' ').trim();
}

function sentenceSplit(text) {
  return cleanText(text)
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => sentence.trim())
    .filter(Boolean);
}

function firstMatch(sentences, patterns) {
  return sentences.find((sentence) => patterns.some((pattern) => pattern.test(sentence)));
}

function splitIntoBuckets(sentences) {
  if (!sentences.length) {
    return {
      objective: '',
      studyMethods: '',
      results: '',
      conclusion: '',
    };
  }

  const size = Math.ceil(sentences.length / 4);
  return {
    objective: sentences.slice(0, size).join(' '),
    studyMethods: sentences.slice(size, size * 2).join(' '),
    results: sentences.slice(size * 2, size * 3).join(' '),
    conclusion: sentences.slice(size * 3).join(' '),
  };
}

function buildStructuredAbstract(paper) {
  const sentences = sentenceSplit(paper.abstract);
  const buckets = splitIntoBuckets(sentences);

  const objectivePatterns = [/\baim(s|ed)?\b/i, /\bobjective(s)?\b/i, /\bpurpose\b/i, /\bthis study\b/i];
  const methodsPatterns = [/\bmethod(s)?\b/i, /\bretrospective\b/i, /\bprospective\b/i, /\brandomi[sz]ed\b/i, /\bcross[- ]sectional\b/i, /\bcohort\b/i];
  const resultsPatterns = [/\bresult(s)?\b/i, /\bfound\b/i, /\bshowed\b/i, /\bdemonstrated\b/i, /\bsignificant\b/i];
  const conclusionPatterns = [/\bconclusion(s)?\b/i, /\bconclude\b/i, /\bsuggest\b/i, /\bindicate\b/i, /\bhighlights?\b/i];

  const objective = cleanText(paper.objective) || firstMatch(sentences, objectivePatterns) || buckets.objective || sentences[0] || 'Not available in source abstract.';
  const studyMethods = cleanText(paper.study_methods || paper.methods) || firstMatch(sentences, methodsPatterns) || buckets.studyMethods || 'Not available in source abstract.';
  const results = cleanText(paper.results) || firstMatch(sentences, resultsPatterns) || buckets.results || 'Not available in source abstract.';
  const conclusion = cleanText(paper.conclusion) || firstMatch(sentences, conclusionPatterns) || buckets.conclusion || sentences[sentences.length - 1] || 'Not available in source abstract.';

  return { objective, studyMethods, results, conclusion };
}

function formatPublishedDate(paper) {
  const raw = cleanText(paper.publication_date);
  const iso = cleanText(paper.publication_date_iso);

  if (raw && iso) return `${raw} (${iso})`;
  if (raw) return raw;
  if (iso) return iso;
  return 'Unknown date';
}

function getPubMedUrl(paper) {
  if (paper.url && /^https?:\/\//.test(paper.url)) return paper.url;
  if (paper.pmid) return `https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}/`;
  return '#';
}

function renderFigures(cardNode, paper) {
  const figureUrls = Array.isArray(paper.figure_urls)
    ? paper.figure_urls.filter((url) => /^https?:\/\//.test(url))
    : [];

  if (!figureUrls.length) {
    return;
  }

  const figuresWrap = cardNode.querySelector('.figures-wrap');
  const figuresGrid = cardNode.querySelector('.figures-grid');
  const figuresLink = cardNode.querySelector('.figures-link');
  const pubmedUrl = getPubMedUrl(paper);

  figuresLink.href = pubmedUrl;

  figureUrls.forEach((url, index) => {
    const anchor = document.createElement('a');
    anchor.href = pubmedUrl;
    anchor.target = '_blank';
    anchor.rel = 'noopener noreferrer';
    anchor.className = 'figure-item';

    const img = document.createElement('img');
    img.src = url;
    img.alt = `Figure ${index + 1} for ${cleanText(paper.title) || 'paper'}`;
    img.loading = 'lazy';

    img.addEventListener('load', () => {
      figuresWrap.classList.remove('hidden');
    });

    img.addEventListener('error', () => {
      anchor.remove();
      if (!figuresGrid.children.length) {
        figuresWrap.classList.add('hidden');
      }
    });

    anchor.appendChild(img);
    figuresGrid.appendChild(anchor);
  });
}

function renderFeed(feed, template, papers) {
  feed.innerHTML = '';

  if (!papers.length) {
    feed.innerHTML = '<p class="empty">No recent papers for this topic today.</p>';
    return;
  }

  papers.forEach((paper, index) => {
    const node = template.content.cloneNode(true);
    const card = node.querySelector('.story-card');

    if (index === 0) card.classList.add('featured');

    node.querySelector('.title').textContent = cleanText(paper.title) || 'Untitled';
    node.querySelector('.authors').textContent = `Authors: ${paper.authors?.join(', ') || 'Unknown'}`;
    node.querySelector('.date').textContent = `Published: ${formatPublishedDate(paper)}`;

    const sections = buildStructuredAbstract(paper);
    node.querySelector('.objective').textContent = sections.objective;
    node.querySelector('.study-methods').textContent = sections.studyMethods;
    node.querySelector('.results').textContent = sections.results;
    node.querySelector('.conclusion').textContent = sections.conclusion;
    node.querySelector('.abstract-full').textContent = cleanText(paper.abstract) || 'No abstract available.';

    const limitations = cleanText(paper.limitations);
    if (limitations) {
      node.querySelector('.limitations').textContent = limitations;
      node.querySelector('.limitations-wrap').classList.remove('hidden');
    }

    const pubmedUrl = getPubMedUrl(paper);
    const link = node.querySelector('.link');
    link.href = pubmedUrl;

    renderFigures(node, paper);

    feed.appendChild(node);
  });
}

async function loadFeed() {
  const feed = document.getElementById('feed');
  const tabs = document.getElementById('topic-tabs');
  const lastUpdated = document.getElementById('last-updated');
  const template = document.getElementById('paper-template');

  try {
    const res = await fetch('data/papers.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('Could not load data');

    const payload = await res.json();
    const allPapers = (payload.papers || []).filter((paper) => isRecent(paper, 7));
    const topics = payload.topics || [];

    lastUpdated.textContent = `Last updated: ${new Date(payload.updated_at).toLocaleString()}`;

    if (!topics.length) {
      renderFeed(feed, template, allPapers);
      return;
    }

    let activeTopic = topics[0];

    const renderTabsAndFeed = () => {
      tabs.innerHTML = '';

      topics.forEach((topic) => {
        const tab = buildTab(topic, activeTopic, (selected) => {
          activeTopic = selected;
          renderTabsAndFeed();
        });
        tabs.appendChild(tab);
      });

      const topicPapers = allPapers.filter((paper) => (paper.topics || []).includes(activeTopic));
      renderFeed(feed, template, topicPapers);
    };

    renderTabsAndFeed();
  } catch (err) {
    feed.innerHTML = `<p class="empty">Failed to load paper feed: ${err.message}</p>`;
  }
}

loadFeed();
