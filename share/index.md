
# Shared aider chat transcript

A user has shared the following transcript of a pair programming chat session
created using <a href="https://aider.chat">aider</a>.

<div class="chat-transcript">
</div>

<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
window.onload = function() {
    var urlParams = new URLSearchParams(window.location.search);
    var conv = urlParams.get('mdurl');
    if (!conv) {
        return;
    }
    // Check if the URL is a non-raw GitHub gist
    var gistRegex = /^https:\/\/gist\.github\.com\/[^\/]+\/([a-f0-9]+)$/;
    var match = gistRegex.exec(conv);
    if (match) {
        // If it is, convert it into a raw URL
        conv = 'https://gist.githubusercontent.com/' + match[1] + '/raw';
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
        var divElement = document.querySelector('.chat-transcript');
        divElement.innerHTML = html;
    })
    .catch(error => {
        console.error('Error fetching markdown:', error);
    });
}
</script>
