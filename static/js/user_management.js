
const API_BASE = '/api';
let currentRoleId = null;
let allPermissions = [];

// Load initial data
$(document).ready(function() {
    loadUsers();
    loadRoles();
    loadPermissions();
});

// Users Management
function loadUsers() {
    $.get(`${API_BASE}/users`, function(users) {
        const tbody = $('#usersTable tbody');
        tbody.empty();

        users.forEach(user => {
            const lastLogin = user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never';
            const statusBadge = user.status === 'active' ? 'success' : user.status === 'locked' ? 'danger' : 'warning';

            tbody.append(`
                <tr>
                    <td>${user.name}</td>
                    <td>${user.username}</td>
                    <td>${user.email || '-'}</td>
                    <td><span class="badge bg-info">${user.role_name}</span></td>
                    <td><span class="badge bg-${statusBadge}">${user.status}</span></td>
                    <td>${lastLogin}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="editUser(${user.id})">
                            <i class="bi bi-pencil"></i>
                        </button>
                        ${user.status === 'active' ? 
                            `<button class="btn btn-sm btn-warning" onclick="toggleUserStatus(${user.id}, 'inactive')">
                                <i class="bi bi-pause"></i>
                            </button>` :
                            `<button class="btn btn-sm btn-success" onclick="toggleUserStatus(${user.id}, 'active')">
                                <i class="bi bi-play"></i>
                            </button>`
                        }
                        <button class="btn btn-sm btn-info" onclick="resetPassword(${user.id})">
                            <i class="bi bi-key"></i>
                        </button>
                    </td>
                </tr>
            `);
        });
    });
}

function showAddUserModal() {
    $('#userModalTitle').text('Add User');
    $('#userForm')[0].reset();
    $('#userId').val('');
    $('#passwordGroup').show();
    $('#userPassword').prop('required', true);
    
    loadRolesDropdown();
    
    const modal = new bootstrap.Modal($('#userModal'));
    modal.show();
}

function editUser(userId) {
    $.get(`${API_BASE}/users/${userId}`, function(user) {
        $('#userModalTitle').text('Edit User');
        $('#userId').val(user.id);
        $('#userName').val(user.name);
        $('#userUsername').val(user.username).prop('disabled', true);
        $('#userEmail').val(user.email);
        $('#userPhone').val(user.phone);
        $('#userRole').val(user.role_id);
        $('#passwordGroup').hide();
        $('#userPassword').prop('required', false);
        
        loadRolesDropdown(user.role_id);
        
        const modal = new bootstrap.Modal($('#userModal'));
        modal.show();
    });
}

function saveUser() {
    const userId = $('#userId').val();
    const data = {
        name: $('#userName').val(),
        username: $('#userUsername').val(),
        email: $('#userEmail').val(),
        phone: $('#userPhone').val(),
        role_id: parseInt($('#userRole').val())
    };

    if (!userId) {
        data.password = $('#userPassword').val();
        
        if (!data.password || data.password.length < 6) {
            alert('Password must be at least 6 characters');
            return;
        }
    }

    const url = userId ? `${API_BASE}/users/${userId}` : `${API_BASE}/users`;
    const method = userId ? 'PUT' : 'POST';

    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function() {
            bootstrap.Modal.getInstance($('#userModal')).hide();
            loadUsers();
            alert('User saved successfully');
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to save user'));
        }
    });
}

function toggleUserStatus(userId, newStatus) {
    if (!confirm(`Are you sure you want to ${newStatus === 'active' ? 'activate' : 'deactivate'} this user?`)) {
        return;
    }

    $.ajax({
        url: `${API_BASE}/users/${userId}/status`,
        method: 'PATCH',
        contentType: 'application/json',
        data: JSON.stringify({ status: newStatus }),
        success: function() {
            loadUsers();
            alert('User status updated');
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to update status'));
        }
    });
}

function resetPassword(userId) {
    const newPassword = prompt('Enter new password (min 6 characters):');
    
    if (!newPassword) return;
    
    if (newPassword.length < 6) {
        alert('Password must be at least 6 characters');
        return;
    }

    $.ajax({
        url: `${API_BASE}/users/${userId}/reset-password`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ password: newPassword }),
        success: function() {
            alert('Password reset successfully. User will be required to change it on next login.');
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to reset password'));
        }
    });
}

function loadRolesDropdown(selectedRoleId) {
    $.get(`${API_BASE}/roles`, function(roles) {
        const select = $('#userRole');
        select.empty();
        
        roles.forEach(role => {
            select.append(`<option value="${role.id}" ${role.id === selectedRoleId ? 'selected' : ''}>${role.role_name}</option>`);
        });
    });
}

// Roles & Permissions Management
function loadRoles() {
    $.get(`${API_BASE}/roles`, function(roles) {
        const list = $('#rolesList');
        list.empty();

        roles.forEach(role => {
            list.append(`
                <a href="#" class="list-group-item list-group-item-action" onclick="selectRole(${role.id}); return false;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-0">${role.role_name}</h6>
                            <small class="text-muted">${role.description || ''}</small>
                        </div>
                        ${!role.is_default ? `<button class="btn btn-sm btn-link" onclick="editRole(${role.id}); return false;"><i class="bi bi-pencil"></i></button>` : ''}
                    </div>
                </a>
            `);
        });
    });
}

function loadPermissions() {
    $.get(`${API_BASE}/permissions`, function(permissions) {
        allPermissions = permissions;
    });
}

function selectRole(roleId) {
    currentRoleId = roleId;
    
    $.get(`${API_BASE}/roles/${roleId}/permissions`, function(rolePermissions) {
        const rolePermIds = rolePermissions.map(p => p.id);
        
        // Group permissions by module
        const groupedPermissions = {};
        allPermissions.forEach(perm => {
            if (!groupedPermissions[perm.module]) {
                groupedPermissions[perm.module] = [];
            }
            groupedPermissions[perm.module].push(perm);
        });

        let html = '<form id="permissionsForm">';
        
        Object.keys(groupedPermissions).forEach(module => {
            html += `<div class="permission-group">
                <h6>${module}</h6>`;
            
            groupedPermissions[module].forEach(perm => {
                const checked = rolePermIds.includes(perm.id) ? 'checked' : '';
                html += `
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" value="${perm.id}" ${checked} id="perm_${perm.id}">
                        <label class="form-check-label" for="perm_${perm.id}">
                            ${perm.description || perm.permission_name}
                        </label>
                    </div>
                `;
            });
            
            html += '</div>';
        });

        html += `<button type="button" class="btn btn-primary" onclick="savePermissions()">
            <i class="bi bi-save"></i> Save Permissions
        </button></form>`;

        $('#permissionsPanel').html(html);
    });
}

function savePermissions() {
    const selectedPermissions = [];
    $('#permissionsForm input:checked').each(function() {
        selectedPermissions.push(parseInt($(this).val()));
    });

    $.ajax({
        url: `${API_BASE}/roles/${currentRoleId}/permissions`,
        method: 'PUT',
        contentType: 'application/json',
        data: JSON.stringify({ permission_ids: selectedPermissions }),
        success: function() {
            alert('Permissions updated successfully');
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to update permissions'));
        }
    });
}

function showAddRoleModal() {
    $('#roleModal').find('.modal-title').text('Add Role');
    $('#roleName').val('');
    $('#roleDescription').val('');
    
    const modal = new bootstrap.Modal($('#roleModal'));
    modal.show();
}

function saveRole() {
    const data = {
        role_name: $('#roleName').val(),
        description: $('#roleDescription').val()
    };

    $.ajax({
        url: `${API_BASE}/roles`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function() {
            bootstrap.Modal.getInstance($('#roleModal')).hide();
            loadRoles();
            alert('Role created successfully');
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to create role'));
        }
    });
}

// Audit Logs
function loadAuditLogs(page = 1) {
    const params = {
        page: page,
        per_page: 20,
        start_date: $('#auditStartDate').val(),
        end_date: $('#auditEndDate').val(),
        action_type: $('#auditActionType').val()
    };

    $.get(`${API_BASE}/audit-logs`, params, function(response) {
        const list = $('#auditLogsList');
        list.empty();

        if (response.logs.length === 0) {
            list.html('<p class="text-muted">No audit logs found</p>');
            return;
        }

        response.logs.forEach(log => {
            const date = new Date(log.created_at).toLocaleString();
            list.append(`
                <div class="audit-log-entry">
                    <div class="d-flex justify-content-between">
                        <strong>${log.action_type}</strong>
                        <small class="text-muted">${date}</small>
                    </div>
                    <div>${log.description}</div>
                    <small class="text-muted">
                        User: ${log.username || 'Unknown'} | IP: ${log.ip_address || '-'}
                    </small>
                </div>
            `);
        });

        // Pagination
        if (response.pages > 1) {
            let pagination = '<ul class="pagination">';
            for (let i = 1; i <= response.pages; i++) {
                pagination += `<li class="page-item ${i === page ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="loadAuditLogs(${i}); return false;">${i}</a>
                </li>`;
            }
            pagination += '</ul>';
            $('#auditPagination').html(pagination);
        }
    });
}
