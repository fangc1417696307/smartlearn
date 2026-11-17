export const RES_TYPES = [
  { key: 'all', label: '全部', icon: '🗂️' },
  { key: 'doc', label: '讲解文档', icon: '📄' },
  { key: 'mindmap', label: '思维导图', icon: '🧠' },
  { key: 'quiz', label: '练习题', icon: '✏️' },
  { key: 'reading', label: '拓展阅读', icon: '📚' },
  { key: 'code', label: '代码案例', icon: '💻' },
  { key: 'video', label: 'B站视频', icon: '🎬' },
]

export const RESOURCES = [
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
]

export const RESOURCE_DETAILS = {
  'doc-btree': { type: '讲解文档', html: `<p>二叉树（Binary Tree）是每个结点最多有两个子结点的树结构，是计算机科学中最基础也最重要的数据结构之一。</p><h4>一、基本性质</h4><ul><li>第 i 层（i≥1）至多有 <b>2^(i-1)</b> 个结点。</li><li>深度为 k 的二叉树至多有 <b>2^k - 1</b> 个结点。</li><li>若叶子数为 n0，度为 2 的结点数为 n2，则 <b>n0 = n2 + 1</b>。</li></ul><div class="callout">💡 易错提醒：完全二叉树不一定是满二叉树，满二叉树一定是完全二叉树。</div><h4>二、遍历方式</h4><p>前序（根左右）、中序（左根右）、后序（左右根）、层序（逐层）。递归实现简单直观，迭代实现需借助栈。</p>` },
  'doc-stack': { type: '讲解文档', html: `<p>栈（Stack）是「后进先出」（LIFO）的受限线性表；队列（Queue）是「先进先出」（FIFO）的受限线性表。</p><h4>栈的应用</h4><ul><li>函数调用栈、表达式求值、括号匹配、递归。</li></ul><h4>队列的应用</h4><ul><li>任务调度、广度优先搜索（BFS）、消息队列。</li></ul>` },
  'mm-btree': { type: '思维导图', mindmap: { root: '二叉树', branches: [{ head: '基本概念', leaves: ['定义', '结点的度', '深度 / 高度'] }, { head: '重要性质', leaves: ['2^(i-1)', '2^k - 1', 'n0 = n2 + 1'] }, { head: '遍历方式', leaves: ['前序', '中序', '后序', '层序'] }, { head: '特殊形态', leaves: ['满二叉树', '完全二叉树', '二叉搜索树', '平衡树(AVL)'] }] } },
  'mm-overview': { type: '思维导图', mindmap: { root: '数据结构', branches: [{ head: '线性结构', leaves: ['数组', '链表', '栈', '队列'] }, { head: '树形结构', leaves: ['二叉树', '堆', '哈夫曼树'] }, { head: '图形结构', leaves: ['邻接矩阵', '邻接表'] }, { head: '查找/排序', leaves: ['二分查找', '快排', '归并', '堆排'] }] } },
  'quiz-btree': { type: '练习题', quiz: [
    { kind: 'single', q: '二叉树的第 i 层（i≥1）至多有多少个结点？', options: ['2^i - 1', '2^(i-1)', '2^(i+1)', 'i^2'], answer: 1 },
    { kind: 'single', q: '深度为 4 的满二叉树，结点总数是？', options: ['7', '8', '15', '16'], answer: 2 },
    { kind: 'judge', q: '完全二叉树一定是满二叉树。', options: ['正确', '错误'], answer: 1 },
    { kind: 'subjective', q: '简述二叉搜索树（BST）与平衡二叉树（AVL）的主要区别，以及 AVL 为什么能保证 O(log n) 的查找效率。', ref: '要点：① BST 仅要求「左小右大」，最坏会退化成链表（O(n)）；② AVL 在 BST 基础上增加平衡因子约束（左右子树高度差 ≤1），通过旋转维持平衡；③ 平衡保证树高约为 O(log n)，查找、插入、删除均为 O(log n)。' },
  ] },
  'quiz-sort': { type: '练习题', quiz: [
    { kind: 'single', q: '快速排序在平均情况下的时间复杂度是？', options: ['O(n)', 'O(n log n)', 'O(n^2)', 'O(log n)'], answer: 1 },
    { kind: 'single', q: '下列哪种排序是稳定排序？', options: ['快速排序', '堆排序', '归并排序', '选择排序'], answer: 2 },
  ] },
  'reading-rbtree': { type: '拓展阅读', reading: [
    { t: '从 AVL 到红黑树：平衡的两种哲学', s: '《算法导论》第 13 章', d: 'AVL 追求严格平衡（查询快、插入旋转多），红黑树追求弱平衡（插入更高效）。' },
    { t: '红黑树的五条性质与旋转', s: '图解红黑树', d: '掌握「黑高」的概念，理解插入后的颜色调整与旋转修复过程。' },
    { t: '工程实践：Java TreeMap 与 Linux CFS', s: '延伸阅读', d: '红黑树在工业级实现中的典型应用。' },
  ] },
  'reading-algo': { type: '拓展阅读', reading: [
    { t: '分治法与递归树分析', s: '《算法导论》第 4 章', d: '用递归树方法推导归并排序的时间复杂度。' },
    { t: '动态规划入门', s: '《算法导论》第 15 章', d: '从「钢条切割」问题理解最优子结构与重叠子问题。' },
  ] },
  'code-traverse': { type: '代码案例', code: { lang: 'Python', source: `class Node:
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
    print(root.val, end=' ')`, note: '递归遍历是最直观的写法。若树很深，可改写为「显式栈」的迭代实现避免递归深度过大。' } },
  'code-heap': { type: '代码案例', code: { lang: 'Python', source: `import heapq

h = []
heapq.heappush(h, 5)
heapq.heappush(h, 1)
heapq.heappush(h, 3)
print(heapq.heappop(h))   # 1（弹出最小值）`, note: '堆是一棵完全二叉树，通常用数组存储；常用于 Top-K 问题与优先队列。' } },
  'video-ds': { type: 'B站视频', videos: [
    { t: '数据结构与算法基础（王卓老师）', up: '青岛大学 · 王卓', url: 'https://search.bilibili.com/all?keyword=%E6%95%B0%E6%8D%AE%E7%BB%93%E6%9E%84%20%E7%8E%8B%E5%8D%93', dur: '系列课 · 100+ 集' },
    { t: '王道计算机考研 · 数据结构', up: '王道计算机教育', url: 'https://search.bilibili.com/all?keyword=%E7%8E%8B%E9%81%93%20%E6%95%B0%E6%8D%AE%E7%BB%93%E6%9E%84', dur: '考研精讲' },
    { t: '左程云 · 算法与数据结构进阶', up: '左程云', url: 'https://search.bilibili.com/all?keyword=%E5%B7%A6%E7%A8%8B%E4%BA%91%20%E7%AE%97%E6%B3%95', dur: '进阶 · 面试算法' },
  ] },
}

export const PATH_TEMPLATE = [
  { id: 1, title: '复习基础：线性表与数组', desc: '回顾线性表存储结构与基本操作，为树结构打基础', res: ['doc-stack', 'code-heap'] },
  { id: 2, title: '掌握二叉树核心概念', desc: '理解二叉树定义、性质与存储结构', res: ['doc-btree', 'mm-btree', 'video-ds'] },
  { id: 3, title: '攻克二叉树三种遍历', desc: '前序 / 中序 / 后序遍历的递归与迭代实现', res: ['code-traverse', 'quiz-btree'] },
  { id: 4, title: '专项练习与查漏补缺', desc: '通过练习巩固，标记易错点并回看讲解', res: ['quiz-btree', 'quiz-sort'] },
  { id: 5, title: '拓展：平衡树与进阶结构', desc: '了解 AVL、红黑树与堆的应用', res: ['reading-rbtree', 'code-heap'] },
]

export const QA_KNOWLEDGE = [
  ['二叉树', '二叉树的三种遍历核心口诀：前序「根左右」、中序「左根右」、后序「左右根」。递归实现最直观；若要避免递归栈溢出，可用「显式栈」模拟。层序遍历则需借助队列逐层访问。'],
  ['平衡', 'AVL 通过「平衡因子」（左右子树高度差 ≤1）约束树形，插入导致失衡时用 LL / RR / LR / RL 四种旋转恢复平衡，从而保证树高约为 O(log n)。'],
  ['堆', '堆是一棵「完全二叉树」，用数组存储。最小堆满足「父结点 ≤ 子结点」。堆顶即最值，插入用上浮、删除用下沉，复杂度 O(log n)。'],
  ['复杂度', '常见复杂度从小到大：O(1) < O(log n) < O(n) < O(n log n) < O(n²) < O(2ⁿ)。'],
]
