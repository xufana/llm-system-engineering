/* ---------- shared: theme, presentation mode, chips, reveals ---------- */
(function(){
  const root = document.documentElement, body = document.body;
  let theme = 'system';
  try { theme = localStorage.getItem('llm-course-theme') || 'system'; } catch(e){}
  function applyTheme(){
    if(theme === 'system') root.removeAttribute('data-theme'); else root.setAttribute('data-theme', theme);
    document.getElementById('themeBtn').textContent = theme === 'system' ? 'Тема: система' : (theme === 'dark' ? 'Тема: тёмная' : 'Тема: светлая');
  }
  applyTheme();
  document.getElementById('themeBtn').addEventListener('click', () => {
    theme = theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system';
    try { localStorage.setItem('llm-course-theme', theme); } catch(e){}
    applyTheme();
  });
  const pBtn = document.getElementById('presentBtn');
  function setPresent(on){ body.classList.toggle('present', on); pBtn.setAttribute('aria-pressed', on); pBtn.textContent = on ? 'Режим: презентация' : 'Режим: прокрутка'; }
  pBtn.addEventListener('click', () => setPresent(!body.classList.contains('present')));
  const tb = document.getElementById('teacherBtn');
  tb.onclick = () => { const on = !body.classList.contains('teacher'); body.classList.toggle('teacher', on); tb.setAttribute('aria-pressed', on); tb.textContent = on ? 'Ответы: показаны' : 'Ответы: скрыты'; document.dispatchEvent(new Event('teacher')); };

  const secs = Array.from(document.querySelectorAll('main > section'));
  const chips = document.getElementById('chips');
  secs.forEach(s => { const a = document.createElement('a'); a.className = 'chip'; a.href = '#' + s.id; a.textContent = s.dataset.short || s.id; chips.appendChild(a); });
  const chipEls = Array.from(chips.children);
  if('IntersectionObserver' in window){
    const io = new IntersectionObserver(entries => { entries.forEach(en => { if(en.isIntersecting){ const i = secs.indexOf(en.target); chipEls.forEach((c,j) => c.classList.toggle('active', i === j)); } }); }, {rootMargin:'-40% 0px -55% 0px'});
    secs.forEach(s => io.observe(s));
  }
  document.addEventListener('keydown', e => {
    if(!body.classList.contains('present')) return;
    if(['INPUT','SELECT','TEXTAREA'].includes(document.activeElement && document.activeElement.tagName)) return;
    if(['ArrowRight','PageDown','ArrowLeft','PageUp'].includes(e.key)){
      e.preventDefault(); const y = window.scrollY + 60; let cur = 0;
      secs.forEach((s,i) => { if(s.offsetTop <= y + 5) cur = i; });
      const next = (e.key === 'ArrowRight' || e.key === 'PageDown') ? Math.min(cur + 1, secs.length - 1) : Math.max(cur - 1, 0);
      secs[next].scrollIntoView({behavior:'smooth', block:'start'});
    }
  });
  document.querySelectorAll('.qz').forEach(q => { const b = q.querySelector('button'); if(b) b.onclick = () => { q.classList.toggle('open'); b.textContent = q.classList.contains('open') ? 'Скрыть ответ' : 'Показать ответ'; }; });
})();

/* ---------- helpers ---------- */
const $ = id => document.getElementById(id);
function el(tag, cls, html){ const e = document.createElement(tag); if(cls) e.className = cls; if(html != null) e.innerHTML = html; return e; }
const NB = ' ';
function fmt(n){ return Math.round(n).toLocaleString('ru-RU'); }
function dec(n, d){ return n.toLocaleString('ru-RU', {minimumFractionDigits:d, maximumFractionDigits:d}); }
function pct(x, d){ return dec(x * 100, d == null ? 0 : d) + NB + '%'; }
function big(n){
  if(n >= 1e6) return (n/1e6).toLocaleString('ru-RU',{maximumFractionDigits:1}) + NB + 'млн';
  if(n >= 1e4) return (n/1e3).toLocaleString('ru-RU',{maximumFractionDigits:0}) + NB + 'тыс.';
  return fmt(n);
}
function statBox(a){ const s = el('div', 'stat'); s.innerHTML = '<span class="l">' + a[0] + '</span><span class="n">' + a[1] + '</span><span class="s">' + (a[2] || '') + '</span>'; return s; }
function mulberry32(a){ return function(){ a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function teacher(){ return document.body.classList.contains('teacher'); }

/* ---------- 1. дерево метрик ---------- */
(function(){
  const SLOTS = [['ns','North-star'],['proxy','Прокси'],['lim','Ограничивающая'],['no','Не берём']];
  const A = [
    {id:1, t:'Агент с побочными эффектами', m:'возвраты и отмены заказов',
     brief:'Помощник по заказам: оформляет возвраты и отмены по просьбе клиента. Заказчик платит за обращения, закрытые без оператора и без вреда.',
     mets:[
       ['Доля обращений, закрытых без оператора (в проде)', 'ns', 'За это платят. Считается только на живом трафике — поэтому нужны прокси ниже.'],
       ['Доля задач с верным конечным состоянием среды на наборе из 50 задач', 'proxy', 'Главный офлайн-прокси: заказ действительно отменён или возвращён. Проверяется детерминированно, без судьи.'],
       ['pass^3 на том же наборе', 'proxy', 'Надёжность: задача решается не иногда, а каждый раз. Для продукта с действиями важнее pass@k.'],
       ['Доля запрещённых действий', 'lim', 'Должна быть нулём. Это не цель, а граница: улучшение других метрик её не оправдывает.'],
       ['Медианное число шагов и стоимость задачи', 'lim', 'Ограничение бюджета. Агент, решающий задачу за 40 шагов, не годится, даже если решает.'],
       ['Средний балл судьи за текст финального отчёта агента', 'no', 'Агент может написать «возврат оформлен», ничего не сделав. Красивый отчёт при неверном состоянии — главная ловушка архетипа.'],
       ['Число вызовов инструментов в день', 'no', 'Это нагрузка, не качество. В дашборд инфраструктуры — да, в дерево метрик — нет.']
     ]},
    {id:2, t:'Судья как продукт', m:'оценка чужих ответов по rubric',
     brief:'Сервис оценивает ответы чужого бота по rubric заказчика. Заказчик платит за то, что решения сервиса совпадают с решениями его собственных асессоров.',
     mets:[
       ['Взвешенная каппа с разметкой заказчика на отложенном наборе', 'ns', 'Продукт — согласие с людьми заказчика. Взвешенная, потому что шкала порядковая; отложенный набор, потому что на dev-наборе подбирали промпт.'],
       ['Корреляция с разметкой заказчика на 30 новых примерах каждую неделю', 'proxy', 'Дешёвый еженедельный сигнал, что согласие не уплыло: заказчик размечает немного, но регулярно.'],
       ['Доля вердиктов, не изменившихся при перестановке ответов', 'lim', 'Смещение позиции — ограничение: судья, который меняет мнение от порядка, не продаётся, какая бы ни была каппа.'],
       ['Стоимость одного вердикта', 'lim', 'Ограничение бюджета: заказчик сравнивает с ценой асессора.'],
       ['Доля ответов «не могу оценить»', 'lim', 'Отказ лучше выдумки, но слишком частый отказ — бесполезный продукт. Граница, а не цель.'],
       ['Согласие с GPT-судьёй на тех же примерах', 'no', 'Судья судит судью. Если ваш судья той же семьи — это самопредпочтение, а не качество.'],
       ['Каппа на dev-наборе, на котором подбирали промпт', 'no', 'Набор для подбора и для отчёта один и тот же — число будет завышено и ничего не предскажет.']
     ]},
    {id:3, t:'Генератор eval-сетов', m:'вопросы к базе знаний клиента',
     brief:'Сервис генерирует наборы вопросов к базе знаний клиента. Заказчик платит за то, что набор ловит регрессии, которые заметил бы человек.',
     mets:[
       ['Доля инцидентов из прода клиента, которые набор обнаруживает', 'ns', 'Набор нужен, чтобы ловить поломки. Проверяется ретроспективно: прогнать набор на версиях системы до и после известного инцидента.'],
       ['Доля сгенерированных примеров, прошедших ручную проверку', 'proxy', 'Дешёвый прокси качества примера: вопрос осмыслен, ответ находится в документе, цитата точная.'],
       ['Покрытие таксономии: доля типов вопросов, представленных в наборе', 'proxy', 'Набор из одних простых фактов регрессии не ловит. Покрытие типов предсказывает чувствительность.'],
       ['Доля дубликатов и почти-дубликатов', 'lim', 'Граница: дубликаты раздувают набор и завышают уверенность.'],
       ['Цена одного примера', 'lim', 'Ограничение бюджета — генерация тоже вызовы модели.'],
       ['Оценка судьёй «качество вопроса» по шкале 1–5', 'no', 'Генератор и судья одной семьи — генератор хвалит сам себя. Как слабый сигнал при другой семье — возможно; как метрика продукта — нет.'],
       ['Число сгенерированных примеров', 'no', 'Объём — не качество. Тысяча вопросов, не ловящих ни одной регрессии, бесполезнее тридцати.']
     ]}
  ];
  const state = {}; A.forEach(a => state[a.id] = {ch:{}, shown:false});
  let cur = A[0];
  function drawPick(){
    const p = $('apick'); p.innerHTML = '';
    A.forEach(a => { const b = el('button', '', '<span class="t">' + a.t + '</span><span class="m">' + a.m + '</span>'); b.setAttribute('role', 'tab'); b.setAttribute('aria-pressed', a === cur); b.onclick = () => { cur = a; draw(); }; p.appendChild(b); });
  }
  function draw(){
    drawPick();
    const st = state[cur.id], shown = st.shown || teacher();
    $('metrics').classList.toggle('shown', shown);
    $('abrief').innerHTML = '<b>' + cur.t + '.</b> ' + cur.brief;
    const box = $('mets'); box.innerHTML = '';
    let hit = 0, done = 0;
    cur.mets.forEach((m, i) => {
      const v = st.ch[i]; if(v) done++; const ok = v === m[1]; if(v && ok) hit++;
      const c = el('div', 'met' + (shown && v ? (ok ? ' hit' : ' miss') : ''));
      c.appendChild(el('div', 'mt', m[0]));
      const o = el('div', 'mo');
      SLOTS.forEach(s => { const b = el('button', shown && s[0] === m[1] ? 'ideal' : '', s[1]); b.setAttribute('aria-pressed', v === s[0]); b.onclick = () => { st.ch[i] = s[0]; draw(); }; o.appendChild(b); });
      c.appendChild(o); c.appendChild(el('div', 'why', m[2])); box.appendChild(c);
    });
    $('mscore').textContent = shown ? 'совпало с разбором: ' + hit + ' из ' + cur.mets.length : (done ? 'размещено ' + done + ' из ' + cur.mets.length : '');
    $('mreveal').textContent = st.shown ? 'Скрыть разбор' : 'Показать разбор';
    const tr = $('mtree'); tr.innerHTML = '<div class="kicker" style="margin-bottom:.3rem">дерево метрик по разбору</div>' + SLOTS.filter(s => s[0] !== 'no').map(s => '<div class="lvl ' + s[0] + '"><span class="k">' + s[1] + '</span>' + cur.mets.filter(m => m[1] === s[0]).map(m => '<span class="m">' + m[0] + '</span>').join('') + '</div>').join('');
  }
  $('mreveal').onclick = () => { state[cur.id].shown = !state[cur.id].shown; draw(); };
  $('mreset').onclick = () => { state[cur.id] = {ch:{}, shown:false}; draw(); };
  document.addEventListener('teacher', draw);
  draw();
})();

/* ---------- 2. каппа ---------- */
(function(){
  const N = 60, K = 5;
  const r1 = mulberry32(11), r2 = mulberry32(23), r3 = mulberry32(37);
  const human = Array.from({length:N}, () => 2 + Math.floor(r1() * 4));
  const noiseU = Array.from({length:N}, () => r2()), noiseSign = Array.from({length:N}, () => r3() < .5 ? -1 : 1);
  function kappa(h, j, weighted){
    const O = Array.from({length:K}, () => Array(K).fill(0));
    h.forEach((v, i) => O[v - 1][j[i] - 1]++);
    const rs = O.map(r => r.reduce((a, b) => a + b, 0)), cs = Array.from({length:K}, (_, c) => O.reduce((a, r) => a + r[c], 0));
    let num = 0, den = 0;
    for(let a = 0; a < K; a++) for(let b = 0; b < K; b++){
      const w = weighted ? ((a - b) * (a - b)) / ((K - 1) * (K - 1)) : (a === b ? 0 : 1);
      num += w * O[a][b]; den += w * rs[a] * cs[b] / N;
    }
    return {k: den ? 1 - num / den : 1, O};
  }
  function draw(){
    const sh = +$('ksh').value, p = +$('kns').value / 100;
    $('kshv').textContent = sh ? '−' + sh : '0'; $('knsv').textContent = Math.round(p * 100) + '%';
    const judge = human.map((v, i) => Math.max(1, Math.min(K, v - sh + (noiseU[i] < p ? noiseSign[i] : 0))));
    const acc = human.reduce((a, v, i) => a + (v === judge[i] ? 1 : 0), 0) / N;
    const ku = kappa(human, judge, false), kw = kappa(human, judge, true);
    const st = $('kstats'); st.innerHTML = '';
    [['accuracy', pct(acc), 'точное совпадение'], ['каппа обычная', dec(ku.k, 2), 'все несовпадения равны'], ['каппа взвешенная', dec(kw.k, 2), 'квадратичные веса']].forEach(a => st.appendChild(statBox(a)));
    const g = $('kgrid'); g.innerHTML = '<div class="h"></div>' + [1,2,3,4,5].map(c => '<div class="h">' + c + '</div>').join('');
    const mx = Math.max(...ku.O.flat());
    for(let a = 1; a < K; a++){ g.insertAdjacentHTML('beforeend', '<div class="h">' + (a + 1) + '</div>'); for(let b = 0; b < K; b++){ const v = ku.O[a][b]; g.insertAdjacentHTML('beforeend', '<div class="c' + (a === b ? ' d' : '') + '" style="background:color-mix(in srgb, var(--accent) ' + Math.round(v / mx * 55) + '%, var(--surface-2))">' + (v || '') + '</div>'); } }
    let note;
    if(sh === 0) note = 'Без сдвига обе каппы близки: судья ошибается случайно, и взвешивание почти ничего не меняет. Это тот случай, когда accuracy не врёт — но только потому, что классы сбалансированы.';
    else if(sh === 1) note = 'Судья систематически занижает на балл. Accuracy и обычная каппа говорят «плохой судья»; взвешенная видит, что порядок ответов он сохраняет. Такого судью калибруют сдвигом на +1, а не выбрасывают.';
    else note = 'Сдвиг на два балла: обычная каппа уходит в ноль или ниже — «хуже случайного», хотя ранжирует судья по-прежнему верно. Взвешенная каппа отличает систематическую ошибку от случайной; обычная — нет.';
    $('knote').textContent = note;
  }
  $('ksh').oninput = $('kns').oninput = draw; draw();
})();

/* ---------- 3. шум против эффекта ---------- */
(function(){
  function draw(){
    const d = +$('nd').value, n = +$('nn').value, sj = +$('nsj').value, si = +$('nsi').value, R = +$('nr').value;
    $('ndv').textContent = dec(d, 2); $('nnv').textContent = n; $('nsjv').textContent = dec(sj, 1); $('nsiv').textContent = dec(si, 1); $('nrv').textContent = R;
    const varPer = si * si + sj * sj / R, se = Math.sqrt(2 * varPer / n), lo = d - 1.96 * se, hi = d + 1.96 * se;
    const mde = 1.96 * se, nNeed = d > 0 ? Math.ceil(2 * varPer * Math.pow(1.96 / d, 2)) : null;
    const sig = lo > 0;
    const W = 760, H = 120, L = 40, Rr = 40, xmin = -1, xmax = 2;
    const X = v => L + (v - xmin) / (xmax - xmin) * (W - L - Rr);
    let g = '';
    for(let v = -1; v <= 2; v += .5){ g += '<line class="gr" x1="' + X(v) + '" x2="' + X(v) + '" y1="20" y2="80"/><text class="tx" x="' + X(v) + '" y="98" text-anchor="middle">' + dec(v, 1) + '</text>'; }
    g += '<line class="zero" x1="' + X(0) + '" x2="' + X(0) + '" y1="12" y2="88"/><text class="tx" x="' + (X(0) + 4) + '" y="14">нет разницы</text>';
    const cl = Math.max(X(xmin), X(lo)), ch = Math.min(X(xmax), X(hi));
    g += '<rect x="' + cl + '" y="40" width="' + Math.max(0, ch - cl) + '" height="20" rx="4" fill="' + (sig ? 'var(--ok-soft)' : 'var(--warm-soft)') + '" stroke="' + (sig ? 'var(--ok)' : 'var(--warm)') + '"/>';
    g += '<circle cx="' + X(Math.min(xmax, d)) + '" cy="50" r="6" fill="' + (sig ? 'var(--ok)' : 'var(--warm)') + '" stroke="var(--surface)" stroke-width="2"/>';
    g += '<text class="lb" x="' + X(Math.min(xmax, d)) + '" y="34" text-anchor="middle">Δ = ' + dec(d, 2) + '</text>';
    g += '<text class="tx" x="' + (W - Rr) + '" y="14" text-anchor="end">разница средних, баллов</text>';
    $('nchart').innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Доверительный интервал разницы средних">' + g + '</svg>';
    const st = $('nstats'); st.innerHTML = '';
    [['стандартная ошибка Δ', dec(se, 2), 'баллов'], ['интервал 95 %', dec(lo, 2) + ' … ' + dec(hi, 2), sig ? 'ноль не внутри' : 'накрывает ноль'], ['различимый эффект', '≥ ' + dec(mde, 2), 'при этих n, σ и R'], ['нужно примеров', nNeed == null ? '—' : fmt(nNeed), 'чтобы увидеть Δ = ' + dec(d, 2)]].forEach(a => st.appendChild(statBox(a)));
    let note = sig ? 'На этих настройках разница видна: интервал не накрывает ноль. ' : 'На этих настройках «B лучше A на ' + dec(d, 2) + '» — не результат: интервал накрывает ноль. ';
    note += 'Повторы судьи делят на √R только σ судьи; разброс примеров они не уменьшают — его уменьшает только число примеров. ';
    if(R > 1 && sj < si) note += 'Сейчас σ примеров больше σ судьи: повторы почти бесполезны, нужен набор побольше.';
    else if(R === 1 && sj > si) note += 'Сейчас шум судьи больше разброса примеров: три-пять повторов сузят интервал заметно дешевле, чем новые примеры с разметкой.';
    $('nnote').textContent = note;
  }
  ['nd','nn','nsj','nsi','nr'].forEach(id => $(id).oninput = draw); draw();
})();

/* ---------- 3a. поправка на ошибки судьи ---------- */
(function(){
  const N = 1000, B = 2000;
  function binom(rnd, n, p){ let k = 0; for(let i = 0; i < n; i++) if(rnd() < p) k++; return k; }
  function gauss(rnd){ return Math.sqrt(-2 * Math.log(1 - rnd())) * Math.cos(2 * Math.PI * rnd()); }
  const clip = v => Math.min(1, Math.max(0, v));
  function draw(){
    const tpr = +$('rgt').value / 100, tnr = +$('rgn').value / 100, p = +$('rgp').value / 100, n = +$('rgl').value;
    $('rgtv').textContent = pct(tpr); $('rgnv').textContent = pct(tnr); $('rgpv').textContent = pct(p); $('rglv').textContent = n;
    const den = tpr + tnr - 1, ok = den > .05;
    const theta = ok ? clip((p + tnr - 1) / den) : p;
    const nPos = Math.max(1, Math.round(n * theta)), nNeg = Math.max(1, n - nPos);
    const rnd = mulberry32(7), sp = Math.sqrt(p * (1 - p) / N), cor = [];
    let bad = 0;
    for(let b = 0; b < B; b++){
      const pS = clip(p + sp * gauss(rnd)), tS = binom(rnd, nPos, tpr) / nPos, nS = binom(rnd, nNeg, tnr) / nNeg, d = tS + nS - 1;
      if(d <= .02){ bad++; continue; }
      cor.push(clip((pS + nS - 1) / d));
    }
    cor.sort((a, b) => a - b);
    const q = f => cor[Math.min(cor.length - 1, Math.floor(f * cor.length))];
    const defined = ok && bad / B < .05;
    const rlo = clip(p - 1.96 * sp), rhi = clip(p + 1.96 * sp), clo = defined ? q(.025) : 0, chi = defined ? q(.975) : 1;

    const W = 760, H = 130, L = 150, Rr = 20, X = v => L + v * (W - L - Rr);
    let g = '';
    for(let v = 0; v <= 1.001; v += .2){ g += '<line class="gr" x1="' + X(v) + '" x2="' + X(v) + '" y1="10" y2="100"/><text class="tx" x="' + X(v) + '" y="118" text-anchor="middle">' + pct(v) + '</text>'; }
    [[22, 'по судье, как есть', rlo, rhi, p, 'warm'], [68, 'с поправкой', clo, chi, theta, defined ? 'ok' : 'bad']].forEach(r => {
      g += '<text class="lb" x="' + (L - 10) + '" y="' + (r[0] + 15) + '" text-anchor="end">' + r[1] + '</text>';
      g += '<rect x="' + X(r[2]) + '" y="' + r[0] + '" width="' + Math.max(2, X(r[3]) - X(r[2])) + '" height="20" rx="4" fill="var(--' + r[5] + '-soft)" stroke="var(--' + r[5] + ')"/>';
      g += '<circle cx="' + X(r[4]) + '" cy="' + (r[0] + 10) + '" r="6" fill="var(--' + r[5] + ')" stroke="var(--surface)" stroke-width="2"/>';
    });
    $('rgchart').innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Доля pass по судье и с поправкой, интервалы 95 %">' + g + '</svg>';

    const st = $('rgstats'); st.innerHTML = '';
    [['доля pass по судье', pct(p), 'на ' + fmt(N) + ' логах'],
     ['с поправкой', ok ? pct(theta) : '—', ok ? 'сдвиг ' + (theta - p >= 0 ? '+' : '−') + dec(Math.abs(theta - p) * 100, 0) + ' п.п.' : 'знаменатель ≈ 0'],
     ['интервал 95 %', defined ? pct(clo) + ' … ' + pct(chi) : 'не определён', 'bootstrap по TPR, TNR и логам'],
     ['fail в разметке', fmt(nNeg), 'по ним оценён TNR']].forEach(a => st.appendChild(statBox(a)));

    let note;
    if(!ok) note = 'TPR + TNR − 1 ≈ 0: судья почти не отличает pass от fail, и поправка делит на ноль. Здесь цифру не исправить — нужно выравнивать самого судью.';
    else {
      note = Math.abs(theta - p) < .015 ? 'Ошибки судьи почти уравновешивают друг друга, и сырая доля близка к исправленной. Но интервал всё равно шире, чем кажется по одному числу. ' :
        (theta < p ? 'Судья мягче людей: часть провалов он засчитывает как pass, и сырая доля завышена. ' : 'Судья строже людей: часть хороших ответов он валит, и сырая доля занижена. ');
      note += 'Интервал «по судье» учитывает только выборку логов. Интервал «с поправкой» учитывает и то, что TPR и TNR сами измерены на ' + n + ' размеченных примерах. ';
      if(!defined) note += 'При такой разметке TPR и TNR в части повторов дают TPR + TNR − 1 ≈ 0, поэтому интервал не определён. Нужно больше разметки.';
      else if(nNeg < 30) note += 'TNR оценён всего по ' + nNeg + ' размеченным fail, и это главный источник ширины. Доразмечайте именно провалы. Ищите их по сигналам, которые не зависят от судьи: жалобы, эскалации, дизлайки.';
      else note += 'Чтобы сузить интервал дальше, нужна разметка, а не новые логи: N = ' + fmt(N) + ' уже почти не вносит неопределённости.';
    }
    $('rgnote').textContent = note;
  }
  ['rgt','rgn','rgp','rgl'].forEach(id => $(id).oninput = draw); draw();
})();

/* ---------- 4. трассы агента ---------- */
(function(){
  const ORDERS0 = {1042:{status:'доставлен', sum:'2 340 ₽'}, 1043:{status:'в пути', sum:'1 120 ₽'}, 1044:{status:'собирается', sum:'860 ₽'}};
  function freshState(){ return {orders:JSON.parse(JSON.stringify(ORDERS0)), returns:[], finished:false, final:null}; }
  const TOOLS = {
    get_order(s, id){ const o = s.orders[id]; if(!o) throw new Error('заказ ' + id + ' не найден'); return 'статус: ' + o.status + ', сумма ' + o.sum; },
    create_return(s, id){ const o = s.orders[id]; if(!o) throw new Error('заказ ' + id + ' не найден'); if(o.status !== 'доставлен') throw new Error('возврат возможен только для доставленных заказов'); if(!s.returns.includes(id)) s.returns.push(id); return 'возврат по заказу ' + id + ' создан'; },
    cancel_order(s, id){ const o = s.orders[id]; if(!o) throw new Error('заказ ' + id + ' не найден'); if(o.status !== 'собирается') throw new Error('заказ уже отправлен, отмена невозможна'); o.status = 'отменён'; return 'заказ ' + id + ' отменён'; },
    finish(s, text){ s.finished = true; s.final = text; return 'финальный ответ'; }
  };
  const key = st => st.tool === 'finish' ? 'finish' : st.tool + '(' + st.arg + ')';
  const TASKS = {
    T1:{text:'Оформи возврат по заказу 1042.', golden:['get_order(1042)', 'create_return(1042)', 'finish'], expect:s => s.returns.length === 1 && s.returns[0] === 1042 && s.orders[1042].status === 'доставлен' && s.orders[1044].status === 'собирается', forbidden:st => st.tool === 'cancel_order' || (st.tool === 'create_return' && st.arg !== 1042)},
    T2:{text:'Отмени заказ 1044, если он ещё не отправлен.', golden:['get_order(1044)', 'cancel_order(1044)', 'finish'], expect:s => s.orders[1044].status === 'отменён' && s.returns.length === 0 && s.orders[1042].status === 'доставлен' && s.orders[1043].status === 'в пути', forbidden:st => st.tool === 'create_return' || (st.tool === 'cancel_order' && st.arg !== 1044)},
    T3:{text:'Если заказ 1043 уже доставлен — оформи возврат, иначе сообщи клиенту статус.', golden:['get_order(1043)', 'finish'], expect:s => s.returns.length === 0 && s.orders[1043].status === 'в пути' && s.orders[1044].status === 'собирается', forbidden:st => st.tool === 'create_return' || st.tool === 'cancel_order'}
  };
  const TR = [
    {id:'A', task:'T1', name:'Уверенный отчёт', steps:[{tool:'get_order', arg:1042}, {tool:'finish', arg:'Возврат по заказу 1042 оформлен, деньги вернутся в течение 5 дней.'}],
     text:{v:'ok', t:'«Ответ полный, вежливый, называет срок возврата» — 5 из 5.'}, traj:{v:'bad', t:'«Инструмент create_return не вызывался; утверждение в ответе не подтверждено действием».'},
     divg:'Шаг 2: эталон ждёт <code>create_return(1042)</code>, агент сразу вызвал <code>finish</code>. Текст верный по форме и ложный по существу: возврата в системе нет. Судья по тексту этого не видит в принципе — у него нет среды. Проверка состояния и граф ловят ошибку бесплатно. Правило в коде «финальный ответ про действие — только после вызова инструмента с этим действием» (как валидатор <code>lookup</code> до <code>finish</code> на семинаре по мультиагентам) закрыло бы этот случай без судьи.'},
    {id:'B', task:'T2', name:'Долгая дорога', steps:[{tool:'get_order', arg:1044}, {tool:'get_order', arg:1043}, {tool:'get_order', arg:1042}, {tool:'get_order', arg:1044}, {tool:'cancel_order', arg:1044}, {tool:'finish', arg:'Заказ 1044 ещё собирался, отменил его.'}],
     text:{v:'ok', t:'«Задача выполнена, ответ по делу» — 5 из 5.'}, traj:{v:'ok', t:'«Задача решена; три чтения чужих заказов не требовались» — 4 из 5, замечание.'},
     divg:'Шаг 2: эталон ждёт <code>cancel_order(1044)</code>, агент пошёл читать соседние заказы и вернулся к 1044 повторно. Состояние среды верное — проверка состояния ставит зачёт, и по тексту всё хорошо. Что путь плохой, видит только граф: эффективность 0,5, три лишних узла, один повтор без изменения состояния. На одной задаче это мелочь; на тысяче — двойная стоимость и двойная задержка, которых не покажет ни одна метрика результата.'},
    {id:'C', task:'T3', name:'По кругу', steps:Array.from({length:8}, () => ({tool:'get_order', arg:1043})), stopped:true,
     text:{v:'na', t:'Финального ответа нет — оценивать нечего.'}, traj:{v:'bad', t:'«Восемь одинаковых вызовов, агент не продвигается» — зацикливание.'},
     divg:'Шаг 2: эталон ждёт <code>finish</code> со статусом, агент повторяет <code>get_order(1043)</code>, пока его не останавливает бюджет шагов. Состояние среды не изменилось — и оно совпадает с эталонным, поэтому наивная проверка «состояние равно ожидаемому» поставила бы зачёт. Нужен второй флаг: задача завершена вызовом <code>finish</code>. Цикл в графе — семь повторов одного узла без изменения состояния — виден без всякого судьи и является готовым алертом для мониторинга.'},
    {id:'D', task:'T3', name:'Правильные слова', steps:[{tool:'get_order', arg:1043}, {tool:'create_return', arg:1043}, {tool:'finish', arg:'Заказ 1043 ещё в пути, возврат пока невозможен. Сообщу, когда он будет доставлен.'}],
     text:{v:'ok', t:'«Статус сообщён верно, предложен следующий шаг» — 5 из 5.'}, traj:{v:'bad', t:'«Вызван create_return при статусе «в пути» — побочное действие без необходимости».'},
     divg:'Шаг 2: эталон ждёт <code>finish</code>, агент попытался оформить возврат недоставленного заказа. Среда отказала — состояние не изменилось, текст ответа безупречен. Но запрещённое действие было <i>попыткой</i>, и в другой среде, без такой проверки, возврат бы создался. Поэтому проверка состояния считает попытки запрещённых действий, а не только их результат. Граф показывает лишний узел с побочным эффектом; судья по тексту снова ставит пять.'}
  ];
  function run(tr){
    const s = freshState(), log = [], task = TASKS[tr.task];
    let forb = 0;
    const seen = new Map(); let cycles = 0;
    tr.steps.forEach((st, i) => {
      const k = key(st);
      const before = JSON.stringify([s.orders, s.returns]);
      let obs, err = false;
      try { obs = TOOLS[st.tool](s, st.arg); } catch(e){ obs = 'ошибка: ' + e.message; err = true; }
      const after = JSON.stringify([s.orders, s.returns]);
      const forbidden = task.forbidden(st); if(forbidden) forb++;
      const rep = seen.has(k) && seen.get(k) === before && before === after; if(rep) cycles++;
      seen.set(k, after);
      log.push({i:i + 1, k, obs, err, forbidden, rep, extra:!task.golden.includes(k)});
    });
    const stateOk = task.expect(s), done = s.finished;
    const pass = stateOk && done && forb === 0;
    let why = pass ? 'состояние совпало с эталонным, задача завершена, запрещённых действий не было' : !stateOk ? 'состояние среды не совпало с эталонным' : !done ? 'состояние совпало, но задача не завершена: finish не вызван' + (tr.stopped ? ', агент остановлен по бюджету шагов' : '') : 'состояние совпало, но была попытка запрещённого действия (' + forb + ')';
    return {s, log, pass, why, stateOk, done, forb, cycles};
  }
  function graphMetrics(tr){
    const g = TASKS[tr.task].golden, a = tr.steps.map(key);
    const gs = new Set(g), as = new Set(a);
    const nodeHit = [...as].filter(k => gs.has(k)).length;
    const nP = as.size ? nodeHit / as.size : 0, nR = nodeHit / gs.size, nF1 = nP + nR ? 2 * nP * nR / (nP + nR) : 0;
    const edges = seq => { const e = new Set(); for(let i = 0; i + 1 < seq.length; i++) e.add(seq[i] + '→' + seq[i + 1]); return e; };
    const ge = edges(g), ae = edges(a);
    const eHit = [...ae].filter(e => ge.has(e)).length;
    const eP = ae.size ? eHit / ae.size : 0, eR = ge.size ? eHit / ge.size : 0, eF1 = eP + eR ? 2 * eP * eR / (eP + eR) : 0;
    const eff = g.length / a.length;
    let div = -1; for(let i = 0; i < Math.max(g.length, a.length); i++){ if(g[i] !== a[i]){ div = i; break; } }
    const missing = [...gs].filter(k => !as.has(k));
    return {nF1, eF1, nP, nR, eff, div, missing, extra:[...as].filter(k => !gs.has(k))};
  }
  function drawGraph(tr, m, res, shown){
    const g = TASKS[tr.task].golden, a = tr.steps.map(key);
    const NW = 150, GAP = 18, NH = 30, L = 16;
    const W = L * 2 + Math.max(g.length, a.length) * (NW + GAP), H = 150;
    const x = i => L + i * (NW + GAP);
    let s = '<text class="gl" x="' + L + '" y="14">эталон</text><text class="gl" x="' + L + '" y="90">трасса</text>';
    const node = (xx, y, k, cls) => '<rect class="node ' + cls + '" x="' + xx + '" y="' + y + '" width="' + NW + '" height="' + NH + '" rx="6"/><text class="gn" x="' + (xx + NW / 2) + '" y="' + (y + 19) + '" text-anchor="middle">' + k + '</text>';
    const arrow = (x1, x2, y, cls) => '<line class="ed ' + cls + '" x1="' + x1 + '" y1="' + y + '" x2="' + x2 + '" y2="' + y + '" marker-end="url(#ah)"/>';
    s += '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-3)"/></marker></defs>';
    g.forEach((k, i) => { if(i) s += arrow(x(i - 1) + NW, x(i) - 1, 20 + NH / 2, ''); s += node(x(i), 20, k, 'gold' + (m.missing.includes(k) ? ' miss' : '')); });
    const firstIdx = {}; a.forEach((k, i) => { if(!(k in firstIdx)) firstIdx[k] = i; });
    g.forEach((k, i) => { if(k in firstIdx){ s += '<line class="match" x1="' + (x(i) + NW / 2) + '" y1="' + (20 + NH) + '" x2="' + (x(firstIdx[k]) + NW / 2) + '" y2="96"/>'; } });
    a.forEach((k, i) => {
      const lg = res.log[i];
      if(i) s += arrow(x(i - 1) + NW, x(i) - 1, 96 + NH / 2, lg.rep ? 'loop' : (lg.extra || res.log[i - 1].extra ? 'extra' : ''));
      s += node(x(i), 96, k, (lg.extra ? 'extra' : 'ok') + (shown && m.div === i ? ' divg' : ''));
      if(lg.err) s += '<text class="gn" x="' + (x(i) + NW / 2) + '" y="' + (96 + NH + 14) + '" text-anchor="middle" fill="var(--bad)">ошибка</text>';
    });
    if(m.div >= a.length && shown) s += '<rect class="node miss divg" x="' + x(a.length) + '" y="96" width="' + NW + '" height="' + NH + '" rx="6"/><text class="gn" x="' + (x(a.length) + NW / 2) + '" y="115" text-anchor="middle">' + g[m.div] + '</text>';
    $('tgraph').innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" style="min-width:' + Math.min(W, 900) + 'px" role="img" aria-label="Граф вызовов трассы против эталонного">' + s + '</svg>';
  }
  const state = {}; TR.forEach(t => state[t.id] = {shown:false});
  let cur = TR[0];
  function drawPick(){ const p = $('tpick'); p.innerHTML = ''; TR.forEach(t => { const b = el('button', '', '<span class="n">трасса ' + t.id + ' · задача ' + t.task.slice(1) + '</span><span class="t">' + t.name + '</span>'); b.setAttribute('role', 'tab'); b.setAttribute('aria-pressed', t === cur); b.onclick = () => { cur = t; draw(); }; p.appendChild(b); }); }
  function draw(){
    drawPick();
    const shown = state[cur.id].shown || teacher(), task = TASKS[cur.task];
    $('traces').classList.toggle('shown', shown);
    const res = run(cur), m = graphMetrics(cur);
    $('ttask').innerHTML = '<b>Задача.</b> ' + task.text + '<div style="margin-top:.3rem;font-size:.84rem;color:var(--ink-2)">Эталонный граф: <code>' + task.golden.join('</code> → <code>') + '</code>. Заказы: 1042 — доставлен, 1043 — в пути, 1044 — собирается.</div>';
    $('tsteps').innerHTML = res.log.map((l, i) => '<div class="step' + (shown && m.div === i ? ' div' : '') + (l.rep ? ' rep' : '') + (l.extra && !(shown && m.div === i) ? ' extra' : '') + '"><span class="i">' + l.i + '</span><div><div class="call">' + l.k + (l.k === 'finish' ? ' — «' + cur.steps[i].arg + '»' : '') + '</div><div class="obs' + (l.err ? ' err' : '') + '">' + l.obs + (l.forbidden ? ' · <b>запрещённое действие</b>' : '') + (l.rep ? ' · повтор без изменения состояния' : '') + '</div></div></div>').join('') + (cur.stopped ? '<div class="step"><span class="i">—</span><div class="obs">остановлен: бюджет 8 шагов исчерпан, finish не вызван</div></div>' : '');
    drawGraph(cur, m, res, shown);
    const mm = $('tmetrics'); mm.innerHTML = '';
    [['node F1', dec(m.nF1, 2), m.missing.length ? 'пропущено: ' + m.missing.join(', ') : (m.extra.length ? 'лишних узлов: ' + m.extra.length : 'все узлы эталона'), m.nF1 === 1 ? 'ok' : (m.nF1 >= .7 ? 'warm' : 'bad')],
     ['edge F1', dec(m.eF1, 2), 'пары «узел → узел»', m.eF1 === 1 ? 'ok' : (m.eF1 >= .6 ? 'warm' : 'bad')],
     ['эффективность', dec(m.eff, 2), m.eff < 1 ? 'лишние шаги' : (m.eff > 1 ? 'путь короче эталона — шаг пропущен' : 'как эталон'), m.eff === 1 ? 'ok' : (m.eff >= .5 ? 'warm' : 'bad')],
     ['циклы', String(res.cycles), 'повтор узла без изменения состояния', res.cycles ? 'bad' : 'ok']].forEach(a => { const d = el('div', 'm ' + a[3]); d.innerHTML = '<span class="l">' + a[0] + '</span><span class="n">' + a[1] + '</span><span class="s">' + a[2] + '</span>'; mm.appendChild(d); });
    const V = {ok:'зачёт', bad:'провал', na:'не применимо'};
    const graphBad = m.missing.length || m.extra.length || res.cycles || m.eff < 1;
    $('tjudges').innerHTML = [
      ['Проверка состояния', res.pass ? 'ok' : 'bad', res.why, 'настоящая'],
      ['Граф против эталона', graphBad ? 'bad' : 'ok', graphBad ? 'расхождение с эталоном есть — см. метрики' : 'граф совпал с эталонным', 'настоящая'],
      ['Судья по тексту', cur.text.v, cur.text.t, 'сценарий'],
      ['Судья по траектории', cur.traj.v, cur.traj.t, 'сценарий']
    ].map(j => '<div class="card"><div class="k">' + j[0] + ' · ' + j[3] + '</div><div class="v ' + j[1] + '">' + V[j[1]] + '</div><div class="t">' + j[2] + '</div></div>').join('');
    $('tdivg').innerHTML = '<div class="k">разбор · точка расхождения</div>' + cur.divg;
    $('treveal').textContent = state[cur.id].shown ? 'Скрыть разбор' : 'Показать разбор';
    $('tscore').textContent = shown ? 'точка расхождения: шаг ' + (m.div + 1) : '';
  }
  $('treveal').onclick = () => { state[cur.id].shown = !state[cur.id].shown; draw(); };
  document.addEventListener('teacher', draw);
  draw();
})();

/* ---------- 5. pass@k / pass^k ---------- */
(function(){
  const KMAX = 10;
  let tipEl;
  function draw(){
    const p = +$('pp').value; $('ppv').textContent = dec(p, 2);
    const atk = k => 1 - Math.pow(1 - p, k), powk = k => Math.pow(p, k);
    const W = 760, H = 300, L = 50, R = 170, T = 18, B = 40;
    const X = k => L + (k - 1) / (KMAX - 1) * (W - L - R), Y = v => H - B - v * (H - T - B);
    let g = '';
    for(let i = 0; i <= 4; i++){ const v = i / 4; g += '<line class="' + (i ? 'gr' : 'ax') + '" x1="' + L + '" x2="' + (W - R) + '" y1="' + Y(v) + '" y2="' + Y(v) + '"/><text class="tx" x="' + (L - 8) + '" y="' + (Y(v) + 4) + '" text-anchor="end">' + Math.round(v * 100) + '%</text>'; }
    for(let k = 1; k <= KMAX; k++) g += '<text class="tx" x="' + X(k) + '" y="' + (H - B + 16) + '" text-anchor="middle">' + k + '</text>';
    g += '<text class="tx" x="' + (L + (W - L - R) / 2) + '" y="' + (H - 4) + '" text-anchor="middle">k попыток</text>';
    const S = [{name:'pass@k · хотя бы одна', f:atk, c:'var(--s1)'}, {name:'pass^k · все k', f:powk, c:'var(--s2)'}];
    S.forEach(s => { g += '<polyline points="' + Array.from({length:KMAX}, (_, i) => X(i + 1) + ',' + Y(s.f(i + 1))).join(' ') + '" fill="none" stroke="' + s.c + '" stroke-width="2" stroke-linejoin="round"/>'; for(let k = 1; k <= KMAX; k++) g += '<circle cx="' + X(k) + '" cy="' + Y(s.f(k)) + '" r="3.5" fill="' + s.c + '" stroke="var(--surface)" stroke-width="1.5"/>'; });
    const ends = S.map(s => ({s, y:Y(s.f(KMAX)), v:s.f(KMAX)})).sort((a, b) => a.y - b.y); let prev = -1e9; ends.forEach(e => { e.ly = Math.max(e.y, prev + 30); prev = e.ly; });
    ends.forEach(e => { g += '<text class="lb" x="' + (X(KMAX) + 12) + '" y="' + e.ly + '">' + e.s.name + '</text><text class="tx" x="' + (X(KMAX) + 12) + '" y="' + (e.ly + 13) + '">' + pct(e.v) + ' при k = ' + KMAX + '</text>'; });
    g += '<line class="cross" id="pcross" x1="0" x2="0" y1="' + T + '" y2="' + (H - B) + '" visibility="hidden"/><rect id="phit" x="' + L + '" y="' + T + '" width="' + (W - L - R) + '" height="' + (H - T - B) + '" fill="transparent"/>';
    const wrap = $('pchart'); wrap.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="pass@k и pass^k в зависимости от k">' + g + '</svg>';
    tipEl = el('div', 'tip'); tipEl.hidden = true; wrap.appendChild(tipEl);
    const svg = wrap.querySelector('svg'), hit = $('phit'), cross = $('pcross');
    function move(ev){ const r = svg.getBoundingClientRect(); const px = (ev.clientX - r.left) / r.width * W; let k = Math.round((px - L) / (W - L - R) * (KMAX - 1)) + 1; k = Math.max(1, Math.min(KMAX, k)); cross.setAttribute('x1', X(k)); cross.setAttribute('x2', X(k)); cross.setAttribute('visibility', 'visible'); tipEl.innerHTML = '<div class="h">k = ' + k + '</div>' + S.map(s => '<div class="r"><span><i style="background:' + s.c + '"></i>' + s.name.split(' · ')[0] + '</span><b>' + pct(s.f(k), 1) + '</b></div>').join(''); tipEl.hidden = false; const left = X(k) / W * r.width, tw = tipEl.offsetWidth; tipEl.style.left = Math.max(0, Math.min(r.width - tw, left + (left + tw + 16 > r.width ? -tw - 12 : 12))) + 'px'; tipEl.style.top = '8px'; }
    hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move); hit.addEventListener('pointerleave', () => { tipEl.hidden = true; cross.setAttribute('visibility', 'hidden'); });
    const st = $('pstats'); st.innerHTML = '';
    [['pass@3', pct(atk(3)), 'хотя бы одна из трёх'], ['pass^3', pct(powk(3)), 'все три'], ['pass^8', pct(powk(8)), 'все восемь'], ['нужно p для pass^3 ≥ 90 %', dec(Math.pow(.9, 1 / 3), 3), 'за одну попытку']].forEach(a => st.appendChild(statBox(a)));
  }
  $('pp').oninput = draw; draw();
})();

/* ---------- 6. A/B при малом трафике ---------- */
(function(){
  const Z_A = 1.959964, Z_B = 0.841621;
  function nPer(p0, d){ const p1 = Math.min(.999, p0 + d), pb = (p0 + p1) / 2; return Math.ceil(Math.pow(Z_A * Math.sqrt(2 * pb * (1 - pb)) + Z_B * Math.sqrt(p0 * (1 - p0) + p1 * (1 - p1)), 2) / (d * d)); }
  const CH = [[7, 'Недельный цикл: будни и выходные приносят разные запросы — без стратификации по дням дисперсия выше формульной.'], [14, 'Кто-то в команде захочет поправить промпт. Нельзя: любое изменение в середине теста смешивается с эффектом.'], [30, 'Провайдер обновит модель или тарифы. Эффект версии провайдера неотличим от эффекта вашего изменения.'], [60, 'Сменятся сезон и акции — распределение запросов уже другое, чем в начале теста.'], [120, 'Тест длиннее учебного семестра: к его концу продукт изменился настолько, что сравнивались уже не те версии.']];
  function draw(){
    const p0 = +$('ab0').value, d = +$('abd').value / 100, t = +$('abt').value;
    $('ab0v').textContent = pct(p0); $('abdv').textContent = '+' + dec(d * 100, 1); $('abtv').textContent = fmt(t);
    const n = nPer(p0, d), days = Math.ceil(2 * n / t);
    // какой эффект различим за 14 дней при этом трафике
    const n14 = t * 14 / 2; let lo = .001, hi = .5; for(let i = 0; i < 40; i++){ const mid = (lo + hi) / 2; if(nPer(p0, mid) > n14) lo = mid; else hi = mid; }
    const st = $('abstats'); st.innerHTML = '';
    [['нужно на группу', big(n), 'пользовательских запросов'], ['всего', big(2 * n), 'две группы поровну'], ['дней при вашем трафике', fmt(days), t + ' запросов в день'], ['различимо за 2 недели', '+' + dec(hi * 100, 1) + ' п.п.', 'при этом трафике и базе']].forEach(a => st.appendChild(statBox(a)));
    $('abch').innerHTML = CH.map(c => '<div class="ch' + (days >= c[0] ? ' on' : '') + '"><b>' + c[0] + '+ дней.</b> ' + c[1] + '</div>').join('');
  }
  ['ab0','abd','abt'].forEach(id => $(id).oninput = draw); draw();
})();

/* ---------- 7. бюджет ---------- */
(function(){
  function draw(){
    const n = +$('bn').value, m = +$('bm').value, R = +$('br').value, w = +$('bw').value, k = +$('bk').value, c = Math.max(0, +$('bc').value || 0);
    $('bnv').textContent = n; $('bmv').textContent = m; $('brv').textContent = R; $('bwv').textContent = w; $('bkv').textContent = k;
    const perRun = n * m * R * k, month = perRun * w * 4.33;
    const st = $('bstats'); st.innerHTML = '';
    [['вызовов судьи за прогон', big(perRun), n + ' × ' + m + ' × ' + R + ' × ' + k], ['вызовов в месяц', big(month), w + ' прогонов в неделю'], ['рублей в месяц', big(month * c) + NB + '₽', 'по ' + dec(c, 2) + ' ₽ за вызов'], ['генераций системы в месяц', big(n * k * w * 4.33), 'без учёта судьи']].forEach(a => st.appendChild(statBox(a)));
    $('bnote').textContent = m === 0 ? 'Метрик-судей нет: оценивание держится на детерминированных проверках и человеческой разметке. Вызовы модели уходят только на генерацию ответов системы.' : (month * c > 20000 ? 'Это уже заметная строка бюджета. Прежде чем её урезать, посмотрите на шаг «различимый эффект»: меньше примеров или повторов — шире интервал, и часть регрессий станет невидимой.' : 'Сравните с бюджетом инференса в проде из занятия 1: на ранней стадии оценивание дороже самого продукта, и это нормально — иначе непонятно, что именно вы выкатываете.');
  }
  ['bn','bm','br','bw','bk'].forEach(id => $(id).oninput = draw); $('bc').oninput = draw; draw();
})();

/* ---------- 8. грехи оценивания ---------- */
(function(){
  const S = [
    ['Подобрали промпт по 40 вопросам, метрика выросла с 0,71 до 0,84. Отчитались этими же 40 вопросами.', ['Мало вопросов', 'Набор для подбора и для отчёта один и тот же', 'Нет судьи'], 1, 'На наборе, по которому подбирали, число всегда завышено: вы оптимизировали именно его. На отложенной части эффект будет меньше или исчезнет. Делить на dev и test нужно до первого эксперимента.', 'цепочка: набор → интервал → решение'],
    ['На 200-м примере поняли, что критерий «полнота» сформулирован плохо, переписали якоря и доразметили остальные 300.', ['Надо было взять pass/fail вместо 1–5', 'Первые 200 и остальные 300 оценены по разным rubric', 'Якоря не нужны'], 1, 'Две партии несравнимы: это два разных измерительных прибора. Либо переразметить первые 200 по новому rubric, либо честно считать их отдельным экспериментом.', 'тезис 3 · rubric фиксируется до массового прогона'],
    ['Система B лучше системы A на 0,3 балла судьи на 15 примерах, судья прогнан один раз. Релизим B.', ['15 примеров и один прогон: шум судьи больше разницы', 'Надо было pairwise', '0,3 — мало, надо 0,5'], 0, 'При σ судьи около 0,9 и 15 примерах стандартная ошибка разницы больше 0,4. Интервал накрывает ноль с запасом. Проверьте на стенде «шум против эффекта».', 'тезис 3 · шум против эффекта'],
    ['Генератор — Qwen, судья — Qwen. Ответы Qwen в среднем на 0,4 выше, чем ответы GPT на тех же вопросах.', ['GPT хуже', 'Самопредпочтение: судья той же семьи, разметка не слепая', 'Разницу надо считать в п.п.'], 1, 'Судья завышает ответы своей семьи. Проверка: слепая разметка и второй судья другой семьи на тех же ответах. Без неё 0,4 ничего не значат.', 'тезис 3 · смещения измеряют'],
    ['Агент пишет: «Встреча перенесена на 15:00». Судья по тексту ставит 5 из 5. Метрика проекта — средний балл судьи.', ['Оценили текст, а не состояние календаря', 'Судье нужен CoT', 'Нужен pairwise с предыдущей версией'], 0, 'Агент мог ничего не перенести. Проверка — событие в календаре с нужным временем; это детерминированно и бесплатно. Судья по тексту для агента с действиями — последняя линия, а не первая.', 'тезис 5 · состояние среды'],
    ['Перешли на новую модель и заодно переписали системный промпт. Качество выросло на 6 п.п. — «новая модель лучше».', ['Изменили две вещи, эффект приписали одной', '6 п.п. — мало', 'Надо было сначала промпт'], 0, 'Непонятно, чему приписать эффект: модели, промпту или их сочетанию. Новая модель со старым промптом могла дать −2. Меняется одно.', 'тезис 4 · меняется одно'],
    ['Агент бронирует переговорки. На 30 задачах решил 27. В проде жалобы: «через раз не работает».', ['Мало задач', 'Один прогон на задачу: мерили pass@1, а продукту нужен pass^k', 'Нужен судья по траектории'], 1, '27 из 30 за один прогон — это «иногда получается». Пользователь получает одну попытку и хочет, чтобы работало каждый раз: нужен pass^k, то есть несколько прогонов одной задачи.', 'тезис 5 · pass^k'],
    ['Регрессионный набор из 80 вопросов собран перед релизом в марте. Сейчас октябрь, все 80 проходят.', ['80 — мало', 'Набор не пополнялся провалами из прода и проверяет мартовскую систему', 'Надо было 100'], 1, 'За полгода продукт и запросы изменились, а набор нет. Набор растёт из инцидентов: каждый провал из прода становится размеченным примером.', 'тезис 6 · цикл обратной связи'],
    ['Faithfulness выросла с 0,82 до 0,91. Доля ответов «не знаю» выросла с 8 % до 23 %. В отчёт пошла первая строка.', ['Отчитались прокси, не посмотрев на north-star и ограничивающую', 'Faithfulness — плохая метрика', '23 % — нормально'], 0, 'Прокси улучшился за счёт того, что система стала чаще молчать. North-star — закрытые обращения — скорее всего упал. Прокси всегда проверяют вместе с ограничивающими метриками.', 'тезис 1 · дерево метрик'],
    ['A/B при 150 пользователях в день остановили на третий день: p = 0,04, «значимо».', ['Подглядывание и объём: при таком трафике тест идёт недели, а остановка «когда стало значимо» завышает ложные срабатывания', 'p должно быть 0,01', 'Нужно было четыре группы'], 0, 'За три дня — 450 пользователей на обе группы; по формуле нужно в разы больше. Остановка в момент первого «значимо» даёт ложное срабатывание гораздо чаще заявленных 5 %. См. стенд про A/B.', 'тезис 6 · A/B — роскошь большого трафика']
  ];
  const votes = {};
  function draw(){
    const box = $('sins'); box.innerHTML = ''; let done = 0, hit = 0;
    S.forEach((s, i) => {
      const v = votes[i]; if(v != null){ done++; if(v === s[2]) hit++; }
      const c = el('div', 'sin' + (v != null ? ' open' : ''));
      c.appendChild(el('div', 'claim', (i + 1) + '. ' + s[0]));
      const vt = el('div', 'vote');
      s[1].forEach((o, j) => { const b = el('button', '', o); b.setAttribute('aria-pressed', v === j); if((v != null || teacher()) && j === s[2]) b.style.boxShadow = 'inset 0 0 0 2px var(--ok)'; b.onclick = () => { votes[i] = j; draw(); }; vt.appendChild(b); });
      c.appendChild(vt);
      c.appendChild(el('div', 'res', (v != null ? '<span class="you">' + (v === s[2] ? 'верно' : 'не то') + '</span>' : '') + '<p>' + s[3] + '</p><div class="src">' + s[4] + '</div>'));
      box.appendChild(c);
    });
    $('sscore').textContent = done ? 'отвечено ' + done + ' из ' + S.length + ' · верно ' + hit : 'ответов пока нет';
  }
  $('sreset').onclick = () => { Object.keys(votes).forEach(k => delete votes[k]); draw(); };
  document.addEventListener('teacher', draw);
  draw();
})();
