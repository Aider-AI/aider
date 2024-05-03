
# Aider's LLM code editing leaderboard

<table>
  <thead>
    <tr>
      <th>Model</th>
      <th>Second</th>
      <th>First</th>
      <th>Format</th>
      <th>Command</th>
      <th>Version</th>
      <th>Commit</th>
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
        <td>{{ row.version }}</td>
        <td>{{ row.commit }}</td>
        <td>{{ row.date }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>
