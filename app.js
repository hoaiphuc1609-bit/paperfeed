function isRecent(paper, maxAgeDays = 7) {
  if (!paper.publication_date_iso) return true;
  const date = new Date(paper.publication_date_iso);
  if (Number.isNaN(date.getTime())) return true;

  const now = new Date();
  const maxAgeMs = maxAgeDays * 24 * 60 * 60 * 1000;
  return now.getTime() - date.getTime() <= maxAgeMs;
}

function buildTab(topic, activeTopic, onClick) {
  const button = document.createElement('button');
  button.className = `topic-tab${topic === activeTopic ? ' active' : ''}`;
  button.textContent = topic;
  button.type = 'button';
  button.addEventListener('click', () => onClick(topic));
  return button;
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

    if (index === 0) {
      card.classList.add('featured');
    }

    node.querySelector('.title').textContent = paper.title || 'Untitled';
    node.querySelector('.authors').textContent = `Authors: ${paper.authors?.join(', ') || 'Unknown'}`;
    node.querySelector('.date').textContent = `Published: ${paper.publication_date || 'Unknown date'}`;
    node.querySelector('.abstract').textContent = paper.abstract || 'No abstract available.';

    if (paper.methods) {
      node.querySelector('.methods').textContent = paper.methods;
      node.querySelector('.methods-wrap').classList.remove('hidden');
    }

    if (paper.limitations) {
      node.querySelector('.limitations').textContent = paper.limitations;
      node.querySelector('.limitations-wrap').classList.remove('hidden');
    }

    const link = node.querySelector('.link');
    link.href = paper.url || '#';

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
