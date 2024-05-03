
# Aider's LLM code editing leaderboard

<table style="width: 100%; max-width: 960px; margin: auto; border-collapse: collapse;">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th style="padding: 8px; text-align: left;">Model</th>
      <th style="padding: 8px; text-align: left;">Percent correct</th>
      <th style="padding: 8px; text-align: left;">Command</th>
      <th style="padding: 8px; text-align: left;">Edit format</th>
    </tr>
  </thead>
  <tbody>
    {% for row in site.data.leaderboard %}
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px;">{{ row.model }}</td>
        <td style="padding: 8px;">{{ row.second }}%</td>
        <td style="padding: 8px;"><pre style="overflow-x: auto; white-space: pre-wrap;">{{ row.command }}</pre></td>
        <td style="padding: 8px;">{{ row.format }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>
