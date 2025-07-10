document.addEventListener('DOMContentLoaded', function() {
  let currentMode = 'view'; // 'view', 'select', 'detail'
  let selectedRows = new Set(); // Store indices of selected rows
  const MAX_DISPLAY_COST_CAP = 200; // Define the constant here

  const allMainRows = document.querySelectorAll('tr[id^="main-row-"]');
  const allDetailsRows = document.querySelectorAll('tr[id^="details-"]');
  const searchInput = document.getElementById('editSearchInput');
  const modeViewButton = document.getElementById('mode-view-btn');
  const modeDetailButton = document.getElementById('mode-detail-btn');
  const modeSelectButton = document.getElementById('mode-select-btn');
  const modeButtons = [modeViewButton, modeSelectButton, modeDetailButton];
  const selectAllCheckbox = document.getElementById('select-all-checkbox');
  const leaderboardTitle = document.getElementById('leaderboard-title'); // Get title element
  const defaultTitle = "Aider polyglot coding leaderboard";
  const filteredTitle = "Aider polyglot coding benchmark results (selected)";

  function applySearchFilter() {
    const searchInputValue = searchInput.value.toLowerCase();
    // Split by comma, trim whitespace from each term, and filter out empty terms
    const searchTerms = searchInputValue.split(',').map(term => term.trim()).filter(term => term.length > 0);

    allMainRows.forEach(row => {
      const textContent = row.textContent.toLowerCase();
      const detailsRow = document.getElementById(row.id.replace('main-row-', 'details-'));
      let matchesSearch = false;

      if (searchTerms.length === 0) { // If no search terms (e.g., input is empty or just commas/spaces)
        matchesSearch = true; // Show all rows
      } else {
        // Check if the row's text content includes *any* of the search terms (OR logic)
        matchesSearch = searchTerms.some(term => textContent.includes(term));
      }

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
    
    // Update cost bars and ticks since visible rows may have changed
    updateCostBars();
    updateCostTicks();
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

    // Get the first header cell (for the toggle/checkbox column)
    const firstHeaderCell = document.querySelector('table thead th:first-child');

    // Show/hide header checkbox based on mode
    selectAllCheckbox.style.display = mode === 'select' ? 'inline-block' : 'none';

    allMainRows.forEach(row => {
      const rowIndex = row.querySelector('.row-selector')?.dataset.rowIndex;
      const toggleButton = row.querySelector('.toggle-details');
      const selectorCheckbox = row.querySelector('.row-selector');
      const firstCell = row.querySelector('td:first-child'); // Get the first cell of the main row
      const detailsRow = document.getElementById(`details-${rowIndex}`);
      const isSelected = selectedRows.has(rowIndex);

      // Reset visibility classes before applying mode logic
      row.classList.remove('hidden-by-mode');
      if (detailsRow) detailsRow.classList.remove('hidden-by-mode');

      // Show/hide the first column (header and data cells) based on mode
      if (firstHeaderCell) {
          firstHeaderCell.style.display = mode === 'view' ? 'none' : '';
      }
      if (firstCell) {
          firstCell.style.display = mode === 'view' ? 'none' : '';
      }

      // Apply mode-specific logic
      if (mode === 'view') { // --- VIEW MODE ---
          toggleButton.style.display = 'none'; // Hide toggle in view mode
          selectorCheckbox.style.display = 'none';
          row.classList.remove('row-selected'); // Ensure no selection highlight
          // view-highlighted is handled by row click listener

          // In 'view' mode, hide row if selections exist AND this row is NOT selected
          if (selectedRows.size > 0 && !isSelected) {
              row.classList.add('hidden-by-mode');
              if (detailsRow) detailsRow.classList.add('hidden-by-mode');
          } else {
              // Ensure row is not hidden by mode if it's selected or no selections exist
              // This is handled by the reset at the start of the loop:
              // row.classList.remove('hidden-by-mode');
              // if (detailsRow) detailsRow.classList.remove('hidden-by-mode');
          }
          // Always hide details row content in view mode regardless of visibility class
          if (detailsRow) {
              detailsRow.style.display = 'none';
          }

      } else if (mode === 'select') { // --- SELECT MODE ---
          toggleButton.style.display = 'none';
          selectorCheckbox.style.display = 'inline-block';
          selectorCheckbox.checked = isSelected;
          row.classList.toggle('row-selected', isSelected);
          row.classList.remove('view-highlighted'); // Clear view highlight when switching to select
          // Always hide details row in select mode
          if (detailsRow) detailsRow.style.display = 'none';

          // In 'select' mode, no rows should be hidden based on selection status
          row.classList.remove('hidden-by-mode');
          if (detailsRow) detailsRow.classList.remove('hidden-by-mode');

      } else { // --- DETAIL MODE --- (mode === 'detail')
          toggleButton.style.display = 'inline-block'; // Show toggle
          selectorCheckbox.style.display = 'none';
          row.classList.remove('row-selected'); // Clear selection highlight
          row.classList.remove('view-highlighted'); // Clear view highlight when switching to detail
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

    // Update the leaderboard title based on mode and selection
    if (leaderboardTitle) {
      // Check if a custom title is provided globally
      if (typeof LEADERBOARD_CUSTOM_TITLE !== 'undefined' && LEADERBOARD_CUSTOM_TITLE) {
        leaderboardTitle.textContent = LEADERBOARD_CUSTOM_TITLE;
      } else {
        if (currentMode === 'view' && selectedRows.size > 0) {
          leaderboardTitle.textContent = filteredTitle;
        } else {
          leaderboardTitle.textContent = defaultTitle;
        }
      }
    }

    // Update the select-all checkbox state after updating the view
    updateSelectAllCheckboxState();
    
    // Update cost bars and ticks since visible/selected rows may have changed
    updateCostBars();
    updateCostTicks();
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

  // Function to calculate the appropriate max display cost based on visible/selected entries
  function calculateDisplayMaxCost() {
    // Get the appropriate set of rows based on the current mode and selection state
    let rowsToConsider;    
    
    if (currentMode === 'view' && selectedRows.size > 0) {
      // In view mode with selections, only consider selected rows
      rowsToConsider = Array.from(allMainRows).filter(row => {
        const rowIndex = row.querySelector('.row-selector')?.dataset.rowIndex;
        return rowIndex && selectedRows.has(rowIndex) && !row.classList.contains('hidden-by-search');
      });
    } else {
      // In other modes or without selections, consider all visible rows
      rowsToConsider = getVisibleMainRows();
    }
    
    // Find the maximum cost among the rows to consider
    let maxCost = 0;
    rowsToConsider.forEach(row => {
      const costBar = row.querySelector('.cost-bar');
      if (costBar) {
        const cost = parseFloat(costBar.dataset.cost || '0');
        if (cost > maxCost) maxCost = cost;
      }
    });
    
    // Cap at MAX_DISPLAY_COST_CAP if any entries exceed that amount, otherwise use actual max
    return maxCost > MAX_DISPLAY_COST_CAP ? MAX_DISPLAY_COST_CAP : Math.max(1, maxCost); // Ensure at least 1 to avoid division by zero
  }
  
  // Process cost bars with dynamic scale
  function updateCostBars() {
    const costBars = document.querySelectorAll('.cost-bar');
    const currentMaxDisplayCost = calculateDisplayMaxCost();
    
    // Remove existing special indicators first
    document.querySelectorAll('.dark-section, .tear-line').forEach(el => el.remove());
    
    costBars.forEach(bar => {
      const cost = parseFloat(bar.dataset.cost);
      
      if (cost > 0) {
        // Calculate percentage based on the dynamic display max
        const percent = Math.min(cost, currentMaxDisplayCost) / currentMaxDisplayCost * 100;
        // Clamp percentage between 0 and 100
        bar.style.width = Math.max(0, Math.min(100, percent)) + '%';
        
        // Mark bars that exceed the limit (only if our display max is capped at 50)
        if (currentMaxDisplayCost === MAX_DISPLAY_COST_CAP && cost > MAX_DISPLAY_COST_CAP) {
          // Create a darker section at the end with diagonal stripes
          const darkSection = document.createElement('div');
          darkSection.className = 'bar-viz dark-section';
          darkSection.style.width = '15%'; // From 85% to 100%
          darkSection.style.left = '85%';
          darkSection.style.backgroundColor = 'rgba(13, 110, 253, 0.6)'; // Darker blue
          darkSection.style.borderRight = '1px solid rgba(13, 110, 253, 0.8)';
          darkSection.style.zIndex = '1';
          // Add diagonal stripes with CSS background
          darkSection.style.backgroundImage = 'repeating-linear-gradient(45deg, rgba(255,255,255,0.3), rgba(255,255,255,0.3) 5px, transparent 5px, transparent 10px)';
          bar.parentNode.appendChild(darkSection);
          
          // Add a dashed "tear line" at the transition point
          const tearLine = document.createElement('div');
          tearLine.className = 'tear-line';
          tearLine.style.position = 'absolute';
          tearLine.style.left = '85%';
          // Center the tear line vertically and make it 1.5x as tall as the bar
          tearLine.style.top = '50%';
          tearLine.style.transform = 'translateY(-50%)';
          tearLine.style.height = '54px'; // 1.5x the bar height (36px)
          tearLine.style.width = '2px';
          tearLine.style.backgroundColor = 'white';
          tearLine.style.borderLeft = '2px dashed rgba(0, 0, 0, 0.3)';
          tearLine.style.zIndex = '2'; // Above the bar
          bar.parentNode.appendChild(tearLine);
        }
      } else {
        // Set width to 0 if cost is 0 or negative
        bar.style.width = '0%';
      }
    });
  }
  
  // Call this initially to set up the bars
  updateCostBars();

  // Update cost ticks dynamically based on current max display cost
  function updateCostTicks() {
    const costCells = document.querySelectorAll('.cost-bar-cell');
    if (costCells.length === 0) return;
    
    const currentMaxDisplayCost = calculateDisplayMaxCost();
    
    // Remove existing ticks first
    document.querySelectorAll('.cost-tick').forEach(tick => tick.remove());
    
    // Generate appropriate tick values based on current max
    let tickValues = [];
    
    // Always use $10 increments, regardless of the max
    const maxTickValue = Math.ceil(currentMaxDisplayCost / 10) * 10; // Round up to nearest $10
    
    for (let i = 0; i <= maxTickValue; i += 10) {
      tickValues.push(i);
    }
    
    // Calculate percentage positions for each tick
    const tickPercentages = tickValues.map(tickCost => {
      return (tickCost / currentMaxDisplayCost) * 100;
    });
    
    // Add tick divs to each cost cell
    costCells.forEach(cell => {
      const costBar = cell.querySelector('.cost-bar');
      // Use optional chaining and provide '0' as fallback if costBar or dataset.cost is missing
      const cost = parseFloat(costBar?.dataset?.cost || '0');
      
      // Only add ticks if the cost is actually greater than 0
      if (cost > 0) {
        tickPercentages.forEach((percent, index) => {
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
  
  // Call this initially to set up the ticks
  updateCostTicks();


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
      
      // Update cost bars and ticks if in view mode, as selection affects what's shown
      if (currentMode === 'view') {
        updateCostBars();
        updateCostTicks();
      }
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
      
      // Update cost bars and ticks after selection changes
      updateCostBars();
      updateCostTicks();
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

  // --- Sorting Logic ---
  const sortableHeaders = document.querySelectorAll('th[data-sort-key]');
  const tableBodyForSort = document.querySelector('table tbody');

  function getCellValue(row, sortKey) {
    let cellValue;
    let cell;
    switch (sortKey) {
      case 'model':
        cell = row.querySelector('td:nth-child(2) span'); // Model is in the 2nd td
        cellValue = cell ? cell.textContent.trim().toLowerCase() : ''; // For case-insensitive sort
        break;
      case 'pass_rate_2': // Percent correct
        cell = row.querySelector('td:nth-child(3) span'); // Percent correct is in the 3rd td
        cellValue = cell ? parseFloat(cell.textContent) : -1; // Default to -1 if parsing fails
        break;
      case 'total_cost': // Cost
        cell = row.querySelector('td:nth-child(4) span'); // Cost is in the 4th td
        const costText = cell ? cell.textContent.trim() : '';
        if (costText === "" || costText === "$0.00") { // Treat empty or "$0.00" as null for sorting
          cellValue = null;
        } else {
          cellValue = parseFloat(costText.substring(1)); // Remove '$'
          if (isNaN(cellValue)) cellValue = null; // If parsing fails, treat as null
        }
        break;
      case 'percent_cases_well_formed': // Correct edit format
        cell = row.querySelector('td.col-conform span'); // Uses class .col-conform
        cellValue = cell ? parseFloat(cell.textContent) : -1; // Default to -1
        break;
      default:
        cellValue = '';
    }
    return cellValue;
  }

  function sortTable(sortKey, direction) {
    const rowsToSort = Array.from(allMainRows); // Use the globally available allMainRows

    rowsToSort.sort((rowA, rowB) => {
      const valA = getCellValue(rowA, sortKey);
      const valB = getCellValue(rowB, sortKey);

      let comparison = 0;

      // Handle nulls for cost: nulls go to the bottom regardless of direction
      if (sortKey === 'total_cost') {
        if (valA === null && valB !== null) return 1; // A (null) is greater, goes to bottom
        if (valB === null && valA !== null) return -1; // B (null) is greater, A goes to top (relative to B)
        if (valA === null && valB === null) return 0; // Both null, equal
      }

      if (typeof valA === 'string' && typeof valB === 'string') {
        comparison = valA.localeCompare(valB, undefined, { numeric: false, sensitivity: 'base' });
      } else { // Numeric comparison
        if (valA < valB) comparison = -1;
        else if (valA > valB) comparison = 1;
      }
      return direction === 'asc' ? comparison : -comparison;
    });

    // Re-append rows (main and their details)
    rowsToSort.forEach(row => {
      tableBodyForSort.appendChild(row);
      const detailsRowId = row.id.replace('main-row-', 'details-');
      const detailsRow = document.getElementById(detailsRowId);
      if (detailsRow) {
        tableBodyForSort.appendChild(detailsRow);
      }
    });

    applySearchFilter(); // Re-apply search and view mode filters
  }

  sortableHeaders.forEach(header => {
    header.addEventListener('click', () => {
      const sortKey = header.dataset.sortKey;
      const currentDirection = header.dataset.sortDirection;
      const newDirection = (currentDirection === 'desc') ? 'asc' : 'desc'; // Default to desc if not set, or toggle

      sortableHeaders.forEach(h => {
        h.querySelector('.sort-indicator').textContent = '';
        if (h !== header) delete h.dataset.sortDirection; // Clear direction from other headers
      });

      header.dataset.sortDirection = newDirection;
      header.querySelector('.sort-indicator').textContent = newDirection === 'asc' ? '▲' : '▼';
      sortTable(sortKey, newDirection);
    });
  });

// Close button functionality
const closeControlsBtn = document.getElementById('close-controls-btn');
if (closeControlsBtn) {
  closeControlsBtn.addEventListener('click', function() {
    const controlsContainer = document.getElementById('controls-container');
    if (controlsContainer) {
      controlsContainer.style.display = 'none';
    }
  });
}

});
