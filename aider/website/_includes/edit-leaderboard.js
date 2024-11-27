document.addEventListener('DOMContentLoaded', function () {
  var ctx = document.getElementById('editChart').getContext('2d');
  const HIGHTLIGHT_MODEL = 'no no no no';
  var leaderboardData = {
    labels: [],
    datasets: [{
      label: 'Percent completed correctly',
      data: [],
      backgroundColor: function(context) {
        const label = context.chart.data.labels[context.dataIndex] || '';
        return (label && label.includes(HIGHTLIGHT_MODEL)) ? 'rgba(255, 99, 132, 0.2)' : 'rgba(54, 162, 235, 0.2)';
      },
      borderColor: function(context) {
        const label = context.chart.data.labels[context.dataIndex] || '';
        return (label && label.includes(HIGHTLIGHT_MODEL)) ? 'rgba(255, 99, 132, 1)' : 'rgba(54, 162, 235, 1)';
      },
      borderWidth: 1
    }]
  };

  var allData = [];
  {% for row in edit_sorted %}
    allData.push({
      model: '{{ row.model }}',
      pass_rate_2: {{ row.pass_rate_2 }},
      percent_cases_well_formed: {{ row.percent_cases_well_formed }}
    });
  {% endfor %}

  function updateChart() {
    var selectedRows = document.querySelectorAll('tr.selected');
    var showAll = selectedRows.length === 0;

    leaderboardData.labels = [];
    leaderboardData.datasets[0].data = [];

    allData.forEach(function(row, index) {
      var rowElement = document.getElementById('edit-row-' + index);
      if (showAll) {
        rowElement.classList.remove('selected');
      }
      if (showAll || rowElement.classList.contains('selected')) {
        leaderboardData.labels.push(row.model);
        leaderboardData.datasets[0].data.push(row.pass_rate_2);
      }
    });

    leaderboardChart.update();
  }

  var tableBody = document.querySelector('table tbody');
  allData.forEach(function(row, index) {
    var tr = tableBody.children[index];
    tr.id = 'edit-row-' + index;
    tr.style.cursor = 'pointer';
    tr.onclick = function() {
      this.classList.toggle('selected');
      updateChart();
    };
  });

  var leaderboardChart = new Chart(ctx, {
    type: 'bar',
    data: leaderboardData,
    options: {
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  });

  updateChart();
  
  // Add search functionality for edit table
  document.getElementById('editSearchInput').addEventListener('keyup', function() {
    var searchWords = this.value.toLowerCase().split(' ').filter(word => word.length > 0);
    var tableBody = document.querySelector('table:first-of-type tbody');
    var rows = tableBody.getElementsByTagName('tr');
    
    leaderboardData.labels = [];
    leaderboardData.datasets[0].data = [];
    
    for (var i = 0; i < rows.length; i++) {
      var rowText = rows[i].textContent;
      if (searchWords.every(word => rowText.toLowerCase().includes(word))) {
        rows[i].style.display = '';
        leaderboardData.labels.push(allData[i].model);
        leaderboardData.datasets[0].data.push(allData[i].pass_rate_2);
      } else {
        rows[i].style.display = 'none';
      }
    }
    leaderboardChart.update();
  });
});
