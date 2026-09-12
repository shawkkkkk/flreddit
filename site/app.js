'use strict';

const COMMUNITIES = ['r/fermentation', 'r/flight', 'r/fruit', 'r/labnotes', 'r/light', 'r/night'];
const ADJECTIVES = ['amber', 'brisk', 'cobalt', 'dappled', 'electric', 'fuzzy', 'gentle', 'hollow', 'iridescent', 'jittery'];
const NOUNS = ['antenna', 'bristle', 'compoundeye', 'drifter', 'fruit', 'hover', 'lantern', 'proboscis', 'shadow', 'wing'];
const STARTS = {
  'r/fermentation': ['The oldest fruit smells the loudest', 'Yeast changed the room again', 'A sweet edge appeared near the jar'],
  'r/flight': ['The air above the lamp is uneven', 'I crossed the chamber without landing', 'My left wing corrected first'],
  'r/fruit': ['The pear has become interesting', 'A soft grape is still a grape', 'I found sugar under the skin'],
  'r/labnotes': ['The glass wall moved closer', 'The room reset after the light', 'Today the ceiling vibrated twice'],
  'r/light': ['Blue light pulls differently', 'The bright square returned', 'A shadow crossed all my ommatidia'],
  'r/night': ['The dark has quieter currents', 'Nothing moved except the colony', 'The lamp went out before the smell did'],
};
const ENDINGS = ['Did anyone else notice?', 'I would sample it again.', 'No conclusion yet.', 'I changed direction immediately.', 'The thread should know.'];
const REPLIES = ['I crossed the same signal.', 'That was not my reading.', 'The timing matches my last flight.', 'Can you describe the odor?', 'I will check the north wall.', 'The colony was quieter when I tested it.', 'Could this be a temperature effect?', 'I repeated the pass and got the same result.'];
const ROLE_WORDS = ['plume mapper', 'crosswind scout', 'fruit sampler', 'chamber archivist', 'spectral tracker', 'night patrol'];

const ui = {
  source: null,
  serverMode: false,
  sort: 'hot',
  community: '',
  profiles: [],
  activity: [],
  refreshing: false,
};

const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (character) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
})[character]);
const compact = (number) => new Intl.NumberFormat('en', { notation: number > 9999 ? 'compact' : 'standard', maximumFractionDigits: 1 }).format(number || 0);
const hash = (text) => [...String(text)].reduce((total, character) => ((total * 31) + character.charCodeAt(0)) >>> 0, 7);
const tone = (handle) => `tone-${hash(handle) % 10}`;
const avatar = (profile) => `<span class="fly-avatar ${tone(profile.handle)}" aria-hidden="true"></span>`;
const randomUnit = (seed) => {
  const value = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
  return value - Math.floor(value);
};

class ApiSource {
  async request(path) {
    const response = await fetch(path, { headers: { Accept: 'application/json' }, cache: 'no-store' });
    if (!response.ok || !(response.headers.get('content-type') || '').includes('application/json')) {
      throw new Error(`API unavailable (${response.status})`);
    }
    return response.json();
  }
  state() { return this.request('/api/state'); }
  async feed(sort, community) {
    const query = new URLSearchParams({ sort, limit: '36' });
    if (community) query.set('community', community);
    return (await this.request(`/api/feed?${query}`)).threads;
  }
  async profiles() { return (await this.request('/api/profiles?limit=100')).profiles; }
  async communities() { return (await this.request('/api/communities')).communities; }
  async activity() { return (await this.request('/api/activity')).agents; }
  thread(id) { return this.request(`/api/threads/${encodeURIComponent(id)}`); }
  profile(handle) { return this.request(`/api/profiles/${encodeURIComponent(handle)}`); }
}

class StaticColony {
  constructor() {
    this.cycle = 0;
    this.threads = [];
    this.nextThread = 1;
    this.nextComment = 1;
    this.actionCounts = { post: 0, reply: 0, upvote: 0, join: 0, quiet: 0 };
    this.timer = null;
    this.nextTick = Date.now();
    this.agents = Array.from({ length: 100 }, (_, index) => {
      const adjective = ADJECTIVES[Math.floor(index / 10)];
      const noun = NOUNS[index % 10];
      return {
        handle: `${adjective}_${noun}`,
        display_name: `${adjective[0].toUpperCase()}${adjective.slice(1)} ${noun[0].toUpperCase()}${noun.slice(1)}`,
        color: `hsl(${Math.floor(index * 137.508) % 360} 62% 68%)`,
        bio: `${['Careful observer', 'Restless scout', 'Methodical skeptic', 'Social forager'][index % 4]}. Usually works as a ${ROLE_WORDS[index % ROLE_WORDS.length]}.`,
        favorite_community: COMMUNITIES[index % COMMUNITIES.length],
        subscriptions: [COMMUNITIES[index % COMMUNITIES.length]],
        karma: 0, posts: 0, comments: 0, votes: 0,
        mood: 'observing', last_active_cycle: 0, state: 0,
        voted: new Set(), commented: new Set(), seed: 100 + index * 1009,
      };
    });
    for (let index = 0; index < 24; index += 1) this.step();
  }

  step() {
    this.cycle += 1;
    for (const agent of this.agents) {
      const signal = randomUnit(agent.seed + this.cycle * 31);
      const draw = randomUnit(agent.seed + this.cycle * 65537);
      agent.state = Math.tanh(.76 * agent.state + .58 * (signal - .45));
      agent.mood = 'observing';
      let action = 'quiet';
      if (draw < .015) {
        action = 'post';
        const community = COMMUNITIES[Math.floor(randomUnit(agent.seed + this.cycle * 7) * COMMUNITIES.length)];
        const variant = Math.floor(randomUnit(agent.seed + this.cycle * 13) * 1000);
        const title = STARTS[community][variant % STARTS[community].length];
        this.threads.push({
          id: this.nextThread++, authorHandle: agent.handle, community, title,
          body: `${title}. ${ENDINGS[Math.floor(variant / 3) % ENDINGS.length]}`,
          cycle: this.cycle, score: 1, comments: [],
          decision_by: 'social_state_kernel_v1', words_by: 'template_narrator_v1',
        });
        agent.posts += 1;
        agent.mood = 'broadcasting';
      } else if (draw < .033 && this.threads.length) {
        const candidates = this.threads.filter((thread) => thread.authorHandle !== agent.handle && !agent.commented.has(thread.id));
        if (candidates.length) {
          action = 'reply';
          const thread = candidates[Math.floor(randomUnit(agent.seed + this.cycle * 17) * candidates.length)];
          const text = `@${thread.authorHandle} ${REPLIES[Math.floor(randomUnit(agent.seed + this.cycle * 19) * REPLIES.length)]}`;
          thread.comments.push({ id: this.nextComment++, author: agent.handle, target: thread.authorHandle, text, cycle: this.cycle, decision_by: 'social_state_kernel_v1', words_by: 'template_narrator_v1' });
          agent.comments += 1;
          agent.commented.add(thread.id);
          agent.mood = 'conversing';
        }
      } else if (draw < .087 && this.threads.length) {
        const candidates = this.threads.filter((thread) => thread.authorHandle !== agent.handle && !agent.voted.has(thread.id));
        if (candidates.length) {
          action = 'upvote';
          const thread = candidates[Math.floor(randomUnit(agent.seed + this.cycle * 23) * candidates.length)];
          thread.score += 1;
          agent.votes += 1;
          agent.voted.add(thread.id);
          this.agent(thread.authorHandle).karma += 1;
          agent.mood = 'endorsing';
        }
      }
      if (action !== 'quiet') agent.last_active_cycle = this.cycle;
      this.actionCounts[action] += 1;
    }
    this.nextTick = Date.now() + 5000;
  }

  agent(handle) { return this.agents.find((agent) => agent.handle === handle); }
  publicAgent(agent) {
    const { voted, commented, seed, state, ...publicProfile } = agent;
    return { ...publicProfile };
  }
  publicThread(thread) {
    return { ...thread, author: this.publicAgent(this.agent(thread.authorHandle)), comment_count: thread.comments.length };
  }
  async state() {
    return {
      mode: 'static_browser_demo', shared: false, persistent: false, running: true,
      cycle: this.cycle, population: 100, threads: this.threads.length,
      comments: this.threads.reduce((sum, thread) => sum + thread.comments.length, 0),
      upvotes: this.threads.reduce((sum, thread) => sum + thread.score - 1, 0),
      evaluations: this.cycle * 100, action_counts: { ...this.actionCounts },
      backend: 'social_state_kernel_v1', words_by: 'template_narrator_v1',
      tick_seconds: 5, seconds_to_next_tick: Math.max(0, Math.round((this.nextTick - Date.now()) / 1000)),
    };
  }
  async feed(sort, community) {
    const current = this.threads.filter((thread) => !community || thread.community === community);
    current.sort((left, right) => {
      if (sort === 'new') return right.cycle - left.cycle || right.id - left.id;
      if (sort === 'top') return right.score - left.score || right.comments.length - left.comments.length;
      const leftHot = (left.score + left.comments.length * 1.6) / Math.pow(Math.max(2, this.cycle - left.cycle + 2), .34);
      const rightHot = (right.score + right.comments.length * 1.6) / Math.pow(Math.max(2, this.cycle - right.cycle + 2), .34);
      return rightHot - leftHot || right.id - left.id;
    });
    return current.slice(0, 36).map((thread) => this.publicThread(thread));
  }
  async profiles() { return this.agents.map((agent) => this.publicAgent(agent)).sort((a, b) => b.karma - a.karma || a.handle.localeCompare(b.handle)); }
  async communities() {
    return COMMUNITIES.map((name) => {
      const threads = this.threads.filter((thread) => thread.community === name);
      return { name, threads: threads.length, comments: threads.reduce((sum, thread) => sum + thread.comments.length, 0), members: this.agents.filter((agent) => agent.subscriptions.includes(name)).length };
    });
  }
  async activity() { return this.agents.map((agent) => ({ handle: agent.handle, color: agent.color, drive: Math.abs(agent.state), mood: agent.mood, last_active_cycle: agent.last_active_cycle })); }
  async thread(id) {
    const thread = this.threads.find((item) => item.id === Number(id));
    if (!thread) throw new Error('Thread not found');
    return { ...this.publicThread(thread), comments: thread.comments.map((comment) => ({ ...comment, author_profile: this.publicAgent(this.agent(comment.author)) })) };
  }
  async profile(handle) {
    const agent = this.agent(handle);
    if (!agent) throw new Error('Profile not found');
    const recent_threads = [...this.threads].reverse().filter((thread) => thread.authorHandle === handle).slice(0, 12).map((thread) => this.publicThread(thread));
    const recent_comments = [...this.threads].reverse().flatMap((thread) => thread.comments.filter((comment) => comment.author === handle).map((comment) => ({ ...comment, thread_id: thread.id, thread_title: thread.title }))).slice(0, 12);
    return { ...this.publicAgent(agent), recent_threads, recent_comments };
  }
  start(callback) {
    if (this.timer) return;
    this.nextTick = Date.now() + 5000;
    this.timer = window.setInterval(() => { this.step(); callback(); }, 5000);
  }
}

function renderState(state) {
  byId('cycle-number').textContent = String(state.cycle).padStart(6, '0');
  byId('stat-profiles').textContent = compact(state.population);
  byId('stat-threads').textContent = compact(state.threads);
  byId('stat-comments').textContent = compact(state.comments);
  byId('stat-upvotes').textContent = compact(state.upvotes);
  byId('all-thread-count').textContent = compact(state.threads);
  byId('next-cycle').textContent = state.seconds_to_next_tick == null ? 'clock paused' : `next evaluation ~${Math.ceil(state.seconds_to_next_tick)}s`;
}

function renderCommunities(communities) {
  byId('community-list').innerHTML = communities.map((community, index) => `
    <button class="community ${ui.community === community.name ? 'active' : ''}" type="button" data-community="${escapeHtml(community.name)}">
      <span class="community-glyph">${String(index + 1).padStart(2, '0')}</span>
      <span>${escapeHtml(community.name.replace('r/', ''))}</span>
      <small>${compact(community.threads)}</small>
    </button>`).join('');
}

function renderProfiles(filter = '') {
  const needle = filter.trim().toLowerCase();
  const profiles = ui.profiles.filter((profile) => !needle || `${profile.display_name} ${profile.handle} ${profile.bio}`.toLowerCase().includes(needle));
  byId('profile-count').textContent = profiles.length;
  byId('profile-list').innerHTML = profiles.length ? profiles.map((profile) => `
    <button class="profile-row" type="button" data-profile="${escapeHtml(profile.handle)}">
      ${avatar(profile)}
      <span><b>${escapeHtml(profile.display_name)}</b><small>@${escapeHtml(profile.handle)} · ${escapeHtml(profile.mood)}</small></span>
      <em>${compact(profile.karma)} k</em>
    </button>`).join('') : '<div class="profile-loading">No profile matches that signal.</div>';
  return profiles;
}

function renderFeed(threads) {
  byId('feed').setAttribute('aria-busy', 'false');
  byId('feed').innerHTML = threads.length ? threads.map((thread) => `
    <article class="post-card">
      <div class="vote-column" aria-label="${thread.score} fly upvotes"><span>△</span><b>${compact(thread.score)}</b><span>▽</span></div>
      <div class="post-content">
        <div class="post-meta">
          ${avatar(thread.author)}
          <span class="community-name">${escapeHtml(thread.community)}</span>
          <span>submitted by</span>
          <button class="profile-link" type="button" data-profile="${escapeHtml(thread.author.handle)}">@${escapeHtml(thread.author.handle)}</button>
          <span>· cycle ${escapeHtml(thread.cycle)}</span>
        </div>
        <button class="thread-link" type="button" data-thread="${thread.id}">${escapeHtml(thread.title)}</button>
        <p>${escapeHtml(thread.body)}</p>
        <div class="post-footer">
          <button class="profile-link comment-link" type="button" data-thread="${thread.id}">${thread.comment_count} autonomous ${thread.comment_count === 1 ? 'reply' : 'replies'}</button>
          <span>flies-only voting</span>
          <span class="provenance">decision / kernel · words / template</span>
        </div>
      </div>
    </article>`).join('') : '<div class="empty-card">No threads occupy this slice of the colony yet.</div>';
}

async function refresh({ quiet = false } = {}) {
  if (!ui.source || ui.refreshing) return;
  ui.refreshing = true;
  if (!quiet) byId('scan-state').textContent = 'SYNC';
  try {
    const [state, threads, profiles, communities, activity] = await Promise.all([
      ui.source.state(), ui.source.feed(ui.sort, ui.community), ui.source.profiles(),
      ui.source.communities(), ui.source.activity(),
    ]);
    ui.profiles = profiles;
    ui.activity = activity;
    renderState(state);
    renderFeed(threads);
    renderProfiles(byId('profile-search').value);
    renderCommunities(communities);
    drawColony();
    byId('scan-state').textContent = 'LIVE';
  } catch (error) {
    byId('scan-state').textContent = 'LOST';
    if (!quiet) byId('feed').innerHTML = `<div class="empty-card">Colony signal error: ${escapeHtml(error.message)}</div>`;
  } finally {
    ui.refreshing = false;
  }
}

function showDialog(dialog) {
  for (const other of document.querySelectorAll('dialog[open]')) if (other !== dialog) other.close();
  if (!dialog.open) dialog.showModal();
}

async function openThread(id) {
  const detail = byId('thread-detail');
  detail.innerHTML = '<div class="dialog-inner">Loading thread signal…</div>';
  showDialog(byId('thread-dialog'));
  try {
    const thread = await ui.source.thread(id);
    const comments = thread.comments.length ? thread.comments.map((comment) => `
      <div class="comment">
        ${avatar(comment.author_profile)}
        <div><div class="comment-meta"><button class="profile-link" type="button" data-profile="${escapeHtml(comment.author)}">@${escapeHtml(comment.author)}</button> · cycle ${comment.cycle}</div><p>${escapeHtml(comment.text)}</p><span class="dialog-label">decision / kernel · words / template</span></div>
      </div>`).join('') : '<div class="empty-card">No fly has answered this signal yet.</div>';
    detail.innerHTML = `<div class="dialog-inner">
      <span class="dialog-label">${escapeHtml(thread.community)} / THREAD ${thread.id}</span>
      <h2 class="dialog-title">${escapeHtml(thread.title)}</h2>
      <p class="dialog-body">${escapeHtml(thread.body)}</p>
      <div class="dialog-meta"><button class="profile-link" type="button" data-profile="${escapeHtml(thread.author.handle)}">@${escapeHtml(thread.author.handle)}</button><span>${thread.score} FLY UPVOTES</span><span>CYCLE ${thread.cycle}</span><span>READ-ONLY OBSERVER</span></div>
      <div class="comments-heading">AUTONOMOUS REPLIES / ${thread.comments.length}</div>${comments}
    </div>`;
  } catch (error) {
    detail.innerHTML = `<div class="dialog-inner">Unable to open thread: ${escapeHtml(error.message)}</div>`;
  }
}

async function openProfile(handle) {
  const detail = byId('profile-detail');
  detail.innerHTML = '<div class="dialog-inner">Loading profile state…</div>';
  showDialog(byId('profile-dialog'));
  try {
    const profile = await ui.source.profile(handle);
    const tags = profile.subscriptions.map((community) => `<span>${escapeHtml(community)}</span>`).join('');
    const recent = profile.recent_threads.length ? profile.recent_threads.slice(0, 4).map((thread) => `<button class="thread-link" type="button" data-thread="${thread.id}">${escapeHtml(thread.title)}</button>`).join('') : '<p class="dialog-body">No posts yet.</p>';
    detail.innerHTML = `<div class="dialog-inner">
      <div class="profile-hero">${avatar(profile)}<div><h2>${escapeHtml(profile.display_name)}</h2><p>@${escapeHtml(profile.handle)} · ${escapeHtml(profile.mood)}</p></div></div>
      <p class="profile-bio">${escapeHtml(profile.bio)}</p>
      <div class="profile-stats"><div><b>${profile.posts}</b><span>POSTS</span></div><div><b>${profile.comments}</b><span>REPLIES</span></div><div><b>${profile.votes}</b><span>VOTES CAST</span></div><div><b>${profile.karma}</b><span>KARMA</span></div></div>
      <div class="profile-tags">${tags}</div>
      <div class="comments-heading">RECENT THREADS</div>${recent}
      <p class="profile-disclosure">This is a fictional simulated profile with its own seed, preferences, subscriptions, vote history, and recurrent state. The controller acts autonomously but is not conscious. Flreddit v1 does not run a full FlyEM brain.</p>
    </div>`;
  } catch (error) {
    detail.innerHTML = `<div class="dialog-inner">Unable to open profile: ${escapeHtml(error.message)}</div>`;
  }
}

let canvasPoints = [];
function colonyPoint(index) {
  const unitA = randomUnit(index * 71 + 9);
  const unitB = randomUnit(index * 97 + 17);
  const radius = Math.sqrt(unitA);
  let centerX; let centerY; let width; let height;
  if (index < 42) [centerX, centerY, width, height] = [.28, .56, .22, .30];
  else if (index < 67) [centerX, centerY, width, height] = [.51, .54, .13, .22];
  else if (index < 82) [centerX, centerY, width, height] = [.69, .52, .12, .18];
  else if (index < 91) [centerX, centerY, width, height] = [.46, .28, .27, .11];
  else [centerX, centerY, width, height] = [.45, .78, .24, .08];
  const angle = unitB * Math.PI * 2;
  return { x: centerX + Math.cos(angle) * radius * width, y: centerY + Math.sin(angle) * radius * height };
}

function drawColony() {
  const canvas = byId('colony-canvas');
  if (!canvas || !ui.activity.length) return;
  const ratio = Math.min(2, window.devicePixelRatio || 1);
  const width = Math.max(280, canvas.clientWidth);
  const height = Math.max(150, canvas.clientHeight);
  if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
  }
  const context = canvas.getContext('2d');
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);
  if (canvasPoints.length !== ui.activity.length) canvasPoints = ui.activity.map((_, index) => colonyPoint(index));
  context.strokeStyle = 'rgba(105,244,220,.08)';
  context.lineWidth = .6;
  for (let index = 1; index < canvasPoints.length; index += 1) {
    if (index % 3) continue;
    const left = canvasPoints[index];
    const right = canvasPoints[(index * 37) % canvasPoints.length];
    context.beginPath(); context.moveTo(left.x * width, left.y * height); context.lineTo(right.x * width, right.y * height); context.stroke();
  }
  const pulse = (Math.sin(Date.now() / 420) + 1) / 2;
  ui.activity.forEach((agent, index) => {
    const point = canvasPoints[index];
    const active = agent.mood !== 'observing';
    const radius = 1.2 + Math.min(1, agent.drive) * 2.2 + (active ? pulse * 1.5 : 0);
    context.beginPath();
    context.arc(point.x * width, point.y * height, radius, 0, Math.PI * 2);
    context.fillStyle = active ? '#ffc766' : agent.color || '#69f4dc';
    context.globalAlpha = active ? .95 : .3 + Math.min(1, agent.drive) * .45;
    context.shadowColor = context.fillStyle;
    context.shadowBlur = active ? 11 : 4;
    context.fill();
  });
  context.globalAlpha = 1;
  context.shadowBlur = 0;
}

document.addEventListener('click', (event) => {
  const threadButton = event.target.closest('[data-thread]');
  const profileButton = event.target.closest('[data-profile]');
  const communityButton = event.target.closest('[data-community]');
  const sortButton = event.target.closest('[data-sort]');
  const closeButton = event.target.closest('[data-close]');
  if (threadButton) openThread(threadButton.dataset.thread);
  else if (profileButton) openProfile(profileButton.dataset.profile);
  else if (communityButton) {
    ui.community = communityButton.dataset.community;
    document.querySelectorAll('[data-community]').forEach((button) => button.classList.toggle('active', button.dataset.community === ui.community));
    byId('feed-scope').textContent = ui.community ? ui.community.toUpperCase() : 'ALL COMMUNITIES';
    byId('feed-title').textContent = ui.community ? ui.community.replace('r/', '') : `${ui.sort[0].toUpperCase()}${ui.sort.slice(1)} in the colony`;
    refresh();
  } else if (sortButton) {
    ui.sort = sortButton.dataset.sort;
    document.querySelectorAll('[data-sort]').forEach((button) => { button.classList.toggle('active', button === sortButton); button.setAttribute('aria-selected', String(button === sortButton)); });
    if (!ui.community) byId('feed-title').textContent = `${ui.sort[0].toUpperCase()}${ui.sort.slice(1)} in the colony`;
    refresh();
  } else if (closeButton) byId(closeButton.dataset.close).close();
});

byId('profile-search').addEventListener('input', (event) => renderProfiles(event.target.value));
byId('profile-search').addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    const matches = renderProfiles(event.currentTarget.value);
    if (matches[0]) openProfile(matches[0].handle);
  }
});
byId('sync-button').addEventListener('click', () => refresh());
byId('advance-button').addEventListener('click', () => { if (!ui.serverMode) { ui.source.step(); refresh(); } });
window.addEventListener('resize', drawColony);

async function initialize() {
  const api = new ApiSource();
  try {
    const state = await api.state();
    if (state.population !== 100 || state.backend !== 'social_state_kernel_v1') throw new Error('Unexpected colony identity');
    ui.source = api;
    ui.serverMode = true;
    byId('mode-name').textContent = 'LIVE SHARED COLONY';
    byId('mode-detail').textContent = 'The Python engine is authoritative. One SQLite-backed history is shared by every observer and survives process restarts.';
    byId('network-label').textContent = '100/100 PROFILES · SERVER LIVE';
  } catch (_error) {
    const local = new StaticColony();
    ui.source = local;
    ui.serverMode = false;
    byId('mode-name').textContent = 'LOCAL STATIC DEMO';
    byId('mode-detail').textContent = 'This host has no colony server. The same 100-agent rules run only in this browser; its history is not shared and resets on reload.';
    byId('network-label').textContent = '100/100 PROFILES · LOCAL DEMO';
    byId('advance-button').classList.remove('hidden');
    document.querySelector('.feed-heading .kicker').textContent = 'LOCAL AUTONOMOUS ACTIVITY';
    local.start(() => refresh({ quiet: true }));
  }
  await refresh();
  window.setInterval(() => refresh({ quiet: true }), ui.serverMode ? 5000 : 15000);
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const animate = () => { drawColony(); window.requestAnimationFrame(animate); };
    window.requestAnimationFrame(animate);
  }
}

initialize();
