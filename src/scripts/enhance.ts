/**
 * The site's scene behaviour.
 *
 * Loaded from BaseLayout, so it runs on every page. It used to be imported by
 * the home page alone, which meant the scroll gate below existed only there:
 * the logo marquee on every subpage, and both loops on the order processing
 * page, ran for as long as the tab was open whether or not anyone was looking.
 * Everything in here past the gate finds its own elements or does nothing, so
 * on a page without them the file costs a lookup that returns null.
 *
 * This exists because the port initially shipped none of it, on a "zero
 * JavaScript" rule that turned out to be the wrong target. The brief asks for
 * *minimal* client-side JavaScript — only what genuinely needs it — and these
 * five do:
 *
 *  - the scroll gate, without which the one-shot reveal animations never fire
 *    at all, because the rules that define them only exist under `.anim-live`;
 *  - the marquee, which has to measure a lazily-loaded row before it knows how
 *    many copies cover the viewport;
 *  - the typewriter, which is a timed effect;
 *  - the context sequence, which is a five-stage loop that a per-item CSS
 *    delay cannot express;
 *  - the cursor label, which follows a pointer.
 *
 * Every one of them is an enhancement over content that is already in the
 * HTML. With this file absent the page still reads completely: the logos sit
 * in a static strip, the question is already written out, the sequence rests
 * on its first frame, and the panels keep the ordinary pointer.
 */

/** Respect the OS setting once, here, rather than in five places. */
const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* --- The scroll gate ------------------------------------------------------
   Looping animations run only while they can be seen: ungated they burn cycles
   on a long page whether or not anyone is looking, and a reader who scrolls to
   a sequence catches it halfway through instead of at its first frame.

   `anim-gated` goes on from here rather than from the markup, so a failed
   script leaves every loop running rather than leaving the page frozen. */
function gateAnimations() {
  const hosts = document.querySelectorAll('[data-anim]');
  if (!hosts.length || !('IntersectionObserver' in window)) return;

  const root = document.documentElement;
  root.classList.add('anim-gated');

  /* Having the constructor is not the same as the callback running. Embedded
     and headless views exist where an observer is created, accepts targets and
     never reports, and there the gate is a trap rather than a saving: every
     loop sits paused on frame zero, and the scenes whose first frame fades in
     from nothing sit blank. So the gate is released if nothing has been
     reported shortly after it goes on. The failure mode stays the one this file
     promises -- everything moves, not nothing does. */
  let reported = false;
  const release = window.setTimeout(() => {
    if (!reported) root.classList.remove('anim-gated');
  }, 1200);

  const io = new IntersectionObserver(
    (entries) => {
      reported = true;
      window.clearTimeout(release);
      for (const entry of entries) {
        entry.target.classList.toggle('anim-live', entry.isIntersecting);
      }
    },
    // Early, so nothing is caught mid-cycle as it arrives, and a margin at the
    // foot so a sequence does not stop the instant its last row leaves.
    { rootMargin: '15% 0px', threshold: 0 }
  );

  for (const host of hosts) io.observe(host);
}

/* --- The logo marquee -----------------------------------------------------
   Two copies alone leave a gap on a wide screen: the belt slides exactly half
   its width, so half of it has to cover the viewport on its own. At 2000px
   that left ~590px of white scrolling past.

   The count is kept even so the -50% shift lands on a repeat and the loop is
   seamless, and the duration scales with width so the speed is the same
   whatever the screen. Done here rather than in the markup because it depends
   on a measured width, and because it degrades to a static strip. */
function fillBelt() {
  const belt = document.querySelector<HTMLElement>('.proof__belt');
  const track = belt?.querySelector<HTMLElement>('.proof__track');
  if (!belt || !track) return;

  for (const clone of belt.querySelectorAll('.proof__track[aria-hidden]')) clone.remove();

  const one = track.getBoundingClientRect().width;
  if (!one) return;

  let copies = Math.max(2, Math.ceil((window.innerWidth * 2) / one));
  if (copies % 2) copies += 1;

  for (let i = 1; i < copies; i++) {
    const clone = track.cloneNode(true) as HTMLElement;
    clone.setAttribute('aria-hidden', 'true');
    clone.removeAttribute('aria-label');
    belt.appendChild(clone);
  }

  document.querySelector('.proof')?.classList.add('proof--rolling');
  belt.style.animationDuration = `${Math.round((one * copies) / 60)}s`;
}

function watchBelt() {
  // The logos are lazy-loaded, so measure once they have real dimensions.
  if (document.readyState === 'complete') fillBelt();
  else window.addEventListener('load', fillBelt);

  let timer: number | undefined;
  window.addEventListener('resize', () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(fillBelt, 200);
  });
}

/* --- Hoshii Chat ----------------------------------------------------------
   The question types itself once the card is on screen. The full string ships
   in the markup, so a crawler and a reader without JavaScript get it whole;
   the height is measured before clearing so the card cannot jump. */
function typeQuestion() {
  const question = document.querySelector<HTMLElement>('.chatband__q');
  const card = question?.closest<HTMLElement>('.chatband__card');
  if (!question || !card || still) return;

  const full = question.textContent?.trim() ?? '';
  question.style.minHeight = `${question.getBoundingClientRect().height}px`;
  question.textContent = '';
  card.classList.add('is-typing');

  const io = new IntersectionObserver(
    (entries) => {
      if (!entries.some((e) => e.isIntersecting)) return;
      io.disconnect();
      let i = 0;
      const tick = () => {
        question.textContent = full.slice(0, ++i);
        if (i < full.length) {
          // A hair of variance, so it reads as typing rather than as a ticker.
          window.setTimeout(tick, full[i - 1] === ' ' ? 90 : 34 + (i % 4) * 10);
        } else {
          card.classList.add('is-typed');
        }
      };
      tick();
    },
    { threshold: 0.4 }
  );
  io.observe(card);
}

/* --- The context sequence -------------------------------------------------
   Class-driven rather than pure CSS: the items arrive on a stagger and are
   then pulled in together, and a per-item animation-delay cannot do that —
   each item's loop would sit at a different point when the field resets, so
   the later ones were still visible when the cycle was meant to start from
   nothing. */
function runContextLoop() {
  const stage = document.querySelector<HTMLElement>('.suckart');
  if (!stage || still) return;

  const STAGES: [string, number][] = [
    ['is-suck', 2300],
    ['is-answer', 3000],
    ['is-think', 4100],
    ['is-result', 5500],
  ];
  const LOOP = 9200;
  const timers: number[] = [];

  const cycle = () => {
    for (const t of timers.splice(0)) window.clearTimeout(t);
    stage.classList.remove('is-in', 'is-suck', 'is-answer', 'is-think', 'is-result');
    // Two frames, so the removal paints before the class that transitions away
    // from it goes back on.
    requestAnimationFrame(() => requestAnimationFrame(() => stage.classList.add('is-in')));
    for (const [cls, at] of STAGES) {
      timers.push(window.setTimeout(() => stage.classList.add(cls), at));
    }
    timers.push(window.setTimeout(cycle, LOOP));
  };

  window.setTimeout(cycle, 60);
}

/* --- The industry panels' cursor ------------------------------------------
   The panels are links and the pointer should say where to, so the arrow is
   replaced by a label that follows it. Gated on a fine pointer that can hover:
   on touch there is no cursor to replace, and the panels are display:none
   there anyway. */
function followPointer() {
  const pill = document.querySelector<HTMLElement>('.cursorpill');
  const zone = document.querySelector<HTMLElement>('.pitch__roles');
  if (!pill || !zone || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

  // Applied from here, not the stylesheet, so a failed script leaves a visible
  // cursor rather than none.
  document.documentElement.classList.add('has-cursorpill');

  let x = 0;
  let y = 0;
  let frame: number | null = null;

  const place = () => {
    frame = null;
    // Flip to the left of the pointer near the right edge, so a fixed element
    // cannot push the viewport wider than it is.
    const w = pill.offsetWidth;
    const flip = x + w + 26 > window.innerWidth;
    pill.style.translate = `${flip ? x - w - 14 : x + 14}px ${y + 16}px`;
  };

  const track = (event: PointerEvent) => {
    x = event.clientX;
    y = event.clientY;
    if (!frame) frame = requestAnimationFrame(place);
  };

  zone.addEventListener('pointerenter', (event) => {
    track(event);
    place();
    pill.classList.add('is-on');
  });
  zone.addEventListener('pointermove', track);
  zone.addEventListener('pointerleave', () => pill.classList.remove('is-on'));
  // Scrolling can move the panels out from under a stationary pointer, which
  // fires no pointer event of its own.
  window.addEventListener('scroll', () => pill.classList.remove('is-on'), { passive: true });
}

/* --- The event bar -------------------------------------------------------- */
function dismissAnnounce() {
  const close = document.querySelector<HTMLElement>('.announce__close');
  close?.addEventListener('click', () => close.parentElement?.remove());
}

gateAnimations();
watchBelt();
typeQuestion();
runContextLoop();
followPointer();
dismissAnnounce();
