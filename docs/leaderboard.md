
# Aider's LLM code editing leaderboard

<table>
  <thead>
    <tr>
      <th>Model</th>
      <th>Percent correct</th>
      <th>Command</th>
      <th>Edit format</th>
    </tr>
  </thead>
  <tbody>
    {% for row in site.data.leaderboard %}
      <tr>
        <td>{{ row.model }}</td>
        <td>{{ row.second }}%</td>
        <td>`{{ row.command }}`</td>
        <td>{{ row.format }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>
