document.addEventListener('DOMContentLoaded', function() {
  let currentMode = 'view'; // 'view', 'select', 'detail'
  let selectedRows = new Set(); // Store indices of selected rows

  const allMainRows = document.querySelectorAll('tr[id^="main-row-"]');
  const allDetailsRows = document.querySelectorAll('tr[id^="details-"]');
  const searchInput = document.getElementById('editSearchInput');
  const modeViewButton = document.getElementById('mode-view-btn');
  const modeDetailButton = document.getElementById('mode-detail-btn');
  const modeSelectButton = document.getElementById('mode-select-btn');
  const modeButtons = [modeViewButton, modeDetailButton, modeSelectButton];
  const selectAllCheckbox = document.getElementById('select-all-checkbox');

  function applySearchFilter() {
    const searchTerm = searchInput.value.toLowerCase();
    allMainRows.forEach(row => {
      const textContent = row.textContent.toLowerCase();
      const detailsRow = document.getElementById(row.id.replace('main-row-', 'details-'));
      const matchesSearch = textContent.includes(searchTerm);

      if (matchesSearch) {
        row.classList.remove('hidden-by-search');
        if (detailsRow) detailsRow.classList.remove('hidden-by-search');
      } else {
        row.classList.add('hidden-by-search');
        if (detailsRow) detailsRow.classList.add('hidden-by-search');
      }
    });
    // After applying search filter, re-apply view mode filter and update select-all state
    updateTableView(currentMode);
    if (currentMode === 'select') {
        updateSelectAllCheckboxState();
    }
  }

  function getVisibleMainRows() {
      // Helper to get rows currently visible (not hidden by search or mode)
      return Array.from(allMainRows).filter(row =>
          !row.classList.contains('hidden-by-search') && !row.classList.contains('hidden-by-mode')
      );
  }

  function updateSelectAllCheckboxState() {
      // Update the header checkbox based on the selection state of *visible* rows
      if (currentMode !== 'select') return; // Only relevant in select mode

      const visibleRows = getVisibleMainRows();
      const visibleRowCount = visibleRows.length;
      const selectedVisibleRowCount = visibleRows.filter(row => selectedRows.has(row.querySelector('.row-selector')?.dataset.rowIndex)).length;

      if (visibleRowCount === 0) {
          selectAllCheckbox.checked = false;
          selectAllCheckbox.indeterminate = false;
      } else if (selectedVisibleRowCount === visibleRowCount) {
          selectAllCheckbox.checked = true;
          selectAllCheckbox.indeterminate = false;
      } else if (selectedVisibleRowCount > 0) {
          selectAllCheckbox.checked = false;
          selectAllCheckbox.indeterminate = true;
      } else {
          selectAllCheckbox.checked = false;
          selectAllCheckbox.indeterminate = false;
      }
  }


  function updateTableView(mode) {
    currentMode = mode; // Update global state ('view', 'select', 'detail')

    // Update button styles first
    modeButtons.forEach(btn => {
        btn.classList.remove('active');
        // Reset specific styles potentially added by .active
        btn.style.backgroundColor = '';
        btn.style.color = '';
    });
    let activeButton;
    if (mode === 'view') activeButton = modeViewButton;
    else if (mode === 'select') activeButton = modeSelectButton;
    else if (mode === 'detail') activeButton = modeDetailButton;

    activeButton.classList.add('active');
    activeButton.style.backgroundColor = '#e7f3ff'; // Use selected row highlight blue
    activeButton.style.color = '#495057'; // Use dark text for contrast on light blue


    // Show/hide header checkbox based on mode
    selectAllCheckbox.style.display = mode === 'select' ? 'inline-block' : 'none';

    allMainRows.forEach(row => {
      const rowIndex = row.querySelector('.row-selector')?.dataset.rowIndex;
      const toggleButton = row.querySelector('.toggle-details');
      const selectorCheckbox = row.querySelector('.row-selector');
      const detailsRow = document.getElementById(`details-${rowIndex}`);
      const isSelected = selectedRows.has(rowIndex);

      // Reset visibility classes before applying mode logic
      row.classList.remove('hidden-by-mode');
      if (detailsRow) detailsRow.classList.remove('hidden-by-mode');

      // Apply mode-specific logic
      if (mode === 'view') { // --- VIEW MODE ---
          toggleButton.style.display = 'none'; // Hide toggle in view mode
          selectorCheckbox.style.display = 'none';
          row.classList.remove('row-selected'); // Ensure no selection highlight in view mode
          // view-highlighted is handled by row click listener

          // Always show main row (if not filtered by search)
          row.classList.remove('hidden-by-mode');
          if (detailsRow) {
              detailsRow.classList.remove('hidden-by-mode');
              detailsRow.style.display = 'none'; // Always hide details in view mode
          }

      } else if (mode === 'select') { // --- SELECT MODE ---
          toggleButton.style.display = 'none';
          selectorCheckbox.style.display = 'inline-block';
          selectorCheckbox.checked = isSelected;
          row.classList.toggle('row-selected', isSelected);
          row.classList.remove('view-highlighted'); // Clear view highlight
          // Always hide details row in select mode
          if (detailsRow) detailsRow.style.display = 'none';

          // In 'select' mode, no rows should be hidden based on selection status
          row.classList.remove('hidden-by-mode');
          if (detailsRow) detailsRow.classList.remove('hidden-by-mode');

      } else { // --- DETAIL MODE --- (mode === 'detail')
          toggleButton.style.display = 'inline-block'; // Show toggle
          selectorCheckbox.style.display = 'none';
          row.classList.remove('row-selected'); // Clear selection highlight
          row.classList.remove('view-highlighted'); // Clear view highlight
          // Details row visibility is controlled by the toggle button state, don't force hide/show here
          // Ensure main row is visible if not hidden by search
          row.classList.remove('hidden-by-mode');
          if (detailsRow) {
              detailsRow.classList.remove('hidden-by-mode');
              // Preserve existing display state (controlled by toggle) unless hidden by search
              if (detailsRow.classList.contains('hidden-by-search')) {
                  detailsRow.style.display = 'none';
              }
          }
      }


      // Ensure rows hidden by search remain hidden regardless of mode
      if (row.classList.contains('hidden-by-search')) {
          row.style.display = 'none';
          if (detailsRow) detailsRow.style.display = 'none';
      } else if (!row.classList.contains('hidden-by-mode')) {
          // Make row visible if not hidden by search or mode
          row.style.display = ''; // Or 'table-row' if needed, but '' usually works
      } else {
          // Row is hidden by mode, ensure it's hidden
          row.style.display = 'none';
          if (detailsRow) detailsRow.style.display = 'none';
      }


    });

    // Update the select-all checkbox state after updating the view
    updateSelectAllCheckboxState();
  }


  // --- Existing Initializations ---
  // Add percentage ticks
  const percentCells = document.querySelectorAll('.bar-cell:not(.cost-bar-cell)');
  percentCells.forEach(cell => {
    // Add ticks at 0%, 10%, 20%, ..., 100%
    for (let i = 0; i <= 100; i += 10) {
      const tick = document.createElement('div');
      tick.className = 'percent-tick';
      tick.style.left = `${i}%`;
      cell.appendChild(tick);
    }
  });

  // Process cost bars
  const costBars = document.querySelectorAll('.cost-bar');
  costBars.forEach(bar => {
    const cost = parseFloat(bar.dataset.cost);
    const maxCost = parseFloat(bar.dataset.maxCost);
 
    if (cost > 0 && maxCost > 0) {
      // Use log10(1 + x) for scaling. Adding 1 handles potential cost=0 and gives non-zero logs for cost > 0.
      const logCost = Math.log10(1 + cost);
      const logMaxCost = Math.log10(1 + maxCost);
 
      if (logMaxCost > 0) {
        // Calculate percentage relative to the log of max cost
        const percent = (logCost / logMaxCost) * 100;
        // Clamp percentage between 0 and 100
        bar.style.width = Math.max(0, Math.min(100, percent)) + '%';
      } else {
        // Handle edge case where maxCost is 0 (so logMaxCost is 0)
        // If maxCost is 0, cost must also be 0, handled below.
        // If maxCost > 0 but logMaxCost <= 0 (e.g., maxCost is very small), set width relative to cost?
        // For simplicity, setting to 0 if logMaxCost isn't positive.
        bar.style.width = '0%';
      }
    } else {
      // Set width to 0 if cost is 0 or negative
      bar.style.width = '0%';
    }
  });

  // Calculate and add cost ticks dynamically
  const costCells = document.querySelectorAll('.cost-bar-cell');
  if (costCells.length > 0) {
    // Find the max cost from the first available cost bar's data attribute
    const firstCostBar = document.querySelector('.cost-bar');
    const maxCost = parseFloat(firstCostBar?.dataset.maxCost || '1'); // Use 1 as fallback

    if (maxCost > 0) {
      const logMaxCost = Math.log10(1 + maxCost);

      if (logMaxCost > 0) { // Ensure logMaxCost is positive to avoid division by zero or negative results
        const tickValues = [];
        // Generate ticks starting at $0, then $10, $20, $30... up to maxCost
        tickValues.push(0); // Add tick at base (0 position)
        for (let tickCost = 10; tickCost <= maxCost; tickCost += 10) {
          tickValues.push(tickCost);
        }

        // Calculate percentage positions for each tick on the log scale
        const tickPercentages = tickValues.map(tickCost => {
          const logTickCost = Math.log10(1 + tickCost);
          return (logTickCost / logMaxCost) * 100;
        });

        // Add tick divs to each cost cell
        costCells.forEach(cell => {
          const costBar = cell.querySelector('.cost-bar');
          // Use optional chaining and provide '0' as fallback if costBar or dataset.cost is missing
          const cost = parseFloat(costBar?.dataset?.cost || '0');

          // Only add ticks if the cost is actually greater than 0
          if (cost > 0) {
            // Clear existing ticks if any (e.g., during updates, though not strictly needed here)
            // cell.querySelectorAll('.cost-tick').forEach(t => t.remove());

            tickPercentages.forEach(percent => {
              // Ensure percentage is within valid range
              if (percent >= 0 && percent <= 100) {
                const tick = document.createElement('div');
                tick.className = 'cost-tick';
                tick.style.left = `${percent}%`;
                cell.appendChild(tick);
              }
            });
          }
        });
      }
    }
  }


  // --- New Event Listeners ---

  // Listener for mode toggle buttons
  modeButtons.forEach(button => {
    button.addEventListener('click', function(event) {
      const newMode = this.dataset.mode;
      if (newMode !== currentMode) {
        // Update active button style
        modeButtons.forEach(btn => {
            btn.classList.remove('active');
            // Reset specific styles potentially added by .active
            btn.style.backgroundColor = '';
            btn.style.color = '';
        });
        this.classList.add('active');
        // Apply active styles directly as inline styles might interfere
        this.style.backgroundColor = '#e7f3ff'; // Use selected row highlight blue
        this.style.color = '#495057'; // Use dark text for contrast on light blue

        // Update table view and apply filters
        updateTableView(newMode);
        applySearchFilter(); // Re-apply search filter when mode changes
      }
    });
  });

  // Listener for row selector checkboxes (using event delegation on table body)
  const tableBody = document.querySelector('table tbody');
  tableBody.addEventListener('change', function(event) {
    if (event.target.classList.contains('row-selector') && currentMode === 'select') {
      const checkbox = event.target;
      const rowIndex = checkbox.dataset.rowIndex;
      const mainRow = checkbox.closest('tr');

      if (checkbox.checked) {
        selectedRows.add(rowIndex);
        mainRow.classList.add('row-selected');
      } else {
        selectedRows.delete(rowIndex);
        mainRow.classList.remove('row-selected');
      }
      // Update select-all checkbox state
      updateSelectAllCheckboxState();
    }
  }); // End of tableBody listener

  // Listener for Select All checkbox
  selectAllCheckbox.addEventListener('change', function() {
      if (currentMode !== 'select') return;

      const isChecked = selectAllCheckbox.checked;
      // Select/deselect only the rows that are currently visible
      const visibleRows = getVisibleMainRows();

      visibleRows.forEach(row => {
          const checkbox = row.querySelector('.row-selector');
          const rowIndex = checkbox?.dataset.rowIndex;
          if (!checkbox || !rowIndex) return; // Skip if no checkbox/index found

          // Only change state if it differs from target state
          if (checkbox.checked !== isChecked) {
              checkbox.checked = isChecked;
              row.classList.toggle('row-selected', isChecked);
              if (isChecked) {
                  selectedRows.add(rowIndex);
              } else {
                  selectedRows.delete(rowIndex);
              }
          }
      });
      // After bulk change, ensure the selectAll checkbox state is correct (not indeterminate)
      updateSelectAllCheckboxState();
  });

  // Listener for search input
  searchInput.addEventListener('input', applySearchFilter);

  // Add toggle functionality for details (Modified to respect modes)
  const toggleButtons = document.querySelectorAll('.toggle-details');
  toggleButtons.forEach(button => {
    button.addEventListener('click', function() {
      // Only allow toggling in 'detail' mode
      if (currentMode !== 'detail') return;

      const targetId = this.getAttribute('data-target');
      const targetRow = document.getElementById(targetId);
      const mainRow = this.closest('tr'); // Get the main row associated with this button

      if (targetRow && !mainRow.classList.contains('hidden-by-mode') && !mainRow.classList.contains('hidden-by-search')) {
        const isVisible = targetRow.style.display !== 'none';
        targetRow.style.display = isVisible ? 'none' : 'table-row';
        this.textContent = isVisible ? '▶' : '▼';
      }
    });
  });

  // Listener for clicking anywhere on a row
  tableBody.addEventListener('click', function(event) {
    const clickedRow = event.target.closest('tr');

    // Ensure it's a main row and not a details row or header/footer
    if (!clickedRow || !clickedRow.id.startsWith('main-row-')) return;

    // --- START conditional logic ---
    if (currentMode === 'select') {
        // --- SELECT MODE LOGIC (Existing) ---
        // Find the checkbox within this row
        const checkbox = clickedRow.querySelector('.row-selector');
        if (!checkbox) return; // No checkbox found in this row

        // If the click was directly on the checkbox or its label (if any),
        // let the default behavior and the 'change' event listener handle it.
        // Otherwise, toggle the checkbox state programmatically.
        if (event.target !== checkbox && event.target.tagName !== 'LABEL' /* Add if you use labels */) {
            checkbox.checked = !checkbox.checked;
            // Manually trigger the change event to update state and UI
            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
        }
        // --- END SELECT MODE LOGIC ---

    } else if (currentMode === 'view') {
        // --- VIEW MODE LOGIC (New) ---
        // Don't highlight if the click was on the details toggle button
        if (event.target.classList.contains('toggle-details')) {
            return;
        }
        // Toggle the highlight class on the clicked row
        clickedRow.classList.toggle('view-highlighted');
        // --- END VIEW MODE LOGIC ---
    }
    // --- END conditional logic ---
  });


  // --- Initial Setup ---
  updateTableView('view'); // Initialize view to 'view' mode
  applySearchFilter(); // Apply initial search filter (if any text is pre-filled or just to set initial state)


});
