
# Shared aider chat transcript

A user has shared the following transcript of a pair programming chat session
created using <a href="https://aider.chat">aider</a>.

<div class="chat-transcript">
</div>

<script>
window.onload = function() {
    var urlParams = new URLSearchParams(window.location.search);
    var conv = urlParams.get('mdurl');
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
    });
}
</script>
