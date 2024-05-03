
# Aider's LLM code editing leaderboard

<table>
  <thead>
    <tr>
      <th>Model</th>
      <th>Final score</th>
      <th>First try score</th>
      <th>Edit format</th>
      <th>Command</th>
      <th>Version</th>
      <th>Git commit</th>
      <th>Date</th>
    </tr>
  </thead>
  <tbody>
    {% for row in site.data.leaderboard %}
      <tr>
        <td>{{ row.model }}</td>
        <td>{{ row.second }}</td>
        <td>{{ row.first }}</td>
        <td>{{ row.format }}</td>
        <td>{{ row.command }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>
