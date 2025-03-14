---
parent: Example chat transcripts
nav_order: 9999
layout: minimal
---

# Recording

<link rel="stylesheet" type="text/css" href="/assets/asciinema/asciinema-player.css" />


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
     }
 );
</script>
  
