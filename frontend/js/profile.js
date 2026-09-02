/**
 * User Profile Management
 */
async function loadUserProfile() {
  try {
    const data = await API.get('/settings');
    const user = data.user || {};
    const settings = data.settings || {};

    const elName = document.getElementById('profile-name');
    if (elName) elName.value = user.full_name || '';

    const elEmail = document.getElementById('profile-email');
    if (elEmail) elEmail.value = user.email || '';

    const elCreated = document.getElementById('profile-created');
    if (elCreated && user.created_at) {
      elCreated.textContent = new Date(user.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
    }

    const elHeaderName = document.getElementById('profile-header-name');
    if (elHeaderName) elHeaderName.textContent = user.full_name || user.email;

    const elHeaderEmail = document.getElementById('profile-header-email');
    if (elHeaderEmail) elHeaderEmail.textContent = user.email;

    const elAvatar = document.getElementById('profile-avatar-large');
    if (elAvatar) elAvatar.textContent = (user.full_name || user.email || 'U')[0].toUpperCase();
  } catch (err) {
    console.error('Failed to load profile:', err);
    UI.showToast('Could not load user profile.', 'error');
  }
}

async function handleUpdateProfile(event) {
  event.preventDefault();
  const fullName = document.getElementById('profile-name').value.trim();
  const currentPassword = document.getElementById('profile-current-pass')?.value || '';
  const newPassword = document.getElementById('profile-new-pass')?.value || '';

  const payload = { full_name: fullName };
  if (newPassword) {
    if (!currentPassword) {
      UI.showToast('Please enter your current password to set a new password.', 'warning');
      return;
    }
    payload.current_password = currentPassword;
    payload.new_password = newPassword;
  }

  try {
    const res = await API.put('/settings/profile', payload);
    localStorage.setItem('user_info', JSON.stringify(res.user));
    UI.populateUserBadge();
    UI.showToast('Profile updated successfully!', 'success');
    if (document.getElementById('profile-current-pass')) document.getElementById('profile-current-pass').value = '';
    if (document.getElementById('profile-new-pass')) document.getElementById('profile-new-pass').value = '';
    loadUserProfile();
  } catch (err) {
    UI.showToast(err.message || 'Failed to update profile.', 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('profile-name')) {
    loadUserProfile();
  }
});
