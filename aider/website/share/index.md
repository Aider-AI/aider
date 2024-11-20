---
nav_exclude: true
---

<meta http-equiv="Content-Security-Policy" 
    content="default-src 'self'; 
             script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; 
             connect-src http: https:;
             style-src 'self' 'unsafe-inline';">

# Shared aider chat transcript

A user has shared the following transcript of a pair programming chat session
created using <a href="https://aider.chat">aider</a>.
Aider is a command line tool that lets you pair program with GPT-3.5 or
GPT-4, to edit code stored in your local git repository.

The transcript is based on <a id="mdurl" href="">this chat transcript data</a>.

<div class="chat-transcript" id="shared-transcript">
</div>

## Transcript format

<div class="chat-transcript" markdown="1">

> This is output from the aider tool.

#### These are chat messages written by the user.

Chat responses from GPT are in a blue font like this,
and often include colorized "diffs" where GPT is editing code:


```python
hello.py
<<<<<<< ORIGINAL
print("hello")
=======
print("goodbye")
>>>>>>> UPDATED
```
</div>

<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js"></script>
<script>
function isValidUrl(url) {
    try {
        const urlObj = new URL(url);
        return urlObj.protocol === 'http:' || urlObj.protocol === 'https:';
    } catch {
        return false;
    }
}

// Configure marked with secure defaults
marked.setOptions({
    headerIds: false,
    mangle: false
});

window.onload = function() {
    var urlParams = new URLSearchParams(window.location.search);
    var conv = urlParams.get('mdurl');
    if (!conv || !isValidUrl(conv)) {
        document.querySelector('#shared-transcript').innerHTML = 
            '<div style="color: red; padding: 1em;">Error: Invalid or missing URL provided</div>';
        return;
    }
    document.getElementById('mdurl').href = conv;
    // Check if the URL is a non-raw GitHub gist
    var gistRegex = /^https:\/\/gist\.github\.com\/([^\/]+)\/([a-f0-9]+)$/;
    var match = gistRegex.exec(conv);
    if (match) {
        // If it is, convert it into a raw URL
        conv = 'https://gist.githubusercontent.com/' + match[1] + '/' + match[2] + '/raw';
    }
    fetch(conv)
    .then(response => response.text())
    .then(markdown => {
        // Ensure every line that starts with '>' ends with exactly 2 spaces
        markdown = markdown.split('\n').map(function(line) {
            if (line.startsWith('>')) {
                return line.trimEnd() + '  ';
            }
            return line;
        }).join('\n');
        var html = marked.parse(markdown);
        var sanitizedHtml = DOMPurify.sanitize(html);
        var divElement = document.querySelector('#shared-transcript');
        divElement.innerHTML = sanitizedHtml;
    })
    .catch(error => {
        console.error('Error fetching markdown:', error);
        document.querySelector('#shared-transcript').innerHTML = 
            '<div style="color: red; padding: 1em;">Error: Failed to load chat transcript</div>';
    });
}
</script>

