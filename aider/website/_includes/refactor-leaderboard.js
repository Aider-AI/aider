document.addEventListener('DOMContentLoaded', function () {
  var ctx = document.getElementById('refacChart').getContext('2d');
  var leaderboardData = {
    labels: [],
    datasets: [{
      label: 'Percent completed correctly',
      data: [],
      backgroundColor: 'rgba(54, 162, 235, 0.2)',
      borderColor: 'rgba(54, 162, 235, 1)',
      borderWidth: 1
    }]
  };

  var allData = [];
  {% for row in refac_sorted %}
    allData.push({
      model: '{{ row.model }}',
      pass_rate_1: {{ row.pass_rate_1 }},
      percent_cases_well_formed: {{ row.percent_cases_well_formed }}
    });
  {% endfor %}

  function updateChart() {
    var selectedRows = document.querySelectorAll('tr.selected');
    var showAll = selectedRows.length === 0;

    leaderboardData.labels = [];
    leaderboardData.datasets[0].data = [];

    allData.forEach(function(row, index) {
      var rowElement = document.getElementById('refac-row-' + index);
      if (showAll) {
        rowElement.classList.remove('selected');
      }
      if (showAll || rowElement.classList.contains('selected')) {
        leaderboardData.labels.push(row.model);
        leaderboardData.datasets[0].data.push(row.pass_rate_1);
      }
    });

    leaderboardChart.update();
  }

  var tableBody = document.querySelectorAll('table tbody')[1];
  allData.forEach(function(row, index) {
    var tr = tableBody.children[index];
    tr.id = 'refac-row-' + index;
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

  // Add search functionality for refactoring table
  document.getElementById('refacSearchInput').addEventListener('keyup', function() {
    var searchWords = this.value.toLowerCase().split(' ').filter(word => word.length > 0);
    var tableBody = document.querySelectorAll('table tbody')[1];
    var rows = tableBody.getElementsByTagName('tr');
    
    leaderboardData.labels = [];
    leaderboardData.datasets[0].data = [];
    
    for (var i = 0; i < rows.length; i++) {
      var rowText = rows[i].textContent;
      if (searchWords.every(word => rowText.toLowerCase().includes(word))) {
        rows[i].style.display = '';
        leaderboardData.labels.push(allData[i].model);
        leaderboardData.datasets[0].data.push(allData[i].pass_rate_1);
      } else {
        rows[i].style.display = 'none';
      }
    }
    leaderboardChart.update();
  });
});
