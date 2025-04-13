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
  const MAX_DISPLAY_COST = 50; // $50 limit for visual display
  
  costBars.forEach(bar => {
    const cost = parseFloat(bar.dataset.cost);
    const maxCost = parseFloat(bar.dataset.maxCost);
 
    if (cost > 0 && maxCost > 0) {
      // Use $50 as the max for display purposes
      const displayMaxCost = Math.min(MAX_DISPLAY_COST, maxCost);
      // Calculate percentage based on the display max
      const percent = Math.min(cost, displayMaxCost) / displayMaxCost * 100;
      // Clamp percentage between 0 and 100
      bar.style.width = Math.max(0, Math.min(100, percent)) + '%';
      
      // Mark bars that exceed the limit
      if (cost > MAX_DISPLAY_COST) {
        // Create a darker section at the end with diagonal stripes
        const darkSection = document.createElement('div');
        darkSection.className = 'bar-viz';
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

  // Calculate and add cost ticks dynamically
  const costCells = document.querySelectorAll('.cost-bar-cell');
  if (costCells.length > 0) {
    const MAX_DISPLAY_COST = 50; // $50 limit for visual display
    
    // Generate fixed tick values at $0, $10, $20, $30, $40, $50
    const tickValues = [0, 10, 20, 30, 40, 50];
    
    // Calculate percentage positions for each tick on the linear scale
    const tickPercentages = tickValues.map(tickCost => {
      return (tickCost / MAX_DISPLAY_COST) * 100;
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
            
            // No dollar amount labels
            
            cell.appendChild(tick);
          }
        });
      }
    });
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
