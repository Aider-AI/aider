(async function get_contributors(){
    const response = await fetch("https://api.github.com/repos/dwash96/aider-ce/contributors");
    const data = await response.json();
    console.log(data)

    let output = [];

    data.forEach((item) => {
        output.push(`<a href="https://github.com/${item.login}">@${item.login}</a>`)
    });

    console.log(output.join("\n"))
})()