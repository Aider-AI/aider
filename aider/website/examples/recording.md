---
parent: Example chat transcripts
nav_order: 9999
layout: minimal
---

# Recording

<link rel="stylesheet" type="text/css" href="/assets/asciinema/asciinema-player.css" />

<style>
.asciinema-player-theme-aider {
  /* Foreground (default text) color */
  --term-color-foreground: #444444;  /* colour238 */

  /* Background color */
  --term-color-background: #fff000; 

  /* Palette of 16 standard ANSI colors */
  --term-color-0: #21222c;
  --term-color-1: #ff5555;
  --term-color-2: #50fa7b;
  --term-color-3: #f1fa8c;
  --term-color-4: #bd93f9;
  --term-color-5: #ff79c6;
  --term-color-6: #8be9fd;
  --term-color-7: #f8f8f2;
  --term-color-8: #6272a4;
  --term-color-9: #ff6e6e;
  --term-color-10: #69ff94;
  --term-color-11: #ffffa5;
  --term-color-12: #d6acff;
  --term-color-13: #ff92df;
  --term-color-14: #a4ffff;
  --term-color-15: #ffffff;
}
</style>

<div id="demo" style="max-height: 80vh; overflow: hidden;"></div>
<script src="/assets/asciinema/asciinema-player.min.js"></script>

<script>
url = "https://gist.githubusercontent.com/paul-gauthier/3011ab9455c2d28c0e5a60947202752f/raw/5a5b3dbf68a9c2b22b4954af287efedecdf79d52/tmp.redacted.cast";
AsciinemaPlayer.create(
     url,
     document.getElementById('demo'),
     {
         speed: 1.25,
         idleTimeLimit: 1,
         theme : "aider",
     }
 );
</script>
  
