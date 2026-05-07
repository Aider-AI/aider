"""
generative_bg.py — Living generative art background for the aider Streamlit GUI.

Usage (in gui.py or any Streamlit entrypoint):

    from aider.generative_bg import inject_generative_background
    inject_generative_background()

Call it once, early in the Streamlit script (before st.title / st.write calls),
so the fixed-position canvas is registered before the rest of the page renders.

The canvas is z-index: -1, pointer-events: none — completely invisible to clicks.
"""


def inject_generative_background():
    """Injects a living generative art background behind the Streamlit UI."""
    import streamlit.components.v1 as components

    html = """
<!DOCTYPE html>
<html>
<head>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 100%; height: 100%; overflow: hidden; background: transparent; }

  #bg-canvas-wrapper {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: -1;
    pointer-events: none;
    overflow: hidden;
  }

  /* Subtle gradient veil at the bottom — fades art into the dark base */
  #bg-canvas-wrapper::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 35vh;
    background: linear-gradient(
      to bottom,
      transparent 0%,
      rgba(13, 17, 23, 0.55) 60%,
      rgba(13, 17, 23, 0.85) 100%
    );
    pointer-events: none;
  }

  #defaultCanvas0 {
    display: block;
    position: absolute;
    top: 0;
    left: 0;
  }
</style>
</head>
<body>
<div id="bg-canvas-wrapper"></div>

<script src="https://cdn.jsdelivr.net/npm/p5@1.9.4/lib/p5.min.js"></script>
<script>
// ─── Flow Field + Particle System ─────────────────────────────────────────────
//
// Design goals
//   • Subtle enough that the eye catches it only after a few seconds
//   • Noise-driven vectors create gentle, organic drift — not random jitter
//   • Deep indigo / blue-violet palette on near-black (#0d1117)
//   • Very low opacity trails accumulate into barely-visible wisps
//   • Fixed seed → same opening composition on every reload
//   • 30 fps cap → roughly halves GPU cost vs uncapped rAF
// ─────────────────────────────────────────────────────────────────────────────

const SEED           = 4217;
const NUM_PARTICLES  = 220;
const PARTICLE_SPEED = 0.55;   // px / frame at 30fps
const NOISE_SCALE    = 0.0023; // spatial frequency of the noise field
const NOISE_Z_SPEED  = 0.0004; // how fast the field evolves over time
const TRAIL_ALPHA    = 0.06;   // 0–255 — opacity of each paint stroke
const FADE_ALPHA     = 6;      // how aggressively old trails fade each frame
const MIN_PX         = 1.0;
const MAX_PX         = 2.2;

// Palette: indigo → deep blue → violet, very dark
const PALETTE = [
  [60,  50,  120],  // deep indigo
  [40,  60,  140],  // navy-indigo
  [70,  40,  110],  // purple-indigo
  [30,  80,  150],  // blue-indigo
  [55,  35,  100],  // dark violet
  [45,  90,  160],  // muted blue
];

const sketch = (p) => {

  let particles = [];
  let noiseZ    = 0;
  let lastMs    = 0;
  const FRAME_MS = 1000 / 30; // ~33 ms

  // ── helpers ────────────────────────────────────────────────────────────────

  function makeParticle() {
    const col = PALETTE[p.floor(p.random(PALETTE.length))];
    return {
      x:   p.random(p.width),
      y:   p.random(p.height),
      px:  0,
      py:  0,
      sz:  p.random(MIN_PX, MAX_PX),
      r:   col[0],
      g:   col[1],
      b:   col[2],
    };
  }

  function resetParticle(pt) {
    // Respawn at a random edge so particles don't cluster in the center
    const edge = p.floor(p.random(4));
    if (edge === 0) { pt.x = p.random(p.width);  pt.y = -5; }
    else if (edge === 1) { pt.x = p.width + 5;   pt.y = p.random(p.height); }
    else if (edge === 2) { pt.x = p.random(p.width);  pt.y = p.height + 5; }
    else                 { pt.x = -5;             pt.y = p.random(p.height); }
    const col = PALETTE[p.floor(p.random(PALETTE.length))];
    pt.r = col[0]; pt.g = col[1]; pt.b = col[2];
  }

  // ── p5 lifecycle ───────────────────────────────────────────────────────────

  p.setup = () => {
    p.randomSeed(SEED);
    p.noiseSeed(SEED);

    const cnv = p.createCanvas(p.windowWidth, p.windowHeight);
    cnv.parent('bg-canvas-wrapper');

    p.background(13, 17, 23); // #0d1117
    p.noStroke();
    p.frameRate(30);

    for (let i = 0; i < NUM_PARTICLES; i++) {
      particles.push(makeParticle());
    }
  };

  p.draw = () => {
    // Manual 30 fps gate (belt + suspenders alongside p.frameRate(30))
    const now = performance.now();
    if (now - lastMs < FRAME_MS - 2) return;
    lastMs = now;

    // Very slow fade — let trails linger for a ghostly smear effect
    p.fill(13, 17, 23, FADE_ALPHA);
    p.rect(0, 0, p.width, p.height);

    noiseZ += NOISE_Z_SPEED;

    for (let i = 0; i < particles.length; i++) {
      const pt = particles[i];

      // Sample Perlin noise to get a flow angle
      const nx    = pt.x * NOISE_SCALE;
      const ny    = pt.y * NOISE_SCALE;
      const angle = p.noise(nx, ny, noiseZ) * p.TWO_PI * 2.5;

      pt.px = pt.x;
      pt.py = pt.y;
      pt.x += Math.cos(angle) * PARTICLE_SPEED;
      pt.y += Math.sin(angle) * PARTICLE_SPEED;

      // Respawn if out of bounds
      if (pt.x < -10 || pt.x > p.width + 10 ||
          pt.y < -10 || pt.y > p.height + 10) {
        resetParticle(pt);
        continue;
      }

      // Draw as a tiny ellipse — not a line — for a dotted-mist look
      p.fill(pt.r, pt.g, pt.b, TRAIL_ALPHA * 255);
      p.ellipse(pt.x, pt.y, pt.sz, pt.sz);
    }
  };

  p.windowResized = () => {
    p.resizeCanvas(p.windowWidth, p.windowHeight);
    p.background(13, 17, 23);
  };
};

// Attach to the wrapper div, not document.body
new p5(sketch);
</script>
</body>
</html>
""".strip()

    # height=0 with scrolling="no" lets the fixed-positioned canvas fill the
    # real viewport without the iframe itself taking up layout space.
    # The iframe is transparent; only the canvas inside it is visible.
    components.html(
        html,
        height=0,
        scrolling=False,
    )
