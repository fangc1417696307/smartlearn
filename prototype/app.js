/* ============================================================
 * SmartLearn 前端（对接 FastAPI 后端）
 * ============================================================ */

/* ---------- 工具 ---------- */
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const API_BASE = 'http://127.0.0.1:8001/api';
const STORE = {
  token: 'sl_token',
  user: 'sl_user',
  profile: 'sl_profile_',
  path: 'sl_path_',
};
const load = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
const save = (k, v) => localStorage.setItem(k, JSON.stringify(v));

/* ---------- API ---------- */
async function api(path, method = 'GET', body = null) {
  const headers = { 'Content-Type': 'application/json' };
  const token = load(STORE.token, null);
  if (token) headers['Authorization'] = 'Bearer ' + token;
  const res = await fetch(API_BASE + path, { method, headers, body: body ? JSON.stringify(body) : null });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || '请求失败');
  return data;
}

/* ---------- 画像维度定义 ---------- */
const PROFILE_DIMS = [
  { key: 'goal', name: '学习目标', icon: '🎯', desc: '驱动学习路径与资源优先级' },
  { key: 'foundation', name: '知识基础', icon: '🧱', desc: '决定资源难度与讲解深度' },
  { key: 'history', name: '学习历史', icon: '📖', desc: '影响内容衔接与查漏补缺' },
  { key: 'pace', name: '学习节奏', icon: '⏱️', desc: '决定路径长度与任务颗粒度' },
  { key: 'style', name: '认知风格', icon: '🧠', desc: '决定推送内容形态与权重' },
  { key: 'weakness', name: '易错点偏好', icon: '⚠️', desc: '影响练习与讲解侧重点' },
];

/* ---------- 画像构建对话脚本 ---------- */
const ONBOARD_SCRIPT = [
  {
    dim: 'goal', ask: '你好，我是学情分析师 🤖 为了给你生成专属学习画像，我们随便聊几句，不用填表。\n\n先告诉我：你这次学习最想达成什么目标？',
    quick: [['期末冲刺 90+', 80], ['考研备考', 70], ['兴趣入门', 45], ['就业求职技能', 85]],
  },
  {
    dim: 'foundation', ask: '收到！那你目前的计算机 / 编程基础大概是什么水平？',
    quick: [['零基础', 20], ['有一点基础', 40], ['比较扎实', 70], ['很熟练', 90]],
  },
  {
    dim: 'history', ask: '之前学过哪些相关课程呢？（可选一个，或直接输入，如"学过 C 语言和数据结构"）',
    quick: [['C 语言', 50], ['数据结构', 55], ['操作系统', 60], ['还没系统学过', 20]],
  },
  {
    dim: 'pace', ask: '你每周大概能投入多少时间学习？',
    quick: [['少于 5 小时', 25], ['5-10 小时', 45], ['10-20 小时', 70], ['20 小时以上', 90]],
  },
  {
    dim: 'style', ask: '你平时更喜欢哪种学习方式？',
    quick: [['看视频', 55], ['读文档', 60], ['动手写代码', 70], ['刷题', 65]],
  },
  {
    dim: 'weakness', ask: '最后，你学习时容易在哪些地方出错？',
    quick: [['概念混淆', 55], ['细节遗漏', 60], ['逻辑推理', 70], ['代码语法', 65]],
  },
];

/* ---------- 学习路径模板（数据结构主线） ---------- */
const PATH_TEMPLATE = [
  { id: 1, title: '复习基础：线性表与数组', desc: '回顾线性表存储结构与基本操作，为树结构打基础', res: ['doc-stack', 'code-heap'] },
  { id: 2, title: '掌握二叉树核心概念', desc: '理解二叉树定义、性质与存储结构', res: ['doc-btree', 'mm-btree', 'video-ds'] },
  { id: 3, title: '攻克二叉树三种遍历', desc: '前序 / 中序 / 后序遍历的递归与迭代实现', res: ['code-traverse', 'quiz-btree'] },
  { id: 4, title: '专项练习与查漏补缺', desc: '通过练习巩固，标记易错点并回看讲解', res: ['quiz-btree', 'quiz-sort'] },
  { id: 5, title: '拓展：平衡树与进阶结构', desc: '了解 AVL、红黑树与堆的应用', res: ['reading-rbtree', 'code-heap'] },
];

/* ---------- 资源类型 ---------- */
const RES_TYPES = [
  { key: 'all', label: '全部', icon: '🗂️' },
  { key: 'doc', label: '讲解文档', icon: '📄' },
  { key: 'mindmap', label: '思维导图', icon: '🧠' },
  { key: 'quiz', label: '练习题', icon: '✏️' },
  { key: 'reading', label: '拓展阅读', icon: '📚' },
  { key: 'code', label: '代码案例', icon: '💻' },
  { key: 'video', label: 'B站视频', icon: '🎬' },
];

/* ---------- 资源数据 ---------- */
const RESOURCES = [
  { id: 'doc-btree', type: 'doc', icon: '📄', title: '二叉树：从入门到掌握', desc: '定义、性质、存储结构与遍历全解析' },
  { id: 'doc-stack', type: 'doc', icon: '📄', title: '栈与队列核心讲解', desc: '两种受限线性表的特性与应用场景' },
  { id: 'mm-btree', type: 'mindmap', icon: '🧠', title: '二叉树知识图谱', desc: '一张图理清二叉树所有核心概念' },
  { id: 'mm-overview', type: 'mindmap', icon: '🧠', title: '数据结构总览导图', desc: '线性表、树、图的整体框架' },
  { id: 'quiz-btree', type: 'quiz', icon: '✏️', title: '二叉树专项练习', desc: '客观题自动判分 + 主观题 LLM 判分' },
  { id: 'quiz-sort', type: 'quiz', icon: '✏️', title: '排序算法练习题', desc: '排序基础与复杂度分析题目' },
  { id: 'reading-rbtree', type: 'reading', icon: '📚', title: '红黑树深入阅读', desc: '从 AVL 到红黑树的平衡演进' },
  { id: 'reading-algo', type: 'reading', icon: '📚', title: '算法导论选读章节', desc: '经典教材推荐章节与延伸材料' },
  { id: 'code-traverse', type: 'code', icon: '💻', title: '二叉树的递归遍历（Python）', desc: '前中后序三种递归实现，含运行示例' },
  { id: 'code-heap', type: 'code', icon: '💻', title: '手写最小堆', desc: '用数组实现最小堆的插入与弹出' },
  { id: 'video-ds', type: 'video', icon: '🎬', title: '数据结构课程视频推荐', desc: '预设 B 站链接库，按知识点匹配' },
];

/* ---------- 资源详情 ---------- */
const DETAILS = {
  'doc-btree': {
    type: '讲解文档',
    html: `
      <p>二叉树（Binary Tree）是每个结点最多有两个子结点的树结构，是计算机科学中最基础也最重要的数据结构之一。</p>
      <h4>一、基本性质</h4>
      <ul>
        <li>第 i 层（i≥1）至多有 <b>2^(i-1)</b> 个结点。</li>
        <li>深度为 k 的二叉树至多有 <b>2^k - 1</b> 个结点。</li>
        <li>若叶子数为 n0，度为 2 的结点数为 n2，则 <b>n0 = n2 + 1</b>。</li>
      </ul>
      <div class="callout">💡 易错提醒：完全二叉树不一定是满二叉树，满二叉树一定是完全二叉树。</div>
      <h4>二、遍历方式</h4>
      <p>前序（根左右）、中序（左根右）、后序（左右根）、层序（逐层）。递归实现简单直观，迭代实现需借助栈。</p>`,
  },
  'doc-stack': {
    type: '讲解文档',
    html: `
      <p>栈（Stack）是「后进先出」（LIFO）的受限线性表；队列（Queue）是「先进先出」（FIFO）的受限线性表。</p>
      <h4>栈的应用</h4>
      <ul><li>函数调用栈、表达式求值、括号匹配、递归。</li></ul>
      <h4>队列的应用</h4>
      <ul><li>任务调度、广度优先搜索（BFS）、消息队列。</li></ul>`,
  },
  'mm-btree': {
    type: '思维导图',
    mindmap: {
      root: '二叉树',
      branches: [
        { head: '基本概念', leaves: ['定义', '结点的度', '深度 / 高度'] },
        { head: '重要性质', leaves: ['2^(i-1)', '2^k - 1', 'n0 = n2 + 1'] },
        { head: '遍历方式', leaves: ['前序', '中序', '后序', '层序'] },
        { head: '特殊形态', leaves: ['满二叉树', '完全二叉树', '二叉搜索树', '平衡树(AVL)'] },
      ],
    },
  },
  'mm-overview': {
    type: '思维导图',
    mindmap: {
      root: '数据结构',
      branches: [
        { head: '线性结构', leaves: ['数组', '链表', '栈', '队列'] },
        { head: '树形结构', leaves: ['二叉树', '堆', '哈夫曼树'] },
        { head: '图形结构', leaves: ['邻接矩阵', '邻接表'] },
        { head: '查找 / 排序', leaves: ['二分查找', '快排', '归并', '堆排'] },
      ],
    },
  },
  'quiz-btree': {
    type: '练习题',
    quiz: [
      { kind: 'single', q: '二叉树的第 i 层（i≥1）至多有多少个结点？', options: ['2^i - 1', '2^(i-1)', '2^(i+1)', 'i^2'], answer: 1 },
      { kind: 'single', q: '深度为 4 的满二叉树，结点总数是？', options: ['7', '8', '15', '16'], answer: 2 },
      { kind: 'judge', q: '完全二叉树一定是满二叉树。', options: ['正确', '错误'], answer: 1 },
      { kind: 'subjective', q: '简述二叉搜索树（BST）与平衡二叉树（AVL）的主要区别，以及 AVL 为什么能保证 O(log n) 的查找效率。', ref: '要点：① BST 仅要求「左小右大」，最坏会退化成链表（O(n)）；② AVL 在 BST 基础上增加平衡因子约束（任意结点左右子树高度差 ≤1），通过旋转维持平衡；③ 平衡保证树高约为 O(log n)，因此查找、插入、删除均为 O(log n)。' },
    ],
  },
  'quiz-sort': {
    type: '练习题',
    quiz: [
      { kind: 'single', q: '快速排序在平均情况下的时间复杂度是？', options: ['O(n)', 'O(n log n)', 'O(n^2)', 'O(log n)'], answer: 1 },
      { kind: 'single', q: '下列哪种排序是稳定排序？', options: ['快速排序', '堆排序', '归并排序', '选择排序'], answer: 2 },
    ],
  },
  'reading-rbtree': {
    type: '拓展阅读',
    reading: [
      { t: '从 AVL 到红黑树：平衡的两种哲学', s: '《算法导论》第 13 章', d: 'AVL 追求严格平衡（查询快、插入旋转多），红黑树追求弱平衡（插入更高效），适用于不同读写比例的场景。' },
      { t: '红黑树的五条性质与旋转', s: '图解红黑树 · 示例链接', d: '掌握「黑高」的概念，理解插入后的颜色调整与旋转修复过程。' },
      { t: '工程实践：Java TreeMap 与 Linux CFS', s: '延伸阅读', d: '红黑树在工业级实现中的典型应用，帮助理解其工程价值。' },
    ],
  },
  'reading-algo': {
    type: '拓展阅读',
    reading: [
      { t: '分治法与递归树分析', s: '《算法导论》第 4 章', d: '用递归树方法推导归并排序的时间复杂度，建立算法分析直觉。' },
      { t: '动态规划入门', s: '《算法导论》第 15 章', d: '从「钢条切割」问题理解最优子结构与重叠子问题。' },
    ],
  },
  'code-traverse': {
    type: '代码案例',
    code: {
      lang: 'Python',
      source: `class Node:
    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None

def preorder(root):          # 前序：根左右
    if not root:
        return
    print(root.val, end=' ')
    preorder(root.left)
    preorder(root.right)

def inorder(root):           # 中序：左根右
    if not root:
        return
    inorder(root.left)
    print(root.val, end=' ')
    inorder(root.right)

def postorder(root):         # 后序：左右根
    if not root:
        return
    postorder(root.left)
    postorder(root.right)
    print(root.val, end=' ')`,
      note: '递归遍历是最直观的写法。若树很深，可改写为「显式栈」的迭代实现避免递归深度过大。',
    },
  },
  'code-heap': {
    type: '代码案例',
    code: {
      lang: 'Python',
      source: `import heapq

# 最小堆：heapq 默认即最小堆
h = []
heapq.heappush(h, 5)
heapq.heappush(h, 1)
heapq.heappush(h, 3)
print(heapq.heappop(h))   # 1（弹出最小值）

# 手写核心操作示意
class MinHeap:
    def __init__(self):
        self.a = [0]       # 下标从 1 开始
    def push(self, x):
        self.a.append(x)
        i = len(self.a) - 1
        while i > 1 and self.a[i] < self.a[i // 2]:   # 上浮
            self.a[i], self.a[i // 2] = self.a[i // 2], self.a[i]
            i //= 2`,
      note: '堆是一棵完全二叉树，通常用数组存储；常用于 Top-K 问题与优先队列。',
    },
  },
  'video-ds': {
    type: 'B站视频',
    videos: [
      { t: '数据结构与算法基础（王卓老师）', up: '青岛大学 · 王卓', url: 'https://search.bilibili.com/all?keyword=%E6%95%B0%E6%8D%AE%E7%BB%93%E6%9E%84%20%E7%8E%8B%E5%8D%93', dur: '系列课 · 100+ 集' },
      { t: '王道计算机考研 · 数据结构', up: '王道计算机教育', url: 'https://search.bilibili.com/all?keyword=%E7%8E%8B%E9%81%93%20%E6%95%B0%E6%8D%AE%E7%BB%93%E6%9E%84', dur: '考研精讲 · 针对性强' },
      { t: '左程云 · 算法与数据结构进阶', up: '左程云', url: 'https://search.bilibili.com/all?keyword=%E5%B7%A6%E7%A8%8B%E4%BA%91%20%E7%AE%97%E6%B3%95', dur: '进阶 · 面试算法' },
    ],
  },
};

/* ---------- 答疑语料 ---------- */
const QA_KNOWLEDGE = [
  ['二叉树', '二叉树的三种遍历核心口诀：前序「根左右」、中序「左根右」、后序「左右根」。递归实现最直观；若要避免递归栈溢出，可用「显式栈」模拟。层序遍历则需借助队列逐层访问。'],
  ['平衡', 'AVL 通过「平衡因子」（左右子树高度差 ≤1）约束树形，插入导致失衡时用 LL / RR / LR / RL 四种旋转恢复平衡，从而保证树高约为 O(log n)，查找稳定在 O(log n)。'],
  ['堆', '堆是一棵「完全二叉树」，用数组存储（下标从 1 开始，i 的左右子为 2i、2i+1）。最小堆满足「父结点 ≤ 子结点」。堆顶即最值，插入用上浮、删除用下沉，复杂度 O(log n)。'],
  ['复杂度', '常见复杂度从小到大：O(1) < O(log n) < O(n) < O(n log n) < O(n²) < O(2ⁿ)。归并/堆排稳定在 O(n log n)，快排平均 O(n log n) 但最坏 O(n²)。'],
];
const QA_FALLBACK = '这是个好问题！我建议你从「定义 → 性质 → 典型操作 → 复杂度」这条主线去理解。如果还卡壳，可以到「资源中心」回看对应的讲解文档与代码案例，或告诉我更具体的困惑点。';

/* ---------- 状态 ---------- */
let state = {
  account: null,
  profile: null,
  path: null,
};

/* ---------- 视图切换 ---------- */
function showView(name) {
  $$('.view').forEach((v) => { v.hidden = v.id !== 'view-' + name; });
}
function showPage(name) {
  $$('.page').forEach((p) => p.classList.toggle('active', p.id === 'page-' + name));
  $$('.nav-item').forEach((n) => n.classList.toggle('active', n.dataset.nav === name));
  const titles = { dashboard: '首页', path: '学习路径', resources: '资源中心', qa: '答疑', assessment: '学习评估', profile: '我的画像', 'resource-detail': '资源详情' };
  $('#topbar-title').textContent = titles[name] || '首页';
}

/* ---------- 登录 / 注册 ---------- */
/* ---------- 登录 / 注册（对接后端） ---------- */
async function refreshCaptcha(prefix) {
  try {
    const cap = await api('/auth/captcha');
    $(`#${prefix}-captcha-q`).textContent = cap.question;
    $(`#${prefix}-captcha-id`).value = cap.captcha_id;
  } catch (e) {
    $(`#${prefix}-captcha-q`).textContent = '验证码加载失败';
  }
}

function applyRoleNav() {
  const perms = state.permissions || [];
  const adminNav = $('#nav-admin');
  if (!adminNav) return;
  adminNav.hidden = !(perms.includes('user.manage') || perms.includes('role.manage'));
  adminNav.querySelectorAll('.nav-item').forEach((item) => {
    const need = item.dataset.nav === 'users' ? 'user.manage' : 'role.manage';
    item.hidden = !perms.includes(need);
  });
}

function continueEnter() {
  const user = load(STORE.user, null);
  if (!user) return;
  state.profile = load(STORE.profile + user.account, null);
  state.path = load(STORE.path + user.account, null);
  if (state.profile && state.path) showMain();
  else startOnboarding();
}

function showPwdModal(loginPassword) {
  $('#pwd-modal').hidden = false;
  $('#pwd-err').textContent = '';
  $('#pwd-new').value = '';
  $('#pwd-submit').onclick = async () => {
    const np = $('#pwd-new').value;
    if (np.length < 6) { $('#pwd-err').textContent = '新密码至少 6 位'; return; }
    try {
      await api('/auth/change-password', 'POST', { old_password: loginPassword, new_password: np });
      const user = load(STORE.user, null);
      user.must_change_password = false;
      save(STORE.user, user);
      $('#pwd-modal').hidden = true;
      continueEnter();
    } catch (err) { $('#pwd-err').textContent = err.message; }
  };
}

function initAuth() {
  const tabs = $$('.auth-tab');
  const switchAuth = (tab) => {
    tabs.forEach((t) => t.classList.toggle('active', t.dataset.authTab === tab));
    $('#form-login').hidden = tab !== 'login';
    $('#form-code-login').hidden = tab !== 'code';
    $('#form-register').hidden = tab !== 'register';
  };
  tabs.forEach((t) => t.addEventListener('click', () => switchAuth(t.dataset.authTab)));
  $$('[data-auth-switch]').forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); switchAuth(a.dataset.authSwitch); }));

  $$('[data-refresh]').forEach((b) => b.addEventListener('click', () => refreshCaptcha(b.dataset.refresh)));
  $('#login-captcha-q').addEventListener('click', () => refreshCaptcha('login'));
  $('#reg-captcha-q').addEventListener('click', () => refreshCaptcha('reg'));

  $('#form-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    const acc = $('#login-account').value.trim();
    const pwd = $('#login-password').value;
    const cid = $('#login-captcha-id').value;
    const ans = $('#login-captcha').value.trim();
    if (!acc || !pwd) { alert('请填写账号和密码'); return; }
    if (!ans) { alert('请填写验证码'); return; }
    try {
      const data = await api('/auth/login', 'POST', { account: acc, password: pwd, captcha_id: cid, captcha_answer: ans });
      enterApp(data.user, data.access_token, data.permissions, pwd);
    } catch (err) {
      alert(err.message);
      refreshCaptcha('login');
    }
  });

  $('#code-send').addEventListener('click', async () => {
    const email = $('#code-email').value.trim();
    if (!email) { alert('请输入邮箱'); return; }
    const btn = $('#code-send');
    try {
      await api('/auth/send-code', 'POST', { email });
      let s = 60;
      btn.disabled = true;
      const timer = setInterval(() => {
        s--;
        btn.textContent = s + 's 后重发';
        if (s <= 0) { clearInterval(timer); btn.disabled = false; btn.textContent = '发送验证码'; }
      }, 1000);
    } catch (err) { alert(err.message); }
  });
  $('#form-code-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = $('#code-email').value.trim();
    const code = $('#code-input').value.trim();
    if (!email || !code) { alert('请输入邮箱和验证码'); return; }
    try {
      const data = await api('/auth/code-login', 'POST', { email, code });
      enterApp(data.user, data.access_token, data.permissions);
    } catch (err) { alert(err.message); }
  });

  $('#form-register').addEventListener('submit', async (e) => {
    e.preventDefault();
    const account = $('#reg-account').value.trim();
    const nickname = $('#reg-nickname').value.trim() || '同学';
    const password = $('#reg-password').value;
    const major = $('#reg-major').value;
    const cid = $('#reg-captcha-id').value;
    const ans = $('#reg-captcha').value.trim();
    if (!account || !password) { alert('请填写学号和密码'); return; }
    if (password.length < 6) { alert('密码至少 6 位'); return; }
    if (!ans) { alert('请填写验证码'); return; }
    try {
      const data = await api('/auth/register', 'POST', { account, password, nickname, major, captcha_id: cid, captcha_answer: ans });
      enterApp(data.user, data.access_token, data.permissions);
    } catch (err) {
      alert(err.message);
      refreshCaptcha('reg');
    }
  });

  $('#btn-logout').addEventListener('click', () => {
    localStorage.removeItem(STORE.token);
    localStorage.removeItem(STORE.user);
    state = { account: null, profile: null, path: null, permissions: [] };
    showView('auth');
  });
}

function enterApp(user, token, permissions, loginPassword) {
  save(STORE.token, token);
  save(STORE.user, user);
  state.account = user.account;
  state.permissions = permissions || [];
  $('#user-name').textContent = user.nickname;
  $('#user-major').textContent = user.major;
  $('#user-avatar').textContent = user.nickname.slice(0, 1);
  applyRoleNav();
  if (user.must_change_password) {
    showPwdModal(loginPassword || '');
    return;
  }
  continueEnter();
}

/* ---------- 画像构建对话 ---------- */
let onboardIndex = 0;
const collected = {};

function startOnboarding() {
  showView('onboarding');
  $('#onboard-chat').innerHTML = '';
  onboardIndex = 0;
  for (const k in collected) delete collected[k];
  botSay(ONBOARD_SCRIPT[0].ask, 700, renderQuickReplies);
}

function botSay(text, delay = 500, after) {
  const box = $('#onboard-chat');
  const typing = document.createElement('div');
  typing.className = 'msg bot typing';
  typing.innerHTML = `<div class="msg-bubble">…</div>`;
  box.appendChild(typing);
  box.scrollTop = box.scrollHeight;
  setTimeout(() => {
    typing.remove();
    appendMsg(box, 'bot', text, '学情分析师');
    if (after) after();
  }, delay);
}
function userSay(text) {
  appendMsg($('#onboard-chat'), 'user', text);
}
function appendMsg(box, role, text, agent) {
  const m = document.createElement('div');
  m.className = 'msg ' + role;
  const tag = agent ? `<div class="agent-tag">${agent}</div>` : '';
  m.innerHTML = `${tag}<div class="msg-bubble">${esc(text).replace(/\n/g, '<br>')}</div>`;
  box.appendChild(m);
  box.scrollTop = box.scrollHeight;
  return m;
}

function submitOnboard(text) {
  if (!text) return;
  const step = ONBOARD_SCRIPT[onboardIndex];
  userSay(text);
  collected[step.dim] = text;
  const q = step.quick.find((o) => o[0] === text);
  collected[step.dim + '_score'] = q ? q[1] : 50;
  onboardIndex++;
  if (onboardIndex < ONBOARD_SCRIPT.length) {
    botSay(ONBOARD_SCRIPT[onboardIndex].ask, 500, renderQuickReplies);
  } else {
    renderQuickReplies();
    botSay('画像特征已抽取完成，正在为你生成专属学习画像…', 400);
    setTimeout(finishOnboarding, 900);
  }
}
function renderQuickReplies() {
  const wrap = $('#onboard-quick-replies');
  wrap.innerHTML = '';
  if (onboardIndex < ONBOARD_SCRIPT.length) {
    ONBOARD_SCRIPT[onboardIndex].quick.forEach(([t]) => {
      const b = document.createElement('button');
      b.className = 'btn btn-sm';
      b.textContent = t;
      b.onclick = () => submitOnboard(t);
      wrap.appendChild(b);
    });
  }
}

function finishOnboarding(skip = false) {
  const profile = {};
  PROFILE_DIMS.forEach((d) => {
    profile[d.key] = skip
      ? { text: '待完善', score: 50 }
      : { text: collected[d.key] || '待补充', score: collected[d.key + '_score'] ?? 50 };
  });
  profile.updatedAt = new Date().toLocaleString('zh-CN');
  state.profile = profile;
  save(STORE.profile + state.account, profile);

  state.path = { steps: PATH_TEMPLATE, done: [] };
  save(STORE.path + state.account, state.path);

  showMain();
}

function botTip(text) {
  // 进入主界面后的轻提示（用 alert 简化，避免复杂 toast）
  setTimeout(() => { }, 0);
}

/* ---------- 主界面 ---------- */
function showMain() {
  showView('main');
  renderDashboard();
  showPage('dashboard');
}

function initMain() {
  $$('.nav-item').forEach((n) => n.addEventListener('click', () => {
    switchPage(n.dataset.nav);
  }));
  $$('[data-go]').forEach((a) => a.addEventListener('click', () => switchPage(a.dataset.go)));
  $('#qa-send').addEventListener('click', submitQA);
  $('#qa-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') submitQA(); });
}

function switchPage(name) {
  if (name === 'dashboard') renderDashboard();
  if (name === 'path') renderPath();
  if (name === 'resources') renderResources('all');
  if (name === 'qa') { if (!$('#qa-chat').childElementCount) qaWelcome(); }
  if (name === 'assessment') renderAssessment();
  if (name === 'profile') renderProfile();
  if (name === 'users') renderUsers();
  if (name === 'roles') renderRoles();
  showPage(name);
}

/* ---------- 首页 ---------- */
function renderDashboard() {
  const p = state.profile;
  const today = new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' });
  $('#topbar-date').textContent = today;
  $('#greeting-title').innerHTML = `你好，<span class="grad-text">${esc($('#user-name').textContent)}</span> 👋`;
  $('#greeting-sub').textContent = p.goal ? `多智能体已根据你的画像规划好路线，今天重点攻克「${nextTopic()}」。` : '开始今天的学习吧。';
  $('#greeting-goal').textContent = '🎯 学习目标：' + (p.goal?.text || '待设置');

  // 今日任务（取路径中未完成的头 3 个）
  const steps = state.path.steps;
  const done = state.path.done;
  const html = steps.filter((s) => !done.includes(s.id)).slice(0, 3).map((s, i) => `
    <div class="task-item">
      <span class="task-check">✓</span>
      <div><div class="task-title">${esc(s.title)}</div><div class="task-meta">${esc(s.desc)}</div></div>
      <span class="task-tag">${i === 0 ? '当前' : '后续'}</span>
    </div>`).join('');
  $('#dash-today').innerHTML = html || '<p class="muted">🎉 太棒了，所有学习步骤都已完成！</p>';

  // 画像速览（取前 4 维）
  $('#dash-profile').innerHTML = PROFILE_DIMS.slice(0, 4).map((d) => {
    const v = p[d.key]?.score ?? 50;
    return `<div class="dim-row"><span class="dim-label">${d.icon} ${d.name}</span><div class="dim-bar"><div class="dim-fill" style="width:${v}%"></div></div><span class="dim-val">${v}</span></div>`;
  }).join('');

  // 精准推送（按画像风格优先：认知风格对应资源类型）
  const push = pickPush();
  $('#dash-push').innerHTML = resourceCards(push);
}

function nextTopic() {
  const done = state.path.done;
  const cur = state.path.steps.find((s) => !done.includes(s.id));
  return cur ? cur.title.split('：').pop() : '全部知识点';
}
function pickPush() {
  const style = state.profile.style?.text || '';
  const order = { video: ['video-ds'], code: ['code-traverse', 'code-heap'], doc: ['doc-btree', 'doc-stack'] };
  let picks = ['doc-btree', 'quiz-btree', 'video-ds', 'code-traverse'];
  if (style.includes('代码')) picks = ['code-traverse', 'code-heap', 'quiz-btree'];
  if (style.includes('视频')) picks = ['video-ds', 'doc-btree', 'quiz-btree'];
  if (style.includes('刷题')) picks = ['quiz-btree', 'quiz-sort', 'doc-btree'];
  return picks.map((id) => RESOURCES.find((r) => r.id === id));
}

/* ---------- 学习路径 ---------- */
function renderPath() {
  const steps = state.path.steps;
  const done = state.path.done;
  const total = steps.length;
  const doneCount = done.length;
  const pct = Math.round((doneCount / total) * 100);
  $('#path-progress-label').textContent = pct + '%';
  $('#path-progress-fill').style.width = pct + '%';

  $('#path-steps').innerHTML = steps.map((s, i) => {
    const isDone = done.includes(s.id);
    const isCurrent = !isDone && i === doneCount;
    const cls = isDone ? 'done' : (isCurrent ? 'current' : '');
    const res = s.res.map((rid) => {
      const r = RESOURCES.find((x) => x.id === rid);
      return r ? `<span class="chip" data-res="${r.id}">${r.icon} ${esc(r.title)}</span>` : '';
    }).join('');
    return `
      <div class="path-step ${cls}">
        <div class="ps-title">${i + 1}. ${esc(s.title)}</div>
        <div class="ps-desc">${esc(s.desc)}</div>
        <div class="ps-res">${res}</div>
        ${isDone ? '<div class="task-tag">✅ 已掌握</div>'
          : `<button class="btn btn-sm btn-primary done-btn" data-done="${s.id}">标记为已完成 / 已掌握</button>`}
      </div>`;
  }).join('');

  $$('#path-steps .chip').forEach((c) => c.addEventListener('click', () => openResource(c.dataset.res)));
  $$('#path-steps [data-done]').forEach((b) => b.addEventListener('click', () => {
    if (!state.path.done.includes(+b.dataset.done)) state.path.done.push(+b.dataset.done);
    save(STORE.path + state.account, state.path);
    renderPath();
  }));
}

/* ---------- 资源中心 ---------- */
function renderResources(type) {
  $('#resource-tabs').innerHTML = RES_TYPES.map((t) =>
    `<button class="resource-tab ${type === t.key ? 'active' : ''}" data-type="${t.key}">${t.icon} ${t.label}</button>`).join('');
  $$('#resource-tabs .resource-tab').forEach((b) => b.addEventListener('click', () => renderResources(b.dataset.type)));

  const list = type === 'all' ? RESOURCES : RESOURCES.filter((r) => r.type === type);
  $('#resource-list').innerHTML = resourceCards(list);
}

function resourceCards(list) {
  return list.map((r) => `
    <div class="resource-card" data-res="${r.id}">
      <div class="resource-icon">${r.icon}</div>
      <div class="resource-type">${(RES_TYPES.find((t) => t.key === r.type) || {}).label || r.type}</div>
      <div class="resource-title">${esc(r.title)}</div>
      <div class="resource-desc">${esc(r.desc)}</div>
    </div>`).join('');
}

function openResource(id) {
  renderResourceDetail(id);
  showPage('resource-detail');
}

/* ---------- 资源详情 ---------- */
function renderResourceDetail(id) {
  const r = RESOURCES.find((x) => x.id === id);
  const d = DETAILS[id];
  const typeLabel = (RES_TYPES.find((t) => t.key === r.type) || {}).label || r.type;
  let body = `<span class="detail-type-badge">${typeLabel}</span><h2 class="detail-title">${esc(r.title)}</h2><p class="detail-meta">${esc(r.desc)}</p>`;

  if (d.html) body += `<div class="article">${d.html}</div>`;
  if (d.mindmap) body += renderMindmap(d.mindmap);
  if (d.quiz) body += renderQuiz(d.quiz);
  if (d.reading) body += d.reading.map((x) => `
    <div style="border:1px solid var(--border);border-radius:11px;padding:14px;margin-bottom:12px">
      <div style="font-weight:700;font-size:14px">${esc(x.t)}</div>
      <div class="muted" style="margin:4px 0 6px">${esc(x.s)}</div>
      <div style="font-size:13px;line-height:1.7;color:#374151">${esc(x.d)}</div>
    </div>`).join('');
  if (d.code) body += `
    <div class="code-block"><pre>${highlightCode(d.code.source)}</pre></div>
    <div class="callout">📌 ${esc(d.code.note)}</div>`;
  if (d.videos) body += d.videos.map((v) => `
    <div style="display:flex;align-items:center;gap:14px;border:1px solid var(--border);border-radius:11px;padding:14px;margin-bottom:12px">
      <div style="font-size:26px">🎬</div>
      <div style="flex:1">
        <div style="font-weight:700;font-size:14px">${esc(v.t)}</div>
        <div class="muted" style="margin-top:3px">UP 主：${esc(v.up)} · ${esc(v.dur)}</div>
      </div>
      <a class="btn btn-sm btn-primary" href="${v.url}" target="_blank" rel="noopener">前往观看</a>
    </div>`).join('');

  $('#resource-detail-body').innerHTML = body;
  bindQuizEvents();
}

function renderMindmap(m) {
  const branches = m.branches.map((b) => `
    <div class="mm-branch">
      <div class="mm-node head">${esc(b.head)}</div>
      ${b.leaves.map((l) => `<div class="mm-leaf">${esc(l)}</div>`).join('')}
    </div>`).join('');
  return `<div class="mindmap"><div class="mm-root">${esc(m.root)}</div><div class="mm-tree">${branches}</div></div>`;
}

function renderQuiz(quiz) {
  let html = '';
  quiz.forEach((q, qi) => {
    if (q.kind === 'subjective') {
      html += `
        <div class="quiz-question">
          <div class="q-type">主观题 · LLM 判分</div>
          <div class="q-title">${qi + 1}. ${esc(q.q)}</div>
          <div class="quiz-subjective">
            <textarea placeholder="写下你的回答…" data-subjective="${qi}"></textarea>
            <button class="btn btn-sm btn-primary quiz-submit" data-submit="${qi}" style="margin-top:8px">提交给 LLM 判分</button>
            <div class="subjective-result" data-subresult="${qi}" style="margin-top:8px"></div>
          </div>
        </div>`;
    } else {
      const typeLabel = q.kind === 'judge' ? '判断题' : '单选题';
      html += `
        <div class="quiz-question" data-quiz="${qi}" data-answer="${q.answer}">
          <div class="q-type">${typeLabel} · 自动判分</div>
          <div class="q-title">${qi + 1}. ${esc(q.q)}</div>
          ${q.options.map((o, oi) => `
            <label class="quiz-option" data-opt="${oi}">
              <input type="radio" name="quiz-${qi}" value="${oi}"> ${esc(o)}
            </label>`).join('')}
        </div>`;
    }
  });
  const hasObjective = quiz.some((q) => q.kind !== 'subjective');
  if (hasObjective) html += `<button class="btn btn-primary quiz-submit" id="quiz-check">提交客观题</button><div id="quiz-score" class="quiz-score"></div>`;
  return html;
}

function bindQuizEvents() {
  const check = $('#quiz-check');
  if (check) check.addEventListener('click', () => {
    let correct = 0, total = 0;
    $$('.quiz-question[data-answer]').forEach((qq) => {
      total++;
      const ans = +qq.dataset.answer;
      const chosen = qq.querySelector('input:checked');
      qq.querySelectorAll('.quiz-option').forEach((opt) => {
        opt.classList.remove('correct', 'wrong');
      });
      if (chosen) {
        const oi = +chosen.value;
        if (oi === ans) { correct++; qq.querySelector(`.quiz-option[data-opt="${oi}"]`).classList.add('correct'); }
        else { qq.querySelector(`.quiz-option[data-opt="${oi}"]`).classList.add('wrong'); qq.querySelector(`.quiz-option[data-opt="${ans}"]`).classList.add('correct'); }
      }
    });
    const score = total ? Math.round((correct / total) * 100) : 0;
    const el = $('#quiz-score');
    el.textContent = `客观题得分：${correct}/${total}（${score} 分）`;
    el.className = 'quiz-score ' + (score >= 60 ? 'good' : '');
  });

  $$('[data-submit]').forEach((b) => b.addEventListener('click', () => {
    const idx = +b.dataset.submit;
    const text = document.querySelector(`[data-subjective="${idx}"]`).value.trim();
    const box = document.querySelector(`[data-subresult="${idx}"]`);
    if (!text) { box.innerHTML = '<span class="muted">请先写下你的回答。</span>'; return; }
    box.innerHTML = '<span class="muted">评估分析师 · LLM 判分中…</span>';
    setTimeout(() => {
      const q = null; // 从 DETAILS 取参考要点
      const ref = (DETAILS['quiz-btree'].quiz.find((x) => x.kind === 'subjective')?.ref) || (DETAILS['quiz-sort'].quiz.find((x) => x.kind === 'subjective')?.ref) || '';
      const detail = ref || '';
      const quizList = Object.values(DETAILS).flatMap((d) => d.quiz || []);
      const subj = quizList.find((x, i) => x.kind === 'subjective' && i === idx) || quizList.find((x) => x.kind === 'subjective');
      const refText = subj?.ref || '';
      box.innerHTML = `<div style="background:var(--green-soft);border-radius:9px;padding:12px;font-size:13px;line-height:1.7">
        <b>评估结果：已作答（主观题评分仅供参考）</b><br><span style="color:#374151">${esc(refText)}</span></div>`;
    }, 1200);
  }));
}

function highlightCode(code) {
  return esc(code)
    .replace(/\b(def|class|return|if|else|import|from|while|for|in|print|not|and|or|None|True|False)\b/g, '<span class="kw">$1</span>')
    .replace(/\b(def|class)\s+([a-zA-Z_]\w*)/g, '$1 <span class="fn">$2</span>')
    .replace(/(#[^\n]*)/g, '<span class="cm">$1</span>')
    .replace(/('.*?'|".*?")/g, '<span class="str">$1</span>');
}

/* ---------- 答疑 ---------- */
function qaWelcome() {
  appendMsg($('#qa-chat'), 'bot', '你好，我是答疑老师 👋 学习中遇到任何问题都可以问我，我会用文字给你讲清楚。', '答疑老师');
}
function submitQA() {
  const input = $('#qa-input');
  const text = input.value.trim();
  if (!text) return;
  appendMsg($('#qa-chat'), 'user', text);
  input.value = '';
  const found = QA_KNOWLEDGE.find(([k]) => text.includes(k));
  const ans = found ? found[1] : QA_FALLBACK;
  setTimeout(() => appendMsg($('#qa-chat'), 'bot', ans, '答疑老师'), 600);
}

/* ---------- 学习评估 ---------- */
function renderAssessment() {
  const radarData = [
    { label: '二叉树', value: 74 }, { label: '栈与队列', value: 88 },
    { label: '图', value: 42 }, { label: '排序', value: 65 },
    { label: '查找', value: 58 }, { label: '复杂度', value: 70 },
  ];
  drawRadar(radarData);
  $('#assess-conclusion').innerHTML = `
    <b>总体结论：</b>你对「栈与队列」「二叉树」掌握较好，但「图」相关知识点较为薄弱，建议重点补强。<br>
    <b>易错点提醒：</b>根据你的画像，注意「细节遗漏」类错误，做练习时多检查边界条件。`;
  $('#assess-stats').innerHTML = `
    <div class="stat-item"><div class="stat-num">12</div><div class="stat-label">已完成资源</div></div>
    <div class="stat-item"><div class="stat-num">68%</div><div class="stat-label">练习正确率</div></div>
    <div class="stat-item"><div class="stat-num">5</div><div class="stat-label">薄弱知识点</div></div>`;
  // 调整后的推送策略
  const push = ['doc-btree', 'mm-btree', 'video-ds'].map((id) => RESOURCES.find((r) => r.id === id));
  $('#assess-push').innerHTML = resourceCards(push);
}

function drawRadar(data) {
  const size = 300, cx = size / 2, cy = size / 2, r = 115;
  const n = data.length;
  const angle = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / n;
  const pt = (i, radius) => [cx + radius * Math.cos(angle(i)), cy + radius * Math.sin(angle(i))];

  let svg = `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`;
  // 网格
  for (let lv = 1; lv <= 4; lv++) {
    const rr = (r / 4) * lv;
    const poly = data.map((_, i) => pt(i, rr).map((v) => v.toFixed(1)).join(',')).join(' ');
    svg += `<polygon points="${poly}" fill="none" stroke="#e8eaf0" stroke-width="1"/>`;
  }
  // 轴线
  data.forEach((_, i) => {
    const [x, y] = pt(i, r);
    svg += `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="#e8eaf0"/>`;
  });
  // 数据多边形
  const dataPoly = data.map((d, i) => pt(i, (r * d.value) / 100).map((v) => v.toFixed(1)).join(',')).join(' ');
  svg += `<polygon points="${dataPoly}" fill="rgba(79,70,229,.18)" stroke="#4f46e5" stroke-width="2"/>`;
  data.forEach((d, i) => {
    const [x, y] = pt(i, (r * d.value) / 100);
    svg += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.5" fill="#4f46e5"/>`;
  });
  // 标签
  data.forEach((d, i) => {
    const [x, y] = pt(i, r + 22);
    svg += `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" font-size="12" text-anchor="middle" fill="#6b7280">${d.label} ${d.value}</text>`;
  });
  svg += '</svg>';
  $('#radar-box').innerHTML = svg;
}

/* ---------- 多智能体协作动画（环形） ---------- */
let orbitSeq = 0;
function renderOrbit(container, size = 300) {
  const cx = size / 2, cy = size / 2;
  const coreR = Math.round(size * 0.1);
  const orbitR = Math.round(size / 2 - 46);
  const nodeR = Math.round(size * 0.075);
  const agents = [
    { icon: '🔍', name: '学情分析', color: '#2908ff' },
    { icon: '📖', name: '课程讲解', color: '#00b5c2' },
    { icon: '✏️', name: '出题判分', color: '#2908ff' },
    { icon: '🧭', name: '路径规划', color: '#00b5c2' },
    { icon: '📤', name: '资源推送', color: '#16a34a' },
    { icon: '📊', name: '学习评估', color: '#2908ff' },
  ];
  const n = agents.length;
  const angle = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / n;
  const pos = (i, r) => [cx + r * Math.cos(angle(i)), cy + r * Math.sin(angle(i))];

  let svg = `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`;
  svg += `<circle class="orbit-core-pulse" cx="${cx}" cy="${cy}" r="${coreR}" fill="none" stroke="#2908ff" stroke-width="2"/>`;
  agents.forEach((a, i) => {
    const [x, y] = pos(i, orbitR);
    svg += `<line class="orbit-link" style="animation-delay:${(i * 0.22).toFixed(2)}s" x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="${a.color}" stroke-width="2" stroke-linecap="round"/>`;
  });
  svg += `<circle cx="${cx}" cy="${cy}" r="${coreR}" fill="#2908ff"/>`;
  svg += `<text x="${cx}" y="${cy + coreR * 0.28}" text-anchor="middle" font-size="${coreR}">🎓</text>`;
  agents.forEach((a, i) => {
    const [x, y] = pos(i, orbitR);
    svg += `<g class="orbit-node"><circle cx="${x}" cy="${y}" r="${nodeR}" fill="#ffffff" stroke="${a.color}" stroke-width="2"/><text x="${x}" y="${y + 5}" text-anchor="middle" font-size="${Math.round(nodeR * 0.66)}">${a.icon}</text><text x="${x}" y="${y + nodeR + 15}" text-anchor="middle" font-size="11" fill="#737373" font-weight="700">${a.name}</text></g>`;
  });
  svg += '</svg>';
  container.innerHTML = svg;
}

/* ---------- 我的画像 ---------- */
function renderProfile() {
  $('#profile-updated').textContent = '最近更新：' + (state.profile.updatedAt || '刚刚');
  $('#profile-dims').innerHTML = PROFILE_DIMS.map((d) => {
    const v = state.profile[d.key];
    return `
      <div class="pdim-card">
        <div class="pdim-icon">${d.icon}</div>
        <div class="pdim-name">${d.name}</div>
        <div class="pdim-desc">${esc(v?.text || '待补充')}</div>
        <div class="pdim-bar"><div class="pdim-fill" style="width:${v?.score ?? 50}%"></div></div>
      </div>`;
  }).join('');
}

/* ---------- 管理界面：用户管理 ---------- */
async function renderUsers() {
  try {
    const users = await api('/users/');
    $('#user-list').innerHTML = `
      <table class="user-table">
        <thead><tr><th>账号</th><th>昵称</th><th>邮箱</th><th>专业</th><th>角色</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>${users.map((u) => `
          <tr>
            <td>${esc(u.account)}</td>
            <td>${esc(u.nickname)}</td>
            <td>${esc(u.email || '-')}</td>
            <td>${esc(u.major || '-')}</td>
            <td>${(u.roles || []).map((r) => `<span class="role-tag">${esc(r.name)}</span>`).join('')}</td>
            <td><span class="status-badge ${u.is_active ? 'on' : 'off'}">${u.is_active ? '正常' : '禁用'}</span></td>
            <td><div class="row-actions">
              <button data-uedit="${u.id}">编辑</button>
              <button class="danger" data-udel="${u.id}">删除</button>
            </div></td>
          </tr>`).join('')}</tbody>
      </table>`;
    $$('#user-list [data-uedit]').forEach((b) => (b.onclick = () => openUserModal(+b.dataset.uedit, users)));
    $$('#user-list [data-udel]').forEach((b) => (b.onclick = () => delUser(+b.dataset.udel)));
  } catch (e) { $('#user-list').innerHTML = `<p class="muted">加载失败：${esc(e.message)}</p>`; }
}

async function openUserModal(id, users) {
  const roles = await api('/roles/');
  const u = id ? users.find((x) => x.id === id) : null;
  $('#user-modal-title').textContent = u ? '编辑用户' : '新增用户';
  $('#user-m-id').value = u ? u.id : '';
  $('#user-m-account').value = u ? u.account : '';
  $('#user-m-nickname').value = u ? u.nickname : '';
  $('#user-m-email').value = u ? (u.email || '') : '';
  $('#user-m-major').value = u ? (u.major || '') : '';
  $('#user-m-password').value = '';
  const selected = u ? (u.roles || []).map((r) => r.id) : [];
  $('#user-m-roles').innerHTML = roles.map((r) => `
    <label class="checkbox-item"><input type="checkbox" value="${r.id}" ${selected.includes(r.id) ? 'checked' : ''}> ${esc(r.name)}</label>`).join('');
  $('#user-modal').hidden = false;
}

async function saveUser() {
  const id = $('#user-m-id').value;
  const account = $('#user-m-account').value.trim();
  const nickname = $('#user-m-nickname').value.trim() || '同学';
  const email = $('#user-m-email').value.trim() || null;
  const major = $('#user-m-major').value.trim();
  const password = $('#user-m-password').value;
  const role_ids = $$('#user-m-roles input:checked').map((i) => +i.value);
  try {
    if (id) {
      const body = { nickname, email, major, role_ids };
      if (password) body.password = password;
      await api('/users/' + id, 'PUT', body);
    } else {
      if (!account || !password) { alert('新增用户需填写学号和密码'); return; }
      await api('/users/', 'POST', { account, password, nickname, email, major, role_ids });
    }
    $('#user-modal').hidden = true;
    renderUsers();
  } catch (e) { alert(e.message); }
}

async function delUser(id) {
  if (!confirm('确认删除该用户？')) return;
  try { await api('/users/' + id, 'DELETE'); renderUsers(); } catch (e) { alert(e.message); }
}

/* ---------- 管理界面：角色管理 ---------- */
async function renderRoles() {
  try {
    const roles = await api('/roles/');
    $('#role-list').innerHTML = roles.map((r) => `
      <div class="role-card">
        <div class="rc-info">
          <div class="rc-name">${esc(r.name)}</div>
          <div class="rc-code">编码：${esc(r.code)}</div>
          <div class="rc-desc">${esc(r.description || '')}</div>
          <div class="rc-perms">${(r.permissions || []).map((p) => `<span class="role-tag">${esc(p.name)}</span>`).join('')}</div>
        </div>
        <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end">
          ${r.is_system ? '<span class="sys-badge">系统内置</span>' : ''}
          <div class="row-actions">
            <button data-redit="${r.id}">编辑</button>
            ${r.is_system ? '' : `<button class="danger" data-rdel="${r.id}">删除</button>`}
          </div>
        </div>
      </div>`).join('');
    $$('#role-list [data-redit]').forEach((b) => (b.onclick = () => openRoleModal(+b.dataset.redit, roles)));
    $$('#role-list [data-rdel]').forEach((b) => (b.onclick = () => delRole(+b.dataset.rdel)));
  } catch (e) { $('#role-list').innerHTML = `<p class="muted">加载失败：${esc(e.message)}</p>`; }
}

async function openRoleModal(id, roles) {
  const perms = await api('/roles/permissions');
  const r = id ? roles.find((x) => x.id === id) : null;
  $('#role-modal-title').textContent = r ? '编辑角色' : '新建角色';
  $('#role-m-id').value = r ? r.id : '';
  $('#role-m-name').value = r ? r.name : '';
  $('#role-m-code').value = r ? r.code : '';
  $('#role-m-desc').value = r ? (r.description || '') : '';
  const selected = r ? (r.permissions || []).map((p) => p.id) : [];
  $('#role-m-perms').innerHTML = perms.map((p) => `
    <label class="checkbox-item"><input type="checkbox" value="${p.id}" ${selected.includes(p.id) ? 'checked' : ''}> ${esc(p.name)}</label>`).join('');
  $('#role-modal').hidden = false;
}

async function saveRole() {
  const id = $('#role-m-id').value;
  const name = $('#role-m-name').value.trim();
  const code = $('#role-m-code').value.trim();
  const description = $('#role-m-desc').value.trim();
  const permission_ids = $$('#role-m-perms input:checked').map((i) => +i.value);
  if (!name || !code) { alert('请填写角色名称和编码'); return; }
  try {
    if (id) { await api('/roles/' + id, 'PUT', { name, description, permission_ids }); }
    else { await api('/roles/', 'POST', { name, code, description, permission_ids }); }
    $('#role-modal').hidden = true;
    renderRoles();
  } catch (e) { alert(e.message); }
}

async function delRole(id) {
  if (!confirm('确认删除该角色？')) return;
  try { await api('/roles/' + id, 'DELETE'); renderRoles(); } catch (e) { alert(e.message); }
}

function initAdmin() {
  $('#user-add-btn').addEventListener('click', () => openUserModal(null, []));
  $('#user-modal-save').addEventListener('click', saveUser);
  $('#user-modal-cancel').addEventListener('click', () => { $('#user-modal').hidden = true; });
  $('#role-add-btn').addEventListener('click', () => openRoleModal(null, []));
  $('#role-modal-save').addEventListener('click', saveRole);
  $('#role-modal-cancel').addEventListener('click', () => { $('#role-modal').hidden = true; });
}

/* ---------- 事件委托：资源点击 ---------- */
function initDelegation() {
  document.addEventListener('click', (e) => {
    const card = e.target.closest('[data-res]');
    if (card) { openResource(card.dataset.res); }
  });
}

/* ---------- 启动 ---------- */
function init() {
  initAuth();
  initMain();
  initDelegation();
  initAdmin();
  renderOrbit($('#auth-orbit'), 280);
  renderOrbit($('#hero-orbit'), 300);
  $('#onboard-send').addEventListener('click', () => {
    const v = $('#onboard-input').value.trim();
    if (v) { submitOnboard(v); $('#onboard-input').value = ''; }
  });
  $('#onboard-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') { $('#onboard-send').click(); } });
  $('#onboard-skip').addEventListener('click', () => finishOnboarding(true));

  refreshCaptcha('login');
  refreshCaptcha('reg');

  const token = load(STORE.token, null);
  if (token) {
    api('/auth/me').then((user) => {
      const perms = (user.roles || []).flatMap((r) => (r.permissions || []).map((p) => p.code));
      enterApp(user, token, perms);
    }).catch(() => {
      localStorage.removeItem(STORE.token);
      localStorage.removeItem(STORE.user);
      showView('auth');
    });
    return;
  }
  showView('auth');
}

document.addEventListener('DOMContentLoaded', init);
