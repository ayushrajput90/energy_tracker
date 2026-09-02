/**
 * Renewable Goals Management & Live Progress Tracking
 */
let goalsList = [];
let deleteGoalId = null;

async function loadGoals() {
  try {
    const data = await API.get('/goals');
    goalsList = data.goals || [];
    renderGoals(goalsList);
  } catch (err) {
    console.error('Failed to load goals:', err);
    UI.showToast('Could not load energy goals.', 'error');
  }
}

function renderGoals(goals) {
  const container = document.getElementById('goals-grid-container');
  if (!container) return;

  if (!goals.length) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; background: var(--bg-surface); border-radius: var(--radius-lg); border: 1px dashed var(--border-strong);">
        <p class="text-muted" style="margin-bottom: 1rem;">No sustainability goals created yet. Set your first milestone!</p>
        <button class="btn btn-primary" onclick="UI.openModal('create-goal-modal')">+ Create Energy Goal</button>
      </div>
    `;
    return;
  }

  container.innerHTML = goals.map(g => {
    const isCompleted = g.status === 'Completed' || g.completion_percentage >= 100;
    const statusBadge = isCompleted 
      ? '<span class="badge badge-success">Completed</span>' 
      : g.status === 'Expired' 
        ? '<span class="badge badge-danger">Expired</span>' 
        : '<span class="badge badge-warning">Active</span>';

    return `
      <div class="kpi-card" style="padding: 1.5rem;">
        <div class="kpi-header">
          <div>
            <span class="badge badge-neutral" style="margin-bottom: 0.375rem;">${g.goal_type}</span>
            <h3 style="font-size: 1.125rem; font-weight: 700; margin: 0;">${g.description || g.goal_type}</h3>
          </div>
          ${statusBadge}
        </div>

        <div style="margin: 1rem 0;">
          <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.25rem;">
            <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-main);">
              ${g.current_value} <span style="font-size: 0.875rem; font-weight: 500; color: var(--text-muted);">${g.unit}</span>
            </div>
            <div class="text-sm font-semibold text-muted">
              Target: ${g.target_value} ${g.unit}
            </div>
          </div>

          <div class="progress-bar-container">
            <div class="progress-bar-fill" style="width: ${Math.min(g.completion_percentage, 100)}%;"></div>
          </div>

          <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
            <span>${g.completion_percentage}% Achieved</span>
            <span>${g.remaining_value > 0 ? `${g.remaining_value} ${g.unit} remaining` : 'Target Reached!'}</span>
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 0.75rem; border-top: 1px solid var(--border-subtle); font-size: 0.75rem; color: var(--text-muted);">
          <span>Timeline: ${g.start_date} to ${g.end_date}</span>
          <div class="table-actions">
            <button class="btn btn-sm btn-outline" onclick="openEditGoalModal(${g.id})" title="Edit">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
            </button>
            <button class="btn btn-sm btn-danger" onclick="confirmDeleteGoal(${g.id})" title="Delete">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

async function handleCreateGoal(event) {
  event.preventDefault();
  const payload = {
    goal_type: document.getElementById('goal-type').value,
    target_value: parseFloat(document.getElementById('goal-target').value),
    start_date: document.getElementById('goal-start-date').value,
    end_date: document.getElementById('goal-end-date').value,
    description: document.getElementById('goal-desc').value
  };

  try {
    await API.post('/goals', payload);
    UI.showToast('Goal created successfully!', 'success');
    UI.closeModal('create-goal-modal');
    document.getElementById('create-goal-form').reset();
    loadGoals();
  } catch (err) {
    UI.showToast(err.message || 'Failed to create goal.', 'error');
  }
}

function openEditGoalModal(goalId) {
  const goal = goalsList.find(g => g.id === goalId);
  if (!goal) return;

  document.getElementById('edit-goal-id').value = goal.id;
  document.getElementById('edit-goal-type').value = goal.goal_type;
  document.getElementById('edit-goal-target').value = goal.target_value;
  document.getElementById('edit-goal-start-date').value = goal.start_date;
  document.getElementById('edit-goal-end-date').value = goal.end_date;
  document.getElementById('edit-goal-desc').value = goal.description || '';
  document.getElementById('edit-goal-status').value = goal.status || 'Active';

  UI.openModal('edit-goal-modal');
}

async function handleUpdateGoal(event) {
  event.preventDefault();
  const id = document.getElementById('edit-goal-id').value;
  const payload = {
    goal_type: document.getElementById('edit-goal-type').value,
    target_value: parseFloat(document.getElementById('edit-goal-target').value),
    start_date: document.getElementById('edit-goal-start-date').value,
    end_date: document.getElementById('edit-goal-end-date').value,
    description: document.getElementById('edit-goal-desc').value,
    status: document.getElementById('edit-goal-status').value
  };

  try {
    await API.put(`/goals/${id}`, payload);
    UI.showToast('Goal updated successfully!', 'success');
    UI.closeModal('edit-goal-modal');
    loadGoals();
  } catch (err) {
    UI.showToast(err.message || 'Failed to update goal.', 'error');
  }
}

function confirmDeleteGoal(goalId) {
  deleteGoalId = goalId;
  UI.openModal('delete-goal-modal');
}

async function executeDeleteGoal() {
  if (!deleteGoalId) return;
  try {
    await API.delete(`/goals/${deleteGoalId}`);
    UI.showToast('Goal deleted successfully.', 'info');
    UI.closeModal('delete-goal-modal');
    deleteGoalId = null;
    loadGoals();
  } catch (err) {
    UI.showToast(err.message || 'Failed to delete goal.', 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('goals-grid-container')) {
    loadGoals();
  }
});
